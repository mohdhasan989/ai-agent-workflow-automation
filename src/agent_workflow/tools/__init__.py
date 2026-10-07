from .assign import check_capacity, match_skills, require_fields, select_best, summarize_products
from .aggregate import count_groups, group_rows, report_counts
from .calc import calculate
from .classify import classify_labels, tag_rows
from .duplicates import find_duplicates
from .io import read_csv
from .llm_tool import build_llm_tools
from .lookup import attach_lookup, find_rows, first_record, require_any, summarize_record
from .ranking import rank
from .registry import ToolNotFoundError, ToolRegistry
from .reporting import build_report, frequent_errors, group_metrics, slow_steps, with_averages
from .rows import (
    dedupe_rows,
    filter_rows,
    join_rows,
    normalize_fields,
    partition_rows,
    select_columns,
    transform_rows,
)
from .table import detect_columns, normalize_columns, read_table
from .text import normalize_text, text_similarity
from .validation import validate_required

_DEFAULT_TOOLS = [
    ("read_csv", read_csv),
    ("calculate", calculate),
    ("validate_required", validate_required),
    ("normalize_text", normalize_text),
    ("text_similarity", text_similarity),
    ("rank", rank),
    ("transform_rows", transform_rows),
    ("filter_rows", filter_rows),
    ("select_columns", select_columns),
    ("join_rows", join_rows),
    ("read_table", read_table),
    ("detect_columns", detect_columns),
    ("normalize_columns", normalize_columns),
    ("normalize_fields", normalize_fields),
    ("partition_rows", partition_rows),
    ("dedupe_rows", dedupe_rows),
    ("find_duplicates", find_duplicates),
    ("classify_labels", classify_labels),
    ("tag_rows", tag_rows),
    ("require_fields", require_fields),
    ("summarize_products", summarize_products),
    ("match_skills", match_skills),
    ("check_capacity", check_capacity),
    ("select_best", select_best),
    ("require_any", require_any),
    ("find_rows", find_rows),
    ("first_record", first_record),
    ("attach_lookup", attach_lookup),
    ("summarize_record", summarize_record),
    ("group_metrics", group_metrics),
    ("with_averages", with_averages),
    ("frequent_errors", frequent_errors),
    ("slow_steps", slow_steps),
    ("build_report", build_report),
    ("group_rows", group_rows),
    ("count_groups", count_groups),
    ("report_counts", report_counts),
]


def build_default_registry(llm=None) -> ToolRegistry:
    registry = ToolRegistry()
    for name, function in _DEFAULT_TOOLS:
        registry.register(name, function)
    for name, function in build_llm_tools(llm).items():
        registry.register(name, function)
    return registry


__all__ = ["ToolRegistry", "ToolNotFoundError", "build_default_registry"]