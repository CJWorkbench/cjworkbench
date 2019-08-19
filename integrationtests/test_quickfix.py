from integrationtests.utils import LoggedInIntegrationTest


class TestQuickFix(LoggedInIntegrationTest):
    def _blur(self):
        self.browser.click_whatever(".module-name", text="Paste data")

    def _create_simple_workflow(self, *, csv_data, expected_colname_and_type):
        b = self.browser

        b.click_button("Create Workflow")
        b.assert_element(
            'input[name="name"][value="Untitled Workflow"]', wait=True
        )  # Wait for page to load

        b.fill_in("name", "Example Workflow")

        self.add_data_step("Paste data")
        b.fill_in("csv", csv_data, wait=True)
        self.submit_wf_module()

        # Wait for table to load
        b.assert_element(".column-key", text=expected_colname_and_type, wait=True)

    def test_quick_fix_convert_to_date(self):
        """
        Tests that a module's `column_types` gets users to click "Convert".
        """
        # https://www.pivotaltracker.com/story/show/160700316
        self._create_simple_workflow(
            csv_data="A,B\n2012-01-01,1\n2012-02-03,3\n2012-01-01,2",
            expected_colname_and_type="A text",
        )

        self.import_module("converttodate")

        self.add_wf_module("Group by date")
        self.select_column("Group by date", "column", "A")
        self.submit_wf_module()

        # Wait for error to occur
        b = self.browser
        b.assert_element(
            ".wf-module-error-msg",
            text="The column “A” must be converted from Text to Dates & Times.",
            wait=True,
        )
        b.click_button("Convert Text to Dates & Times")

        # Wait for module to appear
        b.assert_element(".module-name", text="Convert to date & time", wait=True)

        # Click back to "Group by date" to see its output
        b.click_whatever(".module-name", text="Group by date")
        # Wait for render
        b.assert_no_element(".wf-module-error-msg", wait=True)
        # Wait for table render
        b.assert_element(".column-key", text="count number", wait=True)

    def test_quick_fix_convert_to_text(self):
        """
        Tests that a module's `column_types` gets users to click "Convert".
        """
        b = self.browser

        # "Accidentally" create a column, 'Num' of type Text.
        self._create_simple_workflow(
            csv_data="T,Num\nX,$1\nY,$2\nZ,$3", expected_colname_and_type="T text"
        )

        # Try to format numbers. (It won't work because the input is text.)
        self.add_wf_module("Format numbers")
        self.select_column("Format numbers", "colnames", "Num")
        b.select("format", "Currency")
        self.submit_wf_module()
        # Wait for error
        b.assert_element(
            ".wf-module-error-msg",
            text="The column “Num” must be converted from Text to Numbers.",
            wait=True,
        )

        # Fix the error by clicking the "Quick Fix" button.
        b.click_button("Convert Text to Numbers")
        # Wait for module to appear
        b.assert_element(".module-name", text="Convert to numbers", wait=True)
        # The conversion won't work until we check an option.
        b.check("Extract number")
        self.submit_wf_module()

        # Now, the "Format numbers" module will have the correct output.
        b.click_whatever(".module-name", text="Format numbers")
        b.assert_element(".cell-number", text="$2.00", wait=True)
