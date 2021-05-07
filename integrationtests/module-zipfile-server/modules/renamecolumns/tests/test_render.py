from pathlib import Path
from typing import NamedTuple

import pytest
from cjwmodule.arrow.testing import assert_result_equals, make_column, make_table
from cjwmodule.arrow.types import ArrowRenderResult
from cjwmodule.spec.testing import param_factory
from cjwmodule.testing.i18n import cjwmodule_i18n_message, i18n_message
from cjwmodule.types import RenderError

from renamecolumns import RenderErrorException, _parse_custom_list, _parse_renames
from renamecolumns import render_arrow_v1 as render


class Settings(NamedTuple):
    MAX_BYTES_PER_COLUMN_NAME: int = 100


P = param_factory(Path(__file__).parent.parent / "renamecolumns.yaml")


def test_parse_renames_ignore_missing_columns():
    assert _parse_renames({"A": "B", "C": "D"}, ["A", "X"], settings=Settings()) == (
        {"A": "B"},
        [],
    )


def test_parse_renames_swap():
    assert _parse_renames(
        {"A": "B", "B": "C", "C": "A"}, ["A", "B", "C"], settings=Settings()
    ) == ({"A": "B", "B": "C", "C": "A"}, [])


def test_parse_renames_avoid_duplicates():
    assert _parse_renames(
        {"A": "B", "C": "B"}, ["A", "B", "C"], settings=Settings()
    ) == (
        {"A": "B 2", "C": "B 3"},
        [
            RenderError(
                cjwmodule_i18n_message(
                    id="util.colnames.warnings.numbered",
                    arguments={"n_columns": 2, "first_colname": "B 2"},
                ),
            )
        ],
    )


def test_parse_renames_avoid_duplicates_without_original():
    assert _parse_renames({"A": "C", "B": "C"}, ["A", "B"], settings=Settings()) == (
        {"A": "C", "B": "C 2"},
        [
            RenderError(
                cjwmodule_i18n_message(
                    id="util.colnames.warnings.numbered",
                    arguments={"n_columns": 1, "first_colname": "C 2"},
                )
            )
        ],
    )


def test_parse_renames_rename_too_long_columns():
    assert _parse_renames(
        {"A": "BBBBBBBBBB", "BBBBBBBBBB": "BBBBBBBBBB"},
        ["A", "BBBBBBBBBB"],
        settings=Settings(MAX_BYTES_PER_COLUMN_NAME=10),
    ) == (
        {"A": "BBBBBBBB 2"},
        [
            RenderError(
                cjwmodule_i18n_message(
                    "util.colnames.warnings.truncated",
                    {"n_columns": 1, "first_colname": "BBBBBBBB 2", "n_bytes": 10},
                )
            ),
            RenderError(
                cjwmodule_i18n_message(
                    "util.colnames.warnings.numbered",
                    {"n_columns": 1, "first_colname": "BBBBBBBB 2"},
                )
            ),
        ],
    )


def test_parse_custom_list_by_newline():
    assert _parse_custom_list("X\nY\nZ", ["A", "B", "C"], settings=Settings()) == (
        {"A": "X", "B": "Y", "C": "Z"},
        [],
    )


def test_parse_custom_list_by_comma():
    assert _parse_custom_list("X, Y, Z", ["A", "B", "C"], settings=Settings()) == (
        {"A": "X", "B": "Y", "C": "Z"},
        [],
    )


def test_parse_custom_list_newline_means_ignore_commas():
    assert _parse_custom_list(
        "X,Y\nZ,A\nB,C", ["A", "B", "C"], settings=Settings()
    ) == ({"A": "X,Y", "B": "Z,A", "C": "B,C"}, [])


def test_parse_custom_list_trailing_newline_still_split_by_comma():
    # If the user added a newline to the end, it's still commas.
    assert _parse_custom_list("X, Y, Z\n", ["A", "B", "C"], settings=Settings()) == (
        {"A": "X", "B": "Y", "C": "Z"},
        [],
    )


