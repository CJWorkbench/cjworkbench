Stress-testing Workbench
========================

This directory uses [Artillery](https://artillery.io/) to send an HTTP server
a bunch of HTTP requests that are similar to those we'd experience if a bunch
of people all did something in their web browsers.

Running "Demo" on Staging
-------------------------

1. `npm install` in this directory
1. Create a "Public" and "Example" workflow on staging: "Add from URL" ->
   "Filter" -> "Sort" -> "Column Chart". Remember its ID (here, it's `12345`).
1. `time npm test -- run demo/demo.yml -e staging -v '{ "DemoWorkflowId": 12345 }'`

Tweak `demo/demo.yml` to set the number of users and frequency. Learn from
[Artillery docs](https://artillery.io/docs/) to edit more fully.

Running "Demo" on Dev
---------------------

1. `bin/dev start` one directory up from here. While that's running:
1. Try to register a user, until asked for email confirmation
1. Hack the database to make the user admin:
   `bin/dev exec database psql -Ucjworkbench` -> 
   `UPDATE auth_user SET is_superuser = TRUE, is_active = TRUE, is_staff = TRUE`;
   `UPDATE account_emailaddress SET verified = TRUE` (and Ctrl+D to exit)
1. Create a "Public" and "Example" workflow on staging: "Add from URL" ->
   "Filter" -> "Sort" -> "Column Chart". Remember its ID (here, it's `12345`).
1. `time npm test -- run demo/demo.yml -e dev -v '{ "DemoWorkflowId": 12345 }'`

Dev behaves differently from staging, but it's useful if you want to test how
a change to Workbench affects performance:

1. Run the `time npm test` command to find out how slow old code is
1. Edit code
1. Ctrl+C to kill `./start-dev.sh` but leave the database online. Re-run the
   second half of that file (starting with `docker build`).
1. Run the `time npm test` command to find out how slow new code is
