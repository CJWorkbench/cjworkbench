#!/bin/bash
#
# Called before Workbench start (in dev/unittest/integration-test) or by an
# init container (in staging/production) to create sandbox environments for
# forkserver. It's called just once per container.
#
# This requires CAP_SYS_ADMIN privilege, and seccomp must allow the "mount"
# system call. DO NOT grant CAP_SYS_ADMIN willy-nilly in production. In
# production, we run this in a privileged init container, so the regular
# fetcher/worker/frontend container can run without extra privileges. This
# is a source of frustration: integration-test runs privileged but staging
# and production don't. If you're messing with sandboxes, test on staging.
#
# This is _one_ chroot environment, suitable for _one_ command. Assume
# forkserver never runs two commands at once.
#
# We use overlay mounts:
#
# * The "base" layer holds all we need to run most modules -- Python
#   site-packages, /bin, /lib, /usr/bin, etc. (read-only to everybody).
#   /tmp and /var/tmp exist and are empty.
# * The "upper" layer holds module input/output (input is world-readable;
#   output is world-writable). Modules can write anywhere they have
#   permission -- for instance, /var/tmp or /tmp; if the files/dirs therein
#   have a high-UID owner, they are recognized as module-written tempfiles.
#
# All these are in /var/lib/cjwkernel/:
#
# * /var/lib/cjwkernel/
#   * chroot-layers/ (on container's root filesystem)
#     * base/
#       * lib/
#       * lib64/
#       * tmp/ (empty folder)
#       * var/tmp/ (empty folder)
#       * ...
#   * chroot/ (on a separate filesystem)
#     * editable/ (a singleton)
#       * upperfs.ext4 (a 20GB sparse file with ext4 filesystem)
#       * upperfs/ (upperfs.ext4, loopback-mounted)
#         * upper/ (empty: where mounts and edits from caller+module go)
#         * work/ (for overlayfs -- do not read/modify)
#       * root/ (overlay dev volumes + layers/base + upper)
#     * readonly/
#       * upper/ (do not modify -- contains mountpoints)
#       * work/ (for overlayfs -- do not read/modify)
#       * root/ (overlay dev volumes + layers/base + upper)
#
# We special-case some paths because they're treated differently in
# dev/unittest than in production/integration-test:
#
# * /app/cjworkbench/cjwkernel: we "cp -a" this into chroot-layers/base. In
#   dev mode, Docker points this directory to the host. "cp -a" may not be
#   ideal, but it's fast enough (the directory is tiny); and the benefit is,
#   we get the same logic on dev and production.
# * /root/.local/share/virtualenvs: this only exists in dev. We bind-mount
#   it into each chroot. (We can't bind-mount before overlay-mount: overlayfs
#   would only display the mountpoint, not the mounted filesystem.)
#
# DEVELOPING
#
# If you're iterating on this script, running it multiple times in the same
# environment, call `teardown-sandboxes.sh` to reset.

set -e

MODE="$1"
if [ "$MODE" != only-readonly ] && [ "$MODE" != "all" ]; then
  echo "Usage: $0 only-readonly|all" >&2
  exit 1
fi

CHROOT=/var/lib/cjwkernel/chroot
LAYERS=/var/lib/cjwkernel/chroot-layers
EDITABLE_CHROOT_SIZE=20G  # max size of user edits in EDITABLE_CHROOT
VENV_PATH="/root/.local/share/virtualenvs" # only exits in dev

# NetworkConfig mimics cjwkernel/forkserver/protocol.py
KERNEL_VETH=cjw-veth-kernel
CHILD_VETH_IP4="192.168.123.2"


# /app/cjwkernel (base layer)
# We copy the dir at runtime, not build time, because that's compatible with
# both dev and production.
mkdir -p $LAYERS/base/app
cp -a /app/cjwkernel $LAYERS/base/app/cjwkernel


# READONLY_CHROOT
mkdir -p $CHROOT/readonly/{upper,work,root}
mount -t overlay overlay -o dirsync,lowerdir=$LAYERS/base,upperdir=$CHROOT/readonly/upper,workdir=$CHROOT/readonly/work $CHROOT/readonly/root
# Bind-mount /root/.local/share/virtualenvs in dev mode. (On production, the
# Python environment is different and packages are installed in
# /usr/local/lib/python3.7/site-packages, baked into the Docker image, so this
# step isn't needed.)
#
# We set up a mount per chroot.
if test -d "$VENV_PATH"; then
  mountpoint="$CHROOT/readonly/root$VENV_PATH"
  mkdir -p "$mountpoint"
  mount --bind "$VENV_PATH" "$mountpoint"
fi
# Make readonly readonly (now that we don't need to mount on it any more)
mount -o remount,ro "$CHROOT/readonly/root"


