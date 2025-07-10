import os
import re
import html
from pathlib import Path
from typing import Any, List, Tuple, Set, Optional
from robot.api.parsing import get_model, ModelTransformer


from RobotAid.self_healing_system.reports.report_data import ReportData


LOCATOR_PATTERN = re.compile(
    r'^(?:id|xpath|css|name|link|dom|jquery)=', re.IGNORECASE
)


class ReportGenerator:
    """Generates HTML action logs and healed test suites after locator healing."""

    def __init__(self) -> None:
        """Initializes report directories under the project workspace."""
        self.workspace_dir: Path = Path(__file__).resolve().parents[4]
        self.reports_dir: Path = self.workspace_dir / "reports"
        os.makedirs(self.reports_dir, exist_ok=True)

    def generate_reports(self, report_info: List[ReportData]) -> None:
        """Generates all configured reports.

        Args:
            report_info (List[ReportData]): Data about each healing event.
        """
        self._generate_action_log(report_info)
        self._generate_healed_test_suites(report_info)
        self._generate_diff_file(report_info)

    def _generate_action_log(self, report_info: List[ReportData]) -> None:
        """Writes an HTML table summarizing each locator healing event.

        Args:
            report_info (List[ReportData]): Data about each healing event.
        """
        header = (
            "<html><head><meta charset='utf-8'><title>Locator Healing Report</title>"
            "<style>body{font-family:sans-serif;}table{border-collapse:collapse;width:100%;}"
            "th,td{border:1px solid #ccc;padding:8px;text-align:left;}th{background:#f4f4f4;}"
            "</style></head><body><h1>Locator Healing Report</h1><table>"
            "<tr><th>Suite</th><th>Path</th><th>Test</th><th>Keyword</th>"
            "<th>Keyword Args</th><th>Healed Locator</th><th>Tried Locators</th></tr>"
        )
        rows: List[str] = []
        for entry in report_info:
            args = ", ".join(html.escape(str(a)) for a in entry.keyword_args)
            tried = "<br>".join(html.escape(l) for l in entry.tried_locators)
            rows.append(
                "<tr>"
                f"<td>{html.escape(entry.test_suite)}</td>"
                f"<td>{html.escape(entry.suite_abs_path)}</td>"
                f"<td>{html.escape(entry.test_name)}</td>"
                f"<td>{html.escape(entry.keyword)}</td>"
                f"<td>{args}</td>"
                f"<td>{html.escape(entry.healed_locator or '')}</td>"
                f"<td>{tried}</td>"
                "</tr>"
            )
        footer = "</table></body></html>"
        content = header + "".join(rows) + footer

        output_path = self.reports_dir / "report.html"
        try:
            output_path.write_text(content, encoding="utf-8")
        except OSError as e:
            raise RuntimeError(f"Failed to write action log to {output_path}") from e

    def _generate_healed_test_suites(self, report_info: List[ReportData]) -> None:
        """Applies healed locators to each Robot Framework test suite and saves it.

        Args:
            report_info (List[ReportData]): Data about each healing event.
        """
        paths: Set[str] = {entry.suite_abs_path for entry in report_info}
        for suite_path in paths:
            test_suite_name = Path(suite_path).name
            model = get_model(suite_path)
            replacements = self._get_replacements_for_suite(report_info, test_suite_name)
            LocatorReplacer(replacements).visit(model)
            output_file = self.reports_dir / f"{test_suite_name}.robot"
            try:
                model.save(output_file)
            except OSError as e:
                raise RuntimeError(f"Failed to save healed test suite to {output_file}") from e

    def _generate_diff_file(self, report_info: List[ReportData]) -> None:
        ...

    @staticmethod
    def _get_replacements_for_suite(report_info: List[ReportData], test_suite_name: str) -> List[Tuple[str, str]]:
        """Builds a mapping of original to healed locators for a given suite.

        Args:
            report_info (List[ReportData]): Data about each healing event.
            test_suite_name (str): Name of the suite to filter.

        Returns:
            (List[Tuple[str, str]]): Pairs of (original_locator, healed_locator).
        """
        entries = [
            entry for entry in report_info
            if entry.test_suite == test_suite_name
        ]
        return [
            (ReportGenerator._extract_locator(entry.keyword_args), entry.healed_locator or "")
            for entry in entries
        ]

    @staticmethod
    def _extract_locator(keyword_args: List[str]) -> Optional[str]:
        """Finds the first argument that looks like a locator.

        Args:
            keyword_args (List[str]): Arguments passed to the failed keyword.

        Returns:
            (Optional[str]): The original locator string, or first arg if none match.
        """
        locator = next((arg for arg in keyword_args if ReportGenerator.is_locator(arg)), None)
        return locator or (keyword_args[0] if keyword_args else None)

    @staticmethod
    def is_locator(arg: str) -> bool:
        """Detects whether a string is a locator.

        Args:
            arg (str): A keyword argument.

        Returns:
            bool: True if it matches locator patterns.
        """
        return bool(LOCATOR_PATTERN.match(arg) or arg.startswith("//") or arg.startswith("./"))


class LocatorReplacer(ModelTransformer):
    """Traverses a Robot Framework AST and replaces tokens by mapping."""

    def __init__(self, replacements: List[Tuple[str, str]]) -> None:
        """Stores a dict of original to new locator values.

        Args:
            replacements (List[Tuple[str, str]]): Pairs of (old, new) locator.
        """
        super().__init__()
        self.replacements: dict[str, str] = dict(replacements)

    def visit_KeywordCall(self, node: Any) -> Any:
        """Replaces locator tokens in a keyword call node.

        Args:
            node (Any): A Robot Framework AST keyword call node.

        Returns:
            (Any): The modified node.
        """
        for token in node.tokens[1:]:
            replacement = self.replacements.get(token.value)
            if replacement:
                token.value = replacement
        return node
