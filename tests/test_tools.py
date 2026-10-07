import pytest

from agent_workflow.tools import (
    ToolNotFoundError,
    ToolRegistry,
    build_default_registry,
)
from agent_workflow.tools.assign import (
    check_capacity,
    match_skills,
    require_fields,
    select_best,
    summarize_products,
)
from agent_workflow.tools.lookup import (
    attach_lookup,
    find_rows,
    first_record,
    require_any,
    summarize_record,
)
from agent_workflow.tools.reporting import (
    build_report,
    frequent_errors,
    group_metrics,
    slow_steps,
    with_averages,
)
from agent_workflow.tools.calc import calculate
from agent_workflow.tools.io import read_csv
from agent_workflow.tools.ranking import rank
from agent_workflow.tools.text import normalize_text, text_similarity
from agent_workflow.tools.validation import validate_required


def test_tools_register_and_retrieve():
    registry = ToolRegistry()
    registry.register("double", lambda x: x * 2)
    assert registry.get("double")(4) == 8
    assert set(registry.names()) == {"double"}


def test_default_registry_has_all_foundational_tools():
    registry = build_default_registry()
    assert set(registry.names()) == {
        "read_csv",
        "calculate",
        "validate_required",
        "normalize_text",
        "text_similarity",
        "rank",
        "transform_rows",
        "filter_rows",
        "select_columns",
        "join_rows",
        "read_table",
        "detect_columns",
        "normalize_columns",
        "normalize_fields",
        "partition_rows",
        "dedupe_rows",
        "find_duplicates",
        "classify_labels",
        "tag_rows",
        "require_fields",
        "summarize_products",
        "match_skills",
        "check_capacity",
        "select_best",
        "llm_generate",
        "generate_report",
        "require_any",
        "find_rows",
        "first_record",
        "attach_lookup",
        "summarize_record",
        "group_metrics",
        "with_averages",
        "frequent_errors",
        "slow_steps",
        "build_report",
    }


def test_unknown_tool_raises():
    registry = build_default_registry()
    with pytest.raises(KeyError):
        registry.get("does_not_exist")
    with pytest.raises(ToolNotFoundError):
        registry.get("does_not_exist")


def test_read_csv(tmp_path):
    csv_file = tmp_path / "products.csv"
    csv_file.write_text(
        "sku,name,price\nSKU1,Widget,10\nSKU2,Gadget,20\n",
        encoding="utf-8",
    )
    rows = read_csv(str(csv_file))
    assert rows == [
        {"sku": "SKU1", "name": "Widget", "price": "10"},
        {"sku": "SKU2", "name": "Gadget", "price": "20"},
    ]


def test_calculate_sum():
    assert calculate("sum", 1, 2, 3) == 6


def test_calculate_average():
    assert calculate("average", 10, 20, 30) == 20


def test_calculate_pct_diff():
    assert calculate("pct_diff", 120, 100) == 20.0
    assert calculate("pct_diff", 90, 100) == -10.0


def test_calculate_arithmetic():
    assert calculate("add", 4, 5) == 9
    assert calculate("subtract", 4, 5) == -1
    assert calculate("multiply", 4, 5) == 20
    assert calculate("divide", 20, 5) == 4


def test_calculate_errors():
    with pytest.raises(ValueError):
        calculate("pct_diff", 10, 0)
    with pytest.raises(ValueError):
        calculate("divide", 10, 0)
    with pytest.raises(ValueError):
        calculate("unknown_op", 1, 2)
    with pytest.raises(ValueError):
        calculate("average")


def test_validate_required_single_record():
    result = validate_required({"sku": "A", "name": "Widget"}, ["sku", "name"])
    assert result["valid"] is True
    assert result["issues"] == []


def test_validate_required_missing_and_empty():
    result = validate_required({"sku": "A", "name": ""}, ["sku", "name"])
    assert result["valid"] is False
    assert result["issues"] == [{"index": 0, "missing": ["name"]}]
    assert validate_required({"sku": "A"}, ["sku", "name"])["valid"] is False


def test_validate_required_batch():
    rows = [{"sku": "A", "name": "Widget"}, {"sku": "", "name": "Gadget"}]
    result = validate_required(rows, ["sku", "name"])
    assert result["valid"] is False
    assert result["issues"] == [{"index": 1, "missing": ["sku"]}]


def test_normalize_text():
    assert normalize_text("  Red   Cotton Shirt  ") == "red cotton shirt"


