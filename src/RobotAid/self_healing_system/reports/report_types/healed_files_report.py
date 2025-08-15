from pathlib import Path
from itertools import chain
from typing import List, Tuple, Set

from robot.parsing.model import VariableSection, File
from robot.api.parsing import (
    get_model,
    get_resource_model,
    SettingSection,
    ResourceImport,
)

from RobotAid.self_healing_system.reports.report_types.base_report import BaseReport
from RobotAid.self_healing_system.schemas.internal_state.report_data import ReportData
from RobotAid.self_healing_system.schemas.internal_state.report_context import ReportContext
from RobotAid.self_healing_system.reports.robot_model_visitors import (
    LocatorReplacer,
    VariablesReplacer
)


class HealedFilesReport(BaseReport):

    def __init__(self, base_dir: Path) -> None:
        super().__init__(base_dir, "healed_files")

    def _generate_report(self, report_context: ReportContext) -> ReportContext:
        """Applies healed locators to test suites and external resources, then saves them.

        Args:
            report_info: List of data objects representing healing events.

        Returns:
            A list of paths to external original resource files.

        Raises:
            RuntimeError: If saving healed suites fails.
        """
        sources: Set[Path] = {Path(entry.keyword_source) for entry in report_context.report_info}

        for source_path in sources:
            replacements: List[Tuple[str, str]] = (
                self._get_replacements_for_file(report_context.report_info, source_path)
            )
            self._replace_in_common_model(source_path, replacements)
            self._replace_in_resource_model(source_path, replacements, report_context)
        return report_context

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
            model: File = get_model(source_path)
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

        suite_output_dir: Path = self._out_dir / source_path.parent.name
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
        report_context: ReportContext
    ) -> None:
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
            report_context: Existing list of healed resource paths to extend.

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
                unpacked_tuples: List[str] = list(chain.from_iterable(defined))
                if any(var in unpacked_tuples for var, _ in replacements):
                    res_dir: Path = self._out_dir / res_path.parent.name
                    res_dir.mkdir(parents=True, exist_ok=True)
                    res_out: Path = res_dir / res_path.name
                    if res_out.exists():
                        res_model: File = get_resource_model(res_out)
                    VariablesReplacer(replacements).visit(res_model)
                    res_model.save(str(res_out))
                    report_context.external_resource_paths.append(res_path)
        except (StopIteration, OSError):
            pass
