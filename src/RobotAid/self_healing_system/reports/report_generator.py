import os
import html
import shutil
import difflib

from pathlib import Path
from operator import attrgetter
from typing import List, Tuple, Set
from itertools import chain, groupby

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
from RobotAid.self_healing_system.reports.css_styles import ACTION_LOG_CSS, DIFF_CSS


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
        """Generate action log, healed .robot and .resource files, and diff files for given report data.

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
            f"{ACTION_LOG_CSS}</head><body><h1>Locator Healing Report</h1>"
        )
        groups = sorted(report_info, key=attrgetter("file"))
        body_parts: List[str] = []
        for suite, entries in groupby(groups, key=attrgetter("file")):
            entries_list = list(entries)
            path = html.escape(entries_list[0].keyword_source)
            summary = (
                f"<details><summary>{html.escape(suite)}"
                f"<div class='path'>{path}</div></summary>"
            )
            inner_header = (
                "<table class='inner'>"
                "<tr><th>Test</th><th>Keyword</th><th>Keyword Args</th>"
                "<th>Failed Locator</th><th>Healed Locator</th><th>Tried Locators</th></tr>"
            )
            rows: List[str] = []
            for e in entries_list:
                args = ", ".join(html.escape(str(a)) for a in e.keyword_args)
                tried = "<br>".join(html.escape(l) for l in e.tried_locators)
                rows.append(
                    "<tr>"
                    f"<td>{html.escape(e.test_name)}</td>"
                    f"<td>{html.escape(e.keyword)}</td>"
                    f"<td>{args}</td>"
                    f"<td>{html.escape(e.failed_locator)}</td>"
                    f"<td>{html.escape(e.healed_locator or '')}</td>"
                    f"<td>{tried}</td>"
                    "</tr>"
                )
            inner_footer = "</table></details>"
            body_parts.append(summary + inner_header + "".join(rows) + inner_footer)
        footer: str = "</body></html>"
        content = header + "".join(body_parts) + footer
        output_path: Path = self.reports_dir / "action_log.html"
        try:
            output_path.write_text(content, encoding="utf-8")
        except OSError as e:
            raise RuntimeError(f"Failed to write action log to {output_path}") from e

    def _generate_healed_files(self, report_info: List[ReportData]) -> List[Path]:
        """Applies healed locators to test suites and external resources, then saves them.

        Args:
            report_info: List of data objects representing healing events.

        Returns:
            A list of paths to external original resource files.

        Raises:
            RuntimeError: If saving healed suites fails.
        """
        sources: Set[Path] = {Path(entry.keyword_source) for entry in report_info}
        external_resource_paths: List[Path] = []

        for source_path in sources:
            replacements: List[Tuple[str, str]] = (
                self._get_replacements_for_file(report_info, source_path)
            )
            self._replace_in_common_model(
                source_path=source_path,
                replacements=replacements,
            )
            self._replace_in_resource_model(
                source_path=source_path,
                replacements=replacements,
                external_resource_paths=external_resource_paths
            )
        return external_resource_paths

    @staticmethod
    def _get_replacements_for_file(
            report_info: List[ReportData],
            source_path: Path
    ) -> List[Tuple[str, str]]:
        """Build a list of original-to-healed locator pairs for a file.

        Args:
            report_info: List of data objects representing healing events.
            source_path: Absolute path of the source file to filter on.

        Returns:
            A list of (original_locator, healed_locator) tuples.
        """
        entries: List[ReportData] = [
            entry for entry in report_info if entry.file == source_path.name
        ]
        try:
            # Appends the list of files with the resource imports. Needed for keyword inline arguments of custom
            # written keywords if locators exists in these arguments AND are defined in external resources.
            # This will ultimately include the (original_locator, healed_locator) information of the imported
            # resource files for the inline args in the parent file.
            model = get_model(source_path)
            setting: SettingSection = next(
                s for s in model.sections if isinstance(s, SettingSection)
            )
            resources: List[ResourceImport] = [
                r for r in setting.body if isinstance(r, ResourceImport)
            ]
            for res in resources:
                for entry in report_info:
                    if entry.file in res.name:
                        entries.append(entry)
        except OSError:
            pass

        return [(entry.failed_locator, entry.healed_locator) for entry in entries]

    def _replace_in_common_model(
            self,
            source_path: Path,
            replacements: List[Tuple[str, str]],
    ) -> None:
        """Applies locator replacements to a robot.api.parsing (common) model and saves it.
        Note: In robot.api.parsing exists get_model() and get_resource_model(), depending on the
              file imported having only a VariableSection.

        Retrieves the AST for the suite or resource at `source_path`, applies the given
        keyword locator replacements and variable replacements, and writes the healed
        model back to the reports directory under a folder named for its parent.

        Args:
            source_path: Path to the original Robot Framework file (suite or resource).
            replacements: List of (original_locator, healed_locator) tuples to apply.
            var_repls: List of (variable_name, new_value) tuples to apply in variable sections.

        Raises:
            RuntimeError: If the healed model cannot be saved.
        """
        model: File = get_model(str(source_path))
        LocatorReplacer(replacements).visit(model)
        VariablesReplacer(replacements).visit(model)

        suite_output_dir: Path = self.reports_dir / "healed_files" / source_path.parent.name
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
        replacements: List[Tuple[str, str]],
        external_resource_paths: List[Path]
    ) -> List[Path]:
        """Applies locator replacements to a robot.api.parsing resource model and saves it.
        Note: In robot.api.parsing exists get_model() and get_resource_model(), depending on the
              file imported having only a VariableSection.

        Each resource imported by the suite at `source_path` is loaded, and variable replacements
        are applied when their definitions match. If a healed version of the same resource
        already exists in the reports directory, it is reloaded and used as the basis for further
        replacements.

        Args:
            source_path: Path to the file containing resource imports.
            replacements: List of (old_value, new_value) pairs for resource vars.
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
                    v.value for v in next(
                        sec for sec in res_model.sections if isinstance(sec, VariableSection)
                    ).body
                }
                unpacked_tuples = list(chain.from_iterable(defined))
                if any(var in unpacked_tuples for var, _ in replacements):
                    res_dir: Path = self.reports_dir / "healed_files" / res_path.parent.name
                    res_dir.mkdir(parents=True, exist_ok=True)
                    res_out: Path = res_dir / res_path.name
                    if res_out.exists():
                        res_model: File = get_resource_model(res_out)
                    VariablesReplacer(replacements).visit(res_model)
                    res_model.save(str(res_out))
                    external_resource_paths.append(res_path)
        except (StopIteration, OSError):
            pass

        return external_resource_paths

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
            healed_dir: Path = self.reports_dir / "healed_files" / original_path.parent.name
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

            diff_dir: Path = self.reports_dir / "diff_files" / original_path.parent.name
            diff_path: Path = diff_dir / f"{original_path.stem}_diff.html"
            try:
                os.makedirs(diff_dir, exist_ok=True)
                diff_path.write_text(diff_html, encoding="utf-8")
            except OSError as exc:
                raise RuntimeError(f"Failed to write diff file to {diff_path}") from exc
