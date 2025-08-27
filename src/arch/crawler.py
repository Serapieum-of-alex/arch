from __future__ import annotations

import ast
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Iterable
from arch.data_models import PackageModel, ModuleInfo, ClassInfo, FunctionInfo

# Public API surface of this module:
# - crawl_package(path: str) -> Dict
# - render_tree(model: Dict) -> str
# - to_json(model: Dict, indent: int = 2) -> str
# - main(argv: Optional[List[str]] = None) -> int

IGNORED_DIRS = {
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "venv",
    "env",
    "build",
    "dist",
}



def _is_package_dir(path: str) -> bool:
    """Determine whether a filesystem directory is a Python package.

    Args:
        path (str): Absolute or relative path to a directory.

    Returns:
        bool: True if the directory exists and contains an ``__init__.py`` file.

    Raises:
        None: This function does not raise on its own; it relies on os.path checks only.

    Examples:
    - True when a directory has an __init__.py file
        ```python
        
        >>> import tempfile, os
        >>> with tempfile.TemporaryDirectory() as d:
        ...     _ = open(os.path.join(d, "__init__.py"), "w", encoding="utf-8").close()
        ...     _is_package_dir(d)
        True
        
        ```
    - False when directory is missing or lacks __init__.py
        ```python
        
        >>> import tempfile, os
        >>> with tempfile.TemporaryDirectory() as d:
        ...     _is_package_dir(os.path.join(d, "sub"))  # non-existent
        False
        >>> with tempfile.TemporaryDirectory() as d:
        ...     os.mkdir(os.path.join(d, "sub"))
        ...     _is_package_dir(os.path.join(d, "sub"))
        False
        
        ```
    """
    return os.path.isdir(path) and os.path.isfile(os.path.join(path, "__init__.py"))


def _iter_python_files(root: str) -> Iterable[str]:
    """Yield absolute paths to Python files under a root directory.

    Args:
        root (str): Absolute or relative path to the directory to scan.

    Returns:
        Iterable[str]: Generator of absolute file paths to ``.py`` files. Directories listed in ``IGNORED_DIRS`` are skipped.

    Examples:
    - Find Python files beneath a temporary directory
        ```python
        
        >>> import os, tempfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     _ = open(os.path.join(d, "a.py"), "w", encoding="utf-8").close()
        ...     os.mkdir(os.path.join(d, "sub"))
        ...     _ = open(os.path.join(d, "sub", "b.py"), "w", encoding="utf-8").close()
        ...     files = sorted(os.path.basename(p) for p in _iter_python_files(d))
        >>> files
        ['a.py', 'b.py']
        
        ```
    """
    for dir_path, dir_names, file_names in os.walk(root):
        # prune ignored directories in-place
        dir_names[:] = [d for d in dir_names if d not in IGNORED_DIRS]
        for filename in file_names:
            if not filename.endswith(".py"):
                continue
            yield os.path.join(dir_path, filename)


def _module_name_from_path(root: str, file_path: str) -> str:
    """Compute dotted module name from a file path relative to the crawl root.

    Args:
        root (str): Absolute root directory used for relative path calculation.
        file_path (str): Absolute path to a ``.py`` file.

    Returns:
        str: The dotted module path (e.g., "pkg.sub.module"). For ``__init__.py`` files, the package name is returned (e.g., "pkg.sub").

    Examples:
    - Regular module file
        ```python
        
        >>> import tempfile, os
        >>> with tempfile.TemporaryDirectory() as d:
        ...     pkg = os.path.join(d, "pkg")
        ...     os.mkdir(pkg)
        ...     _ = open(os.path.join(pkg, "__init__.py"), "w", encoding="utf-8").close()
        ...     mod = os.path.join(pkg, "mod.py")
        ...     _ = open(mod, "w", encoding="utf-8").close()
        ...     _module_name_from_path(d, mod)
        'pkg.mod'
        
        ```
    - Package ``__init__.py``
        ```python
        
        >>> import tempfile, os
        >>> with tempfile.TemporaryDirectory() as d:
        ...     pkg = os.path.join(d, "pkg")
        ...     os.mkdir(pkg)
        ...     init = os.path.join(pkg, "__init__.py")
        ...     _ = open(init, "w", encoding="utf-8").close()
        ...     _module_name_from_path(d, init)
        'pkg'
        
        ```
    """
    rel = Path(os.path.relpath(file_path, root))
    no_ext = rel.stem
    parts = []
    for part in no_ext.split(os.sep):
        if part == "__init__":
            # __init__.py represents the package itself; skip the last part
            continue
        parts.append(part)
    dotted = ".".join(parts).replace("/", ".").replace("\\", ".")
    # If file is __init__.py at the root package directory, dotted may be empty.
    # We'll handle roots separately.
    return dotted


