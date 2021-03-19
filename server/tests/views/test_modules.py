from http import HTTPStatus as status

import cjwstate.modules
from cjwstate.tests.utils import DbTestCase, create_module_zipfile


class ModulesTest(DbTestCase):
    """Logged in, logging disabled, rabbitmq/commands disabled."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cjwstate.modules.init_module_system()  # create module tempdir

    def test_bad_slug_is_404(self):
        response = self.client.get("/modules/my-module.html")

        self.assertEqual(response.status_code, status.NOT_FOUND)

    def test_missing_html_is_404(self):
        create_module_zipfile("filter", spec_kwargs={"html_output": False})

        response = self.client.get("/modules/filter.html")

        self.assertEqual(response.status_code, status.NOT_FOUND)

    def test_happy_path(self):
        create_module_zipfile(
            "chart", spec_kwargs={"html_output": True}, html="hello, world!"
        )

        response = self.client.get("/modules/chart.html")

        self.assertEqual(response.status_code, status.OK)
        self.assertEqual(response.content, b"hello, world!")
        self.assertEqual(response["Content-Type"], "text/html; charset=utf-8")
