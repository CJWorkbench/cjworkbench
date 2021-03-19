from columnchart import migrate_params


def test_v0_empty_y_columns():
    result = migrate_params(
        {
            "title": "Title",
            "x_axis_label": "X axis",
            "y_axis_label": "Y axis",
            "x_column": "X",
            "y_columns": "",
        }
    )
    assert result == {
        "title": "Title",
        "x_axis_label": "X axis",
        "y_axis_label": "Y axis",
        "x_column": "X",
        "y_columns": [],
    }


def test_v0_json_parse():
    result = migrate_params(
        {
            "title": "Title",
            "x_axis_label": "X axis",
            "y_axis_label": "Y axis",
            "x_column": "X",
            "y_columns": '[{"column": "X", "color": "#111111"}]',
        }
    )
    assert result == {
        "title": "Title",
        "x_axis_label": "X axis",
        "y_axis_label": "Y axis",
        "x_column": "X",
        "y_columns": [{"column": "X", "color": "#111111"}],
    }


def test_v1_no_op():
    result = migrate_params(
        {
            "title": "Title",
            "x_axis_label": "X axis",
            "y_axis_label": "Y axis",
            "x_column": "X",
            "y_columns": [{"column": "X", "color": "#111111"}],
        }
    )
    assert result == {
        "title": "Title",
        "x_axis_label": "X axis",
        "y_axis_label": "Y axis",
        "x_column": "X",
        "y_columns": [{"column": "X", "color": "#111111"}],
    }
