from pathlib import Path
import capybara
from capybara.session import Session
from contextlib import contextmanager
from typing import Any

# for Browser.send_keys
from selenium.webdriver.common.keys import Keys  # noqa: F401


# DISABLE capybara's default wait time! We're more explicit about timeouts in
# our tests, so our behavior is more predictable. (We try to avoid tests that
# fail intermittently.)
capybara.default_max_wait_time = 0


# @capybara.register_driver('selenium')
# def init_selenium_driver(app):
#     from capybara.selenium.driver import Driver
#     return Driver(app, browser="chrome")
@capybara.register_driver("selenium")
def init_selenium_driver(app):
    from capybara.selenium.driver import Driver
    from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

    capabilities = DesiredCapabilities.FIREFOX.copy()
    capabilities["moz:firefoxOptions"] = {"log": {"level": "trace"}, "args": []}
    return Driver(app, browser="firefox", desired_capabilities=capabilities)


def _sanitize_base_url(url: str) -> str:
    # self.base_url: always a string, never ending with '/'
    if url and url[-1] == "/":
        url = url[0:-2]
    return url


class Browser:
    """A real web browser window that does what you want.

    This browser is modeled after Capybara:
    https://www.rubydoc.info/github/teamcapybara/capybara/master#The_DSL

    This DSL encourages single-call methods, to avoid races. It _discourages_
    code like `browser.find('input[name="foo"]').click()`, because that has a
    race: what happens if the input disappears after `find()` and before
    `click()`? An exception -- which is not ideal.

    The DSL also encourages you to consider races with every line of code.
    `wait_for_element()` will stall until an element appears. And
    `not browser.exists(..., wait: true)` is different from
    `browser.not_exists(..., wait: true)`, since the latter will wait for the
    element to disappear.

    Keyword arguments:
    base_url -- automatic prefix to 'visit()' urls (default '')
    default_wait_timeout -- default timeout for 'wait_for_element()' etc, in s
                            (default 15)
    """

    def __init__(self, **kwargs):
        self.page = Session("selenium", None)
        self.base_url = _sanitize_base_url(kwargs.get("base_url") or "")

        # default wait timeout -- None means forever
        self.default_wait_timeout = kwargs.get("default_wait_timeout", 20)

    def _capybarize_kwargs(self, kwargs):
        """Modify kwargs in-place.

        Conversions:
        - Converts 'wait':True to 'wait':default_wait_timeout.
        """
        if kwargs.get("wait") is True:
            kwargs["wait"] = self.default_wait_timeout

    def visit(self, url: str) -> None:
        """Type 'url' into the address bar, press Enter, and await onload."""
        if url[0] == "/":
            url = self.base_url + url
        self.page.visit(url)

    def exec_js(self, js: str, *args: Any) -> Any:
        """Execute the given JavaScript on the page."""
        self.page.execute_script(js, *args)

    def fill_in(self, locator: str, text: str, **kwargs) -> None:
        """Type 'text' into field with name/label/id 'locator'.

        Raises ValueError if text is empty. (Empty text is usually an error in
        test code.)

        Keyword arguments:
        wait -- True or number of seconds to wait until element appears
        """
        if not text:
            raise ValueError("fill_in() called without text")
        kwargs["value"] = text
        self._capybarize_kwargs(kwargs)
        self.page.fill_in(locator, **kwargs)

    def fill_text_in_whatever(self, text: str, *selector, **kwargs) -> None:
        """Type 'text' into field matching selector.

        Raises ValueError if text is empty. (Empty text is usually an error in
        test code.)

        See 'assert_element()' for syntax.

        Prefer `fill_in`. All our HTML fields should have names or titles;
        anything else is an accessibility issue we should fix. Notice that
        this method's arguments are reversed from `fill_in`'s arguments.

        Keyword arguments:
        wait -- True or number of seconds to wait until element appears
        """
        if not text:
            raise ValueError("fill_in() called without text")
        kwargs["value"] = text
        self._capybarize_kwargs(kwargs)
        # There's a race here between find() and fill_in(). If we get an error
        # about "missing element", write the exception handler we need.
        self.page.find(*selector, **kwargs).set(text)

    def send_keys(self, locator: str, *keys: str, **kwargs) -> None:
        """
        Press `keys` in field with name/label/id 'locator'.

        Raise ValueError if text is empty. (Empty text is usually an error in
        test code.)

        Keyword arguments:
        wait -- True or number of seconds to wait until element appears
        """
        self._capybarize_kwargs(kwargs)
        self.page.find("fillable_field", locator, **kwargs).send_keys(*keys)

    def attach_file(self, locator: str, path: Path, **kwargs) -> None:
        """
        Choose `path` in file-upload field with name/label/id 'locator'.

        Keyword arguments:
        wait -- True or number of seconds to wait until element appears
        """
        self._capybarize_kwargs(kwargs)
        self.page.find("file_field", locator, **kwargs).set(str(path))

    def check(self, locator: str, **kwargs) -> None:
        """Check the checkbox with name/label/id 'locator'.

        Keyword arguments:
        wait -- True or number of seconds to wait until element appears
        """
        self._capybarize_kwargs(kwargs)
        self.page.check(locator, **kwargs)

    def uncheck(self, locator: str, **kwargs) -> None:
        """Uncheck the checkbox with name/label/id 'locator'.

        Keyword arguments:
        wait -- True or number of seconds to wait until element appears
        """
        self._capybarize_kwargs(kwargs)
        self.page.uncheck(locator, **kwargs)

    def select(self, locator: str, text: str, **kwargs) -> None:
        """Select 'text' in the select box with name/label/id 'locator'.

        Keyword arguments:
        wait -- True or number of seconds to wait until element appears
        """
        self._capybarize_kwargs(kwargs)
        kwargs["field"] = locator
        self.page.select(text, **kwargs)

    def click_button(self, locator: str, **kwargs) -> None:
        """Click the button with name/id/text 'locator'.

        Keyword arguments:
        wait -- True or number of seconds to wait until element appears
        """
        self._capybarize_kwargs(kwargs)
        self.page.click_button(locator, **kwargs)

    def click_link(self, locator: str, **kwargs) -> None:
        """Click the <a> with id/text/title 'locator'.

        Keyword arguments:
        wait -- True or number of seconds to wait until element appears
        """
        self._capybarize_kwargs(kwargs)
        self.page.click_link(locator, **kwargs)

    def click_whatever(self, *selector, **kwargs) -> None:
        """Click the selected element.

        Raises unless 1 element matches the selector.

        Calling this method usually means the site has an accessibility
        problem. Prefer click_link() and click_button(): the user should be
        clicking on links and buttons to make things happen.

        See 'assert_element()' for syntax.

        Keyword arguments:
        wait -- seconds to poll (default 0)
        text -- text the element must contain
        """
        self._capybarize_kwargs(kwargs)
        # There's a race here between find() and click(). If we get an error
        # about "missing element", write the exception handler we need.
        self.page.find(*selector, **kwargs).click()

    def double_click_whatever(self, *selector, **kwargs) -> None:
        """Double-click the selected element.

        Raises unless 1 element matches the selector.

        See 'assert_element()' for syntax.

        Keyword arguments:
        wait -- seconds to poll (default 0)
        text -- text the element must contain
        """
        self._capybarize_kwargs(kwargs)

        # There's a race here between find() and execute(). If we get an
        # error about "missing element", write the exception handler we need.
        native_node = self.page.find(*selector, **kwargs).native

        # https://github.com/mozilla/geckodriver/issues/661 means we can't just
        # double_click(). We need to dispatch a JS event.
        #
        # [adamhooper, 2018-06-20] bug reproduced as late as today, which is
        # odd because the GitHub issue is marked resolved. I gave up
        # investigating.
        script = """
            var ev = new MouseEvent(
                'dblclick',
                { bubbles: true, cancelable: true, view: window }
            )
            arguments[0].dispatchEvent(ev);
        """
        self.page.driver.browser.execute_script(script, native_node)

    def hover_over_element(self, *selector, **kwargs) -> None:
        """Hover over the selected element.

        Raises unless 1 element matches the selector.

        Calling this method usually means the site has an accessibility
        problem. Not all users can hover.

        See 'assert_element()' for syntax.

        Keyword arguments:
        wait -- seconds to poll (default 0)
        text -- text the element must contain
        """
        self._capybarize_kwargs(kwargs)
        # There's a race here between find() and hover(). If we get an error
        # about "missing element", write the exception handler we need.
        self.page.find(*selector, **kwargs).hover()

    def assert_element(self, *selector, **kwargs) -> None:
        """Test that 'selector' matches, or throws an error.

        Example selectors:
        - 'div.foo'
        - '#main'
        - 'xpath', '//h1[contains(text(), "foo")]' (two arguments, more
          complex than simply using the 'text' kwarg.)

        Keyword arguments:
        wait -- seconds to poll (default 0)
        text -- text the element must contain
        """
        self._capybarize_kwargs(kwargs)
        self.page.assert_selector(*selector, **kwargs)

    def assert_no_element(self, *selector, **kwargs) -> None:
        """Test that 'selector' does _not_ match, or throws an error.

        Example selectors:
        - 'div.foo'
        - '#main'
        - 'xpath', '//h1[contains(text(), "foo")]' (two arguments, more
          complex than simply using the 'text' kwarg.)

        Keyword arguments:
        wait -- seconds to poll until the element goes away (default 0)
        text -- text the element we don't want to find must contain
        """
        self._capybarize_kwargs(kwargs)
        self.page.assert_no_selector(*selector, **kwargs)

    def wait_for_element(self, *selector, **kwargs) -> None:
        """Polls until 'selector' matches; throws error on timeout.

        Keyword arguments:
        wait -- seconds to poll (default default_wait_timeout)
        text -- text the element must contain
        """
        if "wait" not in kwargs:
            kwargs["wait"] = self.default_wait_timeout
        self.assert_element(*selector, **kwargs)

    def text(self, *selector, **kwargs) -> str:
        """Returns text of element matching selector.
        See 'assert_element()' for selector syntax.

        Keyword arguments:
        wait -- seconds to poll (default 0)
        text -- text the element must contain
        """
        self._capybarize_kwargs(kwargs)
        return self.page.find(*selector, **kwargs).all_text

    @contextmanager
    def scope(self, *selector, **kwargs) -> None:
        """Within the given block, scopes all selectors within 'selector'.

        Example:

            with browser.scope('#root'):
                browser.assert_element('h2')

        Keyword arguments:
        wait -- seconds to poll (default 0)
        text -- text the element must contain
        """
        self._capybarize_kwargs(kwargs)
        with self.page.scope(*selector, **kwargs):
            yield

    @contextmanager
    def iframe(self, *selector, **kwargs) -> None:
        """
        Within the given block, `window` is the chosen iframe.

        Example:

            with browser.iframe('#root', wait=True):
                browser.assert_element('h2')
        """
        # There's a race here: the iframe can disappear before we switch to it.
        # If this becomes an issue, find a fix.
        el = self.page.find(*selector, **kwargs)
        with self.page.frame(el):
            yield

    def clear_cookies(self) -> None:
        """Delete all cookies and navigates to a blank page."""
        self.page.reset()

    def get_url(self) -> str:
        """Find the URL in the browser's address bar."""
        return self.page.current_url

    def quit(self) -> None:
        """Destroys the browser and everything it created.
        """
        self.page.driver.browser.quit()  # hack Capybara's internals
