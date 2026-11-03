"""Offline tests for the notebook output checks (synthetic notebooks; nothing is executed)."""

from nbformat.v4 import new_code_cell, new_notebook, new_output

from sp500_momentum.run_notebooks import BUDGET_KB, MAX_OUTPUT_LINES, check_notebook


def _nb(*outputs):
    cell = new_code_cell("x")
    cell.outputs = list(outputs)
    return new_notebook(cells=[cell])


def _table(lines):
    return new_output(
        "execute_result", data={"text/plain": "\n".join(["row"] * lines)}, execution_count=1
    )


def test_a_clean_notebook_passes():
    nb = _nb(_table(10), new_output("stream", name="stdout", text="12 features with an IC\n"))
    assert check_notebook(nb, size_kb=100) == []


def test_a_dumped_table_fails():
    problems = check_notebook(_nb(_table(MAX_OUTPUT_LINES + 1)), size_kb=100)
    assert len(problems) == 1 and "lines" in problems[0]


def test_anything_on_stderr_fails():
    nb = _nb(new_output("stream", name="stderr", text="INFO: building features\n"))
    assert "stderr" in check_notebook(nb, size_kb=100)[0]


def test_local_paths_emails_and_secrets_fail():
    nb = _nb(
        new_output("stream", name="stdout", text=r"saved to C:\Users\someone\project" + "\n"),
        new_output("stream", name="stdout", text="contact me@example.com\n"),
        new_output("stream", name="stdout", text="key=ABC123SECRET\n"),
    )
    problems = " | ".join(check_notebook(nb, size_kb=100, secrets=("ABC123SECRET",)))
    assert "Windows path" in problems
    assert "e-mail" in problems
    assert "secret" in problems


def test_over_budget_fails():
    assert "budget" in check_notebook(_nb(), size_kb=BUDGET_KB + 1)[0]
