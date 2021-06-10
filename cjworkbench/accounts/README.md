# TESTING

## Setting up for these tests

You'll want to have one "admin" account and lots of disposable user accounts. Each test means creating a user account; after you're done the test, use "admin" to delete it.

Open a "secondary" web browser -- Firefox maybe, or an Incognito-mode tab -- to https://app.workbenchdata.com/admin => users.

Also delete the user in Intercom.

## The test suite

All these tests start logged out

### Google signup, with newsletter

1. Go to "Sign in" (you could go "Sign up", but the effect is the same); click "Google"; sign in as a non-existent account
2. When prompted (new!), click the "Subscribe" button
3. Check that the user is subscribed in Intercom

### Google signup, no newsletter

1. Go to "Sign in"; click "Google"; sign in as a non-existent account
2. When prompted (new!), click the "Don't subscribe" button
3. Check that the user is unsubscribed in Intercom

### Existing Google user

1. Go to "Sign in"; click "Google"; sign in as an existing account
2. Confirm that there is no newsletter prompt

### Email signin

1. Go to "Sign up"; enter info with a new email address; uncheck the "Subscribe" checkbox
2. Confirm that the user _does not exist_ in Intercom
3. Open the email and click the confirmation link
4. Confirm that the user is "unsubscribed" in Intercom
