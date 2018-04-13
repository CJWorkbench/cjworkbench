from server.tests.utils import *
from server.execute import execute_nocache
from django.test import override_settings
import mock
import tempfile
from urllib.error import URLError, HTTPError


# override b/c we depend on StoredObject to transmit data between event() and render(), so make sure not leave files around
@override_settings(MEDIA_ROOT=tempfile.gettempdir())

class ScrapeTableTest(LoggedInTestCase):
    def setUp(self):
        super(ScrapeTableTest, self).setUp()  # log in
        self.wfmodule = load_and_add_module('scrapetable')

        # save references to our parameter values so we can tweak them later
        self.url_pval = ParameterVal.objects.get(parameter_spec=ParameterSpec.objects.get(id_name='url'))
        self.fetch_pval = ParameterVal.objects.get(parameter_spec=ParameterSpec.objects.get(id_name='version_select'))

    # send fetch event to button to load data
    def press_fetch_button(self):
        self.client.post('/api/parameters/%d/event' % self.fetch_pval.id, {'type': 'click'})

    def test_scrape_table(self):
        url = 'http://test.com/tablepage.html'
        self.url_pval.set_value(url)
        self.url_pval.save()

        # should be no data saved yet, no Deltas on the workflow
        self.assertIsNone(self.wfmodule.get_fetched_data_version())
        self.assertIsNone(self.wfmodule.retrieve_fetched_table())
        self.assertIsNone(self.wfmodule.workflow.last_delta)

        with mock.patch('pandas.read_html') as readmock:
            readmock.return_value = [mock_csv_table]
            self.press_fetch_button()
            out = execute_nocache(self.wfmodule)
            self.assertEqual(readmock.call_args, mock.call(url) )

        self.assertTrue(out.equals(mock_csv_table))

        # should create a new data version on the WfModule, and a new delta representing the change
        self.wfmodule.refresh_from_db()
        self.wfmodule.workflow.refresh_from_db()
        self.assertIsNotNone(self.wfmodule.get_fetched_data_version())
        self.assertIsNotNone(self.wfmodule.workflow.last_delta)

    def test_invalid_url(self):
        url = 'nuh uh not a url'
        self.url_pval.set_value(url)
        self.url_pval.save()

        self.press_fetch_button()
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.ERROR)

    def test_bad_server(self):
        url = 'http://test.com/the.csv'
        self.url_pval.set_value(url)
        self.url_pval.save()

        with mock.patch('pandas.read_html') as readmock:
            readmock.side_effect = URLError('fake error message')
            self.press_fetch_button()

        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.ERROR)

    def test_404(self):
        url = 'http://test.com/the.csv'
        self.url_pval.set_value(url)
        self.url_pval.save()

        with mock.patch('pandas.read_html') as readmock:
            readmock.side_effect = HTTPError(url, 404, "fake error message", None, None)
            self.press_fetch_button()

        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.ERROR)
