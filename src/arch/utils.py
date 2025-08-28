import ast

def _extract_name(node: ast.AST) -> str:
    """Best-effort string extraction for names from AST nodes.

    The function is used to turn various AST node types (Name, Attribute, Tuple,
    Call, Subscript, Constant) into a readable string representation that
    resembles the original source code identifier expression.

    Args:
        node (ast.AST): An AST node representing an expression.

    Returns:
        str: A readable string for the node. For unsupported nodes, ``repr(node)`` is used.

    Examples:
    - Names and attributes
        ```python

        >>> import ast
        >>> node = ast.parse("a.b.c", mode="eval").body
        >>> _extract_name(node)
        'a.b.c'

        ```
    - Tuple of names
        ```python

        >>> import ast
        >>> node = ast.parse("(x, y)", mode="eval").body
        >>> _extract_name(node)
        'x, y'

        ```
    """
    # Convert ast nodes representing names/attributes to a string
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_extract_name(node.value)}.{node.attr}"
    if isinstance(node, ast.Subscript):
        return _extract_name(node.value)
    if isinstance(node, ast.Call):
        return _extract_name(node.func)
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.Tuple):
        return ", ".join(_extract_name(elt) for elt in node.elts)
    return getattr(node, "id", repr(node))