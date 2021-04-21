import datetime
import os
import tempfile
import unittest
from pathlib import Path

from cjwkernel import types
from cjwkernel.thrift import ttypes
from cjwmodule.i18n import I18nMessage


class ThriftConvertersTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.basedir = Path(tempfile.mkdtemp())
        self.old_cwd = os.getcwd()
        os.chdir(self.basedir)

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.basedir.rmdir()
        super().tearDown()

    def test_thrift_json_object_to_pydict(self):
        self.assertEqual(
            types.thrift_json_object_to_pydict(
                {
                    "str": ttypes.Json(string_value="s"),
                    "int": ttypes.Json(int64_value=2),
                    "float": ttypes.Json(number_value=1.2),
                    "null": ttypes.Json(),
                    "bool": ttypes.Json(boolean_value=False),
                    "arrayofobjects": ttypes.Json(
                        array_value=[
                            ttypes.Json(
                                object_value={
                                    "A": ttypes.Json(string_value="a"),
                                    "B": ttypes.Json(string_value="b"),
                                }
                            ),
                            ttypes.Json(
                                object_value={
                                    "C": ttypes.Json(string_value="c"),
                                    "D": ttypes.Json(string_value="d"),
                                }
                            ),
                        ]
                    ),
                },
            ),
            {
                "str": "s",
                "int": 2,
                "float": 1.2,
                "null": None,
                "bool": False,
                "arrayofobjects": [{"A": "a", "B": "b"}, {"C": "c", "D": "d"}],
            },
        )

    def test_pydict_to_thrift_json_object(self):
        self.assertEqual(
            types.pydict_to_thrift_json_object(
                {
                    "str": "s",
                    "int": 2,
                    "float": 1.2,
                    "null": None,
                    "bool": False,
                    "arrayofobjects": [{"A": "a", "B": "b"}, {"C": "c", "D": "d"}],
                }
            ),
            {
                "str": ttypes.Json(string_value="s"),
                "int": ttypes.Json(int64_value=2),
                "float": ttypes.Json(number_value=1.2),
                "null": ttypes.Json(),
                "bool": ttypes.Json(boolean_value=False),
                "arrayofobjects": ttypes.Json(
                    array_value=[
                        ttypes.Json(
                            object_value={
                                "A": ttypes.Json(string_value="a"),
                                "B": ttypes.Json(string_value="b"),
                            }
                        ),
                        ttypes.Json(
                            object_value={
                                "C": ttypes.Json(string_value="c"),
                                "D": ttypes.Json(string_value="d"),
                            }
                        ),
                    ]
                ),
            },
        )

    def test_i18n_message_from_thrift_source_module(self):
        self.assertEqual(
            types.thrift_i18n_message_to_arrow(
                ttypes.I18nMessage(
                    "modules.x.y",
                    {
                        "a": ttypes.I18nArgument(string_value="s"),
                        "b": ttypes.I18nArgument(i32_value=12345678),
                        "c": ttypes.I18nArgument(double_value=0.123),
                    },
                    "module",
                )
            ),
            I18nMessage("modules.x.y", {"a": "s", "b": 12345678, "c": 0.123}, "module"),
        )

    def test_i18n_message_to_thrift_source_module(self):
        self.assertEqual(
            types.arrow_i18n_message_to_thrift(
                I18nMessage(
                    "modules.x.y", {"a": "s", "b": 12345678, "c": 0.123}, "module"
                )
            ),
            ttypes.I18nMessage(
                "modules.x.y",
                {
                    "a": ttypes.I18nArgument(string_value="s"),
                    "b": ttypes.I18nArgument(i32_value=12345678),
                    "c": ttypes.I18nArgument(double_value=0.123),
                },
                "module",
            ),
        )

    def test_i18n_message_from_thrift_source_library(self):
        self.assertEqual(
            types.thrift_i18n_message_to_arrow(
                ttypes.I18nMessage(
                    "modules.x.y",
                    {
                        "a": ttypes.I18nArgument(string_value="s"),
                        "b": ttypes.I18nArgument(i32_value=12345678),
                        "c": ttypes.I18nArgument(double_value=0.123),
                    },
                    "cjwmodule",
                )
            ),
            I18nMessage(
                "modules.x.y", {"a": "s", "b": 12345678, "c": 0.123}, "cjwmodule"
            ),
        )

    def test_i18n_message_to_thrift_source_library(self):
        self.assertEqual(
            types.arrow_i18n_message_to_thrift(
                I18nMessage(
                    "modules.x.y", {"a": "s", "b": 12345678, "c": 0.123}, "cjwmodule"
                )
            ),
            ttypes.I18nMessage(
                "modules.x.y",
                {
                    "a": ttypes.I18nArgument(string_value="s"),
                    "b": ttypes.I18nArgument(i32_value=12345678),
                    "c": ttypes.I18nArgument(double_value=0.123),
                },
                "cjwmodule",
            ),
        )

    def test_i18n_message_from_thrift_source_none(self):
        self.assertEqual(
            types.thrift_i18n_message_to_arrow(
                ttypes.I18nMessage(
                    "modules.x.y",
                    {
                        "a": ttypes.I18nArgument(string_value="s"),
                        "b": ttypes.I18nArgument(i32_value=12345678),
                        "c": ttypes.I18nArgument(double_value=0.123),
                    },
                    None,
                )
            ),
            I18nMessage("modules.x.y", {"a": "s", "b": 12345678, "c": 0.123}, None),
        )

    def test_i18n_message_to_thrift_source_none(self):
        self.assertEqual(
            types.arrow_i18n_message_to_thrift(I18nMessage("modules.x.y", {}, None)),
            ttypes.I18nMessage("modules.x.y", {}, None),
        )

    def test_i18n_message_from_thrift_invalid_source(self):
        with self.assertRaises(ValueError):
            types.thrift_i18n_message_to_arrow(
                ttypes.I18nMessage("modules.x.y", {}, "random")
            )

    def test_prepend_step_quick_fix_action_from_thrift(self):
        self.assertEqual(
            types.thrift_quick_fix_action_to_arrow(
                ttypes.QuickFixAction(
                    prepend_step=ttypes.PrependStepQuickFixAction(
                        "filter", {"x": ttypes.Json(string_value="y")}
                    )
                )
            ),
            types.QuickFixAction.PrependStep("filter", {"x": "y"}),
        )

    def test_prepend_step_quick_fix_action_to_thrift(self):
        self.assertEqual(
            types.arrow_quick_fix_action_to_thrift(
                types.QuickFixAction.PrependStep("filter", {"x": "y"})
            ),
            ttypes.QuickFixAction(
                prepend_step=ttypes.PrependStepQuickFixAction(
                    "filter", {"x": ttypes.Json(string_value="y")}
                )
            ),
        )

    def test_quick_fix_from_thrift(self):
        self.assertEqual(
            types.thrift_quick_fix_to_arrow(
                ttypes.QuickFix(
                    ttypes.I18nMessage("click", {}, None),
                    ttypes.QuickFixAction(
                        prepend_step=ttypes.PrependStepQuickFixAction(
                            "filter", {"x": ttypes.Json(string_value="y")}
                        )
                    ),
                )
            ),
            types.QuickFix(
                I18nMessage("click", {}, None),
                types.QuickFixAction.PrependStep("filter", {"x": "y"}),
            ),
        )

    def test_quick_fix_to_thrift(self):
        self.assertEqual(
            types.arrow_quick_fix_to_thrift(
                types.QuickFix(
                    I18nMessage("click", {}, None),
                    types.QuickFixAction.PrependStep("filter", {"x": "y"}),
                )
            ),
            ttypes.QuickFix(
                ttypes.I18nMessage("click", {}, None),
                ttypes.QuickFixAction(
                    prepend_step=ttypes.PrependStepQuickFixAction(
                        "filter", {"x": ttypes.Json(string_value="y")}
                    )
                ),
            ),
        )

    def test_render_error_from_thrift(self):
        self.assertEqual(
            types.thrift_render_error_to_arrow(
                ttypes.RenderError(
                    ttypes.I18nMessage("foo", {}, None),
                    [
                        ttypes.QuickFix(
                            ttypes.I18nMessage("click", {}, None),
                            ttypes.QuickFixAction(
                                prepend_step=ttypes.PrependStepQuickFixAction(
                                    "filter", {"x": ttypes.Json(string_value="y")}
                                )
                            ),
                        )
                    ],
                )
            ),
            types.RenderError(
                I18nMessage("foo", {}, None),
                [
                    types.QuickFix(
                        I18nMessage("click", {}, None),
                        types.QuickFixAction.PrependStep("filter", {"x": "y"}),
                    )
                ],
            ),
        )

    def test_render_error_to_thrift(self):
        self.assertEqual(
            types.arrow_render_error_to_thrift(
                types.RenderError(
                    I18nMessage("foo", {}, None),
                    [
                        types.QuickFix(
                            I18nMessage("click", {}, None),
                            types.QuickFixAction.PrependStep("filter", {"x": "y"}),
                        )
                    ],
                )
            ),
            ttypes.RenderError(
                ttypes.I18nMessage("foo", {}, None),
                [
                    ttypes.QuickFix(
                        ttypes.I18nMessage("click", {}, None),
                        ttypes.QuickFixAction(
                            prepend_step=ttypes.PrependStepQuickFixAction(
                                "filter", {"x": ttypes.Json(string_value="y")}
                            )
                        ),
                    )
                ],
            ),
        )

    def test_render_result_from_thrift(self):
        pass  # TODO test RenderResult conversion

    def test_render_result_to_thrift(self):
        pass  # TODO test RenderResult conversion

    def test_fetch_result_from_thrift_disallow_directories(self):
        with self.assertRaisesRegex(ValueError, "must not include directory names"):
            types.thrift_fetch_result_to_arrow(
                ttypes.FetchResult("/etc/passwd", []), self.basedir
            )

    def test_fetch_result_from_thrift_disallow_hidden_files(self):
        with self.assertRaisesRegex(ValueError, "must not be hidden"):
            types.thrift_fetch_result_to_arrow(
                ttypes.FetchResult(".secrets", []), self.basedir
            )

    def test_fetch_result_from_thrift_disallow_non_files(self):
        with self.assertRaisesRegex(ValueError, "must exist"):
            types.thrift_fetch_result_to_arrow(
                ttypes.FetchResult("missing", []), self.basedir
            )

    def test_fetch_result_from_thrift_disallow_non_file(self):
        with tempfile.TemporaryDirectory(dir=str(self.basedir)) as tmpsubdir:
            with self.assertRaisesRegex(ValueError, "be a regular file"):
                types.thrift_fetch_result_to_arrow(
                    ttypes.FetchResult(Path(tmpsubdir).name, []),
                    self.basedir,
                )

    def test_fetch_result_from_thrift_happy_path(self):
        with tempfile.NamedTemporaryFile(dir=str(self.basedir)) as tf:
            filename = Path(tf.name).name
            self.assertEqual(
                types.thrift_fetch_result_to_arrow(
                    ttypes.FetchResult(
                        filename,
                        [ttypes.FetchError(ttypes.I18nMessage("hi", {}, None))],
                    ),
                    self.basedir,
                ),
                types.FetchResult(
                    Path(tf.name),
                    [types.FetchError(types.I18nMessage("hi", {}, None))],
                ),
            )

    def test_uploaded_file_to_thrift(self):
        self.assertEqual(
            types.arrow_uploaded_file_to_thrift(
                types.UploadedFile(
                    "x.tar.gz",
                    "839526fa-1adb-4eec-9d29-f5b4d2fbba30_x.tar.gz",
                    datetime.datetime(2021, 4, 20, 15, 48, 11, 906539),
                ),
            ),
            ttypes.UploadedFile(
                "x.tar.gz",
                "839526fa-1adb-4eec-9d29-f5b4d2fbba30_x.tar.gz",
                1618933691906539,
            ),
        )

    def test_uploaded_file_from_thrift(self):
        self.assertEqual(
            types.thrift_uploaded_file_to_arrow(
                ttypes.UploadedFile(
                    "x.tar.gz",
                    "839526fa-1adb-4eec-9d29-f5b4d2fbba30_x.tar.gz",
                    1618933691906539,
                )
            ),
            types.UploadedFile(
                "x.tar.gz",
                "839526fa-1adb-4eec-9d29-f5b4d2fbba30_x.tar.gz",
                datetime.datetime(2021, 4, 20, 15, 48, 11, 906539),
            ),
        )
