import unittest
from datetime import date, datetime
from pathlib import Path

from cjwmodule.spec.paramschema import ParamSchema
from cjwmodule.arrow.testing import assert_arrow_table_equals, make_column, make_table
from cjwmodule.arrow.types import ArrowRenderResult
from cjwmodule.types import (
    FetchError,
    FetchResult,
    I18nMessage,
    QuickFix,
    QuickFixAction,
    RenderError,
)

from cjwkernel.tests.util import arrow_table_context, override_settings
from cjwkernel.types import RenderResult, TabOutput, UploadedFile
from cjwkernel.util import tempfile_context
from .util import ModuleTestEnv


class RenderTests(unittest.TestCase):
    def test_render_with_tab_name(self):
        def render_arrow_v1(table, params, *, tab_name, **kwargs):
            self.assertEqual(tab_name, "Tab X")
            return ArrowRenderResult(make_table())

        with ModuleTestEnv(render_arrow_v1=render_arrow_v1) as env:
            env.call_render(make_table(), {}, tab_name="Tab X")

    @override_settings(MAX_ROWS_PER_TABLE=12)
    def test_render_with_settings(self):
        def render_arrow_v1(table, params, *, settings, **kwargs):
            self.assertEqual(settings.MAX_ROWS_PER_TABLE, 12)
            return ArrowRenderResult(make_table())

        with ModuleTestEnv(render_arrow_v1=render_arrow_v1) as env:
            env.call_render(make_table(), {})

    def test_render_exception_raises(self):
        def render_arrow_v1(table, params, **kwargs):
            raise RuntimeError("move along")

        with ModuleTestEnv(render_arrow_v1=render_arrow_v1) as env:
            with self.assertRaisesRegexp(RuntimeError, "move along"):
                env.call_render(make_table(), {})

    def test_render_invalid_retval(self):
        def render_arrow_v1(table, params, **kwargs):
            return {"foo": "bar"}  # not a valid retval

        with ModuleTestEnv(render_arrow_v1=render_arrow_v1) as env:
            with self.assertRaisesRegexp(
                ValueError, "must return a cjwmodule.arrow.types.ArrowRenderResult"
            ):
                env.call_render(make_table(), {})

    def test_render_fetch_result(self):
        def render_arrow_v1(table, params, *, fetch_result, **kwargs):
            self.assertEqual(fetch_result, FetchResult(tf))
            self.assertEqual(fetch_result.path.read_bytes(), b"abcd")
            return ArrowRenderResult(make_table())

        with ModuleTestEnv(render_arrow_v1=render_arrow_v1) as env:
            with tempfile_context(dir=env.basedir) as tf:
                tf.write_bytes(b"abcd")
                env.call_render(make_table(), {}, fetch_result=FetchResult(path=tf))

    def test_render_fetch_result_errors(self):
        def render_arrow_v1(table, params, *, fetch_result, **kwargs):
            self.assertEqual(
                fetch_result.errors, [FetchError(I18nMessage("foo", {}, "cjwmodule"))]
            )
            return ArrowRenderResult(make_table())

        with ModuleTestEnv(render_arrow_v1=render_arrow_v1) as env:
            with tempfile_context(dir=env.basedir) as tf:
                env.call_render(
                    make_table(),
                    {},
                    fetch_result=FetchResult(
                        Path(tf.name), [FetchError(I18nMessage("foo", {}, "cjwmodule"))]
                    ),
                )

    def test_render_input_table(self):
        now = datetime.now()

        def render_arrow_v1(table, params, **kwargs):
            assert_arrow_table_equals(
                table,
                make_table(
                    make_column("A", ["x"]),
                    make_column("B", [1], format="{:,.3f}"),
                    make_column("C", [now]),
                    make_column("D", [date(2021, 4, 12)], unit="week"),
                ),
            )
            return ArrowRenderResult(make_table())

        with ModuleTestEnv(render_arrow_v1=render_arrow_v1) as env:
            env.call_render(
                make_table(
                    make_column("A", ["x"]),
                    make_column("B", [1], format="{:,.3f}"),
                    make_column("C", [now]),
                    make_column("D", [date(2021, 4, 12)], unit="week"),
                ),
                {},
            )

    def test_render_write_output_table(self):
        now = datetime.now()

        def render_arrow_v1(table, params, **kwargs):
            return ArrowRenderResult(
                make_table(
                    make_column("A", ["x"]),
                    make_column("B", [1], format="{:,.3f}"),
                    make_column("C", [now]),
                    make_column("D", [date(2021, 4, 12)], unit="week"),
                )
            )

        with ModuleTestEnv(render_arrow_v1=render_arrow_v1) as env:
            outcome = env.call_render(make_table(), {})
            self.assertEqual(outcome.result, RenderResult())
            assert_arrow_table_equals(
                outcome.read_table(),
                make_table(
                    make_column("A", ["x"]),
                    make_column("B", [1], format="{:,.3f}"),
                    make_column("C", [now]),
                    make_column("D", [date(2021, 4, 12)], unit="week"),
                ),
            )

    def test_render_result(self):
        error = RenderError(
            message=I18nMessage("x", {"y": 1}, "module"),
            quick_fixes=[
                QuickFix(
                    button_text=I18nMessage("z", {}, "module"),
                    action=QuickFixAction.PrependStep("converttotext", {"a": "b"}),
                )
            ],
        )  # we're testing it is serialized+deserialized correctly

        def render_arrow_v1(table, params, **kwargs):
            return ArrowRenderResult(make_table(make_column("A", ["x"])), [error])

        with ModuleTestEnv(render_arrow_v1=render_arrow_v1) as env:
            outcome = env.call_render(make_table(), {})
            self.assertEqual(outcome.result, RenderResult([error]))

    def test_render_json(self):
        def render_arrow_v1(table, params, **kwargs):
            return ArrowRenderResult(make_table(), [], {"json": ["A-", 1]})

        with ModuleTestEnv(render_arrow_v1=render_arrow_v1) as env:
            outcome = env.call_render(make_table(), {})
            self.assertEqual(outcome.result, RenderResult([], {"json": ["A-", 1]}))

    def test_render_tab_outputs(self):
        def render_arrow_v1(table, params, *, tab_outputs, **kwargs):
            self.assertEqual(params["tab"], "tab-x")
            self.assertEqual(tab_outputs["tab-x"].tab_name, "Tab X")
            assert_arrow_table_equals(
                tab_outputs["tab-x"].table,
                make_table(
                    make_column("X", [1], format="{:,d}"),
                    make_column("Y", ["y"]),
                ),
            )
            return ArrowRenderResult(make_table())

        param_schema = ParamSchema.Dict({"tab": ParamSchema.Tab()})
        with ModuleTestEnv(
            param_schema=param_schema, render_arrow_v1=render_arrow_v1
        ) as env:
            with arrow_table_context(
                make_column("X", [1], format="{:,d}"),
                make_column("Y", ["y"]),
                dir=env.basedir,
            ) as (path, _):
                env.call_render(
                    make_table(),
                    params={"tab": "tab-x"},
                    tab_outputs={
                        "tab-x": TabOutput(tab_name="Tab X", table_filename=path.name)
                    },
                )

    def test_render_uploaded_files(self):
        def render_arrow_v1(table, params, *, uploaded_files, **kwargs):
            self.assertEqual(params["file"], "406b5e37-f217-4e87-b6b2-eede3bec6492")
            uploaded_file = uploaded_files[params["file"]]
            self.assertEqual(uploaded_file.name, "x.data")
            self.assertEqual(uploaded_file.uploaded_at, datetime(2021, 4, 21, 12, 4, 5))
            return ArrowRenderResult(make_table())

        param_schema = ParamSchema.Dict({"file": ParamSchema.File()})
        with ModuleTestEnv(
            param_schema=param_schema, render_arrow_v1=render_arrow_v1
        ) as env:
            temp_path = env.basedir / "406b5e37-f217-4e87-b6b2-eede3bec6492_x.data"
            temp_path.write_bytes(b"hello, world!")
            env.call_render(
                make_table(),
                params={"file": "406b5e37-f217-4e87-b6b2-eede3bec6492"},
                uploaded_files={
                    "406b5e37-f217-4e87-b6b2-eede3bec6492": UploadedFile(
                        name="x.data",
                        filename=temp_path.name,
                        uploaded_at=datetime(2021, 4, 21, 12, 4, 5),
                    ),
                },
            )
