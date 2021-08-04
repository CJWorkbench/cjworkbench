from integrationtests.utils import LoggedInIntegrationTest


class TestApi(LoggedInIntegrationTest):
    def test_api(self):
        b = self.browser
        b.click_button("Create your first workflow")
        # wait for page load
        b.assert_element('input[name="name"][value="Untitled Workflow"]', wait=True)

        self.add_csv_data_module(csv="A,B\nx,y")
        b.click_button("API Publisher")
        b.check("datasetPublisherTab[tab-1]")
        b.click_button("publish")

        b.wait_for_element("a.api-instructions")
        b.click_link("API description")

        b.click_link(".json", wait=True)  # wait for page load

        self.assertEqual(
            b.text("body"), '[{"A":"x","B":"y"}]', wait=True
        )  # wait for page load
