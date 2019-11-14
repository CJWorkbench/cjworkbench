#!/bin/bash
#
# Called by cjwkernel (in dev/unittest/integration-test) or an init container
# (in staging/prodution) to create chroot environments for forkserver. It's
# just called once, on container start.
#
# This requires CAP_SYS_ADMIN privilege, and seccomp must allow the "mount"
# system call. DO NOT give CAP_SYS_ADMIN willy-nilly. We use it and then drop
# it in dev/unittest/integration-test. In production, we run this in a
# privileged init container, so the regular fetcher/worker/frontend container
# can run without extra privileges.
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
#       * upper/ (empty: where mounts and edits from caller+module go)
#       * work/ (for overlayfs -- do not read/modify)
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
# To undo everything this script does:
#
#     rm -rf /var/lib/cjwkernel/chroot-layers/base/app
#     for path in $(mount | grep /var/lib/cjwkernel/chroot | cut -d' ' -f1 | sort -r); do umount -f $path; done
#     rm -rf /var/lib/cjwkernel/chroot/*

set -e

CHROOT=/var/lib/cjwkernel/chroot
LAYERS=/var/lib/cjwkernel/chroot-layers
VENV_PATH="/root/.local/share/virtualenvs" # only exits in dev

# /app/cjwkernel (base layer)
rm -rf $LAYERS/base/app # in case we're re-running this script
mkdir -p $LAYERS/base/app
cp -a /app/cjwkernel $LAYERS/base/app/cjwkernel

# Create directories on the chroots filesystem (not the root filesystem)
mkdir -p \
  $CHROOT/editable/upperfs/upper \
  $CHROOT/editable/upperfs/work \
  $CHROOT/editable/root \
  $CHROOT/readonly/upper \
  $CHROOT/readonly/work \
  $CHROOT/readonly/root \

# Overlay!
mount -t overlay overlay -o dirsync,lowerdir=$LAYERS/base,upperdir=$CHROOT/editable/upperfs/upper,workdir=$CHROOT/editable/upperfs/work $CHROOT/editable/root
mount -t overlay overlay -o dirsync,lowerdir=$LAYERS/base,upperdir=$CHROOT/readonly/upper,workdir=$CHROOT/readonly/work $CHROOT/readonly/root

# Bind-mount /root/.local/share/virtualenvs in dev mode. (On production, the
# Python environment is different and packages are installed in
# /usr/local/lib/python3.7/site-packages, baked into the Docker image, so this
# step isn't needed.)
#
# We set up a mount per chroot.
if test -d "$VENV_PATH"; then
  for chroot in editable "readonly"; do
    mountpoint="$CHROOT/$chroot/root$VENV_PATH"
    mkdir -p "$mountpoint"
    mount --bind "$VENV_PATH" "$mountpoint"
    #mount -o remount,ro "$mountpoint"
  done
fi

# Make readonly readonly (now that we don't need to mount on it any more)
mount -o remount,ro "$CHROOT/readonly/root"
