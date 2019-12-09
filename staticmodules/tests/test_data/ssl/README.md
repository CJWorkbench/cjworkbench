Some tests use a fake HTTPS server. OAuth API doesn't allow plain HTTP.

For the fake HTTPS server, we use a special, "test" Python SSL contexts. The
pieces in play are:

* `ca` -- a fake root certificate authority
* `server` -- uses private key, with certificate signed by `ca`
* `client` -- trusts `ca`.

Regenerate certs with `./create-certs.sh`. We put this stuff on GitHub
because it takes ~0.1s to generate them, which is more than we want to
spend when we run unit tests.
