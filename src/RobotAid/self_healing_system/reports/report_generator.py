import os
import re
import html
import shutil
import difflib

from pathlib import Path
from typing import List, Tuple, Set, Optional, Pattern

from robot.api.parsing import (
    get_model,
    get_resource_model,
    SettingSection,
    ResourceImport,
)
from robot.parsing.model import VariableSection, File

from RobotAid.self_healing_system.reports.report_data import ReportData
from RobotAid.self_healing_system.reports.robot_model_visitors import (
    LocatorReplacer,
    VariablesReplacer
)


LOCATOR_PATTERN: Pattern[str] = re.compile(
    r'^(?:id|xpath|css|name|link|dom|jquery)=', re.IGNORECASE
)

ACTION_LOG_CSS: str = (
    "<style>"
    "body{font-family:sans-serif;}"
    "table{border-collapse:collapse;width:100%;}"
    "th,td{border:1px solid #ccc;padding:8px;text-align:left;}"
    "th{background:#f4f4f4;}"
    "</style>"
)
DIFF_CSS: str = (
    "<style>"
    "td.diff_add, td.diff_sub, td.diff_chg{background:none;}"
    "span.diff_add{background-color:#dfd;}"
    "span.diff_sub{background-color:#fdd;}"
    "span.diff_chg{background-color:#ffd;}"
    "</style>"
)


