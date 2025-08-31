import ast
from typing import List, Dict, Optional, Any
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field
from arch.utils import _extract_name


def get_filtered_objects(items):
    groups = defaultdict(list)
    for obj in items:
        groups[type(obj)].append(obj)

    return groups


@dataclass
class Function:
    """Lightweight description of a top-level or method function discovered in a module.

    Args:
        name (str): The function/method name.
        lineno (int): Line number where the function is defined in its source file (1-based).
        decorators (List[str]): Names of decorators applied to this function, if any.

    Examples:
    - Inspect a simple function and record its name and definition line
        ```python

        >>> info = Function(name="foo", lineno=10, decorators=["staticmethod"])
        >>> info.name
        'foo'

        ```
    """

    name: str
    lineno: int
    decorators: List[str] = field(default_factory=list)

    @classmethod
    def from_tree_node(cls, node):
        decorators = [_extract_name(d) for d in node.decorator_list]
        return cls(name=node.name, lineno=node.lineno, decorators=decorators)

    def to_dict(self):
        return {
            "name": self.name,
            "lineno": self.lineno,
            "decorators": self.decorators,
        }

    def build_edges(self, module_name: str) -> Dict[str, str]:
        return {
                "type": "module_contains",
                "from": module_name,
                "to": f"{module_name}.{self.name}",
            }

    def to_mermaid_class_diagram(self, detail_level: str = "all", include_decorators: bool = False) -> str:
        """Create a Mermaid class diagram string for this function.

        Args:
            detail_level (str): Controls whether this function is rendered based on naming convention.
                - "all": always render this function (default)
                - "public": render only if the function name does not start with an underscore
                - "none": do not render anything
            include_decorators (bool): If True and the function is rendered, add a Mermaid note listing decorators.

        Returns:
            str: Mermaid class diagram representing this function node. If filtered out by
            detail_level, returns a diagram header with no nodes.
        """
        allowed_levels = {"all", "public", "none"}
        if detail_level not in allowed_levels:
            raise ValueError(
                f"Unsupported detail_level '{detail_level}'. Expected one of {sorted(allowed_levels)}"
            )

        lines: List[str] = ["classDiagram"]

        # Apply filtering based on detail_level
        if detail_level == "none":
            return "\n".join(lines)
        if detail_level == "public" and self.name.startswith("_"):
            return "\n".join(lines)

        # Render the function as a stereotyped class node
        s = "{\n    }"
        lines.append(f"    class {self.name} {s}")

        # Optionally add decorators as a note
        if include_decorators and self.decorators:
            decos = ", ".join(f"@{d}" if not str(d).startswith("@") else str(d) for d in self.decorators)
            # Mermaid classDiagram supports notes attached to a class
            lines.append(f"note for {self.name} \"decorators: {decos}\"")

        return "\n".join(lines)


