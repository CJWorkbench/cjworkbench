import os
import shutil
from pathlib import Path
from tempfile import mkstemp
from typing import Any, Dict, NamedTuple, Optional

import pyarrow as pa
from cjwmodule.types import FetchResult

import cjwkernel.pandas.module
from cjwkernel.tests.util import arrow_table_context
from cjwkernel.thrift import ttypes
from cjwkernel.types import (
    Params,
    RenderResult,
    Tab,
    arrow_fetch_result_to_thrift,
    arrow_params_to_thrift,
    arrow_tab_to_thrift,
    thrift_render_result_to_arrow,
)
from cjwkernel.util import create_tempdir
from cjwkernel.validate import load_untrusted_arrow_file_with_columns


class RenderOutcome(NamedTuple):
    """Result of calling render().

    This is so you can observe the side effects.
    """

    result: RenderResult
    """The RenderResult returned by the module."""

    path: Path
    """The file written by the module.

    `ModuleTestEnv.__exit__()` will delete this temporary file.
    """

    def read_table(self) -> pa.Table:
        """Table written to disk.

        Raise `ValidateError` if the file on disk is not a Workbench-valid
        table.

        Raise `ValidateError` if the file on disk is empty. Workbench accepts
        empty values, but we differentiate here so calling code won't be
        ambiguous.
        """
        return load_untrusted_arrow_file_with_columns(self.path)[0]


class ModuleTestEnv:
    r"""Module code and environment to execute it

    Usage:

        def render(arrow_table, *args, **kwargs):
            raise NotImplementedError

        def test_something():
            with ModuleTextEnv(render=render) as env:
                output_path = env.call_render(
                    table=make_table(make_column("A", [1])), params={}
                )
                assert_arrow_table_equals(
                    env.read_table(output_path), make_table(make_column("A", [2])),
                )

    The same `ModuleTestEnv` can test any framework. Choose a framework by
    passing the correct function signatures to `__init__()`.
    """

    def __init__(self, **functions):
        self.functions = functions

    def __enter__(self):
        self.basedir = create_tempdir()
        mod = cjwkernel.pandas.module
        self.old_functions = {
            name: mod.__dict__[name] for name in self.functions.keys()
        }
        mod.__dict__.update(self.functions)
        return self

    def __exit__(self, *args):
        cjwkernel.pandas.module.__dict__.update(self.old_functions)
        del self.old_functions
        shutil.rmtree(self.basedir)
        del self.basedir

    def call_render(
        self,
        table: pa.Table,
        params: Dict[str, Any],
        tab: Tab = Tab("tab-1", "Tab 1"),
        fetch_result: Optional[FetchResult] = None,
    ) -> RenderOutcome:
        """Conveniently call the module's `render_thrift()`.

        The calling convention is designed for ease of testing.
        """
        # tempfile will be deleted in __exit__().
        fd, output_filename = mkstemp(prefix="out-", suffix=".arrow", dir=self.basedir)
        os.close(fd)
        output_path = Path(output_filename)

        with arrow_table_context(table, dir=self.basedir) as (input_path, _):
            old_cwd = os.getcwd()
            os.chdir(self.basedir)
            try:
                thrift_result = cjwkernel.pandas.module.render_thrift(
                    ttypes.RenderRequest(
                        basedir=self.basedir,
                        input_filename=input_path.name,
                        params=arrow_params_to_thrift(Params(params)),
                        tab=arrow_tab_to_thrift(tab),
                        fetch_result=(
                            arrow_fetch_result_to_thrift(fetch_result)
                            if fetch_result is not None
                            else None
                        ),
                        output_filename=output_path.name,
                    )
                )
            finally:
                os.chdir(old_cwd)
            arrow_result = thrift_render_result_to_arrow(thrift_result)
            return RenderOutcome(arrow_result, output_path)