class ReportGenerator:
    """Generates action log, healed Robot Framework test suites (and/or resources) and diff files with the respective
       changes.
    """

    def __init__(self) -> None:
        """Initialize report directories under the project workspace."""
        self.workspace_dir: Path = Path(__file__).resolve().parents[4]
        self.reports_dir: Path = self.workspace_dir / "reports"
        shutil.rmtree(self.reports_dir, ignore_errors=True)
        os.makedirs(self.reports_dir, exist_ok=True)

    def generate_reports(self, report_info: List[ReportData]) -> None:
        """Generate action log, healed suites, and diff files for given report data.

        Args:
            report_info: List of data objects representing healing events.
        """
        self._generate_action_log(report_info=report_info)
        external_resource_paths: List[Path] = self._generate_healed_files(report_info=report_info)
        self._generate_diff_files(
            report_info=report_info,
            external_resource_paths=external_resource_paths,
        )

    def _generate_action_log(self, report_info: List[ReportData]) -> None:
        """Writes an HTML table summarizing each locator healing event.

        Args:
            report_info: List of data objects representing healing events.

        Raises:
            RuntimeError: If writing to the output file fails.
        """
        header: str = (
            "<html><head><meta charset='utf-8'><title>Locator Healing Report</title>"
            f"{ACTION_LOG_CSS}</head><body><h1>Locator Healing Report</h1><table>"
            "<tr><th>Suite</th><th>Path</th><th>Test</th><th>Keyword</th>"
            "<th>Keyword Args</th><th>Healed Locator</th><th>Tried Locators</th></tr>"
        )
        rows: List[str] = []
        for entry in report_info:
            args: str = ", ".join(html.escape(str(a)) for a in entry.keyword_args)
            tried: str = "<br>".join(html.escape(l) for l in entry.tried_locators)
            rows.append(
                "<tr>"
                f"<td>{html.escape(entry.file)}</td>"
                f"<td>{html.escape(entry.keyword_source)}</td>"
                f"<td>{html.escape(entry.test_name)}</td>"
                f"<td>{html.escape(entry.keyword)}</td>"
                f"<td>{args}</td>"
                f"<td>{html.escape(entry.healed_locator or '')}</td>"
                f"<td>{tried}</td>"
                "</tr>"
            )
        footer: str = "</table></body></html>"
        content: str = header + ''.join(rows) + footer

        output_path: Path = self.reports_dir / "action_log.html"
        try:
            output_path.write_text(content, encoding="utf-8")
        except OSError as e:
            raise RuntimeError(f"Failed to write action log to {output_path}") from e

    def _generate_diff_files(
        self,
        report_info: List[ReportData],
        external_resource_paths: List[Path],
    ) -> None:
        """Generates HTML diff files between original and healed suites/resources.

        Args:
            report_info: List of data objects representing healing events.
            external_resource_paths: Paths to external original resource files.

        Raises:
            RuntimeError: If reading or writing diff files fails.
        """
        sources: Set[Path] = {Path(entry.keyword_source) for entry in report_info}
        all_paths: Set[Path] = sources.union(external_resource_paths)
        for original_path in all_paths:
            healed_dir: Path = self.reports_dir / original_path.parent.name
            healed_file: Path = healed_dir / original_path.name
            try:
                original_lines: List[str] = original_path.read_text(encoding="utf-8").splitlines()
                healed_lines: List[str] = healed_file.read_text(encoding="utf-8").splitlines()
            except OSError as e:
                raise RuntimeError(
                    f"Failed to read files for diff: {original_path} or {healed_file}"
                ) from e

            diff_html: str = difflib.HtmlDiff(tabsize=4, wrapcolumn=80).make_file(
                original_lines, healed_lines, fromdesc="Original", todesc="Healed"
            )
            diff_html: str = diff_html.replace("</head>", f"{DIFF_CSS}</head>", 1)

            diff_path: Path = self.reports_dir / f"{original_path.stem}_diff.html"
            try:
                diff_path.write_text(diff_html, encoding="utf-8")
            except OSError as exc:
                raise RuntimeError(f"Failed to write diff file to {diff_path}") from exc

    def _generate_healed_files(self, report_info: List[ReportData]) -> List[Path]:
        """Applies healed locators to test suites and external resources, then saves them.

        Args:
            report_info: List of data objects representing healing events.

        Returns:
            A list of paths to external original resource files.

        Raises:
            RuntimeError: If saving healed suites fails.
        """
        var_pattern: Pattern[str] = re.compile(r'^\${[^}]+}$')
        sources: Set[Path] = {Path(entry.keyword_source) for entry in report_info}
        external_resource_paths: List[Path] = []

        for source_path in sources:
            replacements: List[Tuple[str, str]] = (
                self._get_replacements_for_file(report_info, source_path.name)
            )
            suite_repls: List[Tuple[str, str]] = [
                (orig, new) for orig, new in replacements if not var_pattern.match(orig)
            ]
            var_repls: List[Tuple[str, str]] = [
                (orig, new) for orig, new in replacements if var_pattern.match(orig)
            ]
            self._replace_in_common_model(
                source_path=source_path,
                suite_repls=suite_repls,
                var_repls=var_repls,
            )
            self._replace_in_resource_model(
                source_path=source_path,
                var_repls=var_repls,
                external_resource_paths=external_resource_paths
            )
        return external_resource_paths

    def _replace_in_common_model(
            self,
            source_path: Path,
            suite_repls: List[Tuple[str, str]],
            var_repls: List[Tuple[str, str]]
    ) -> None:
        """Applies locator replacements to a robot.api.parsing (common) model and saves it.
        Note: In robot.api.parsing exists get_model() and get_resource_model(), depending on the
              file imported having a only a VariableSection.

        Retrieves the AST for the suite or resource at `source_path`, applies the given
        keyword locator replacements and variable replacements, and writes the healed
        model back to the reports directory under a folder named for its parent.

        Args:
            source_path: Path to the original Robot Framework file (suite or resource).
            suite_repls: List of (original_locator, healed_locator) tuples to apply in keywords.
            var_repls: List of (variable_name, new_value) tuples to apply in variable sections.

        Raises:
            RuntimeError: If the healed model cannot be saved.
        """
        model: File = get_model(str(source_path))
        LocatorReplacer(suite_repls).visit(model)
        VariablesReplacer(var_repls).visit(model)

        suite_output_dir: Path = self.reports_dir / source_path.parent.name
        suite_output_dir.mkdir(parents=True, exist_ok=True)
        suite_output_file: Path = suite_output_dir / source_path.name
        try:
            model.save(str(suite_output_file))
        except OSError as exc:
            raise RuntimeError(
                f"Failed to save healed test suite to {suite_output_file}"
            ) from exc

    def _replace_in_resource_model(
        self,
        source_path: Path,
        var_repls: List[Tuple[str, str]],
        external_resource_paths: List[Path]
    ) -> List[Path]:
        """Applies locator replacements to a robot.api.parsing resource model and saves it.
        Note: In robot.api.parsing exists get_model() and get_resource_model(), depending on the
              file imported having a only a VariableSection.

        Each resource imported by the suite at `source_path` is loaded, and
        variable replacements are applied when their definitions match.
        If a healed version of the same resource already exists in the reports
        directory, it is reloaded and used as the basis for further replacements.

        Args:
            source_path: Path to the file containing resource imports.
            var_repls: List of (variable_name, new_value) pairs for resource vars.
            external_resource_paths: Existing list of healed resource paths to extend.

        Returns:
            The updated list of Paths to healed external resources.
        """
        try:
            model: File = get_model(str(source_path))
            setting: SettingSection = next(
                s for s in model.sections if isinstance(s, SettingSection)
            )
            resources: List[ResourceImport] = [
                r for r in setting.body if isinstance(r, ResourceImport)
            ]
            for res in resources:
                res_path: Path = source_path.parent / res.name
                res_model: File = get_resource_model(str(res_path))
                defined: Set[str] = {
                    v.name for v in next(
                        sec for sec in res_model.sections if isinstance(sec, VariableSection)
                    ).body
                }
                if any(var in defined for var, _ in var_repls):
                    res_dir: Path = self.reports_dir / res_path.parent.name
                    res_dir.mkdir(parents=True, exist_ok=True)
                    res_out: Path = res_dir / res_path.name
                    if res_out.exists():
                        res_model: File = get_resource_model(res_out)
                    VariablesReplacer(var_repls).visit(res_model)
                    res_model.save(str(res_out))
                    external_resource_paths.append(res_path)
        except (StopIteration, OSError):
            pass

        return external_resource_paths

    @staticmethod
    def _get_replacements_for_file(
        report_info: List[ReportData],
        file_name: str
    ) -> List[Tuple[str, str]]:
        """Build a list of original-to-healed locator pairs for a file.

        Args:
            report_info: List of data objects representing healing events.
            file_name: Name of the file to filter on.

        Returns:
            A list of (original_locator, healed_locator) tuples.
        """
        entries: List[ReportData] = [
            entry for entry in report_info if entry.file == file_name
        ]
        return [
            (
                ReportGenerator._extract_locator(entry.keyword_args),
                entry.healed_locator or "",
            )
            for entry in entries
        ]

    @staticmethod
    def _extract_locator(keyword_args: List[str]) -> Optional[str]:
        """Extract the first locator-looking argument.

        Args:
            keyword_args: Arguments passed to the failed keyword.

        Returns:
            The first argument matching locator pattern or the first arg if none match.
        """
        # TODO: replace with LLM to enable custom keyword with multiple arguments
        locator: Optional[str] = next(
            (arg for arg in keyword_args if ReportGenerator.is_locator(arg)), None
        )
        return locator or (keyword_args[0] if keyword_args else None)

    @staticmethod
    def is_locator(arg: str) -> bool:
        """Check if a string appears to be a Robot Framework locator.

        Args:
            arg: A keyword argument string.

        Returns:
            True if the string matches known locator patterns.
        """
        return bool(
            LOCATOR_PATTERN.match(arg)
            or arg.startswith("//")
            or arg.startswith("./")
        )
