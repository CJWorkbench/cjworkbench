from integrationtests.utils import LoggedInIntegrationTest


class DuplicateTest(LoggedInIntegrationTest):
    def test_duplicate(self):
        b = self.browser

        b.visit("/workflows/")
        b.click_button("Create Workflow")
        # Wait for page to load
        b.assert_element('input[name="name"][value="Untitled Workflow"]', wait=True)

        b.fill_in("name", "Example")

        self.add_data_step("Paste data")
        b.fill_in("csv", "foo,bar,baz\n1,2,\n2,3,\n3,4,", wait=True)
        self.submit_wf_module()

        self.import_module("nulldropper")
        self.add_wf_module("Drop empty columns")

        # Wait for _any_ output to load
        b.assert_element(".column-key", text="bar", wait=True)
        # Wait for the _final_ output to load -- which means the "baz" column
        # will not be there.
        b.assert_no_element(".column-key", text="baz", wait=True)
        # Wait for the _data_ to load -- not just the headers
        b.assert_element(".react-grid-Cell", text="2", wait=True)

        url1 = b.get_url()

        # Duplicate it!
        b.click_button("Duplicate")

        # Wait for the new workflow to load -- by name
        b.assert_element('input[name="name"][value="Copy of Example"]', wait=True)

        url2 = b.get_url()
        self.assertNotEqual(url2, url1)

        b.assert_element(
            "textarea[name=csv]", text="foo,bar,baz\n1,2,\n2,3,\n3,4,", wait=True
        )
        b.assert_element(".react-grid-Cell", text="2", wait=True)
