import binascii
import email
import email.message
import hashlib
import os
import shutil
from typing import Optional
from urllib.error import HTTPError
from urllib.request import urlopen
import weakref
import psycopg2
from integrationtests.browser import Browser


EmailPath = '/app/local_mail'


def login(browser: Browser, email: str, password: str) -> None:
    """Log in through `/account/login` as the given user."""
    browser.visit('/account/login')
    browser.fill_in('login', email)
    browser.fill_in('password', password)
    browser.click_button('Sign In')
    browser.wait_for_element('a', text='MY WORKFLOWS', wait=True)


def _close_connection(conn):
    """Close the given subprocess which is a Python shell.
    """
    conn.close()


class UserHandle:
    def __init__(self, username: str, password: str, email: str):
        self.username = username
        self.password = password
        self.email = email


class EmailAddressHandle:
    def __init__(self, var: str):
        self._var = var


class AccountAdmin:
    """
    An interface to inject data into Workbench without a web browser.

    Example usage:

        import integrationtests.helpers.accounts
        account_admin = accounts.AccountAdmin()

        user = account_admin.create_user('user@example.org')

        # ...test things...
        # e.g., `accounts.login(browser, user.email, user.email); ...`
    """

    def __init__(self, live_server_url: str, db_connect_str: str,
                 data_path: str):
        """
        Connect to services.

        Rather than log in using the web admin interface, we connect to
        frontend's SQL server and Docker volume. This is a hack.
        """
        self.live_server_url = live_server_url
        self.data_path = data_path
        self.conn = psycopg2.connect(db_connect_str)
        self.conn.autocommit = True

        self._finalizer = weakref.finalize(
            self,
            _close_connection,
            self.conn
        )

        self.clear_data_from_previous_tests()

    def _sql(self, sql: str, **kwargs) -> None:
        """Execute SQL query."""
        with self.conn.cursor() as cursor:
            cursor.execute(sql, kwargs)

    def clear_data_from_previous_tests(self):
        """Delete all accounts and related data."""
        _Tables = [
            'server_aclentry',
            'server_addmodulecommand',
            'server_changedataversioncommand',
            'server_changeparameterscommand',
            'server_changewfmodulenotescommand',
            'server_changewfmoduleupdatesettingscommand',
            'server_changeworkflowtitlecommand',
            'server_deletemodulecommand',
            'server_initworkflowcommand',
            'server_delta',
            'server_parameterval',
            'server_reordermodulescommand',
            'server_storedobject',
            'server_uploadedfile',
            'server_wfmodule',
            'server_workflow',
            'django_session',
            'account_emailconfirmation',
            'account_emailaddress',
            'auth_group',
            'auth_group_permissions',
            'auth_permission',
            'cjworkbench_userprofile',
            'django_admin_log',
            'auth_user',
            'auth_user_groups',
            'auth_user_user_permissions',
        ]
        _clear_db_sql = f"""
            WITH
            f{', '.join([f't{i} AS (DELETE FROM {table})' for i, table in enumerate(_Tables)])},
            dps AS (
                DELETE FROM server_parameterspec
                WHERE module_version_id NOT IN (
                    SELECT id FROM server_moduleversion
                    WHERE source_version_hash = '1.0'
                )
            ),
            dmv AS (
                DELETE FROM server_moduleversion
                WHERE source_version_hash <> '1.0'
            ),
            dm AS (DELETE FROM server_module WHERE author <> 'Workbench')
            SELECT 1
        """
        self._sql(_clear_db_sql)

        for subdir in ['importedmodules', 'saveddata']:
            path = os.path.join(self.data_path, subdir)
            for subbasename in os.listdir(path):
                subpath = os.path.join(path, subbasename)
                if os.path.isfile(subpath):
                    os.unlink(subpath)
                else:
                    shutil.rmtree(subpath)

    def create_user(self, email: str, username: str=None,
                    password: str=None, is_staff: bool=False,
                    is_superuser: bool=False) -> UserHandle:
        """Add the specified user to the database, with email confirmed.

        Keyword arguments:
        username -- string (default user portion of email)
        password -- string (default email)
        is_staff -- bool (default False)
        is_superuser -- bool (default False)
        """
        if not username:
            username = email.split('@')[0]
        if not password:
            password = email

        hmac = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                   b'salt', 1)
        hmac_base64 = binascii.b2a_base64(hmac, newline=False)

        password_hash = '$'.join(['pbkdf2_sha256', '1', 'salt',
                                  hmac_base64.decode('ascii')])

        self._sql(
            """
                WITH u AS (
                    INSERT INTO auth_user (
                        first_name, last_name, is_active, date_joined,
                        email, username, password, is_staff, is_superuser
                    )
                    VALUES (
                        'First', 'Last', TRUE, NOW(),
                        %(email)s, %(username)s, %(password_hash)s,
                        %(is_staff)s, %(is_superuser)s
                    )
                    RETURNING id, email
                )
                INSERT INTO account_emailaddress (
                    verified, "primary", user_id, email
                )
                SELECT TRUE, TRUE, u.id, u.email
                FROM u
            """,
            email=email,
            username=username,
            password_hash=password_hash,
            is_staff=is_staff,
            is_superuser=is_superuser
        )

        return UserHandle(username, password, email)

    @property
    def latest_sent_email(self) -> Optional[email.message.Message]:
        """The last sent email, or None."""
        filenames = os.listdir(EmailPath)

        if not filenames:
            return None

        filenames.sort()
        with open(os.path.join(EmailPath, filenames[-1]), 'rb') as f:
            return email.message_from_bytes(f.read())