# Only fetcher|renderer need EDITABLE_CHROOT and networking. If we aren't
# fetcher|renderer, return.
if [ "$MODE" = "only-readonly" ]; then
  exit 0
fi


# EDITABLE_CHROOT
# Build upperfs.ext4 and mount it
# What's upperfs.ext4? It's a space-limited filesystem. If users write data
# larger than $EDITABLE_CHROOT_SIZE to the chroot filesystem, they'll get
# "out of disk space" errors. We build a sparse file (`truncate`) to make this
# script super-fast on producion. (We don't care much about FS speed. The
# intended use case is large tempfiles and no fsync. When files grow beyond
# the Linux I/O cache size, users should expect slowdowns.)
mkdir -p $CHROOT/editable/upperfs
truncate --size=$EDITABLE_CHROOT_SIZE $CHROOT/editable/upperfs.ext4  # create sparse file
mkfs.ext4 -q -O ^has_journal $CHROOT/editable/upperfs.ext4
if ! mount -o loop $CHROOT/editable/upperfs.ext4 $CHROOT/editable/upperfs; then
  # Docker without --privileged doesn't provide a loopback device. This affects
  # dev mode (which we don't care about). But it should never happen on production.
  echo "******* WARNING: failed to mount loopback filesystem $CHROOT/editable/upperfs *****" >&2
  echo "Workbench will not constrain modules' disk usage. If a module writes" >&2
  echo "too much to disk, Workbench will experience undefined behavior." >&2
fi
# Build overlay filesystem, with upper layer on upperfs
mkdir -p $CHROOT/editable/upperfs/{upper,work}
mkdir -p $CHROOT/editable/root
mount -t overlay overlay -o dirsync,lowerdir=$LAYERS/base,upperdir=$CHROOT/editable/upperfs/upper,workdir=$CHROOT/editable/upperfs/work $CHROOT/editable/root


# iptables
# "ip route get 1.1.1.1" will display the default route. It looks like:
#     1.1.1.1 via 192.168.86.1 dev wlp2s0 src 192.168.86.70 uid 1000
# Grep for the "src x.x.x.x" part and store the "x.x.x.x"
ipv4_snat_source=$(ip route get 1.1.1.1 | grep -oe "src [^ ]\+" | cut -d' ' -f2)
cat << EOF | iptables-legacy-restore --noflush
*filter
:INPUT ACCEPT
:FORWARD DROP
# Block access to the host itself from a module.
-A INPUT -i $KERNEL_VETH -j REJECT
# Allow forwarding response packets back to our module (even
# though our module's IP is in UNSAFE_IPV4_ADDRESS_BLOCKS).
-A FORWARD -o $KERNEL_VETH -j ACCEPT
# Block unsafe destination addresses. Modules should not be
# able to access internal services. (Not even our DNS server.)
-A FORWARD -d 0.0.0.0/8          -i $KERNEL_VETH -j REJECT
-A FORWARD -d 10.0.0.0/8         -i $KERNEL_VETH -j REJECT
-A FORWARD -d 100.64.0.0/10      -i $KERNEL_VETH -j REJECT
-A FORWARD -d 127.0.0.0/8        -i $KERNEL_VETH -j REJECT
-A FORWARD -d 169.254.0.0/16     -i $KERNEL_VETH -j REJECT
-A FORWARD -d 172.16.0.0/12      -i $KERNEL_VETH -j REJECT
-A FORWARD -d 192.0.0.0/24       -i $KERNEL_VETH -j REJECT
-A FORWARD -d 192.0.2.0/24       -i $KERNEL_VETH -j REJECT
-A FORWARD -d 192.88.99.0/24     -i $KERNEL_VETH -j REJECT
-A FORWARD -d 192.168.0.0/16     -i $KERNEL_VETH -j REJECT
-A FORWARD -d 198.18.0.0/15      -i $KERNEL_VETH -j REJECT
-A FORWARD -d 198.51.100.0/24    -i $KERNEL_VETH -j REJECT
-A FORWARD -d 203.0.113.0/24     -i $KERNEL_VETH -j REJECT
-A FORWARD -d 224.0.0.0/4        -i $KERNEL_VETH -j REJECT
-A FORWARD -d 240.0.0.0/4        -i $KERNEL_VETH -j REJECT
-A FORWARD -d 255.255.255.255/32 -i $KERNEL_VETH -j REJECT
# Allow forwarding exactly the source address of the module.
# Don't forward just any address (i.e. don't set policy
# ACCEPT): if a module somehow gains CAP_NET_ADMIN (which
# shouldn't happen) it should not be able to spoof source
# addresses.
-A FORWARD -i $KERNEL_VETH -s $CHILD_VETH_IP4 -j ACCEPT
COMMIT
*nat
:POSTROUTING ACCEPT
-A POSTROUTING -s $CHILD_VETH_IP4 -j SNAT --to-source $ipv4_snat_source
COMMIT
EOF
