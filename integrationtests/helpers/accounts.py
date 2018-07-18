import email
import email.message
import os
import random
import select
import string
import subprocess
import termios
from typing import Optional
from urllib.error import HTTPError
from urllib.request import urlopen
import weakref

from integrationtests.browser import Browser


def login(browser: Browser, email: str, password: str) -> None:
    """Log in through `/account/login` as the given user."""
    browser.visit('/account/login')
    browser.fill_in('login', email)
    browser.fill_in('password', password)
    browser.click_button('Sign In')
    browser.wait_for_element('h3', text='WORKFLOWS', wait=True)


def _close_shell(shell, pty_master):
    """Close the given subprocess which is a Python shell.
    """
    os.close(pty_master)

    try:
        stdout, stderr = shell.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        shell.kill()
        stdout, stderr = shell.communicate()

    if stdout.strip() or stderr.strip():
        print(f"STDOUT (wanted empty): {stdout}")
        print(f"STDERR (wanted empty): {stderr}")


def _open_python_in_docker(pty_slave):
    return subprocess.Popen(
        [
            'docker', 'exec', '-it',
            '-e', 'CJW_PRODUCTION=True',
            '-e', 'CJW_DB_HOST=workbench-db',
            '-e', 'CJW_DB_PASSWORD=cjworkbench',
            'cjworkbench_integrationtest_django',
            'sh', '-c', ' '.join([
                # do not convert \n to \r\n
                # https://github.com/moby/moby/issues/8513
                'stty -onlcr -echo;',
                'echo "import sys; sys.ps1 = sys.ps2 = str()" >/tmp/pystart;',
                'chmod +x /tmp/pystart;',
                'PYTHONSTARTUP=/tmp/pystart',
                'python',  # not ./manage.py shell, because it isn't quiet
                '-q',  # no copyright
            ])
        ],
        stdin=pty_slave,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,  # no buffer on subprocess stdin/stdout/stderr
        universal_newlines=False
    )


def _open_python_no_docker(pty_slave):
    with open('/tmp/pystart', 'w') as f:
        f.write('import sys; sys.ps1 = sys.ps2 = str()')
    os.chmod('/tmp/pystart', 0o755)

    env = dict(os.environ)
    env['PYTHONSTARTUP'] = '/tmp/pystart'

    return subprocess.Popen(
        [
            'sh',
            '-c',
            'stty -onlcr -echo; python -q -u',
        ],
        env=env,
        stdin=pty_slave,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,  # no buffer on subprocess stdin/stdout/stderr
        universal_newlines=False
    )


def _open_python_manage_shell(pty_slave):
    """Open a subprocess controlling a Python shell.

    You should close pty_slave after calling this method; thereafter, reading
    or writing on pty_master will communicate with a Python interactive shell.

    There are two modes this function can run in: within Docker and
    outside Docker. Within Docker, the `docker` executable does not exist, so
    we invoke `python` directly and assume the project code is in the current
    working directory. Outside docker, the `docker` executable does exist, so
    we invoke `python` within a `docker exec` on the
    `cjworkbench_integrationtest_django` container, which we assume is running.
    """

    try:
        return _open_python_in_docker(pty_slave)
    except FileNotFoundError:
        return _open_python_no_docker(pty_slave)


class UserHandle:
    def __init__(self, var: str, username: str, password: str, email: str):
        self._var = var
        self.username = username
        self.password = password
        self.email = email


class EmailAddressHandle:
    def __init__(self, var: str):
        self._var = var


