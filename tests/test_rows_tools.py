import pytest

from agent_workflow.tools.rows import filter_rows, join_rows, select_columns, transform_rows


def test_transform_rows_adds_computed_column():
    rows = [
        {"sku": "A", "stock": "5", "min_stock": "10"},
        {"sku": "B", "stock": "20", "min_stock": "10"},
    ]
    result = transform_rows(rows, "stock_diff", "subtract", ["stock", "min_stock"])
    assert result[0]["stock_diff"] == -5.0
    assert result[1]["stock_diff"] == 10.0
    assert [r["sku"] for r in result] == ["A", "B"]


def test_transform_rows_pct_diff():
    rows = [{"internal": "80", "vendor": "72"}]
    result = transform_rows(rows, "diff", "pct_diff", ["internal", "vendor"])
    assert abs(result[0]["diff"] - 11.11111111111111) < 1e-9


def test_filter_rows_operators():
    rows = [
        {"id": 1, "value": "5"},
        {"id": 2, "value": "10"},
        {"id": 3, "value": "15"},
    ]
    assert [r["id"] for r in filter_rows(rows, "value", "lt", 10)] == [1]
    assert [r["id"] for r in filter_rows(rows, "value", "ge", 10)] == [2, 3]
    assert [r["id"] for r in filter_rows(rows, "value", "outside", 4)] == [1, 2, 3]


def test_filter_rows_unknown_operator():
    with pytest.raises(ValueError):
        filter_rows([{"value": "1"}], "value", "approx", 1)


def test_select_columns_projects_fields():
    rows = [{"sku": "A", "name": "Widget", "extra": 1}]
    assert select_columns(rows, ["sku", "name"]) == [{"sku": "A", "name": "Widget"}]


def test_join_rows_merges_by_key(tmp_path):
    left = [{"sku": "A", "internal": "50"}, {"sku": "B", "internal": "80"}]
    right = tmp_path / "vendor.csv"
    right.write_text("sku,vendor_price\nA,55\nB,72\n", encoding="utf-8")
    joined = join_rows(left, str(right), "sku", "sku")
    assert joined == [
        {"sku": "A", "internal": "50", "vendor_price": "55"},
        {"sku": "B", "internal": "80", "vendor_price": "72"},
    ]