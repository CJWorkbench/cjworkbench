from urllib.parse import urlsplit
from unittest import mock

import unittest

from server.modules.enigma import handle_dotcom_url, handle_dotio_url
from server.tests.utils import *

def mock_response(*args, **kwargs):
    class MockResponse:
        def __init__(self, text, status_code):
            self.text = json.dumps(text)
            self.status_code = status_code
        
    if args[0] == "https://public.enigma.com/api/datasets/dataset_failure?row_limit=500":
        error_msg = {
            'id': 'resource_not_found', 
            'message': 'Requested resource not found', 
            'detail': {'type': 'dataset'}
            }
        return MockResponse(error_msg, 404)

    if args[0] == "https://public.enigma.com/api/datasets/dataset_success?row_limit=500":
        data = {
            "current_snapshot": {
                "table_rows": {
                    "fields": ["A", "B", "C"],
                    "rows": [[1,2,3],[4,5,6]]
                }
            }
        }
        return MockResponse(data, 200)



class EnigmaTests(LoggedInTestCase):
    def setUp(self):
        super(EnigmaTests, self).setUp()  # log in
        self.wfmodule = load_and_add_module('enigma')

    # send fetch event to button to load data
    def press_fetch_button(self):
        self.client.post('/api/parameters/%d/event' % self.fetch_pval.id, {'type': 'click'})

    # get rendered result
    def get_render(self):
        return self.client.get('/api/wfmodules/%d/render' % self.wfmodule.id)

    def test_enigma_io_error_conditions(self):
        url = "www.test.com"
        split_url = urlsplit(url)
        out = handle_dotio_url(self.wfmodule, url, split_url, 1000)
        self.assertEquals(out, "You can request a maximum of 500 rows.")

    def test_enigma_com_error_conditions(self):
        # tests existence of API key 
        url = "www.test.com"
        split_url = urlsplit(url)
        out = handle_dotcom_url(self.wfmodule, url, split_url, 1000)
        self.assertEquals(out, "No Enigma API Key set.")

        # tests proper URL
        os.environ["ENIGMA_COM_API_KEY"] = "TESTKEY"
        out = handle_dotcom_url(self.wfmodule, url, split_url, 1000)
        self.assertEquals(out, "Unable to retrieve the dataset id from request.")

    @mock.patch('requests.get', side_effect=mock_response)
    def test_enigma_com_request_response_failure(self, mock_get):
        url = "http://test.com/failure/datasets/dataset_failure/limit/500"
        split_url = urlsplit(url)
        out = handle_dotcom_url(self.wfmodule, url, split_url, 500)
        self.assertTrue("Requested resource not found" in out)

        
    @mock.patch('requests.get', side_effect=mock_response)
    def test_enigma_com_request_response_success(self, mock_get):
        url = "http://test.com/success/datasets/dataset_success/limit/500"
        split_url = urlsplit(url)
        returned = handle_dotcom_url(self.wfmodule, url, split_url, 500)
        self.assertTrue(len(returned) == 2) # make sure we have all the data
        self.assertTrue(list(returned.columns.values) == ['A', 'B', 'C']) # make sure we set the header
