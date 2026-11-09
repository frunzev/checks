from pathlib import Path

from check_support import (
    link_toolkit_code_models,
    link_toolkit_virtual_environment,
    repository,
    run_check,
    stage_file,
    stderr_lines,
)

CHECK_NAME = "semantic-duplicates"
ORDERS_PATH = "user-service/src/orders.py"
BASKETS_PATH = "user-service/src/baskets.py"
MAIL_PATH = "user-service/src/mail.py"
ORDERS_TYPESCRIPT_PATH = "ui-service/src/orders.ts"
ORDER_TOTAL = (
    "def order_total(order_lines):\n"
    "    total_amount = 0\n"
    "    for order_line in order_lines:\n"
    "        if order_line.is_cancelled:\n"
    "            continue\n"
    "        total_amount += order_line.price * order_line.quantity\n"
    "    return total_amount\n"
)
BASKET_TOTAL = (
    "def basket_total(order_lines):\n"
    "    running_total = 0\n"
    "    for order_line in order_lines:\n"
    "        if not order_line.is_cancelled:\n"
    "            running_total += order_line.price * order_line.quantity\n"
    "    return running_total\n"
)
SEND_REMINDER = (
    "def send_reminder(recipient_address):\n"
    "    smtp_connection = smtplib.SMTP(SMTP_HOST)\n"
    "    smtp_connection.login(SMTP_USER, SMTP_PASSWORD)\n"
    "    smtp_connection.sendmail(SENDER, recipient_address, REMINDER_TEXT)\n"
    "    smtp_connection.quit()\n"
)
ORDER_TOTAL_TYPESCRIPT = (
    "export function basketTotal(orderLines: OrderLine[]): number {\n"
    "  let runningTotal = 0;\n"
    "  for (const orderLine of orderLines) {\n"
    "    if (!orderLine.isCancelled) {\n"
    "      runningTotal += orderLine.price * orderLine.quantity;\n"
    "    }\n"
    "  }\n"
    "  return runningTotal;\n"
    "}\n"
)
ORDERS_FINDING = (
    f"{ORDERS_PATH}:1: order_total duplicates {BASKETS_PATH}:1: basket_total"
)
BASKETS_FINDING = (
    f"{BASKETS_PATH}:1: basket_total duplicates {ORDERS_PATH}:1: order_total"
)


def _staged_repository(tmp_path: Path, files: dict[str, str]) -> None:
    repository(tmp_path)
    link_toolkit_virtual_environment(tmp_path)
    link_toolkit_code_models(tmp_path)

    for path, source in files.items():
        stage_file(tmp_path, path, source)


def test_reports_a_copied_function_from_both_sides(tmp_path: Path) -> None:
    _staged_repository(
        tmp_path, {ORDERS_PATH: ORDER_TOTAL, BASKETS_PATH: BASKET_TOTAL}
    )

    finished = run_check(tmp_path, CHECK_NAME)

    assert finished.returncode == 1
    assert ORDERS_FINDING in stderr_lines(finished)
    assert BASKETS_FINDING in stderr_lines(finished)


def test_passes_functions_that_do_different_things(tmp_path: Path) -> None:
    _staged_repository(
        tmp_path, {ORDERS_PATH: ORDER_TOTAL, MAIL_PATH: SEND_REMINDER}
    )

    finished = run_check(tmp_path, CHECK_NAME)

    assert finished.returncode == 0, finished.stderr


def test_passes_the_same_logic_written_in_two_languages(
    tmp_path: Path,
) -> None:
    _staged_repository(
        tmp_path,
        {
            ORDERS_PATH: ORDER_TOTAL,
            ORDERS_TYPESCRIPT_PATH: ORDER_TOTAL_TYPESCRIPT,
        },
    )

    finished = run_check(tmp_path, CHECK_NAME)

    assert finished.returncode == 0, finished.stderr


def test_passes_whitelisted_findings(tmp_path: Path) -> None:
    _staged_repository(
        tmp_path, {ORDERS_PATH: ORDER_TOTAL, BASKETS_PATH: BASKET_TOTAL}
    )
    whitelist = f'whitelist = ["{ORDERS_FINDING}", "{BASKETS_FINDING}"]\n'

    finished = run_check(tmp_path, CHECK_NAME, {CHECK_NAME: whitelist})

    assert finished.returncode == 0, finished.stderr


def test_passes_a_copy_below_a_higher_code_similarity(tmp_path: Path) -> None:
    _staged_repository(
        tmp_path, {ORDERS_PATH: ORDER_TOTAL, BASKETS_PATH: BASKET_TOTAL}
    )
    higher_similarity = "code-similarity = 99\n"

    finished = run_check(tmp_path, CHECK_NAME, {CHECK_NAME: higher_similarity})

    assert finished.returncode == 0, finished.stderr