@dataclass
class Class:
    """Description of a class discovered in a module.

    Attributes:
        name (str): Class name.
        lineno (int): Line number where the class is defined in its source file (1-based).
        bases (List[str]): Names of the base classes as parsed from the AST.
        methods (List[Function]): Methods defined directly on the class.

    Examples:
    - Create a ClassInfo with two methods
        ```python

        >>> cls = Class(name="MyClass", lineno=5, bases=["Base"], methods=[Function("a", 10), Function("b", 20)])
        >>> [m.name for m in cls.methods]
        ['a', 'b']

        ```
    """

    name: str
    lineno: int
    bases: List[str] = field(default_factory=list)
    methods: List[Function] = field(default_factory=list)

    @classmethod
    def from_tree_node(cls, node):
        bases = [_extract_name(b) for b in node.bases]
        methods: List[Function] = []
        for n in node.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                decorators = [_extract_name(d) for d in n.decorator_list]
                methods.append(
                    Function(
                        name=n.name, lineno=n.lineno, decorators=decorators
                    )
                )

        return cls(
                name=node.name, lineno=node.lineno, bases=bases, methods=methods
            )

    def to_dict(self):
        return {
            "name": self.name,
            "lineno": self.lineno,
            "bases": self.bases,
            "methods": [
                {
                    "name": m.name,
                    "lineno": m.lineno,
                    "decorators": m.decorators,
                }
                for m in self.methods
            ],
        }

    def build_edges(self, module_name: str):
        edges = [
            {
                "type": "module_contains",
                "from": module_name,
                "to": f"{module_name}.{self.name}",
            }
        ]
        # class -> method containment
        for meth in self.methods:
            edges.append(
                {
                    "type": "class_contains",
                    "from": f"{module_name}.{self.name}",
                    "to": f"{module_name}.{self.name}.{meth.name}",
                }
            )
        # inheritance edges
        for base in self.bases:
            edges.append(
                {"type": "inherits", "from": f"{module_name}.{self.name}", "to": base}
            )

        return edges

    def to_mermaid_class_diagram(self, include_relations: bool = True, detail_level: str = "all") -> str:
        """Create a Mermaid class diagram string for this class.

        Args:
            include_relations (bool): If True, include inheritance relations to base classes.
            detail_level (str): Controls which methods are included in the diagram. One of:
                - "all": include all methods (default)
                - "public": include only methods that do not start with an underscore
                - "none": do not include any methods

        Returns:
            str: Mermaid class diagram describing this class.

        Notes:
            - Only method names are available; parameters and attributes are not tracked by the model.
            - Methods are rendered as public (+) with empty parameter lists for simplicity.
        """
        # Validate detail_level
        allowed_levels = {"all", "public", "none"}
        if detail_level not in allowed_levels:
            raise ValueError(f"Unsupported detail_level '{detail_level}'. Expected one of {sorted(allowed_levels)}")

        lines: List[str] = ["classDiagram"]

        # Class declaration with methods
        lines.append(f"class {self.name} {{")
        # Determine which methods to include
        if detail_level == "all":
            selected_methods = self.methods
        elif detail_level == "public":
            selected_methods = [m for m in self.methods if not m.name.startswith("_")]
        else:  # "none"
            selected_methods = []

        for m in sorted(selected_methods, key=lambda mm: mm.name):
            lines.append(f"  +{m.name}()")
        lines.append("}")

        # Inheritance relations
        if include_relations:
            for base in sorted(self.bases):
                # Mermaid: Base <|-- Derived
                lines.append(f"{base} <|-- {self.name}")

        return "\n".join(lines)


