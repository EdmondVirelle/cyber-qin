#!/usr/bin/env python3
"""
CI Script to verify that all translation keys used in the codebase exist.

Scans for:
    translator.tr("key")
    translator.tr('key')

Verifies against keys defined in:
    cyber_qin/core/translator.py
"""

import ast
import re
import sys
from pathlib import Path


def get_defined_keys(translator_path: Path) -> set[str]:
    """Extract keys defined in the Translator class in translator.py."""
    if not translator_path.exists():
        print(f"Error: {translator_path} not found.")
        sys.exit(1)

    content = translator_path.read_text(encoding="utf-8")

    # Simple regex to find keys in the DEFAULT_DATA or similar dictionary structure
    # This assumes keys are strings inside a dictionary definition.
    # A more robust way would be to import the module, but that requires setting up path.
    # For now, let's try to extract keys from the _data structure using regex which is
    # usually safer for static analysis than importing.

    # We look for patterns like "key": "value" inside the dictionary.
    # However, since translator.py might be complex, let's assume a specific structure.
    # Let's read the file and look for key definitions.

    # Actually, importing might be better if we can mocking things, but let's stick to AST/Regex for safety.
    # Let's look for known keys. In `translator_py`, keys are usually hardcoded strings.

    # Let's try to find all strings that look like keys (dot.separated) in the file?
    # No, that's too broad.

    # Let's try to parse the `DEFAULT_DATA` or `_data` dict if it exists.
    # Based on previous context, `translator.py` has a `_data` or `DEFAULT_DATA`.

    # Let's inspect the `translator.py` content via AST to find the dictionary.

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"Error parsing {translator_path}: {e}")
        sys.exit(1)

    keys = set()

    class KeyVisitor(ast.NodeVisitor):
        def visit_Dict(self, node):
            for key in node.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    # Heuristic: keys usually don't have spaces and might have dots
                    if "." in key.value or "_" in key.value:
                        keys.add(key.value)
            self.generic_visit(node)

    KeyVisitor().visit(tree)

    # Initial set of keys might be incomplete if we just scan all dicts.
    # Let's try to be smarter. If the file has a specific structure for languages.
    # We can try to just grab ALL strings that are used as keys in the codebase and check if they exist in the file.
    # But we need to know what exists.

    # Alternative: Just grep for all string literals in translator.py that look like "section.key".
    # This is a bit hacky but might work for a start.

    found_keys = set()
    matches = re.findall(r'["\']([a-z0-9_]+\.[a-z0-9_]+)["\']', content)
    found_keys.update(matches)

    return found_keys


def scan_usages(root_dir: Path) -> list[tuple[Path, int, str]]:
    """Scan codebase for translator.tr("key") usages."""
    usages = []

    # Regex for translator.tr("key") or translator.tr('key')
    pattern = re.compile(r'translator\.tr\(\s*["\']([a-z0-9_]+\.[a-z0-9_]+)["\']')

    for py_file in root_dir.rglob("*.py"):
        if "tests" in py_file.parts:
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            for match in pattern.finditer(line):
                key = match.group(1)
                usages.append((py_file, i, key))

    return usages


def main():
    root = Path(__file__).resolve().parent.parent
    translator_path = root / "cyber_qin" / "core" / "translator.py"

    if not translator_path.exists():
        print(f"Critical: {translator_path} does not exist.")
        return 1

    defined_keys = get_defined_keys(translator_path)
    print(f"Found {len(defined_keys)} defined keys in translator.py")

    usages = scan_usages(root / "cyber_qin")
    print(f"Found {len(usages)} translation usages.")

    missing = []
    for file_path, line, key in usages:
        if key not in defined_keys:
            # Maybe it's defined but my simple parser missed it?
            # Or maybe it's dynamic?
            # For now, let's report it.
            missing.append(
                f"{file_path.relative_to(root)}:{line} uses '{key}' which was not found."
            )

    if missing:
        print("\nMissing Keys (or parser failed to find them):")
        for m in missing:
            print(m)
        print(f"\nFound {len(missing)} missing translation keys.")
        return 1

    print("\nAll translation keys verified!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
