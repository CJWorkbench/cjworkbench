# DO NOT USE
#
# HACK: way back when, our Django models were declared in the "server" app.
# So that's where migrations are wired to find them.
#
# We moved state-modifying code into `cjwstate`, and that meant moving Django
# models to `cjwstate.models`. `cjwstate` isn't a Django app, so migrations
# won't happen there.
#
# Long-term, we're going to nix Django ORM (because Active Record is complex)
# and nix Django migrations (because they're hard to maintain).
#
# In the meantime, this import statement makes a "fake" `server.models`
# module for Django to find, with all the models in `cjwstate.models`.

from cjwstate.models import *  # DO NOT USE