@dataclass
class Module:
    """Container describing a single Python module discovered under the root.

    Args:
        name (str): Dotted module name relative to the crawl root (e.g., "pkg.sub.module").
        path (str): Absolute filesystem path to the module file.
        classes (List[Class]): Classes defined in this module.
        functions (List[Function]): Top-level functions defined in this module.
        imports (List[str]): Imported module names (best-effort, based on static AST parsing).

    Examples:
    - Construct a module description manually
        ```python

        >>> mi = Module(name="pkg.mod", path="/abs/path/mod.py")
        >>> mi.name
        'pkg.mod'

        ```

    See Also:
        crawl_package: High-level crawler producing ModuleInfo entries.
        build_edges: Generates relationships for modules, classes and functions.
    """

    name: str  # dotted name relative to root (e.g., package.sub.module)
    path: str  # absolute filesystem path
    classes: List[Class] = field(default_factory=list)
    functions: List[Function] = field(default_factory=list)
    imports: List[str] = field(
        default_factory=list
    )  # imported module names (best-effort)

    @staticmethod
    def convert_path_to_dot(root: str, file_path: str) -> str:
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
            >>> Module.convert_path_to_dot("/path/to/root", "/path/to/root/pkg/mod.py")  # doctest: +SKIP
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
            >>> Module.convert_path_to_dot("/path/to/root", "/path/to/root/pkg/__init__.py")  # doctest: +SKIP
            'pkg'
            ```
        """
        file_p = Path(file_path).resolve()

        if root is not None:
            root_path = Path(root).resolve()
            try:
                rel = file_p.relative_to(root_path)
            except ValueError:
                # Fallback to generic relative path computation if not under root
                rel = Path(str(file_p).replace(str(root_path), "").lstrip("/\\"))
        else:
            rel = Path(str(file_p).lstrip("/\\"))

        # Remove extension and split into parts
        no_ext = rel.with_suffix("")
        parts = [part for part in no_ext.parts if part != "__init__"]
        dotted = ".".join(parts)
        # If file is __init__.py at the root package directory, dotted may be empty.
        # We'll handle roots separately.
        return dotted

    @staticmethod
    def get_tree(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=path)
        except (SyntaxError, UnicodeDecodeError):
            return None
        return tree

    @staticmethod
    def get_classes(groups):
        return [Class.from_tree_node(node) for node in groups.get(ast.ClassDef, [])]

    @staticmethod
    def get_functions(groups):
        return [
            Function.from_tree_node(node) for node in
            groups.get(ast.FunctionDef, []) + groups.get(ast.AsyncFunctionDef, [])
        ]

    @staticmethod
    def get_imports(groups):
        imports = []

        for node in groups.get(ast.Import, []):

            for alias in node.names:
                if alias.name:
                    imports.append(alias.name)

        for node in groups.get(ast.ImportFrom, []):
            module = node.module or ""
            if module:
                imports.append(module)

        return imports

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "classes": [c.to_dict() for c in self.classes],
            "functions": [f.to_dict() for f in self.functions],
            "imports": self.imports,
        }

    def build_edges(self):
        edges = []
        for class_data in self.classes:
            edges.extend(class_data.build_edges(self.name))

        for func in self.functions:
            edges.append(
                func.build_edges(self.name)
            )
        # imports edges
        for imp in self.imports:
            edges.append({"type": "imports", "from": self.name, "to": imp})

        return edges

    def to_mermaid_class_diagram(
        self, include_relations: bool = True, class_detail_level: str = "all", function_detail_level: str = "all",
        include_decorators=True
    ) -> str:
        """Create a Mermaid class diagram string for this module.

        This renders all classes found in the module (and optionally inheritance
        relations) and optionally includes top-level functions as stereotyped
        function nodes.

        Args:
            include_relations (bool): If True, include inheritance relations among classes.
            class_detail_level (str): Which class methods to include. One of:
                - "all": include all methods
                - "public": only methods that do not start with an underscore
                - "none": do not include any methods
            function_detail_level (str): Which top-level functions to include. One of:
                - "all": include all functions
                - "public": only functions that do not start with an underscore
                - "none": do not include any functions

        Returns:
            str: Mermaid class diagram describing all classes (and optionally functions) in this module.
        """
        allowed_levels = {"all", "public", "none"}
        if class_detail_level not in allowed_levels:
            raise ValueError(
                f"Unsupported class_detail_level '{class_detail_level}'. Expected one of {sorted(allowed_levels)}"
            )
        if function_detail_level not in allowed_levels:
            raise ValueError(
                f"Unsupported function_detail_level '{function_detail_level}'. Expected one of {sorted(allowed_levels)}"
            )

        lines: List[str] = ["classDiagram"]

        # Render classes
        for cls in sorted(self.classes, key=lambda c: c.name):
            # Reuse Class.to_mermaid_class_diagram and drop the header line
            cls_diagram = cls.to_mermaid_class_diagram(
                include_relations=False, detail_level=class_detail_level
            )
            parts = cls_diagram.splitlines()
            if parts and parts[0].strip().lower() == "classdiagram":
                parts = parts[1:]
            lines.extend(parts)

        # Render inheritance relations once (to avoid duplicates across class blocks)
        if include_relations:
            for cls in sorted(self.classes, key=lambda c: c.name):
                for base in sorted(cls.bases):
                    lines.append(f"{base} <|-- {cls.name}")

        # Render top-level functions via Function.to_mermaid_class_diagram
        if function_detail_level != "none":
            if function_detail_level == "all":
                funcs = self.functions
            else:  # "public"
                funcs = [f for f in self.functions if not f.name.startswith("_")]

            for f in sorted(funcs, key=lambda ff: ff.name):
                func_diagram = f.to_mermaid_class_diagram(detail_level=function_detail_level, include_decorators=include_decorators)
                parts = func_diagram.splitlines()
                if parts and parts[0].strip().lower() == "classdiagram":
                    parts = parts[1:]
                lines.extend(parts)

        return "\n".join(lines)

    def dependency(self):
        lines: List[str] = ["classDiagram"]
        added_imports = set()
        for imp in self.imports:
            edge = (self.name, imp)
            if edge not in added_imports:
                lines.append(f"{self.name} ..> {imp} : imports")
                added_imports.add(edge)

        return "\n".join(lines)

    @classmethod
    def from_file(cls, file_path: str, root: str) -> Optional["Module"]:
        """Parse a Python source file and extract high-level structural information.

        This function uses Python's ``ast`` module to find classes, top-level functions,
        and imported module names. It returns a ModuleInfo describing the contents.

        Args:
            file_path (str): Absolute path to a Python source file to parse.
            dotted_name (str): Dotted module name that will be associated with the file.

        Returns:
            Optional[Module]: A populated ModuleInfo on success, or ``None`` when the
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
        dotted_name = Module.convert_path_to_dot(root, file_path)
        # If dotted is empty (root __init__.py), use the directory name as module name
        if not dotted_name:
            base = Path(file_path).parent.name
            dotted_name = base

        tree = cls.get_tree(file_path)
        groups = get_filtered_objects(list(tree.body))

        return cls(
            name=dotted_name,
            path=str(Path(file_path).absolute()),
            classes=cls.get_classes(groups),
            functions=cls.get_functions(groups),
            imports=sorted(set(cls.get_imports(groups))),
        )


@dataclass
class Package:
    """In-memory representation of the crawled package structure.

    Args:
        root_path (str): Absolute root directory that was crawled.
        roots (List[str]): Top-level package names discovered beneath the root.
        modules (Dict[str, Module]): Mapping from dotted module name to ModuleInfo.

    Attributes:
        root_path (str): See Args.
        roots (List[str]): See Args.
        modules (Dict[str, Module]): See Args.

    Raises:
        TypeError: If instantiated with arguments of incompatible types.

    Examples:
    - Construct a minimal empty model and convert to a plain dictionary
        ```python

        >>> model = Package(root_path="C:/tmp", roots=["pkg"], modules={})
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
    modules: Dict[str, Module]  # dotted module name -> Module

    def to_dict(self) -> Dict:
        """Convert the model to a plain serializable dictionary.

        Returns:
            Dict: A dictionary with keys 'root_path', 'roots', 'modules', and 'edges'.

        Examples:
        - Minimal conversion
            ```python
            >>> from arch.crawler import Package
            >>> model = Package(root_path="C:/tmp", roots=[], modules={})
            >>> data = model.to_dict()
            >>> sorted(data.keys())
            ['edges', 'modules', 'root_path', 'roots']

            ```
        """
        return {
            "root_path": self.root_path,
            "roots": self.roots,
            "modules": {k: v.to_dict() for k, v in sorted(self.modules.items())},
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

            >>> mod = Module(name='pkg.m', path='X',
            ...                  classes=[Class(name='A', lineno=1, bases=['Base'], methods=[Function('x', 2)])],
            ...                  functions=[Function('f', 3)], imports=['math'])
            >>> pm = Package(root_path='/', roots=['pkg'], modules={'pkg.m': module})
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

        for _, module in self.modules.items():
            edges.extend(module.build_edges())

        return edges

    def to_mermaid_class_diagram(
        self,
        include_class_relations: bool = True,
        class_detail_level: str = "all",
        function_detail_level: str = "all",
        include_decorators: bool = True,
    ) -> str:
        """Create a Mermaid class diagram for the entire package.

        This combines all classes (and optionally functions) from every module into
        a single Mermaid "classDiagram". It can also include inheritance relations
        across all classes and add module import relations.

        Args:
            include_class_relations (bool): If True, include inheritance relations among
                all classes across modules.
            class_detail_level (str): Which class methods to include. One of:
                - "all": include all methods
                - "public": only methods that do not start with an underscore
                - "none": do not include any methods
            function_detail_level (str): Which top-level functions to include. One of:
                - "all": include all functions
                - "public": only functions that do not start with an underscore
                - "none": do not include any functions

        Returns:
            str: Mermaid class diagram describing the whole package.
        """
        allowed_levels = {"all", "public", "none"}
        if class_detail_level not in allowed_levels:
            raise ValueError(
                f"Unsupported class_detail_level '{class_detail_level}'. Expected one of {sorted(allowed_levels)}"
            )
        if function_detail_level not in allowed_levels:
            raise ValueError(
                f"Unsupported function_detail_level '{function_detail_level}'. Expected one of {sorted(allowed_levels)}"
            )

        lines: List[str] = ["classDiagram"]

        # Render each module's classes and functions, stripping individual headers
        for _, module in sorted(self.modules.items(), key=lambda kv: kv[0]):
            mod_diagram = module.to_mermaid_class_diagram(
                include_relations=False,
                class_detail_level=class_detail_level,
                function_detail_level=function_detail_level,
                include_decorators=include_decorators,
            )
            parts = mod_diagram.splitlines()
            if parts and parts[0].strip().lower() == "classdiagram":
                parts = parts[1:]
            lines.extend(parts)

        # Aggregate inheritance relations across all classes
        if include_class_relations:
            added_rel = set()
            for _, module in sorted(self.modules.items(), key=lambda kv: kv[0]):
                for cls in module.classes:
                    for base in cls.bases:
                        rel = (base, cls.name)
                        if rel not in added_rel:
                            lines.append(f"{base} <|-- {cls.name}")
                            added_rel.add(rel)


        return "\n".join(lines)
