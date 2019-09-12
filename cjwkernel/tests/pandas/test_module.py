from contextlib import ExitStack  # workaround https://github.com/psf/black/issues/664
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd
from pandas.testing import assert_frame_equal
import pyarrow
from cjwkernel.tests.util import assert_arrow_table_equals, parquet_file
from cjwkernel.thrift import ttypes
from cjwkernel.types import I18nMessage, Params, RawParams, RenderError
from cjwkernel.pandas import module


class FetchTests(unittest.TestCase):
    def test_fetch_get_stored_dataframe_happy_path(self):
        async def fetch(params, *, get_stored_dataframe):
            df = await get_stored_dataframe()
            assert_frame_equal(df, pd.DataFrame({"A": [1]}))

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            stored_filename = ctx.enter_context(parquet_file({"A": [1]}))
            ctx.enter_context(patch.object(module, "fetch", fetch))
            module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    last_fetch_result=ttypes.FetchResult(stored_filename, []),
                    output_filename=output_filename,
                )
            )

    def test_fetch_get_stored_dataframe_unhandled_parquet_is_error(self):
        # Why an error? So module authors can handle it. They _created_ the
        # problem, after all. Let's help them detect it.
        async def fetch(params, *, get_stored_dataframe):
            with self.assertRaises(pyarrow.ArrowIOError):
                await get_stored_dataframe()

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            stored_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            Path(stored_filename).write_bytes(b"12345")
            module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    last_fetch_result=ttypes.FetchResult(stored_filename, []),
                    output_filename=output_filename,
                )
            )

    def test_fetch_get_stored_dataframe_empty_file_is_empty_table(self):
        async def fetch(params, *, get_stored_dataframe):
            df = await get_stored_dataframe()
            assert_frame_equal(df, pd.DataFrame())

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            stored_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    last_fetch_result=ttypes.FetchResult(stored_filename, []),
                    output_filename=output_filename,
                )
            )

    def test_fetch_get_stored_dataframe_none_is_none(self):
        async def fetch(params, *, get_stored_dataframe):
            df = await get_stored_dataframe()
            self.assertIsNone(df)

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    output_filename=output_filename,
                )
            )

    def test_fetch_get_input_dataframe_happy_path(self):
        async def fetch(params, *, get_input_dataframe):
            df = await get_input_dataframe()
            assert_frame_equal(df, pd.DataFrame({"A": [1]}))

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            input_filename = ctx.enter_context(parquet_file({"A": [1]}))
            ctx.enter_context(patch.object(module, "fetch", fetch))
            module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    input_table_parquet_filename=input_filename,
                    output_filename=output_filename,
                )
            )

    def test_fetch_get_input_dataframe_empty_file_is_empty_table(self):
        async def fetch(params, *, get_input_dataframe):
            df = await get_input_dataframe()
            assert_frame_equal(df, pd.DataFrame())

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            input_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    input_table_parquet_filename=input_filename,
                    output_filename=output_filename,
                )
            )

    def test_fetch_get_input_dataframe_none_is_none(self):
        async def fetch(params, *, get_input_dataframe):
            df = await get_input_dataframe()
            self.assertIsNone(df)

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    output_filename=output_filename,
                )
            )

    def test_fetch_params(self):
        async def fetch(params):
            self.assertEqual(params, {"A": [{"B": "C"}]})

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({"A": [{"B": "C"}]}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    output_filename=output_filename,
                )
            )

    def test_fetch_secrets(self):
        async def fetch(params, *, secrets):
            self.assertEqual(secrets, {"A": "B"})

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({"A": "B"}).to_thrift(),
                    output_filename=output_filename,
                )
            )

    def test_fetch_return_dataframe(self):
        async def fetch(params):
            return pd.DataFrame({"A": [1, 2, 3]})

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            result = module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    output_filename=output_filename,
                )
            )
            self.assertEqual(result.filename, output_filename)
            self.assertEqual(result.errors, [])
            arrow_table = pyarrow.parquet.read_table(output_filename, use_threads=False)
            assert_arrow_table_equals(arrow_table, {"A": [1, 2, 3]})

    def test_fetch_return_error(self):
        async def fetch(params):
            return "bad things"

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            result = module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    output_filename=output_filename,
                )
            )
            self.assertEqual(result.filename, output_filename)
            self.assertEqual(
                [RenderError.from_thrift(e) for e in result.errors],
                [RenderError(I18nMessage.TODO_i18n("bad things"))],
            )
            self.assertEqual(Path(output_filename).read_bytes(), b"")

    def test_fetch_sync(self):
        def fetch(params):
            return pd.DataFrame({"A": [1, 2, 3]})

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            result = module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    output_filename=output_filename,
                )
            )
            self.assertEqual(result.filename, output_filename)
            self.assertEqual(result.errors, [])
            arrow_table = pyarrow.parquet.read_table(output_filename, use_threads=False)
            assert_arrow_table_equals(arrow_table, {"A": [1, 2, 3]})
