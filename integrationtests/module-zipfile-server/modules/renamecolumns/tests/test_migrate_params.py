from pathlib import Path

from cjwmodule.spec.testing import param_factory

from renamecolumns import migrate_params

P = param_factory(Path(__file__).parent.parent / "renamecolumns.yaml")


def test_v0_empty_rename_entries():
    assert migrate_params(
        {"custom_list": False, "list_string": "A\nB\nC", "rename-entries": ""}
    ) == P(custom_list=False, list_string="A\nB\nC", renames={})


def test_v0():
    assert (
        migrate_params(
            {
                "custom_list": False,
                "list_string": "A\nB\nC",
                "rename-entries": '{"A":"B","B":"C"}',
            }
        )
        == P(custom_list=False, list_string="A\nB\nC", renames={"A": "B", "B": "C"})
    )


def test_v1():
    assert (
        migrate_params(
            {
                "custom_list": False,
                "list_string": "A\nB\nC",
                "renames": {"A": "B", "B": "C"},
            }
        )
        == P(custom_list=False, list_string="A\nB\nC", renames={"A": "B", "B": "C"})
    )
