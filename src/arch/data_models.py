import ast
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass, field
from arch.utils import _extract_name


@dataclass
class FunctionInfo:
    """Lightweight description of a top-level or method function discovered in a module.

    Args:
        name (str): The function/method name.
        lineno (int): Line number where the function is defined in its source file (1-based).
        decorators (List[str]): Names of decorators applied to this function, if any.

    Examples:
    - Inspect a simple function and record its name and definition line
        ```python

        >>> info = FunctionInfo(name="foo", lineno=10, decorators=["staticmethod"])
        >>> info.name
        'foo'

        ```
    """

    name: str
    lineno: int
    decorators: List[str] = field(default_factory=list)


@dataclass
class ClassInfo:
    """Description of a class discovered in a module.

    Attributes:
        name (str): Class name.
        lineno (int): Line number where the class is defined in its source file (1-based).
        bases (List[str]): Names of the base classes as parsed from the AST.
        methods (List[FunctionInfo]): Methods defined directly on the class.

    Examples:
    - Create a ClassInfo with two methods
        ```python

        >>> cls = ClassInfo(name="MyClass", lineno=5, bases=["Base"], methods=[FunctionInfo("a", 10), FunctionInfo("b", 20)])
        >>> [m.name for m in cls.methods]
        ['a', 'b']

        ```
    """

    name: str
    lineno: int
    bases: List[str] = field(default_factory=list)
    methods: List[FunctionInfo] = field(default_factory=list)