def test_text_similarity_deterministic():
    assert text_similarity("Red Shirt", "RED shirt") == 1.0
    first = text_similarity("Widget A", "Widget B")
    second = text_similarity("Widget A", "Widget B")
    assert first == second
    assert 0.0 <= first <= 1.0
    assert text_similarity("Widget A", "Widget A") == 1.0


def test_rank_orders_by_weighted_score():
    candidates = [
        {"name": "Alice", "skill": 3, "workload": 5},
        {"name": "Bob", "skill": 5, "workload": 2},
        {"name": "Carol", "skill": 4, "workload": 4},
    ]
    criteria = [
        {"field": "skill", "weight": 1},
        {"field": "workload", "weight": -1},
    ]
    results = rank(candidates, criteria)
    assert [r["candidate"]["name"] for r in results] == ["Bob", "Carol", "Alice"]
    assert results[0]["score"] == 3.0


def test_require_fields_passes_and_returns_values():
    assert require_fields(name="Widget", category="Coffee") == {
        "name": "Widget",
        "category": "Coffee",
    }


def test_require_fields_reports_missing():
    with pytest.raises(ValueError, match="Missing required inputs: .*category"):
        require_fields(name="Widget", category="")
    with pytest.raises(ValueError, match="Missing required inputs: .*goal, .*dates"):
        require_fields(goal="", dates="")


def test_summarize_products_counts_and_names():
    rows = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
    summary = summarize_products(rows)
    assert summary == {"product_count": 3, "product_names": ["A", "B", "C"]}


def test_match_skills_scores_each_employee():
    employees = [
        {"name": "Ana", "skills": "Python;SQL"},
        {"name": "Bob", "skills": "SQL"},
        {"name": "Dan", "skills": "Rust"},
    ]
    matched = match_skills(employees, ["Python", "SQL"])
    by_name = {row["name"]: row for row in matched}
    assert by_name["Ana"]["skill_match_count"] == 2
    assert by_name["Ana"]["skill_match_fraction"] == 1.0
    assert by_name["Bob"]["skill_match_count"] == 1
    assert by_name["Bob"]["skill_match_fraction"] == 0.5
    assert by_name["Dan"]["skill_match_count"] == 0
    assert by_name["Dan"]["skill_match_fraction"] == 0.0


def test_check_capacity_computes_available_capacity():
    employees = [
        {"name": "Ana", "workload": "3", "capacity": "5"},
        {"name": "Zed", "workload": "8", "capacity": "8"},
    ]
    checked = {row["name"]: row for row in check_capacity(employees)}
    assert checked["Ana"]["available_capacity"] == 2.0
    assert checked["Zed"]["available_capacity"] == 0.0


def test_select_best_returns_top_fit():
    ranked = [
        {"candidate": {"name": "Ana", "skill_match_fraction": 1.0, "available_capacity": 2}, "score": 12.0},
        {"candidate": {"name": "Cara", "skill_match_fraction": 1.0, "available_capacity": 1}, "score": 11.0},
        {"candidate": {"name": "Dan", "skill_match_fraction": 0.0, "available_capacity": 0}, "score": 0.0},
    ]
    selection = select_best(ranked)
    assert selection["recommended_employee"]["name"] == "Ana"
    assert selection["score"] == 12.0


def test_select_best_escalates_when_no_suitable():
    ranked = [
        {"candidate": {"name": "Zed", "skill_match_fraction": 1.0, "available_capacity": 0}, "score": 10.0},
        {"candidate": {"name": "Yara", "skill_match_fraction": 0.0, "available_capacity": 2}, "score": 2.0},
    ]
    with pytest.raises(ValueError, match="escalate for manual assignment"):
        select_best(ranked)


def test_require_any_accepts_single_identifier():
    assert require_any(order_id="ORD-1001", customer_email="") == {"order_id": "ORD-1001"}
    assert require_any(order_id="", customer_email="bob@example.com") == {
        "customer_email": "bob@example.com"
    }


def test_require_any_rejects_when_none_supplied():
    with pytest.raises(ValueError, match="at least one of order_id, customer_email"):
        require_any(order_id="", customer_email="")


def test_find_rows_matches_supplied_criteria_case_insensitive():
    rows = [
        {"order_id": "ORD-1001", "customer_email": "Alice@Example.com"},
        {"order_id": "ORD-1002", "customer_email": "bob@example.com"},
    ]
    assert [r["order_id"] for r in find_rows(rows, order_id="ORD-1001", customer_email="")] == [
        "ORD-1001"
    ]
    assert [r["order_id"] for r in find_rows(rows, customer_email="alice@example.com")] == [
        "ORD-1001"
    ]
    assert find_rows(rows, order_id="NOPE") == []


