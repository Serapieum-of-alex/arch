import os
from pathlib import Path

from arch.data_models import FunctionInfo, ClassInfo, ModuleInfo, PackageModel


class TestFunctionInfoInit:
    def test_default_decorators_list_is_empty_and_independent(self):
        """Inputs: Construct two FunctionInfo instances without passing decorators.
        Expected: Each instance has an empty list for `decorators`, and mutating one instance's list
        does not affect the other (verifies default_factory creates independent lists).
        Checks: List default behavior and independence across instances.
        """
        f1 = FunctionInfo(name="f1", lineno=1)
        f2 = FunctionInfo(name="f2", lineno=2)

        assert f1.decorators == []
        assert f2.decorators == []

        f1.decorators.append("cached")
        assert f1.decorators == ["cached"]
        assert f2.decorators == []  # independence

    def test_specified_decorators_including_multiple_values(self):
        """Inputs: Construct FunctionInfo with a provided `decorators` list (including multiple entries).
        Expected: The `decorators` attribute equals the provided list in the same order.
        Checks: Proper assignment and preservation of order for decorators.
        """
        f = FunctionInfo(name="multi", lineno=10, decorators=["deco1", "deco2"])
        assert f.decorators == ["deco1", "deco2"]


class TestClassInfoInit:
    def test_defaults_for_bases_and_methods_are_empty_and_independent(self):
        """Inputs: Construct two ClassInfo instances without passing bases/methods.
        Expected: Each instance has empty independent lists for `bases` and `methods`.
        Checks: List defaults via default_factory and independence across instances.
        """
        c1 = ClassInfo(name="A", lineno=1)
        c2 = ClassInfo(name="B", lineno=2)

        assert c1.bases == [] and c1.methods == []
        assert c2.bases == [] and c2.methods == []

        c1.bases.append("Base")
        c1.methods.append(FunctionInfo("m", 3))

        assert c1.bases == ["Base"]
        assert [m.name for m in c1.methods] == ["m"]
        # c2 remains unchanged
        assert c2.bases == [] and c2.methods == []

    def test_populated_with_multiple_methods_and_bases(self):
        """Inputs: Construct ClassInfo with multiple bases and methods.
        Expected: The object stores bases and methods as provided.
        Checks: Correct storage and retrieval of bases and nested FunctionInfo items.
        """
        methods = [FunctionInfo("area", 10), FunctionInfo("default", 11, decorators=["classmethod"]) ]
        cls = ClassInfo(name="Concrete", lineno=5, bases=["PrintableMixin", "Base"], methods=methods)

        assert cls.name == "Concrete"
        assert cls.bases == ["PrintableMixin", "Base"]
        assert [m.name for m in cls.methods] == ["area", "default"]
        assert cls.methods[1].decorators == ["classmethod"]



class TestModuleInfoInit:
    def test_defaults_for_collections_are_empty_and_independent(self, tmp_path: Path):
        """Inputs: Create two ModuleInfo objects with only name/path provided.
        Expected: classes/functions/imports default to empty lists, independent across instances.
        Checks: default_factory behavior for ModuleInfo lists.
        """
        path1 = str(tmp_path / "m1.py")
        path2 = str(tmp_path / "m2.py")
        m1 = ModuleInfo(name="pkg.m1", path=path1)
        m2 = ModuleInfo(name="pkg.m2", path=path2)

        assert m1.classes == [] and m1.functions == [] and m1.imports == []
        assert m2.classes == [] and m2.functions == [] and m2.imports == []

        m1.classes.append(ClassInfo("A", 1))
        m1.functions.append(FunctionInfo("f", 2))
        m1.imports.append("os")

        assert [c.name for c in m1.classes] == ["A"]
        assert [f.name for f in m1.functions] == ["f"]
        assert m1.imports == ["os"]
        # m2 unchanged
        assert m2.classes == [] and m2.functions == [] and m2.imports == []

    def test_populated_module_uses_realistic_paths(self):
        """Inputs: Construct a ModuleInfo referencing an actual file under tests/data/test-package-1.
        Expected: The provided absolute path is preserved in the dataclass `path` attribute.
        Checks: Path assignment correctness; not validating existence logic in data model, only storage.
        """
        file_path = Path(__file__).parent / "data" / "test-package-1" / "core.py"
        mod = ModuleInfo(name="pkg.core", path=str(file_path))
        assert mod.path.endswith(os.path.join("tests", "data", "test-package-1", "core.py"))


