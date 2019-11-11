#!/bin/bash
#
# Called in Dockerfile, enabling `setup-chroots.sh` later.
#
# Documentation is in setup-chroots.sh.
#
# We run this in the Dockerfile so we don't need to run it during startup. It
# takes a few seconds.
set -e

LAYERS=/var/lib/cjwkernel/chroot-layers

create_chroot_layer()
{
  # Usage: create_chroot_layer CHROOT_DIR REALDIR1 REALDIR2 REALDIR3....
  #
  # We can't bind-mount to create the chroot layer, because overlayfs will
  # only show the mountpoints, not the files mounted within them. So let's
  # hard-link every file under the sun.
  #
  # This is acceptable because:
  #
  # A. All actual files are protected from writes by overlayfs (it's safe)
  # B. We only copy once (it's fast enough)
  # C. We don't edit these files (it's correct)
  #
  # In some cases (e.g., dev's virtualenvs volume), hard-linking isn't allowed.
  # Copy in that case.
  layer="$1"
  shift
  mkdir -p "$layer"
  for src in "$@"; do
    dest="$layer""$src"
    echo "Preparing $dest..."
    mkdir -p "$(dirname "$dest")"
    # -d: copy symlinks as-is
    # -r: recurse (copying directory tree)
    # -l: hard-link instead of copying data (saves space)
    cp -drl "$src" "$dest"
  done
}

create_chroot_layer $LAYERS/base \
  /bin \
  /lib \
  /lib64 \
  /usr/share/nltk_data \
  /usr/bin \
  /usr/lib \
  /usr/local/lib \
  /etc/ld.so.cache \
  /etc/ssl \
  /usr/share/ca-certificates \
  /etc/nsswitch.conf
for tempdir in $LAYERS/base/tmp $LAYERS/base/var/tmp; do
  # Create empty tempdirs. If callers or modules write files, these directories
  # will be mirrored in the upper layer.
  mkdir -p $tempdir
  chmod 1777 $tempdir
done
# /app/cjworkbench/cjwkernel we handle in setup-chroots.sh