def test_first_record_returns_head_or_raises():
    assert first_record([{"id": 1}, {"id": 2}]) == {"id": 1}
    with pytest.raises(ValueError, match="No matching record found"):
        first_record([])


def test_attach_lookup_merges_source_and_keeps_missing():
    record = {"order_id": "ORD-1", "shipment_id": "SHP-1"}
    source = [{"shipment_id": "SHP-1", "status": "delivered", "tracking": "T1"}]
    assert attach_lookup(record, source, "shipment_id", "shipment_id") == {
        "order_id": "ORD-1",
        "shipment_id": "SHP-1",
        "status": "delivered",
        "tracking": "T1",
    }
    assert attach_lookup({"order_id": "ORD-2", "shipment_id": "SHP-9"}, source, "shipment_id", "shipment_id") == {
        "order_id": "ORD-2",
        "shipment_id": "SHP-9",
    }


def test_summarize_record_includes_optional_when_available():
    record = {"order_id": "ORD-1", "order_status": "shipped", "shipment_status": "delivered", "tracking_number": "T1"}
    summary = summarize_record(record, ["order_id", "order_status", "shipment_status"], ["tracking_number"])
    assert "tracking_number" in summary
    bare = dict(record)
    bare["tracking_number"] = ""
    summary = summarize_record(bare, ["order_id", "order_status", "shipment_status"], ["tracking_number"])
    assert "tracking_number" not in summary


def test_group_metrics_computes_rates():
    rows = [
        {"workflow_id": "A", "status": "success"},
        {"workflow_id": "A", "status": "failure"},
        {"workflow_id": "A", "status": "failure"},
        {"workflow_id": "B", "status": "success"},
    ]
    metrics = group_metrics(rows)
    by_id = {m["workflow_id"]: m for m in metrics}
    assert by_id["A"]["total"] == 3
    assert by_id["A"]["successful"] == 1
    assert by_id["A"]["failed"] == 2
    assert by_id["A"]["success_rate"] == pytest.approx(0.3333)
    assert by_id["A"]["failure_rate"] == pytest.approx(0.6667)
    assert by_id["B"]["failure_rate"] == 0.0


def test_with_averages_attaches_mean_time():
    rows = [
        {"workflow_id": "A", "execution_time_s": 2.0},
        {"workflow_id": "A", "execution_time_s": 4.0},
        {"workflow_id": "B", "execution_time_s": 9.0},
    ]
    metrics = group_metrics(rows)
    enriched = with_averages(metrics, rows)
    by_id = {m["workflow_id"]: m for m in enriched}
    assert by_id["A"]["average_time_s"] == 3.0
    assert by_id["A"]["executions"] == 2
    assert by_id["B"]["average_time_s"] == 9.0


def test_frequent_errors_groups_above_min_count():
    rows = [
        {"error": "TimeoutError"},
        {"error": "TimeoutError"},
        {"error": "EncodingError"},
        {"error": ""},
    ]
    items = frequent_errors(rows, min_count=2)
    assert items == [{"error": "TimeoutError", "count": 2}]


def test_slow_steps_flags_steps_above_min_average():
    rows = [
        {"slowest_step": "load", "execution_time_s": 3.0},
        {"slowest_step": "load", "execution_time_s": 4.0},
        {"slowest_step": "transform", "execution_time_s": 12.0},
    ]
    items = slow_steps(rows, min_average=5.0)
    assert items == [{"step": "transform", "executions": 1, "average_time_s": 12.0}]


def test_build_report_flags_and_recommends():
    metrics = [
        {"workflow_id": "A", "failure_rate": 0.0, "average_time_s": 3.0},
        {"workflow_id": "B", "failure_rate": 0.5, "average_time_s": 9.0},
    ]
    rule = {
        "op": "or",
        "rules": [
            {"op": "gt", "left": {"field": "failure_rate"}, "right": {"value": 0.10}},
            {"op": "gt", "left": {"field": "average_time_s"}, "right": {"value": 10.0}},
        ],
    }
    report = build_report(metrics, [{"error": "TimeoutError", "count": 2}], [{"step": "transform", "average_time_s": 12.0}], rule)
    assert [w["workflow_id"] for w in report["flagged_workflows"]] == ["B"]
    assert any("failure rate" in r for r in report["recommendations"])
    assert any("TimeoutError" in r for r in report["recommendations"])
    assert any("transform" in r for r in report["recommendations"])