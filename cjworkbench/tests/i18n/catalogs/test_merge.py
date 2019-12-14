import unittest
from babel.messages.catalog import Catalog
from cjworkbench.i18n.catalogs.merge import _merge_source_catalog, _merge_catalog
from cjworkbench.tests.i18n.catalogs.util import (
    assert_catalogs_deeply_equal,
    assert_messages_deeply_equal,
)


class MergeTest(unittest.TestCase):
    def test_merge_source_catalog_parse_python_special_comments(self):
        js_catalog = Catalog("en")
        python_catalog = Catalog("en")
        python_catalog.add(
            "id1",
            locations=[("file1", "1")],
            auto_comments=["default-message: Text1", "some comment"],
        )
        old_source_catalog = Catalog("en")

        new_js_catalog, new_python_catalog, fuzzy = _merge_source_catalog(
            js_catalog, python_catalog, old_source_catalog
        )

        expected_python_catalog = Catalog("en")
        expected_python_catalog.add(
            "id1",
            string="Text1",
            locations=[("file1", "1")],
            auto_comments=["some comment"],
        )
        expected_js_catalog = Catalog("en")
        expected_js_catalog.add(
            "id1",
            string="Text1",
            locations=[("file1", "1")],
            auto_comments=["some comment"],
        )
        assert_catalogs_deeply_equal(new_js_catalog, expected_js_catalog)
        assert_catalogs_deeply_equal(new_python_catalog, expected_python_catalog)
        self.assertEqual(fuzzy, frozenset())

    def test_merge_source_catalog_add_js_and_python(self):
        js_catalog = Catalog("en")
        js_catalog.add(
            "id0",
            string="Text0",
            locations=[("file0", "2")],
            auto_comments=["some js comment"],
        )
        python_catalog = Catalog("en")
        python_catalog.add(
            "id1",
            locations=[("file1", "1")],
            auto_comments=["default-message: Text1", "some comment"],
        )
        old_source_catalog = Catalog("en")

        new_js_catalog, new_python_catalog, fuzzy = _merge_source_catalog(
            js_catalog, python_catalog, old_source_catalog
        )

        expected_python_catalog = Catalog("en")
        expected_python_catalog.add(
            "id1",
            string="Text1",
            locations=[("file1", "1")],
            auto_comments=["some comment"],
        )
        expected_js_catalog = Catalog("en")
        expected_js_catalog.add(
            "id0",
            string="Text0",
            locations=[("file0", "2")],
            auto_comments=["some js comment"],
        )
        expected_js_catalog.add(
            "id1",
            string="Text1",
            locations=[("file1", "1")],
            auto_comments=["some comment"],
        )
        assert_catalogs_deeply_equal(new_js_catalog, expected_js_catalog)
        assert_catalogs_deeply_equal(new_python_catalog, expected_python_catalog)
        self.assertEqual(fuzzy, frozenset())

    def test_merge_source_catalog_update_existing_old(self):
        js_catalog = Catalog("en")
        js_catalog.add(
            "id0",
            string="Text0",
            locations=[("file0", "2")],
            auto_comments=["some js comment"],
        )
        python_catalog = Catalog("en")
        python_catalog.add(
            "id1",
            locations=[("file1", "1")],
            auto_comments=["default-message: Text1", "some comment"],
        )
        old_source_catalog = Catalog("en")
        old_source_catalog.add(
            "id0",
            string="Text0",
            locations=[("file0", "3")],
            auto_comments=["some js comment"],
        )
        old_source_catalog.add(
            "id1",
            string="Text1",
            locations=[("file0", "2")],
            auto_comments=["some old comment"],
        )

        new_js_catalog, new_python_catalog, fuzzy = _merge_source_catalog(
            js_catalog, python_catalog, old_source_catalog
        )

        expected_python_catalog = Catalog("en")
        expected_python_catalog.add(
            "id1",
            string="Text1",
            locations=[("file1", "1")],
            auto_comments=["some comment"],
        )
        expected_js_catalog = Catalog("en")
        expected_js_catalog.add(
            "id0",
            string="Text0",
            locations=[("file0", "2")],
            auto_comments=["some js comment"],
        )
        expected_js_catalog.add(
            "id1",
            string="Text1",
            locations=[("file1", "1")],
            auto_comments=["some comment"],
        )
        assert_catalogs_deeply_equal(new_js_catalog, expected_js_catalog)
        assert_catalogs_deeply_equal(new_python_catalog, expected_python_catalog)
        self.assertEqual(fuzzy, frozenset())

    def test_merge_source_catalog_remove_deprecated_old(self):
        js_catalog = Catalog("en")
        js_catalog.add(
            "id0", locations=[("file0", "2")], auto_comments=["some js comment"]
        )
        python_catalog = Catalog("en")
        python_catalog.add(
            "id1",
            locations=[("file1", "1")],
            auto_comments=["default-message: Text1", "some comment"],
        )
        old_source_catalog = Catalog("en")
        old_source_catalog.add(
            "id2", locations=[("file1", "1")], auto_comments=["some comment"]
        )

        new_js_catalog, new_python_catalog, fuzzy = _merge_source_catalog(
            js_catalog, python_catalog, old_source_catalog
        )

        expected_python_catalog = Catalog("en")
        expected_python_catalog.add(
            "id1",
            string="Text1",
            locations=[("file1", "1")],
            auto_comments=["some comment"],
        )
        expected_js_catalog = Catalog("en")
        expected_js_catalog.add(
            "id0", locations=[("file0", "2")], auto_comments=["some js comment"]
        )
        expected_js_catalog.add(
            "id1",
            string="Text1",
            locations=[("file1", "1")],
            auto_comments=["some comment"],
        )
        assert_catalogs_deeply_equal(new_js_catalog, expected_js_catalog)
        assert_catalogs_deeply_equal(new_python_catalog, expected_python_catalog)
        self.assertEqual(fuzzy, frozenset())

    def test_merge_source_catalog_fuzzy_in_python(self):
        js_catalog = Catalog("en")
        python_catalog = Catalog("en")
        python_catalog.add(
            "id1",
            locations=[("file1", "1")],
            auto_comments=["default-message: Text1", "some comment"],
        )
        old_source_catalog = Catalog("en")
        old_source_catalog.add(
            "id1",
            string="Text0",
            locations=[("file1", "1")],
            auto_comments=["some comment"],
        )

        new_js_catalog, new_python_catalog, fuzzy = _merge_source_catalog(
            js_catalog, python_catalog, old_source_catalog
        )

        expected_python_catalog = Catalog("en")
        expected_python_catalog.add(
            "id1",
            string="Text1",
            locations=[("file1", "1")],
            auto_comments=["some comment"],
        )
        expected_js_catalog = Catalog("en")
        expected_js_catalog.add(
            "id1",
            string="Text1",
            locations=[("file1", "1")],
            auto_comments=["some comment"],
        )
        assert_catalogs_deeply_equal(new_js_catalog, expected_js_catalog)
        assert_catalogs_deeply_equal(new_python_catalog, expected_python_catalog)
        self.assertEqual(fuzzy, frozenset(["id1"]))

    def test_merge_source_catalog_fuzzy_in_js(self):
        js_catalog = Catalog("en")
        js_catalog.add(
            "id1",
            string="Text1",
            locations=[("file1", "1")],
            auto_comments=["some comment"],
        )
        python_catalog = Catalog("en")
        old_source_catalog = Catalog("en")
        old_source_catalog.add(
            "id1",
            string="Text0",
            locations=[("file1", "1")],
            auto_comments=["some comment"],
        )

        new_js_catalog, new_python_catalog, fuzzy = _merge_source_catalog(
            js_catalog, python_catalog, old_source_catalog
        )

        expected_python_catalog = Catalog("en")
        expected_js_catalog = Catalog("en")
        expected_js_catalog.add(
            "id1",
            string="Text1",
            locations=[("file1", "1")],
            auto_comments=["some comment"],
        )
        assert_catalogs_deeply_equal(new_js_catalog, expected_js_catalog)
        assert_catalogs_deeply_equal(new_python_catalog, expected_python_catalog)
        self.assertEqual(fuzzy, frozenset(["id1"]))

    def test_merge_catalog_add_from_python(self):
        js_catalog = Catalog("el")
        python_catalog = Catalog("en")
        python_catalog.add(
            "id1",
            string="Text0",
            locations=[("file2", "1")],
            auto_comments=["some new comment"],
        )
        old_catalog = Catalog("el")
        fuzzy = frozenset()

        new_catalog = _merge_catalog(js_catalog, python_catalog, old_catalog, fuzzy)

        expected_catalog = Catalog("el")
        expected_catalog.add(
            "id1",
            string="",
            locations=[("file2", "1")],
            auto_comments=["some new comment"],
        )
        assert_catalogs_deeply_equal(new_catalog, expected_catalog)

    def test_merge_catalog_update_from_python(self):
        js_catalog = Catalog("el")
        python_catalog = Catalog("en")
        python_catalog.add(
            "id1",
            string="Text1",
            locations=[("file2", "1")],
            auto_comments=["some new comment"],
        )
        old_catalog = Catalog("el")
        old_catalog.add(
            "id1",
            string="Text0",
            locations=[("file3", "2")],
            auto_comments=["some old comment"],
        )
        fuzzy = frozenset()

        new_catalog = _merge_catalog(js_catalog, python_catalog, old_catalog, fuzzy)

        expected_catalog = Catalog("el")
        expected_catalog.add(
            "id1",
            string="Text0",
            locations=[("file2", "1")],
            auto_comments=["some new comment"],
        )
        assert_catalogs_deeply_equal(new_catalog, expected_catalog)

    def test_merge_catalog_add_from_js(self):
        js_catalog = Catalog("el")
        js_catalog.add(
            "id1", string="", locations=[("file1", "1")], auto_comments=["some comment"]
        )
        python_catalog = Catalog("en")
        old_catalog = Catalog("el")
        fuzzy = frozenset()

        new_catalog = _merge_catalog(js_catalog, python_catalog, old_catalog, fuzzy)

        expected_catalog = Catalog("el")
        expected_catalog.add(
            "id1", string="", locations=[("file1", "1")], auto_comments=["some comment"]
        )
        assert_catalogs_deeply_equal(new_catalog, expected_catalog)

    def test_merge_catalog_update_from_js(self):
        js_catalog = Catalog("el")
        js_catalog.add(
            "id1",
            string="",
            locations=[("file2", "2")],
            auto_comments=["some new comment"],
        )
        python_catalog = Catalog("en")
        old_catalog = Catalog("el")
        old_catalog.add(
            "id1",
            string="Text2",
            locations=[("file1", "1")],
            auto_comments=["some comment"],
        )
        fuzzy = frozenset()

        new_catalog = _merge_catalog(js_catalog, python_catalog, old_catalog, fuzzy)

        expected_catalog = Catalog("el")
        expected_catalog.add(
            "id1",
            string="Text2",
            locations=[("file2", "2")],
            auto_comments=["some new comment"],
        )
        assert_catalogs_deeply_equal(new_catalog, expected_catalog)

    def test_merge_catalog_update_from_python_fuzzy_old(self):
        js_catalog = Catalog("el")
        python_catalog = Catalog("en")
        python_catalog.add(
            "id1",
            string="Text2",
            locations=[("file2", "1")],
            auto_comments=["some new comment"],
        )
        old_catalog = Catalog("el")
        old_catalog.add(
            "id1",
            string="Text0",
            flags=["fuzzy"],
            locations=[("file1", "1")],
            auto_comments=["some comment"],
        )
        fuzzy = frozenset()

        new_catalog = _merge_catalog(js_catalog, python_catalog, old_catalog, fuzzy)

        expected_catalog = Catalog("el")
        expected_catalog.add(
            "id1",
            string="Text0",
            flags=["fuzzy"],
            locations=[("file2", "1")],
            auto_comments=["some new comment"],
        )
        assert_catalogs_deeply_equal(new_catalog, expected_catalog)

    def test_merge_catalog_update_from_python_fuzzy_new(self):
        js_catalog = Catalog("el")
        python_catalog = Catalog("en")
        python_catalog.add(
            "id1",
            string="Text0",
            locations=[("file2", "1")],
            auto_comments=["some new comment"],
        )
        old_catalog = Catalog("el")
        old_catalog.add(
            "id1",
            string="Text2",
            locations=[("file1", "1")],
            auto_comments=["some comment"],
        )
        fuzzy = frozenset(["id1"])

        new_catalog = _merge_catalog(js_catalog, python_catalog, old_catalog, fuzzy)

        expected_catalog = Catalog("el")
        expected_catalog.add(
            "id1",
            string="Text2",
            flags=["fuzzy"],
            locations=[("file2", "1")],
            auto_comments=["some new comment"],
        )
        assert_catalogs_deeply_equal(new_catalog, expected_catalog)

    def test_merge_catalog_update_from_python_fuzzy_empty(self):
        js_catalog = Catalog("el")
        python_catalog = Catalog("en")
        python_catalog.add(
            "id1",
            string="Text0",
            locations=[("file2", "1")],
            auto_comments=["some new comment"],
        )
        old_catalog = Catalog("el")
        old_catalog.add(
            "id1", string="", locations=[("file1", "1")], auto_comments=["some comment"]
        )
        fuzzy = frozenset(["id1"])

        new_catalog = _merge_catalog(js_catalog, python_catalog, old_catalog, fuzzy)

        expected_catalog = Catalog("el")
        expected_catalog.add(
            "id1",
            string="",
            locations=[("file2", "1")],
            auto_comments=["some new comment"],
        )
        assert_catalogs_deeply_equal(new_catalog, expected_catalog)

    def test_merge_catalog_update_from_js_fuzzy_old(self):
        js_catalog = Catalog("el")
        js_catalog.add(
            "id1",
            string="",
            locations=[("file2", "1")],
            auto_comments=["some new comment"],
        )
        python_catalog = Catalog("en")
        old_catalog = Catalog("el")
        old_catalog.add(
            "id1",
            string="Text0",
            flags=["fuzzy"],
            locations=[("file1", "1")],
            auto_comments=["some comment"],
        )
        fuzzy = frozenset()

        new_catalog = _merge_catalog(js_catalog, python_catalog, old_catalog, fuzzy)

        expected_catalog = Catalog("el")
        expected_catalog.add(
            "id1",
            string="Text0",
            flags=["fuzzy"],
            locations=[("file2", "1")],
            auto_comments=["some new comment"],
        )
        assert_catalogs_deeply_equal(new_catalog, expected_catalog)

    def test_merge_catalog_update_from_js_fuzzy_new(self):
        js_catalog = Catalog("el")
        js_catalog.add(
            "id1",
            string="",
            locations=[("file2", "1")],
            auto_comments=["some new comment"],
        )
        python_catalog = Catalog("en")
        old_catalog = Catalog("el")
        old_catalog.add(
            "id1",
            string="Text2",
            locations=[("file1", "1")],
            auto_comments=["some comment"],
        )
        fuzzy = frozenset(["id1"])

        new_catalog = _merge_catalog(js_catalog, python_catalog, old_catalog, fuzzy)

        expected_catalog = Catalog("el")
        expected_catalog.add(
            "id1",
            string="Text2",
            flags=["fuzzy"],
            locations=[("file2", "1")],
            auto_comments=["some new comment"],
        )
        assert_catalogs_deeply_equal(new_catalog, expected_catalog)

    def test_merge_catalog_update_from_js_fuzzy_empty(self):
        js_catalog = Catalog("el")
        js_catalog.add(
            "id1",
            string="",
            locations=[("file2", "1")],
            auto_comments=["some new comment"],
        )
        python_catalog = Catalog("en")
        old_catalog = Catalog("el")
        old_catalog.add(
            "id1", string="", locations=[("file1", "1")], auto_comments=["some comment"]
        )
        fuzzy = frozenset(["id1"])

        new_catalog = _merge_catalog(js_catalog, python_catalog, old_catalog, fuzzy)

        expected_catalog = Catalog("el")
        expected_catalog.add(
            "id1",
            string="",
            locations=[("file2", "1")],
            auto_comments=["some new comment"],
        )
        assert_catalogs_deeply_equal(new_catalog, expected_catalog)
