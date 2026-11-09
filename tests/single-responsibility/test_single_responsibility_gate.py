from pathlib import Path

from check_support import (
    link_toolkit_code_models,
    link_toolkit_virtual_environment,
    repository,
    run_check,
    stage_file,
    stderr_lines,
)

CHECK_NAME = "single-responsibility"
PYTHON_PATH = "user-service/src/order_desk.py"
TYPESCRIPT_PATH = "ui-service/src/orderDesk.ts"
SPLIT_PYTHON_CLASS = (
    "class OrderDesk:\n"
    "    def invoice_total(self, invoice_lines):\n"
    "        total_amount = 0\n"
    "        for invoice_line in invoice_lines:\n"
    "            total_amount += invoice_line.price * invoice_line.quantity\n"
    "        return total_amount\n"
    "\n"
    "    def invoice_tax(self, invoice_lines):\n"
    "        total_amount = self.invoice_total(invoice_lines)\n"
    "        return total_amount * TAX_RATE\n"
    "\n"
    "    def send_receipt_email(self, recipient_address, message_body):\n"
    "        smtp_connection = smtplib.SMTP(SMTP_HOST)\n"
    "        smtp_connection.sendmail(\n"
    "            SENDER_ADDRESS, recipient_address, message_body\n"
    "        )\n"
    "\n"
    "    def send_reminder_email(self, recipient_address):\n"
    "        smtp_connection = smtplib.SMTP(SMTP_HOST)\n"
    "        smtp_connection.sendmail(\n"
    "            SENDER_ADDRESS, recipient_address, REMINDER_TEXT\n"
    "        )\n"
)
SPLIT_PYTHON_FINDING = (
    f"{PYTHON_PATH}:1: class OrderDesk has 2 responsibilities: "
    "OrderDesk.invoice_total, OrderDesk.invoice_tax | "
    "OrderDesk.send_receipt_email, OrderDesk.send_reminder_email"
)
SPLIT_TYPESCRIPT_CLASS = (
    "export class OrderDesk {\n"
    "  invoiceTotal(invoiceLines: InvoiceLine[]): number {\n"
    "    let totalAmount = 0;\n"
    "    for (const invoiceLine of invoiceLines) {\n"
    "      totalAmount += invoiceLine.price * invoiceLine.quantity;\n"
    "    }\n"
    "    return totalAmount;\n"
    "  }\n"
    "\n"
    "  invoiceTax(invoiceLines: InvoiceLine[]): number {\n"
    "    return this.invoiceTotal(invoiceLines) * TAX_RATE;\n"
    "  }\n"
    "\n"
    "  sendReceiptEmail(recipientAddress: string, body: string) {\n"
    "    const smtpConnection = createTransport(SMTP_HOST);\n"
    "    smtpConnection.sendMail({ to: recipientAddress, text: body });\n"
    "  }\n"
    "\n"
    "  sendReminderEmail(recipientAddress: string) {\n"
    "    const smtpConnection = createTransport(SMTP_HOST);\n"
    "    smtpConnection.sendMail({ to: recipientAddress, text: REMINDER });\n"
    "  }\n"
    "}\n"
)
SPLIT_TYPESCRIPT_FINDING = (
    f"{TYPESCRIPT_PATH}:1: class OrderDesk has 2 responsibilities: "
    "OrderDesk.invoiceTotal, OrderDesk.invoiceTax | "
    "OrderDesk.sendReceiptEmail, OrderDesk.sendReminderEmail"
)
COHESIVE_PYTHON_CLASS = (
    "class Basket:\n"
    "    def add_item(self, basket_item):\n"
    "        self.basket_items.append(basket_item)\n"
    "\n"
    "    def remove_item(self, basket_item):\n"
    "        self.basket_items.remove(basket_item)\n"
    "\n"
    "    def item_count(self):\n"
    "        return len(self.basket_items)\n"
    "\n"
    "    def basket_total(self):\n"
    "        return sum(item.price for item in self.basket_items)\n"
)


def _staged_repository(tmp_path: Path, path: str, source: str) -> None:
    repository(tmp_path)
    link_toolkit_virtual_environment(tmp_path)
    link_toolkit_code_models(tmp_path)
    stage_file(tmp_path, path, source)


def test_reports_a_python_class_with_two_responsibilities(
    tmp_path: Path,
) -> None:
    _staged_repository(tmp_path, PYTHON_PATH, SPLIT_PYTHON_CLASS)

    finished = run_check(tmp_path, CHECK_NAME)

    assert finished.returncode == 1
    assert SPLIT_PYTHON_FINDING in stderr_lines(finished)


def test_reports_a_typescript_class_with_two_responsibilities(
    tmp_path: Path,
) -> None:
    _staged_repository(tmp_path, TYPESCRIPT_PATH, SPLIT_TYPESCRIPT_CLASS)

    finished = run_check(tmp_path, CHECK_NAME)

    assert finished.returncode == 1
    assert SPLIT_TYPESCRIPT_FINDING in stderr_lines(finished)


def test_passes_a_class_whose_methods_share_their_words(
    tmp_path: Path,
) -> None:
    _staged_repository(tmp_path, PYTHON_PATH, COHESIVE_PYTHON_CLASS)

    finished = run_check(tmp_path, CHECK_NAME)

    assert finished.returncode == 0, finished.stderr


def test_passes_a_whitelisted_finding(tmp_path: Path) -> None:
    _staged_repository(tmp_path, PYTHON_PATH, SPLIT_PYTHON_CLASS)
    whitelist = f'whitelist = ["{SPLIT_PYTHON_FINDING}"]\n'

    finished = run_check(tmp_path, CHECK_NAME, {CHECK_NAME: whitelist})

    assert finished.returncode == 0, finished.stderr


def test_relates_more_methods_under_a_lower_code_similarity(
    tmp_path: Path,
) -> None:
    _staged_repository(tmp_path, PYTHON_PATH, SPLIT_PYTHON_CLASS)
    lower_similarity = "code-similarity = 10\n"

    finished = run_check(tmp_path, CHECK_NAME, {CHECK_NAME: lower_similarity})

    assert finished.returncode == 0, finished.stderr


def test_fails_when_the_code_model_is_not_installed(tmp_path: Path) -> None:
    repository(tmp_path)
    link_toolkit_virtual_environment(tmp_path)
    stage_file(tmp_path, PYTHON_PATH, SPLIT_PYTHON_CLASS)

    finished = run_check(tmp_path, CHECK_NAME)

    assert finished.returncode == 1
    assert "install.sh" in finished.stderr
