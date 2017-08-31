from django.test import TestCase
from server.models import WfModule
from server.tests.utils import *
from server.views.WfModule import make_render_json
import pandas as pd
import io

# ---- PasteCSV ----

class PasteCSVTests(LoggedInTestCase):
    def setUp(self):
        super(PasteCSVTests, self).setUp()  # log in
        self.workflow = create_testdata_workflow()
        self.wf_module = WfModule.objects.all().first()

    def test_csv(self):
        response = self.client.get('/api/wfmodules/%d/render' % self.wf_module.id)
        table = pd.read_csv(io.StringIO(mock_csv_text))
        self.assertEqual(response.content, make_render_json(table))
