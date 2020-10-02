from integrationtests.helpers import accounts
from integrationtests.utils import WorkbenchBase


class TestTabs(WorkbenchBase):
    def setUp(self):
        super().setUp()

        self.account_admin.create_user("a@example.org", is_staff=True)

    def _create_workflow(self):
        b = self.browser

        b.visit("/workflows/")
        b.click_button("Create Workflow", wait=True)  # wait for React render
        # Wait for page to load
        b.assert_element('input[name="name"][value="Untitled Workflow"]', wait=True)

        b.fill_in("name", "Example Workflow")

    def _select_tab(self, tab_name):
        # Needs visible=False because there is no visible text. The user sees
        # the tab name as an <input> _value_; 'Tab 2' also appears as text but
        # that text is _invisible_, used only to size the <input>.
        b = self.browser
        b.click_whatever(
            "div.tabs>ul>li:not(.pending)>.tab",
            text=tab_name,
            visible=False,
            wait=True,  # in case it was .pending
        )

    def test_tabs_have_distinct_modules(self):
        b = self.browser

        accounts.login(b, "a@example.org", "a@example.org")
        self._create_workflow()

        self.import_module("pastecsv")

        self.add_data_step("Paste data")
        b.fill_in("csv", "A,B\n1,2,\n2,3", wait=True)

        b.click_button("Create tab")

        # Switch to Tab 2
        self._select_tab("Tab 2")
        b.assert_no_element('.step[data-module-name="Paste data"]')

        # Add a module that should not appear on Tab 1
        self.import_module("loadurl")
        self.add_data_step("Load from URL")

        # Switch to Tab 1
        self._select_tab("Tab 1")
        b.assert_element('.step[data-module-name="Paste data"]')
        b.assert_no_element('.step[data-module-name="Load from URL"]')

    def test_tab_deps(self):
        b = self.browser
        accounts.login(b, "a@example.org", "a@example.org")
        self._create_workflow()

        self.import_module("pastecsv")
        self.import_module("startfromtab")

        self.add_data_step("Paste data")
        b.fill_in("csv", "foo,bar\n1,2", wait=True)
        self.submit_step()

        # Switch to Tab 2
        b.click_button("Create tab")
        self._select_tab("Tab 2")
        b.assert_no_element('.step[data-module-name="Paste data"]')

        # Load data from tab 1
        self.add_data_step("Start from tab")
        self.select_tab_param("Start from tab", "tab", "Tab 1")
        self.submit_step()
        # Wait for data to load from tab 1
        b.assert_element(".data-grid-column-header", text="bar", wait=True)

        # Confirm changes to tab 1 affect tab 2
        # We'll change the Tab1 colnames from "foo,bar" to "bar,baz" and check
        # Tab2's output changed, too.
        self._select_tab("Tab 1")
        b.fill_in("csv", "bar,baz\n1,2", wait=True)
        self.submit_step()
        self._select_tab("Tab 2")
        # Wait for tab1's data to go away (in case there's a race somewhere)
        b.assert_no_element(".data-grid-column-header", text="foo", wait=True)
        b.assert_element(".data-grid-column-header", text="baz", wait=True)

    def test_tab_cycle(self):
        b = self.browser
        accounts.login(b, "a@example.org", "a@example.org")
        self._create_workflow()

        self.import_module("pastecsv")
        self.import_module("startfromtab")

        # Create Tab 2, and make Tab 1 depend on it
        b.click_button("Create tab")
        # wait for server to add it
        b.assert_no_element(".tabs>ul>li.pending", wait=True)

        # make Tab 1 depend on Tab 2
        self.add_data_step("Start from tab")
        self.select_tab_param("Start from tab", "tab", "Tab 2")
        self.submit_step()

        # Now make Tab 2 depend on Tab 1
        self._select_tab("Tab 2")
        self.add_data_step("Start from tab")
        self.select_tab_param("Start from tab", "tab", "Tab 1")
        self.submit_step(wait=True)  # wait for previous render to end

        b.assert_element(
            ".step-error-msg", text="The chosen tab depends on this one", wait=True
        )  # wait for render

        self._select_tab("Tab 1")
        b.assert_element(".step-error-msg", text="The chosen tab depends on this one")

    def test_start_from_empty_tab(self):
        b = self.browser
        accounts.login(b, "a@example.org", "a@example.org")
        self._create_workflow()

        self.import_module("startfromtab")

        # Create Tab 2, and make Tab 1 depend on it
        b.click_button("Create tab")
        # wait for server to add it
        b.assert_no_element(".tabs>ul>li.pending", wait=True)

        # make Tab 1 depend on Tab 2
        self.add_data_step("Start from tab")
        self.select_tab_param("Start from tab", "tab", "Tab 2")
        self.submit_step()

        b.assert_element(
            ".step-error-msg", text="The chosen tab has no output. ", wait=True
        )  # wait for render

    def test_duplicate_tab(self):
        b = self.browser
        accounts.login(b, "a@example.org", "a@example.org")
        self._create_workflow()

        self.import_module("pastecsv")
        self.add_data_step("Paste data")
        b.fill_in("csv", "foo,bar\n1,2", wait=True)
        self.submit_step()

        # duplicate tab
        b.click_whatever(".tabs>ul>li.selected button.toggle")
        with b.scope(".dropdown-menu"):
            b.click_button("Duplicate")
        # wait for server to add it
        b.assert_no_element(".tabs>ul>li.pending", wait=True)

        self._select_tab("Tab 1 (1)")  # assume this is how it's named
        # Make sure everything's there.
        b.assert_element('.step[data-module-name="Paste data"]')
