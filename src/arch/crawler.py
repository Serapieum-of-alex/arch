from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Dict, List, Iterable
from arch.data_models import PackageModel, ModuleInfo

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
    p = Path(path)
    return p.is_dir() and (p / "__init__.py").is_file()


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
    root_path = Path(root).absolute()
    for p in root_path.rglob("*.py"):
        # Skip any files that are inside ignored directories
        if any(part in IGNORED_DIRS for part in p.parts):
            continue
        yield str(p.absolute())


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
        roots.append(Path(root).name)
    # Also include any immediate sub-directories that are packages
    try:
        for p in Path(root).iterdir():
            if p.is_dir() and _is_package_dir(str(p)):
                roots.append(p.name)
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

        mod = ModuleInfo.from_file(file_path, abs_root)
        if mod is None:
            continue
        modules[mod.name] = mod

    model = PackageModel(
        root_path=str(abs_root), roots=_discover_roots(abs_root), modules=modules
    )
    return model.to_dict()


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
