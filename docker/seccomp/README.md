System for building our seccomp BPF filter.

Why not use libseccomp in Python? Because Python libseccomp bindings aren't on
PyPI, and [adamhooper, 2019-11-07] I don't want to fiddle with building....

Usage:

1. Examine the list in `allowed-syscalls.txt` and see that it is good
2. Run `./run-with-docker.sh` to overwrite `rules.bpf`
3. Use the resulting BPF struct as a syscall -- you can just pass the
   bytes as a void*. (We copy it to
   `cjwkernel/forkserver/sandbox-seccomp.bpf`)