class TestPackageModel_to_dict:
    def test_empty_model_serialization(self):
        """Inputs: Create a PackageModel with no modules and empty roots list.
        Expected: to_dict returns a dict with keys root_path, roots, modules={}, edges=[].
        Checks: Structure of the serialized dict and the empty edges list from build_edges.
        """
        pm = PackageModel(root_path=str(Path.cwd()), roots=[], modules={})
        d = pm.to_dict()
        assert sorted(d.keys()) == ["edges", "modules", "root_path", "roots"]
        assert d["root_path"] == str(Path.cwd())
        assert d["roots"] == []
        assert d["modules"] == {}
        assert d["edges"] == []

    def test_populated_model_serialization_and_sorted_modules(self):
        """Inputs: Build a PackageModel with multiple modules containing classes, methods, functions, and imports.
        Expected: to_dict returns a dict with modules serialized under sorted keys; nested structures for classes,
        methods, and functions include name/lineno/decorators; imports are preserved; edges are included.
        Checks: Sorting of module keys, correctness of nested serialization, and presence of expected edge types.
        """
        # Build classes and functions
        concrete = ClassInfo(
            name="Concrete",
            lineno=60,
            bases=["PrintableMixin", "Base"],
            methods=[
                FunctionInfo("area", 66),
                FunctionInfo("default", 70, decorators=["classmethod"]),
                FunctionInfo("tau", 42, decorators=["staticmethod"]),
            ],
        )
        core_funcs = [
            FunctionInfo("greet", 44, decorators=["simple_deco"]),
            FunctionInfo("add", 48, decorators=["times"]),
        ]
        mod_core = ModuleInfo(
            name="pkg.core",
            path=str(Path(__file__).parent / "data" / "test-package-1" / "core.py"),
            classes=[concrete],
            functions=core_funcs,
            imports=["math", "typing"],
        )

        mod_utils = ModuleInfo(
            name="pkg.utils",
            path=str(Path(__file__).parent / "data" / "test-package-1" / "utils.py"),
            classes=[],
            functions=[FunctionInfo("parse", 97)],
            imports=[],
        )

        mod_only = ModuleInfo(
            name="pkg.only_imports",
            path=str(Path(__file__).parent / "data" / "test-package-1" / "only_imports.py"),
            classes=[],
            functions=[],
            imports=["os", "sys", "math"],
        )

        mod_multi = ModuleInfo(
            name="pkg.multi",
            path=str(Path(__file__).parent / "data" / "test-package-1" / "multi_decorators.py"),
            classes=[],
            functions=[FunctionInfo("multi", 15, decorators=["deco1", "deco2"])],
            imports=[],
        )

        modules = {
            mod_core.name: mod_core,
            mod_utils.name: mod_utils,
            mod_only.name: mod_only,
            mod_multi.name: mod_multi,
        }
        pm = PackageModel(root_path=str(Path.cwd()), roots=["pkg"], modules=modules)

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
        """Inputs: PackageModel with an empty modules mapping.
        Expected: build_edges returns an empty list.
        Checks: No edges created when there are no modules/classes/functions/imports.
        """
        pm = PackageModel(root_path="/", roots=[], modules={})
        assert pm.build_edges() == []

    def test_edges_for_comprehensive_model(self):
        """Inputs: Construct a PackageModel with modules containing classes (with methods and multiple bases),
        functions, and imports, including a module that only has imports.
        Expected: build_edges returns edges of types module_contains (for classes and functions),
        class_contains (for each method), inherits (for each base), and imports (for each import).
        Checks: Count of edges per category and presence of specific representative edges.
        """
        concrete = ClassInfo(
            name="Concrete",
            lineno=60,
            bases=["PrintableMixin", "Base"],
            methods=[FunctionInfo("area", 66), FunctionInfo("default", 70)],
        )
        mod_core = ModuleInfo(
            name="pkg.core",
            path="/abs/core.py",
            classes=[concrete],
            functions=[FunctionInfo("greet", 44), FunctionInfo("add", 48)],
            imports=["math", "typing"],
        )
        mod_utils = ModuleInfo(
            name="pkg.utils",
            path="/abs/utils.py",
            classes=[],
            functions=[FunctionInfo("parse", 97)],
            imports=[],
        )
        mod_only = ModuleInfo(
            name="pkg.only_imports",
            path="/abs/only_imports.py",
            classes=[],
            functions=[],
            imports=["os", "sys", "math"],
        )
        modules = {m.name: m for m in [mod_core, mod_utils, mod_only]}
        pm = PackageModel(root_path="/abs", roots=["pkg"], modules=modules)

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
        """Inputs: PackageModel with a single module that has only imports but no classes or functions.
        Expected: build_edges creates only 'imports' edges corresponding to each import.
        Checks: Edge list contains only 'imports' entries and in the expected count.
        """
        mod = ModuleInfo(name="pkg.only", path="/abs/only.py", imports=["os", "sys"])  # no classes/functions
        pm = PackageModel(root_path="/", roots=["pkg"], modules={"pkg.only": mod})
        edges = pm.build_edges()
        assert all(e["type"] == "imports" for e in edges)
        assert {e["to"] for e in edges} == {"os", "sys"}
