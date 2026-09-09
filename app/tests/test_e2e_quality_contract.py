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
                if isinstance(node.type, ast.Name):
                    if node.type.id == "Exception":
                        message = f"{path.name}:{node.lineno}: broad except Exception"
                        violations.append(message)

            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == "wait_for_timeout":
                        message = f"{path.name}:{node.lineno}: wait_for_timeout"
                        violations.append(message)

            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test_"):
                continue

            for child in ast.walk(node):
                if isinstance(child, ast.Return) and child.value is None:
                    message = (
                        f"{path.name}:{child.lineno}: silent return in {node.name}"
                    )
                    violations.append(message)

    assert not violations, "\n".join(violations)
