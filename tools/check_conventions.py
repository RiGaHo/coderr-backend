"""Check source spans, documentation and prohibited Python constructs."""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def source_files():
    """Exclude generated migrations and installed third-party packages."""
    return [
        path
        for path in ROOT.rglob("*.py")
        if not {".venv", "migrations"}.intersection(path.relative_to(ROOT).parts)
    ]


def check_function(path, node):
    """Count every physical source line, including blanks and docstrings."""
    issues = []
    length = node.end_lineno - node.lineno + 1
    if length > 14:
        issues.append(
            f"{path}:{node.lineno}: {node.name} spans {length} lines (max 14)"
        )
    if not ast.get_docstring(node):
        issues.append(f"{path}:{node.lineno}: {node.name} needs a docstring")
    return issues


def check_node(path, node):
    """Check function spans and forbidden calls without scanning string content."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return check_function(path, node)
    if (
        isinstance(node, ast.ClassDef)
        and node.name != "Meta"
        and not ast.get_docstring(node)
    ):
        return [f"{path}:{node.lineno}: class {node.name} needs a docstring"]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id == "print":
            return [f"{path}:{node.lineno}: print() is prohibited"]
    return []


def main():
    """Report all source violations with a failing process status."""
    issues = []
    files = source_files()
    for path in files:
        for node in ast.walk(ast.parse(path.read_text())):
            issues.extend(check_node(path.relative_to(ROOT), node))
    sys.stdout.write(
        "\n".join(issues) + "\n" if issues else f"Checked {len(files)} files: OK\n"
    )
    return bool(issues)


if __name__ == "__main__":
    sys.exit(main())