def _discover_roots(root: str) -> List[str]:
    """Discover top-level Python package directories under a filesystem root.

    A directory is considered a root package if it contains an ``__init__.py`` file.
    The provided ``root`` itself is included if it looks like a package, and any
    immediate subdirectories that are packages are also included. Duplicates are
    removed while preserving discovery order.

    Args:
        root (str): Absolute or relative path to scan for Python packages.

    Returns:
        List[str]: Names of discovered top-level package directories (not full paths).

    Raises:
        None: Any FileNotFoundError from listing the directory is handled internally.

    Examples:
    - Root is a package and has a subpackage
        ```python
        
        >>> import os, tempfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     # create root as a package (its exact name is non-deterministic)
        ...     _ = open(os.path.join(d, "__init__.py"), "w", encoding="utf-8").close()
        ...     # create subpackage
        ...     sub = os.path.join(d, "sub")
        ...     os.mkdir(sub)
        ...     _ = open(os.path.join(sub, "__init__.py"), "w", encoding="utf-8").close()
        ...     roots = _discover_roots(d)
        ...     'sub' in roots
        True
        
        ```
    - Root is not a package, but contains two top-level packages
        ```python
        
        >>> import os, tempfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     for name in ("a", "b"):
        ...         p = os.path.join(d, name)
        ...         os.mkdir(p)
        ...         _ = open(os.path.join(p, "__init__.py"), "w", encoding="utf-8").close()
        ...     sorted(_discover_roots(d))
        ['a', 'b']
        
        ```
    """
    # If the given root is itself a Python package, consider it a root.
    roots: List[str] = []
    if _is_package_dir(root):
        roots.append(os.path.basename(os.path.normpath(root)))
    # Also include any immediate sub-directories that are packages
    try:
        for name in os.listdir(root):
            full = os.path.join(root, name)
            if _is_package_dir(full):
                roots.append(name)
    except FileNotFoundError:
        pass
    # De-duplicate while preserving order
    seen = set()
    out: List[str] = []
    for r in roots:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


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


