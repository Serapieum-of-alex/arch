from arch.data_models import Package, Module, Class, Function
from pathlib import Path


class TestPackageModel_to_dict:
    def test_empty_model_serialization(self):
        """Inputs: Create a Package with no modules and empty roots list.
        Expected: to_dict returns a dict with keys root_path, roots, modules={}, edges=[].
        Checks: Structure of the serialized dict and the empty edges list from build_edges.
        """
        pm = Package(root_path=str(Path.cwd()), roots=[], modules={})
        d = pm.to_dict()
        assert sorted(d.keys()) == ["edges", "modules", "root_path", "roots"]
        assert d["root_path"] == str(Path.cwd())
        assert d["roots"] == []
        assert d["modules"] == {}
        assert d["edges"] == []

    def test_populated_model_serialization_and_sorted_modules(self):
        """Inputs: Build a Package with multiple modules containing classes, methods, functions, and imports.
        Expected: to_dict returns a dict with modules serialized under sorted keys; nested structures for classes,
        methods, and functions include name/lineno/decorators; imports are preserved; edges are included.
        Checks: Sorting of module keys, correctness of nested serialization, and presence of expected edge types.
        """
        # Build classes and functions
        concrete = Class(
            name="Concrete",
            lineno=60,
            bases=["PrintableMixin", "Base"],
            methods=[
                Function("area", 66),
                Function("default", 70, decorators=["classmethod"]),
                Function("tau", 42, decorators=["staticmethod"]),
            ],
        )
        core_funcs = [
            Function("greet", 44, decorators=["simple_deco"]),
            Function("add", 48, decorators=["times"]),
        ]
        mod_core = Module(
            name="pkg.core",
            path=str(Path(__file__).parent / "data" / "test-package-1" / "core.py"),
            classes=[concrete],
            functions=core_funcs,
            imports=["math", "typing"],
        )

        mod_utils = Module(
            name="pkg.utils",
            path=str(Path(__file__).parent / "data" / "test-package-1" / "utils.py"),
            classes=[],
            functions=[Function("parse", 97)],
            imports=[],
        )

        mod_only = Module(
            name="pkg.only_imports",
            path=str(Path(__file__).parent / "data" / "test-package-1" / "only_imports.py"),
            classes=[],
            functions=[],
            imports=["os", "sys", "math"],
        )

        mod_multi = Module(
            name="pkg.multi",
            path=str(Path(__file__).parent / "data" / "test-package-1" / "multi_decorators.py"),
            classes=[],
            functions=[Function("multi", 15, decorators=["deco1", "deco2"])],
            imports=[],
        )

        modules = {
            mod_core.name: mod_core,
            mod_utils.name: mod_utils,
            mod_only.name: mod_only,
            mod_multi.name: mod_multi,
        }
        pm = Package(root_path=str(Path.cwd()), roots=["pkg"], modules=modules)

        d = pm.to_dict()
        # Keys present
        assert sorted(d.keys()) == ["edges", "modules", "root_path", "roots"]
        # Sorted modules by key
        module_keys = list(d["modules"].keys())
        assert module_keys == sorted(modules.keys())
        # Check nested serialization for a class
        core_ser = d["modules"]["pkg.core"]
        assert core_ser["classes"][0]["name"] == "Concrete"
        assert core_ser["classes"][0]["bases"] == ["PrintableMixin", "Base"]
        meth_names = [m["name"] for m in core_ser["classes"][0]["methods"]]
        assert set(meth_names) == {"area", "default", "tau"}
        # Function decorators preserved
        multi_ser = d["modules"]["pkg.multi"]
        assert multi_ser["functions"][0]["decorators"] == ["deco1", "deco2"]
        # Imports preserved
        only_ser = d["modules"]["pkg.only_imports"]
        assert set(only_ser["imports"]) == {"os", "sys", "math"}
        # Edges exist (sanity; detailed checks in build_edges tests)
        assert any(e["type"] == "module_contains" for e in d["edges"])  # coarse check



class TestPackageModel_build_edges:
    def test_no_edges_for_empty_model(self):
        """Inputs: Package with an empty modules mapping.
        Expected: build_edges returns an empty list.
        Checks: No edges created when there are no modules/classes/functions/imports.
        """
        pm = Package(root_path="/", roots=[], modules={})
        assert pm.build_edges() == []

    def test_edges_for_comprehensive_model(self):
        """Inputs: Construct a Package with modules containing classes (with methods and multiple bases),
        functions, and imports, including a module that only has imports.
        Expected: build_edges returns edges of types module_contains (for classes and functions),
        class_contains (for each method), inherits (for each base), and imports (for each import).
        Checks: Count of edges per category and presence of specific representative edges.
        """
        concrete = Class(
            name="Concrete",
            lineno=60,
            bases=["PrintableMixin", "Base"],
            methods=[Function("area", 66), Function("default", 70)],
        )
        mod_core = Module(
            name="pkg.core",
            path="/abs/core.py",
            classes=[concrete],
            functions=[Function("greet", 44), Function("add", 48)],
            imports=["math", "typing"],
        )
        mod_utils = Module(
            name="pkg.utils",
            path="/abs/utils.py",
            classes=[],
            functions=[Function("parse", 97)],
            imports=[],
        )
        mod_only = Module(
            name="pkg.only_imports",
            path="/abs/only_imports.py",
            classes=[],
            functions=[],
            imports=["os", "sys", "math"],
        )
        modules = {m.name: m for m in [mod_core, mod_utils, mod_only]}
        pm = Package(root_path="/abs", roots=["pkg"], modules=modules)

        edges = pm.build_edges()

        # categorize
        mc = [e for e in edges if e["type"] == "module_contains"]
        cc = [e for e in edges if e["type"] == "class_contains"]
        inh = [e for e in edges if e["type"] == "inherits"]
        imps = [e for e in edges if e["type"] == "imports"]

        # Counts
        assert len(mc) == 1 + 2 + 1  # 1 class in core + 2 funcs in core + 1 func in utils
        assert len(cc) == 2  # 2 methods on Concrete
        assert len(inh) == 2  # PrintableMixin, Base
        assert len(imps) == 2 + 0 + 3  # core has 2, utils 0, only_imports 3

        # Specific edges
        assert {e["to"] for e in mc} >= {"pkg.core.Concrete", "pkg.core.greet", "pkg.core.add", "pkg.utils.parse"}
        assert {e["to"] for e in cc} == {"pkg.core.Concrete.area", "pkg.core.Concrete.default"}
        assert {e["to"] for e in inh} == {"PrintableMixin", "Base"}
        assert {e["to"] for e in imps} >= {"os", "sys", "math", "typing"}

    def test_edges_when_no_classes_or_functions_but_imports_exist(self):
        """Inputs: Package with a single module that has only imports but no classes or functions.
        Expected: build_edges creates only 'imports' edges corresponding to each import.
        Checks: Edge list contains only 'imports' entries and in the expected count.
        """
        mod = Module(name="pkg.only", path="/abs/only.py", imports=["os", "sys"])  # no classes/functions
        pm = Package(root_path="/", roots=["pkg"], modules={"pkg.only": mod})
        edges = pm.build_edges()
        assert all(e["type"] == "imports" for e in edges)
        assert {e["to"] for e in edges} == {"os", "sys"}
