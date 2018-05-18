from allauth.account.models import EmailAddress
from typing import Tuple

from server.models import User
from integrationtests.browser import Browser

def login(browser: Browser, email: str, password: str) -> None:
    """Logs in through `/account/login` to the given URL.
    """
    browser.visit('/account/login')
    browser.fill_in('login', email)
    browser.fill_in('password', password)
    browser.click_button('Sign In')
    browser.wait_for_element('h3', text='WORKFLOWS', wait=200)


class AccountAdmin:
    """Provides an interface for the caller to create/delete users.

    Example usage:

        import integrationtests.helpers.accounts
        account_admin = accounts.AccountAdmin()

        user = account_admin.create_user('user@example.org')
        user_email = account_admin.verify_user_email(user)

        # ...test things...
        # e.g., `accounts.login(browser, user.email, user.email); ...`

        account_admin.destroy_user_email(user_email)
        account_admin.destroy_user(user)
    """
    # [adam, 2018-05-18] this is a class because I expect we'll someday want to
    # handle user admin externally instead of through global variables.

    def create_user(self, email: str, username: str=None, password: str=None) -> User:
        """Adds the specified user to the database.

        When done with the User, `account_admin.destroy_user(user)`

        Keyword arguments:
        username -- string (default user portion of email)
        password -- string (default email)
        """
        if username is None: username = email.split('@')[0]
        if password is None: password = email
        return User.objects.create_user(username=username, email=email,
                                        password=password)


    def destroy_user(self, user: User) -> None:
        """Cleans up the return value of create_user().
        """
        # This isn't just `email.destroy` because we may migrate away from
        # global variables one day, meaning this wouldn't be a django model.
        user.delete()


    def verify_user_email(self, user: User) -> EmailAddress:
        """Verifies a user's email address.

        When done with the EmailAddress, `account_admin.destroy_email(email)`.

        The user can't log in until the email address is verified.
        """
        return EmailAddress.objects.create(user=user, email=user.email,
                                           primary=True, verified=True)


    def destroy_user_email(self, email: EmailAddress) -> None:
        """Cleans up the return value of verify_user_email().
        """
        # This isn't just `email.destroy` because we may migrate away from
        # global variables one day, meaning this wouldn't be a django model.
        email.delete()
