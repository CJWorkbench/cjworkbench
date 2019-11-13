import binascii
import email
import email.message
import hashlib
import minio
import os
from typing import Optional
import weakref
import psycopg2
from integrationtests.browser import Browser


EmailPath = "/app/local_mail"


def _minio_connect():
    try:
        return _minio_connect._connection
    except AttributeError:
        protocol, _unused, endpoint = os.environ["MINIO_URL"].split("/")
        mc = minio.Minio(
            endpoint,
            access_key=os.environ["MINIO_ACCESS_KEY"],
            secret_key=os.environ["MINIO_SECRET_KEY"],
            secure=(protocol == "https:"),
        )
        _minio_connect._connection = mc
        return mc


def _clear_minio():
    mc = _minio_connect()

    for bucket_name in (
        "user-files",
        "stored-objects",
        "external-modules",
        "cached-render-results",
    ):
        bucket = f"integrationtest-{bucket_name}"
        keys = [
            o.object_name
            for o in mc.list_objects_v2(bucket, "", recursive=True)
            if not o.is_dir
        ]
        if keys:
            for err in mc.remove_objects(bucket, keys):
                raise err


def login(browser: Browser, email: str, password: str) -> None:
    """Log in through `/account/login` as the given user."""
    browser.visit("/account/login")
    browser.fill_in("login", email)
    browser.fill_in("password", password)
    browser.click_button("Sign In")
    browser.wait_for_element("a", text="MY WORKFLOWS", wait=True)


def logout(browser: Browser) -> None:
    """Log out through `/account/logout` as the given user."""
    browser.visit("/account/logout")
    browser.click_button("Log out")


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

    def __init__(self, live_server_url: str, db_connect_str: str, data_path: str):
        """
        Connect to services.

        Rather than log in using the web admin interface, we connect to
        frontend's SQL server and Docker volume. This is a hack.
        """
        self.live_server_url = live_server_url
        self.data_path = data_path
        self.conn = psycopg2.connect(db_connect_str)
        self.conn.autocommit = True

        self._finalizer = weakref.finalize(self, _close_connection, self.conn)

        self.clear_data_from_previous_tests()

    def _sql(self, sql: str, **kwargs) -> None:
        """Execute SQL query."""
        with self.conn.cursor() as cursor:
            cursor.execute(sql, kwargs)

    def clear_data_from_previous_tests(self):
        """Delete all accounts and related data."""
        _Tables = [
            "server_aclentry",
            "server_addmodulecommand",
            "server_addtabcommand",
            "server_changedataversioncommand",
            "server_changeparameterscommand",
            "server_changewfmodulenotescommand",
            "server_changeworkflowtitlecommand",
            "server_deletemodulecommand",
            "server_deletetabcommand",
            "server_duplicatetabcommand",
            "server_reordermodulescommand",
            "server_reordertabscommand",
            "server_settabnamecommand",
            "server_initworkflowcommand",
            "server_delta",
            "server_storedobject",
            "server_uploadedfile",
            "server_inprogressupload",
            "server_wfmodule",
            "server_tab",
            "server_workflow",
            "django_session",
            "account_emailconfirmation",
            "account_emailaddress",
            "auth_group",
            "auth_group_permissions",
            "auth_permission",
            "cjworkbench_userprofile",
            "django_admin_log",
            "auth_user",
            "auth_user_groups",
            "auth_user_user_permissions",
        ]
        _clear_db_sql = f"""
            WITH
            f{', '.join([f't{i} AS (DELETE FROM {table})' for i, table in enumerate(_Tables)])},
            dmv AS (
                DELETE FROM server_moduleversion
                WHERE source_version_hash <> '1.0'
            )
            SELECT 1
        """
        self._sql(_clear_db_sql)

        _clear_minio()

    def create_user(
        self,
        email: str,
        username: str = None,
        password: str = None,
        *,
        first_name: str = "First",
        last_name: str = "Last",
        is_staff: bool = False,
        is_superuser: bool = False,
    ) -> UserHandle:
        """Add the specified user to the database, with email confirmed.

        Keyword arguments:
        username -- string (default user portion of email)
        password -- string (default email)
        is_staff -- bool (default False)
        is_superuser -- bool (default False)
        """
        if not username:
            username = email.split("@")[0]
        if not password:
            password = email

        hmac = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), b"salt", 1)
        hmac_base64 = binascii.b2a_base64(hmac, newline=False)

        password_hash = "$".join(
            ["pbkdf2_sha256", "1", "salt", hmac_base64.decode("ascii")]
        )

        self._sql(
            """
                WITH u AS (
                    INSERT INTO auth_user (
                        first_name, last_name, is_active, date_joined,
                        email, username, password, is_staff, is_superuser
                    )
                    VALUES (
                        %(first_name)s, %(last_name)s, TRUE, NOW(),
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
            first_name=first_name,
            last_name=last_name,
            is_staff=is_staff,
            is_superuser=is_superuser,
        )

        return UserHandle(username, password, email)

    @property
    def latest_sent_email(self) -> Optional[email.message.Message]:
        """The last sent email, or None."""
        filenames = os.listdir(EmailPath)

        if not filenames:
            return None

        filenames.sort()
        with open(os.path.join(EmailPath, filenames[-1]), "rb") as f:
            return email.message_from_bytes(f.read())
