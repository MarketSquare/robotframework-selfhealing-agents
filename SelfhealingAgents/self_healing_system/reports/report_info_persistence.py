import json

from pathlib import Path
from typing import List, Iterable

from SelfhealingAgents.self_healing_system.schemas.internal_state.report_data import ReportData

REPORT_INFO_FILE = Path("report_info.json")


def save_report_info(report_info: List[ReportData], path: Path | str = REPORT_INFO_FILE) -> None:
    """Persist report_info as JSON in the given path. Used to preserve healing steps if Rerun-option of failed
       tests is activated as the rerun would overwrite the previous run.
    """
    path = Path(path)
    payload = [item.model_dump() for item in report_info]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_report_info(path: Path | str = REPORT_INFO_FILE) -> List[ReportData]:
    """Load report_info from JSON. Returns [] if file missing or invalid."""
    path = Path(path)
    if not path.is_file():
        return []

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
        return [ReportData.model_validate(obj) for obj in raw]
    except Exception:
        return []


def deduplicate_report_info(report_info: Iterable[ReportData]) -> List[ReportData]:
    """Remove duplicate ReportData entries, keeping the first occurrence.
    Two entries are considered duplicates based on:
      - file
      - keyword_source
      - test_name
      - locator_origin
      - keyword
      - keyword_args
      - lineno
      - failed_locator
    Differences in healed_locator or tried_locators do NOT affect duplicate status.
    """
    seen = set()
    unique: List[ReportData] = []
    for item in report_info:
        key = (
            item.file,
            item.keyword_source,
            item.test_name,
            item.locator_origin,
            item.keyword,
            tuple(item.keyword_args),
            item.lineno,
            item.failed_locator,
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def sort_report_info(report_info: Iterable[ReportData]) -> List[ReportData]:
    """Sort report entries by file and then by lineno (ascending)."""
    return sorted(report_info, key=lambda r: (r.file, r.lineno))