class AccountAdmin:
    """An interface for the caller to create/delete users.

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
    def __init__(self, live_server_url):
        """Open a Django shell, using Docker.

        Rather than log in using the web admin interface, we log in using the
        commandline. This is a hack, with consequences:

        - We're write-only.
        - Any output from the subprocess that isn't "_ok" is an error.

        Call _execute() to run a Python command in the subprocess.
        """
        self.live_server_url = live_server_url

        (self.pty_master, pty_slave) = os.openpty()
        self.shell = _open_python_manage_shell(pty_slave)
        os.close(pty_slave)  # the child process owns it now

        self._finalizer = weakref.finalize(
            self,
            _close_shell,
            self.shell,
            self.pty_master
        )

        self._execute('\n'.join([
            'import os',
            'import django',
            'import shutil',
            '_ = os.environ.setdefault(',
            "    'DJANGO_SETTINGS_MODULE', 'cjworkbench.settings'",
            ')',
            'django.setup()',
            'from allauth.account.models import EmailAddress',
            'from cjworkbench.models.Profile import UserProfile',
            'from server.models import User, ModuleVersion, Module, Workflow',
            'from server import dynamicdispatch',
        ]))
        self.clear_data_from_previous_tests()

    def clear_data_from_previous_tests(self):
        """Delete all accounts and related data."""
        self._execute('\n'.join([
            '_ = EmailAddress.objects.all().delete()',
            '_ = UserProfile.objects.all().delete()',
            '_ = User.objects.all().delete()',
            '_ = Workflow.objects.all().delete()',
        ]))
        self.destroy_modules()

    def _ensure_empty_stdout_and_stderr(self) -> None:
        """Raise RuntimeError if self.shell wrote to stdout or stderr."""
        r, _, _ = select.select(
            [self.shell.stdout, self.shell.stderr],
            [],
            [],
            0.05
        )
        if r:
            raise RuntimeError(
                f'Unexpected data on stdout or stderr: {r[0].read(1024)}'
            )

    def _execute(self, code: str, timeout: float=10) -> None:
        """Run the given Python code.

        To make sure the code returns, we do the following:

        1. Send the code to stdin, followed by \n
        2. Send a separate line: print('_ok')\n
        3. Read back the '_ok\n' on stdout

        This strategy lets us write _blocks_ of code (since the un-indented
        print() comes after, Python knows the block is closed). But if the code
        outputs any messages, that's an error.

        Keyword arguments:
        timeout -- Number of seconds to wait for _ok before throwing
        """
        self._ensure_empty_stdout_and_stderr()

        message = f"{code}\nprint('_ok')\n".encode('utf-8')
        os.write(self.pty_master, message)
        termios.tcdrain(self.pty_master)
        r, _, _ = select.select(
            [self.shell.stdout, self.shell.stderr],
            [],
            [],
            timeout
        )
        b = b''
        if r == [self.shell.stdout]:
            b = r[0].read(4)
            if b == b"_ok\n":
                return  # we're done!
            raise RuntimeError(
                f'Expected b"_ok\\n"; got: {b}\nCode was:\n{code}'
            )
        else:
            if not r:
                raise RuntimeError(f'Timeout running code:\n{code}')
            else:
                raise RuntimeError('\n'.join([
                    'Python wrote to stderr while executing code:',
                    code,
                    'STDERR:',
                    str(r[0].read(1024)),
                ]))

    def _execute_setvar(self, code: str, timeout: float=5) -> str:
        """Execute code, replacing 'VAR = ' with a random variable name.

        Call this to set a variable. For instance:

            var = self._execute_setvar('VAR = User.objects.create_user(...)')
            self._execute(f'{var}.delete(); delete {var}')

        Keyword arguments:
        timeout -- Number of seconds to wait for _ok before throwing
        """
        if 'VAR = ' not in code:
            raise ValueError(f"Code is missing 'VAR = ':\n{code}")

        var = f"var_{''.join(random.choices(string.ascii_lowercase, k=8))}"
        replaced_code = code.replace('VAR = ', f"{var} = ")

        self._execute(replaced_code, timeout=timeout)

        return var

    def create_user(self, email: str, username: str=None,
                    password: str=None, is_staff: bool=False,
                    is_superuser: bool=False) -> UserHandle:
        """Add the specified user to the database.

        When done with the User, `account_admin.destroy_user(user)`

        Keyword arguments:
        username -- string (default user portion of email)
        password -- string (default email)
        is_staff -- bool (default False)
        is_superuser -- bool (default False)
        """
        if username is None:
            username = email.split('@')[0]
        if password is None:
            password = email
        var = self._execute_setvar('\n'.join([
            f'VAR = User.objects.create_user(',
            f'    username={repr(username)},',
            f'    password={repr(password)},',
            f'    email={repr(email)},',
            f'    is_staff={repr(is_staff)},',
            f'    is_superuser={repr(is_superuser)}'
            f')',
        ]))
        return UserHandle(var, username, password, email)

    def destroy_user(self, user: UserHandle) -> None:
        """Clean up the return value of create_user().
        """
        self._execute(f'_ = {user._var}.delete(); del {user._var}')

    def verify_user_email(self, user: UserHandle) -> EmailAddressHandle:
        """Verify a user's email address.

        When done with the EmailAddress, `account_admin.destroy_email(email)`.

        The user can't log in until the email address is verified.
        """
        var = self._execute_setvar('\n'.join([
            f'VAR = EmailAddress.objects.create(',
            f'    user={user._var},',
            f'    email={repr(user.email)},',
            f'    primary=True,',
            f'    verified=True',
            f')',
        ]))
        return EmailAddressHandle(var)

    def destroy_user_email(self, email: EmailAddressHandle) -> None:
        """Clean up the return value of verify_user_email()."""
        self._execute(f'_ = {email._var}.delete(); del {email._var}')

    def destroy_modules(self) -> None:
        """Clean up any modules imported during test."""
        self._execute('\n'.join([
            'dynamicdispatch.load_module.cache_clear()',
            '_ = ModuleVersion.objects.exclude(module__link="").delete()',
            '_ = Module.objects.exclude(link="").delete()',
            'shutil.rmtree("importedmodules", ignore_errors=True)',
        ]))

    @property
    def latest_sent_email(self) -> Optional[email.message.Message]:
        """The last sent email, or None.

        FIXME make None work, if we need it. (Right now it'll give an error.)
        """
        url = self.live_server_url + '/last-sent-email'
        try:
            with urlopen(url) as f:
                return email.message_from_bytes(f.read())
        except HTTPError as err:
            if err.code == 404:
                return None
            else:
                raise
