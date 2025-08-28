from typing import Dict, List


def _insert_into_tree(tree: Dict[str, dict], path_parts: List[str], mod: Dict) -> None:
    """Insert a module dict into the tree at the given path parts.

    Mirrors the logic of the previous nested `insert` function inside render_tree.
    """
    cur = tree
    for i, part in enumerate(path_parts):
        cur = cur.setdefault(part, {})
        if i == len(path_parts) - 1:
            cur.setdefault("__module__", mod)


def _draw_tree(node: Dict, lines: List[str], prefix: str = "") -> None:
    """Populate `lines` with the ASCII representation for `node`.

    Mirrors the logic of the previous nested `draw` function inside render_tree.
    """
    # list entries except the special __module__ key
    keys = [k for k in node.keys() if k != "__module__"]
    keys.sort()
    mod = node.get("__module__")
    if mod:
        # print classes and functions under this module
        for c in mod.get("classes", []):
            lines.append(
                f"{prefix}├─ class {c['name']} (bases: {', '.join(c.get('bases', [])) or 'object'})"
            )
            methods = c.get("methods", [])
            for j, m in enumerate(methods):
                is_last_method = j == len(methods) - 1 and not keys
                branch = "└" if is_last_method else "├"
                lines.append(f"{prefix}│  {branch}─ def {m['name']}()")
        funcs = mod.get("functions", [])
        for i, f in enumerate(funcs):
            is_last_func = i == len(funcs) - 1 and not keys
            branch = "└" if is_last_func else "├"
            lines.append(f"{prefix}{branch}─ def {f['name']}()")

    for i, k in enumerate(keys):
        is_last = i == len(keys) - 1
        branch = "└" if is_last else "├"
        lines.append(f"{prefix}{branch}─ {k}")
        _draw_tree(node[k], lines, prefix + ("   " if is_last else "│  "))


def render_tree(model_dict: Dict) -> str:
    """Render a human-readable ASCII tree of the package hierarchy.

    Args:
        model_dict (Dict): A model as produced by ``crawl_package`` or ``PackageModel.to_dict``.

    Returns:
        str: A string with an ASCII tree, prefixed by a header listing package roots.

    Raises:
        KeyError: If ``model_dict`` lacks required keys (only when providing a malformed input).

    Examples:
    - Render a small in-memory model
        ```python

        >>> model = {
        ...     'roots': ['pkg'],
        ...     'modules': {
        ...         'pkg': {
        ...             'name': 'pkg',
        ...             'path': 'X',
        ...             'classes': [{'name': 'A', 'lineno': 1, 'bases': [], 'methods': []}],
        ...             'functions': [{'name': 'f', 'lineno': 2, 'decorators': []}],
        ...             'imports': []
        ...         }
        ...     }
        ... }
        >>> out = render_tree(model)
        >>> 'Package roots: pkg' in out
        True
        >>> 'class A' in out and 'def f()' in out
        True

        ```

    See Also:
        crawl_package: Produces a compatible model dictionary.
        to_json: For serializing the model to JSON.
    """
    modules: Dict[str, Dict] = model_dict.get("modules", {})

    # Build nested dict tree structure based on dotted module names
    tree: Dict[str, dict] = {}

    for name, mod in modules.items():
        parts = name.split(".") if name else ["<root>"]
        _insert_into_tree(tree, parts, mod)

    lines: List[str] = []

    _draw_tree(tree, lines)
    header = f"Package roots: {', '.join(model_dict.get('roots', []))}\n"
    return header + "\n".join(lines)
