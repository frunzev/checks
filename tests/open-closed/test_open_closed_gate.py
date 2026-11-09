from pathlib import Path

from check_support import (
    link_toolkit_virtual_environment,
    repository,
    run_check,
    stage_file,
    stderr_lines,
)

CHECK_NAME = "open-closed"
EXPORT_PATH = "user-service/src/export.py"
PREVIEW_PATH = "ui-service/src/preview.ts"
SETTINGS_PATH = "user-service/src/settings.py"
EXPORT_REPORT = (
    "def export_report(report_kind):\n"
    '    if report_kind == "pdf":\n'
    "        return render_pdf()\n"
    '    elif report_kind == "csv":\n'
    "        return render_csv()\n"
    '    elif report_kind == "xlsx":\n'
    "        return render_xlsx()\n"
    "    raise ValueError(report_kind)\n"
)
PREVIEW_REPORT = (
    "export function previewReport(reportKind: string): string {\n"
    "  switch (reportKind) {\n"
    '    case "pdf":\n'
    "      return showPdf();\n"
    '    case "csv":\n'
    "      return showCsv();\n"
    '    case "xlsx":\n'
    "      return showXlsx();\n"
    "  }\n"
    "  throw new Error(reportKind);\n"
    "}\n"
)
ENVIRONMENT_CHECKS = (
    "def debug_level():\n"
    '    if os.environ["APP_MODE"] == "development":\n'
    "        return 10\n"
    "    return 20\n"
    "\n"
    "def cache_seconds():\n"
    '    if os.environ["APP_MODE"] == "development":\n'
    "        return 0\n"
    "    return 60\n"
)
EXPORT_FINDING = (
    f"{EXPORT_PATH}:1: export_report branches on csv, pdf, xlsx, as do"
    f" {PREVIEW_PATH}:1 previewReport"
)
PREVIEW_FINDING = (
    f"{PREVIEW_PATH}:1: previewReport branches on csv, pdf, xlsx, as do"
    f" {EXPORT_PATH}:1 export_report"
)


def _staged_repository(tmp_path: Path, files: dict[str, str]) -> None:
    repository(tmp_path)
    link_toolkit_virtual_environment(tmp_path)

    for path, source in files.items():
        stage_file(tmp_path, path, source)


def test_reports_variants_dispatched_in_two_languages(tmp_path: Path) -> None:
    _staged_repository(
        tmp_path, {EXPORT_PATH: EXPORT_REPORT, PREVIEW_PATH: PREVIEW_REPORT}
    )

    finished = run_check(tmp_path, CHECK_NAME)

    assert finished.returncode == 1
    assert EXPORT_FINDING in stderr_lines(finished)
    assert PREVIEW_FINDING in stderr_lines(finished)


def test_passes_variants_dispatched_in_one_place(tmp_path: Path) -> None:
    _staged_repository(tmp_path, {EXPORT_PATH: EXPORT_REPORT})

    finished = run_check(tmp_path, CHECK_NAME)

    assert finished.returncode == 0, finished.stderr


def test_passes_the_same_single_condition_in_two_places(
    tmp_path: Path,
) -> None:
    _staged_repository(tmp_path, {SETTINGS_PATH: ENVIRONMENT_CHECKS})

    finished = run_check(tmp_path, CHECK_NAME)

    assert finished.returncode == 0, finished.stderr


def test_passes_whitelisted_findings(tmp_path: Path) -> None:
    _staged_repository(
        tmp_path, {EXPORT_PATH: EXPORT_REPORT, PREVIEW_PATH: PREVIEW_REPORT}
    )
    whitelist = f'whitelist = ["{EXPORT_FINDING}", "{PREVIEW_FINDING}"]\n'

    finished = run_check(tmp_path, CHECK_NAME, {CHECK_NAME: whitelist})

    assert finished.returncode == 0, finished.stderr
