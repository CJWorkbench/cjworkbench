#!/bin/bash
#
# Called during preStop by a privileged container (in staging/prodution) to
# allow the pod to exit.
#
#     "any volume mounts created by Containers in Pods must be destroyed
#     (unmounted) by the Containers on termination"
#     -- https://kubernetes.io/docs/concepts/storage/volumes/#mount-propagation
#
# See `setup-sandboxes.sh`. All our mounts are beneath
# /var/lib/cjwkernel/chroot/.

set -e

CHROOT=/var/lib/cjwkernel/chroot

# Sort in reverse order: that way, a nested mount will be removed before its
# parent.
for path in $(mount | grep "on $CHROOT/" | cut -d" " -f3 | sort -r); do
	# unmount lazily. This may avoid a race in production: what happens if
  # we unmount before the app shuts down? Let the unmount succeed: assume that
  # we're running this script because the app _is_ shutting down. The exact
  # chronology isn't important. What's important is once the app and this
  # program have exited, there are no more mounts.
  umount --lazy --verbose $path
done