@dataclass
class ModuleInfo:
    """Container describing a single Python module discovered under the root.

    Args:
        name (str): Dotted module name relative to the crawl root (e.g., "pkg.sub.module").
        path (str): Absolute filesystem path to the module file.
        classes (List[ClassInfo]): Classes defined in this module.
        functions (List[FunctionInfo]): Top-level functions defined in this module.
        imports (List[str]): Imported module names (best-effort, based on static AST parsing).

    Examples:
    - Construct a module description manually
        ```python

        >>> mi = ModuleInfo(name="pkg.mod", path="/abs/path/mod.py")
        >>> mi.name
        'pkg.mod'

        ```

    See Also:
        crawl_package: High-level crawler producing ModuleInfo entries.
        build_edges: Generates relationships for modules, classes and functions.
    """

    name: str  # dotted name relative to root (e.g., package.sub.module)
    path: str  # absolute filesystem path
    classes: List[ClassInfo] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    imports: List[str] = field(
        default_factory=list
    )  # imported module names (best-effort)

    @staticmethod
    def _module_name_from_path(root: str, file_path: str) -> str:
        """Compute dotted module name from a file path relative to the crawl root.

        Args:
            root (str):
                Absolute root directory of the package, the root is used for relative path calculation.
            file_path (str):
                module Absolute path.

        Returns:
            str:
                The dotted module path (e.g., "pkg.sub.module"). For ``__init__.py`` files, the package name is returned (e.g., "pkg.sub").

        Examples:
        - Regular module file
            Root directory layout:
            ```text

            /path/to/root/
            └── pkg/
                ├── __init__.py
                └── mod.py
            ```
            - the function is called with ``/path/to/root`` as root and ``/path/to/root/pkg/mod.py`` as file path
            ```python
            >>> ModuleInfo._module_name_from_path("/path/to/root", "/path/to/root/pkg/mod.py")  # doctest: +SKIP
            'pkg.mod'
            ```

        - Package ``__init__.py``
            - Root directory layout:
            ```text
            /path/to/root/
            └── pkg/
                └── __init__.py
            ```
            - The function is called with ``/path/to/root`` as root and ``/path/to/root/pkg/__init__.py`` as file path
            ```python
            >>> ModuleInfo._module_name_from_path("/path/to/root", "/path/to/root/pkg/__init__.py")  # doctest: +SKIP
            'pkg'
            ```
        """
        root_path = Path(root).resolve()
        file_p = Path(file_path).resolve()
        try:
            rel = file_p.relative_to(root_path)
        except ValueError:
            # Fallback to generic relative path computation if not under root
            rel = Path(str(file_p).replace(str(root_path), "").lstrip("/\\"))
        # Remove extension and split into parts
        no_ext = rel.with_suffix("")
        parts = [part for part in no_ext.parts if part != "__init__"]
        dotted = ".".join(parts)
        # If file is __init__.py at the root package directory, dotted may be empty.
        # We'll handle roots separately.
        return dotted

    @classmethod
    def from_file(cls, file_path: str, dotted_name: str) -> Optional["ModuleInfo"]:
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
                        methods.append(
                            FunctionInfo(
                                name=n.name, lineno=n.lineno, decorators=decorators
                            )
                        )
                classes.append(
                    ClassInfo(
                        name=node.name, lineno=node.lineno, bases=bases, methods=methods
                    )
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                decorators = [_extract_name(d) for d in node.decorator_list]
                functions.append(
                    FunctionInfo(name=node.name, lineno=node.lineno, decorators=decorators)
                )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name:
                        imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module:
                    imports.append(module)

        return cls(
            name=dotted_name,
            path=str(Path(file_path).absolute()),
            classes=classes,
            functions=functions,
            imports=sorted(set(imports)),
        )


@dataclass
class PackageModel:
    """In-memory representation of the crawled package structure.

    Args:
        root_path (str): Absolute root directory that was crawled.
        roots (List[str]): Top-level package names discovered beneath the root.
        modules (Dict[str, ModuleInfo]): Mapping from dotted module name to ModuleInfo.

    Attributes:
        root_path (str): See Args.
        roots (List[str]): See Args.
        modules (Dict[str, ModuleInfo]): See Args.

    Raises:
        TypeError: If instantiated with arguments of incompatible types.

    Examples:
    - Construct a minimal empty model and convert to a plain dictionary
        ```python

        >>> model = PackageModel(root_path="C:/tmp", roots=["pkg"], modules={})
        >>> d = model.to_dict()
        >>> sorted(d.keys())
        ['edges', 'modules', 'root_path', 'roots']

        ```

    See Also:
        crawl_package: Build a PackageModel from a filesystem tree.
        build_edges: Compute relationships stored under the 'edges' key.
    """

    root_path: str
    roots: List[str]  # top-level package names discovered
    modules: Dict[str, ModuleInfo]  # dotted module name -> ModuleInfo

    def to_dict(self) -> Dict:
        """Convert the model to a plain serializable dictionary.

        Returns:
            Dict: A dictionary with keys 'root_path', 'roots', 'modules', and 'edges'.

        Examples:
        - Minimal conversion
            ```python
            >>> from arch.crawler import PackageModel
            >>> model = PackageModel(root_path="C:/tmp", roots=[], modules={})
            >>> data = model.to_dict()
            >>> sorted(data.keys())
            ['edges', 'modules', 'root_path', 'roots']

            ```
        """
        return {
            "root_path": self.root_path,
            "roots": self.roots,
            "modules": {
                k: {
                    "name": v.name,
                    "path": v.path,
                    "classes": [
                        {
                            "name": c.name,
                            "lineno": c.lineno,
                            "bases": c.bases,
                            "methods": [
                                {
                                    "name": m.name,
                                    "lineno": m.lineno,
                                    "decorators": m.decorators,
                                }
                                for m in c.methods
                            ],
                        }
                        for c in v.classes
                    ],
                    "functions": [
                        {
                            "name": f.name,
                            "lineno": f.lineno,
                            "decorators": f.decorators,
                        }
                        for f in v.functions
                    ],
                    "imports": v.imports,
                }
                for k, v in sorted(self.modules.items())
            },
            "edges": self.build_edges(),
        }

    def build_edges(self) -> List[Dict[str, str]]:
        """Build relationship edges between modules, classes, functions, and imports.

        For each module, this function creates the following edge types:
        - ``module_contains``: from module to each class or function.
        - ``class_contains``: from class to each of its methods.
        - ``inherits``: from class to each base class name string.
        - ``imports``: from module to each imported module name.

        Returns:
            List[Dict[str, str]]: A list of edges, each with keys ``type``, ``from``, and ``to``.

        Raises:
            None

        Examples:
        - Build edges for a minimal model
            ```python

            >>> mod = ModuleInfo(name='pkg.m', path='X',
            ...                  classes=[ClassInfo(name='A', lineno=1, bases=['Base'], methods=[FunctionInfo('x', 2)])],
            ...                  functions=[FunctionInfo('f', 3)], imports=['math'])
            >>> pm = PackageModel(root_path='/', roots=['pkg'], modules={'pkg.m': mod})
            >>> edges = build_edges(pm)
            >>> any(e['type']=='module_contains' and e['to']=='pkg.m.A' for e in edges)
            True
            >>> any(e['type']=='class_contains' and e['to']=='pkg.m.A.x' for e in edges)
            True
            >>> any(e['type']=='inherits' and e['to']=='Base' for e in edges)
            True
            >>> any(e['type']=='imports' and e['to']=='math' for e in edges)
            True

            ```

        See Also:
            crawl_package: Produces the PackageModel consumed here.
        """
        edges: List[Dict[str, str]] = []
        # module -> class/function containment
        for mname, mod in self.modules.items():
            for c in mod.classes:
                edges.append(
                    {
                        "type": "module_contains",
                        "from": mname,
                        "to": f"{mname}.{c.name}",
                    }
                )
                # class -> method containment
                for meth in c.methods:
                    edges.append(
                        {
                            "type": "class_contains",
                            "from": f"{mname}.{c.name}",
                            "to": f"{mname}.{c.name}.{meth.name}",
                        }
                    )
                # inheritance edges
                for base in c.bases:
                    edges.append(
                        {"type": "inherits", "from": f"{mname}.{c.name}", "to": base}
                    )
            for f in mod.functions:
                edges.append(
                    {
                        "type": "module_contains",
                        "from": mname,
                        "to": f"{mname}.{f.name}",
                    }
                )
            # imports edges
            for imp in mod.imports:
                edges.append({"type": "imports", "from": mname, "to": imp})
        return edges
