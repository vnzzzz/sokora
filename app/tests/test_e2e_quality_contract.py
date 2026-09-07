"""E2E tests must fail when critical browser contracts are not exercised."""

import ast
from pathlib import Path

E2E_DIR = Path(__file__).parent / "e2e"


def _iter_test_functions(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                yield node
            yield node


def _is_count_positive_test(node: ast.AST) -> bool:
    if not isinstance(node, ast.Compare) or len(node.ops) != 1:
        return False
    if not isinstance(node.ops[0], ast.Gt):
        return False
    if len(node.comparators) != 1:
        return False
    comparator = node.comparators[0]
    if not isinstance(comparator, ast.Constant) or comparator.value != 0:
        return False
    left = node.left
    return (
        isinstance(left, ast.Call)
        and isinstance(left.func, ast.Attribute)
        and left.func.attr == "count"
    )


def _is_nonnegative_len_tautology(node: ast.AST) -> bool:
    if not isinstance(node, ast.Compare) or len(node.ops) != 1:
        return False
    if not isinstance(node.ops[0], ast.GtE):
        return False
    if len(node.comparators) != 1:
        return False
    comparator = node.comparators[0]
    if not isinstance(comparator, ast.Constant) or comparator.value != 0:
        return False
    left = node.left
    return (
        isinstance(left, ast.Call)
        and isinstance(left.func, ast.Name)
        and left.func.id == "len"
    )


def test_e2e_suite_has_no_known_false_pass_patterns() -> None:
    violations: list[str] = []

    for path in sorted(E2E_DIR.glob("test_*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                exception_type = node.type
                if isinstance(exception_type, ast.Name) and exception_type.id == "Exception":
                    violations.append(
                        f"{path.name}:{node.lineno}: broad except Exception"
                    )

            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "wait_for_timeout"
            ):
                violations.append(
                    f"{path.name}:{node.lineno}: wait_for_timeout"
                )

            if _is_nonnegative_len_tautology(node):
                violations.append(
                    f"{path.name}:{node.lineno}: len(...) >= 0 tautology"
                )

        for test_function in _iter_test_functions(tree):
            for node in ast.walk(test_function):
                if isinstance(node, ast.Return) and node.value is None:
                    violations.append(
                        f"{path.name}:{node.lineno}: silent return in {test_function.name}"
                    )
                if isinstance(node, ast.If) and _is_count_positive_test(node.test):
                    violations.append(
                        f"{path.name}:{node.lineno}: optional count() > 0 assertion in "
                        f"{test_function.name}"
                    )

    assert not violations, "\n".join(violations)