def _parse_module(file_path: str, dotted_name: str) -> Optional[ModuleInfo]:
    """Parse a Python source file and extract high-level structural information.

    This function uses Python's ``ast`` module to find classes, top-level functions,
    and imported module names. It returns a ModuleInfo describing the contents.

    Args:
        file_path (str): Absolute path to a Python source file to parse.
        dotted_name (str): Dotted module name that will be associated with the file.

    Returns:
        Optional[ModuleInfo]: A populated ModuleInfo on success, or ``None`` when the
        source cannot be parsed due to ``SyntaxError`` or ``UnicodeDecodeError``.

    Raises:
        None: Parse errors are caught and result in ``None`` being returned.

    Examples:
    - Parse a simple module with a class and a function
        ```python
        
        >>> import os, tempfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     p = os.path.join(d, "mod.py")
        ...     with open(p, "w", encoding="utf-8") as fh:
        ...         _ = fh.write("import math\\n")
        ...         _ = fh.write("\\n")
        ...         _ = fh.write("class A:\\n")
        ...         _ = fh.write("    pass\\n")
        ...         _ = fh.write("\\n")
        ...         _ = fh.write("def f():\\n")
        ...         _ = fh.write("    return 42\\n")
        ...     mi = _parse_module(p, "mod")
        ...     (mi.name, [c.name for c in mi.classes], [f.name for f in mi.functions], mi.imports)
        ('mod', ['A'], ['f'], ['math'])
        
        ```
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=file_path)
    except (SyntaxError, UnicodeDecodeError):
        return None

    classes: List[ClassInfo] = []
    functions: List[FunctionInfo] = []
    imports: List[str] = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            bases = [_extract_name(b) for b in node.bases]
            methods: List[FunctionInfo] = []
            for n in node.body:
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    decorators = [_extract_name(d) for d in n.decorator_list]
                    methods.append(FunctionInfo(name=n.name, lineno=n.lineno, decorators=decorators))
            classes.append(ClassInfo(name=node.name, lineno=node.lineno, bases=bases, methods=methods))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decorators = [_extract_name(d) for d in node.decorator_list]
            functions.append(FunctionInfo(name=node.name, lineno=node.lineno, decorators=decorators))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module:
                imports.append(module)

    return ModuleInfo(name=dotted_name, path=os.path.abspath(file_path), classes=classes, functions=functions, imports=sorted(set(imports)))


def crawl_package(root_path: str) -> Dict:
    """Crawl a directory for Python packages and build a serializable model.

    The crawler walks the directory tree under ``root_path``, finds Python modules,
    parses them to extract classes, functions, and imports, discovers top-level
    package roots, and finally returns a JSON-serializable dictionary.

    Args:
        root_path (str): Path to the root directory of the package or repository to crawl.

    Returns:
        Dict: A dictionary with keys:
            - ``root_path`` (str): Absolute root path that was crawled.
            - ``roots`` (List[str]): Discovered top-level package names.
            - ``modules`` (Dict[str, Any]): Dotted module name -> description dict.
            - ``edges`` (List[Dict[str, str]]): Relationships between modules, classes, and functions.

    Raises:
        None: Invalid files or non-parseable sources are skipped silently.

    Examples:
    - Crawl a tiny temporary package and inspect keys
        ```python
        
        >>> import os, tempfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     pkg = os.path.join(d, 'pkg')
        ...     os.mkdir(pkg)
        ...     _ = open(os.path.join(pkg, '__init__.py'), 'w', encoding='utf-8').close()
        ...     mpy = os.path.join(pkg, 'm.py')
        ...     with open(mpy, 'w', encoding='utf-8') as fh:
        ...         _ = fh.write('class A:\\n    pass\\n')
        ...     model = crawl_package(d)
        ...     sorted(model.keys())
        ['edges', 'modules', 'root_path', 'roots']
        
        ```
    - Check that the discovered module and class appear
        ```python
        
        >>> 'pkg.m' in model['modules']
        True
        >>> any(e['type'] == 'module_contains' and e['to'].endswith('.A') for e in model['edges'])
        True
        
        ```

    See Also:
        PackageModel: In-memory format used before conversion to dict.
        build_edges: Generates the relationships included in the output.
    """
    abs_root = Path(root_path).absolute()
    modules: Dict[str, ModuleInfo] = {}

    for file_path in _iter_python_files(abs_root):
        dotted = _module_name_from_path(abs_root, file_path)
        # If dotted is empty (root __init__.py), use the directory name as module name
        if not dotted:
            base = os.path.basename(os.path.dirname(file_path))
            dotted = base
        mod = _parse_module(file_path, dotted)
        if mod is None:
            continue
        modules[mod.name] = mod

    model = PackageModel(root_path=abs_root, roots=_discover_roots(abs_root), modules=modules)
    return model.to_dict()


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

    def insert(path_parts: List[str], mod: Dict):
        cur = tree
        for i, part in enumerate(path_parts):
            cur = cur.setdefault(part, {})
            if i == len(path_parts) - 1:
                cur.setdefault("__module__", mod)

    for name, mod in modules.items():
        parts = name.split(".") if name else ["<root>"]
        insert(parts, mod)

    lines: List[str] = []

    def draw(node: Dict, prefix: str = ""):
        # list entries except the special __module__ key
        keys = [k for k in node.keys() if k != "__module__"]
        keys.sort()
        mod = node.get("__module__")
        if mod:
            # print classes and functions under this module
            for c in mod.get("classes", []):
                lines.append(f"{prefix}├─ class {c['name']} (bases: {', '.join(c.get('bases', [])) or 'object'})")
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
            draw(node[k], prefix + ("   " if is_last else "│  "))

    draw(tree)
    header = f"Package roots: {', '.join(model_dict.get('roots', []))}\n"
    return header + "\n".join(lines)


def to_json(model_dict: Dict, indent: int = 2) -> str:
    """Serialize a model dictionary to a JSON string.

    Args:
        model_dict (Dict): Model as produced by ``crawl_package``.
        indent (int, optional): Indentation level passed to ``json.dumps``. Defaults to 2.

    Returns:
        str: JSON representation of the model.

    Examples:
    - Serialize a tiny model
        ```python
        
        >>> s = to_json({'roots': ['pkg'], 'modules': {}, 'edges': [], 'root_path': 'X'}, indent=0)
        >>> isinstance(s, str) and '"roots"' in s
        True
        
        ```
    """
    return json.dumps(model_dict, indent=indent)

