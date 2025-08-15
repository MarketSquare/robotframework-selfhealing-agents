import difflib
from pathlib import Path
from typing import List, Set

from RobotAid.self_healing_system.reports.css_styles import DIFF_CSS
from RobotAid.self_healing_system.schemas.internal_state.report_context import ReportContext
from RobotAid.self_healing_system.reports.report_types.base_report import BaseReport


class DiffFilesReport(BaseReport):
    """Generates HTML diff reports between original and healed Robot Framework files.

    This report compares original and healed test suites or resource files and
    generates HTML files highlighting the differences. The diffs are styled and
    saved in the reports directory for review.
    """
    def __init__(self, base_dir: Path):
        """Initializes the DiffFilesReport with the given base directory.

        Args:
            base_dir: The base directory where diff files will be saved.
        """
        super().__init__(base_dir, "diff_files")

    def _generate_report(self, report_context: ReportContext) -> ReportContext:
        """Generates HTML diff files between original and healed suites/resources.

        For each file referenced in the report context, compares the original and
        healed versions. If differences are found, generates an HTML diff file
        using difflib and saves it to the output directory.

        Args:
            report_context: The context object containing healing event data and
                paths to external resource files.

        Returns:
            The updated ReportContext after generating diff files.

        Raises:
            RuntimeError: If reading or writing diff files fails.
        """
        sources: Set[Path] = {Path(entry.keyword_source) for entry in report_context.report_info}
        all_paths: Set[Path] = sources.union(report_context.external_resource_paths)
        for original_path in all_paths:
            healed_dir: Path = self._base_dir / "healed_files" / original_path.parent.name
            healed_file: Path = healed_dir / original_path.name
            try:
                original_lines: List[str] = original_path.read_text(encoding="utf-8").splitlines()
                healed_lines: List[str] = healed_file.read_text(encoding="utf-8").splitlines()
            except OSError as e:
                raise RuntimeError(
                    f"Failed to read files for diff: {original_path} or {healed_file}"
                ) from e

            if original_lines == healed_lines:
                continue

            diff_html: str = difflib.HtmlDiff(tabsize=4, wrapcolumn=80).make_file(
                original_lines, healed_lines, fromdesc="Original", todesc="Healed"
            )
            diff_html: str = diff_html.replace("</head>", f"{DIFF_CSS}</head>", 1)

            diff_dir: Path = self._out_dir / original_path.parent.name
            diff_dir.mkdir(parents=True, exist_ok=True)
            diff_path: Path = diff_dir / f"{original_path.stem}_diff.html"
            try:
                diff_path.write_text(diff_html, encoding="utf-8")
            except OSError as exc:
                raise RuntimeError(f"Failed to write diff file to {diff_path}") from exc

        return report_context