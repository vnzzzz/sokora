"""E2E tests must fail when critical browser contracts are not exercised."""

import ast
from pathlib import Path

E2E_DIR = Path(__file__).parent / "e2e"


def test_e2e_suite_has_no_known_false_pass_patterns() -> None:
    violations: list[str] = []

    for path in sorted(E2E_DIR.glob("test_*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))

        if ".count() > 0" in source:
            violations.append(f"{path.name}: optional count() > 0 assertion")
        if "len(search_value) >= 0" in source:
            violations.append(f"{path.name}: len(...) >= 0 tautology")

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                exception_type = node.type
                is_exception = isinstance(exception_type, ast.Name)
                if is_exception and exception_type.id == "Exception":
                    violations.append(
                        f"{path.name}:{node.lineno}: broad except Exception"
                    )

            is_wait_call = isinstance(node, ast.Call) and isinstance(
                node.func, ast.Attribute
            )
            if is_wait_call and node.func.attr == "wait_for_timeout":
                violations.append(
                    f"{path.name}:{node.lineno}: wait_for_timeout"
                )

            is_test = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            if is_test and node.name.startswith("test_"):
                for child in ast.walk(node):
                    if isinstance(child, ast.Return) and child.value is None:
                        violations.append(
                            f"{path.name}:{child.lineno}: silent return in {node.name}"
                        )

    assert not violations, "\n".join(violations)