def test_parse_custom_list_allow_too_few_columns():
    assert _parse_custom_list("X\nY", ["A", "B", "C"], settings=Settings()) == (
        {"A": "X", "B": "Y"},
        [],
    )


def test_parse_custom_list_ignore_no_op_renames():
    assert _parse_custom_list("A\nY\nC", ["A", "B", "C"], settings=Settings()) == (
        {"B": "Y"},
        [],
    )


def test_parse_custom_list_too_many_columns_is_render_error():
    with pytest.raises(RenderErrorException):
        _parse_custom_list("A\nB\nC\nD", ["A", "B", "C"], settings=Settings())


def test_parse_custom_list_ignore_trailing_newline():
    assert _parse_custom_list("X\nY\n", ["A", "B"], settings=Settings()) == (
        {"A": "X", "B": "Y"},
        [],
    )  # no ValueError


def test_parse_custom_list_skip_whitespace_columns():
    assert _parse_custom_list("X\n\nZ", ["A", "B", "C"], settings=Settings()) == (
        {"A": "X", "C": "Z"},
        [],
    )


def test_render_rename_empty_is_no_op():
    result = render(
        make_table(make_column("A", ["x"])),
        P(custom_list=False, renames={}),
        settings=Settings(),
    )
    assert_result_equals(result, ArrowRenderResult(make_table(make_column("A", ["x"]))))


def test_render_rename_custom_list_empty_is_no_op():
    result = render(
        make_table(make_column("A", ["x"])),
        P(custom_list=True, list_string=""),
        settings=Settings(),
    )
    assert_result_equals(result, ArrowRenderResult(make_table(make_column("A", ["x"]))))


def test_render_rename_custom_list_too_many_columns_is_error():
    result = render(
        make_table(make_column("A", ["x"])),
        P(custom_list=True, list_string="X,Y"),
        settings=Settings(),
    )
    assert_result_equals(
        result,
        ArrowRenderResult(
            make_table(),
            [
                RenderError(
                    i18n_message(
                        "badParam.custom_list.wrongNumberOfNames",
                        {"n_names": 2, "n_columns": 1},
                    )
                )
            ],
        ),
    )


def test_render_rename_formats():
    result = render(
        make_table(make_column("A", ["x"]), make_column("B", [1], format="{:d}")),
        P(custom_list=False, renames={"A": "X", "B": "Y"}),
        settings=Settings(),
    )
    assert_result_equals(
        result,
        ArrowRenderResult(
            make_table(make_column("X", ["x"]), make_column("Y", [1], format="{:d}"))
        ),
    )


def test_render_rename_swap_columns():
    result = render(
        make_table(make_column("A", ["x"]), make_column("B", [1], format="{:d}")),
        P(custom_list=False, renames={"A": "B", "B": "A"}),
        settings=Settings(),
    )
    assert_result_equals(
        result,
        ArrowRenderResult(
            make_table(make_column("B", ["x"]), make_column("A", [1], format="{:d}"))
        ),
    )


def test_render_custom_list():
    result = render(
        make_table(make_column("A", ["x"]), make_column("B", [1])),
        P(custom_list=True, list_string="X\nY"),
        settings=Settings(),
    )
    assert_result_equals(
        result,
        ArrowRenderResult(make_table(make_column("X", ["x"]), make_column("Y", [1]))),
    )


def test_render_dict_disallow_rename_to_null():
    result = render(
        make_table(make_column("A", ["x"])),
        P(renames={"A": ""}),
        settings=Settings(),
    )
    assert_result_equals(result, ArrowRenderResult(make_table(make_column("A", ["x"]))))


def test_render_custom_list_disallow_rename_to_null():
    result = render(
        make_table(
            make_column("A", ["a"]), make_column("B", ["b"]), make_column("C", ["c"])
        ),
        P(custom_list=True, list_string="D\n\nF"),
        settings=Settings(),
    )
    assert_result_equals(
        result,
        ArrowRenderResult(
            make_table(
                make_column("D", ["a"]),
                make_column("B", ["b"]),
                make_column("F", ["c"]),
            )
        ),
    )
