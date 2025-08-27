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

from SelfhealingAgents.utils.logging import log
from SelfhealingAgents.self_healing_system.reports.report_types.base_report import BaseReport
from SelfhealingAgents.self_healing_system.schemas.internal_state.report_data import ReportData
from SelfhealingAgents.self_healing_system.schemas.internal_state.report_context import ReportContext
from SelfhealingAgents.self_healing_system.reports.robot_model_visitors import (
    LocatorReplacer,
    VariablesReplacer
)


class HealedFilesReport(BaseReport):
    """Generates healed Robot Framework test suites and resource files.

    This report applies locator and variable replacements to test suites and their
    imported resources, saving the healed versions to the reports directory.
    """
    def __init__(self, base_dir: Path) -> None:
        """Initializes the HealedFilesReport with the given base directory.

        Args:
            base_dir: The base directory where healed files will be saved.
        """
        super().__init__(base_dir, "healed_files")

    @log
    def _generate_report(self, report_context: ReportContext) -> ReportContext:
        """Applies healed locators to test suites and external resources, then saves them.

        Iterates over all source files referenced in the report context, applies locator
        and variable replacements, and saves the healed files to the output directory.

        Args:
            report_context: The context object containing healing event data.

        Returns:
            The updated ReportContext after applying replacements.

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
        """Builds a list of original-to-healed locator pairs for a file.

        Collects all locator replacements relevant to the given source file, including
        those from imported resources.

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
        """Applies locator and variable replacements to a Robot Framework file and saves it.

        Loads the AST for the suite or resource at `source_path`, applies the given
        keyword locator and variable replacements, and writes the healed model to
        the reports directory.

        Args:
            source_path: Path to the original Robot Framework file (suite or resource).
            replacements: List of (original_locator, healed_locator) tuples to apply.

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
        """Applies variable replacements to imported resource files and saves them.

        For each resource imported by the suite at `source_path`, loads the resource,
        applies variable replacements if definitions match, and saves the healed resource
        to the reports directory. Updates the report context with paths to healed resources.

        Args:
            source_path: Path to the file containing resource imports.
            replacements: List of (old_value, new_value) pairs for resource variables.
            report_context: The current report context to update with healed resource paths.
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
