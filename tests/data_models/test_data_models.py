from pathlib import Path

from arch.data_models import Function, Class, Module


class TestFunctionInfoInit:
    def test_default_decorators_list_is_empty_and_independent(self):
        """Inputs: Construct two Function instances without passing decorators.
        Expected: Each instance has an empty list for `decorators`, and mutating one instance's list
        does not affect the other (verifies default_factory creates independent lists).
        Checks: List default behavior and independence across instances.
        """
        f1 = Function(name="f1", lineno=1)
        f2 = Function(name="f2", lineno=2)

        assert f1.decorators == []
        assert f2.decorators == []

        f1.decorators.append("cached")
        assert f1.decorators == ["cached"]
        assert f2.decorators == []  # independence

    def test_specified_decorators_including_multiple_values(self):
        """Inputs: Construct Function with a provided `decorators` list (including multiple entries).
        Expected: The `decorators` attribute equals the provided list in the same order.
        Checks: Proper assignment and preservation of order for decorators.
        """
        f = Function(name="multi", lineno=10, decorators=["deco1", "deco2"])
        assert f.decorators == ["deco1", "deco2"]


class TestClassInfoInit:
    def test_defaults_for_bases_and_methods_are_empty_and_independent(self):
        """Inputs: Construct two Class instances without passing bases/methods.
        Expected: Each instance has empty independent lists for `bases` and `methods`.
        Checks: List defaults via default_factory and independence across instances.
        """
        c1 = Class(name="A", lineno=1)
        c2 = Class(name="B", lineno=2)

        assert c1.bases == [] and c1.methods == []
        assert c2.bases == [] and c2.methods == []

        c1.bases.append("Base")
        c1.methods.append(Function("m", 3))

        assert c1.bases == ["Base"]
        assert [m.name for m in c1.methods] == ["m"]
        # c2 remains unchanged
        assert c2.bases == [] and c2.methods == []

    def test_populated_with_multiple_methods_and_bases(self):
        """Inputs: Construct Class with multiple bases and methods.
        Expected: The object stores bases and methods as provided.
        Checks: Correct storage and retrieval of bases and nested Function items.
        """
        methods = [Function("area", 10), Function("default", 11, decorators=["classmethod"])]
        cls = Class(name="Concrete", lineno=5, bases=["PrintableMixin", "Base"], methods=methods)

        assert cls.name == "Concrete"
        assert cls.bases == ["PrintableMixin", "Base"]
        assert [m.name for m in cls.methods] == ["area", "default"]
        assert cls.methods[1].decorators == ["classmethod"]



class TestModuleInfoInit:
    def test_defaults_for_collections_are_empty_and_independent(self, tmp_path: Path):
        """Inputs: Create two Module objects with only name/path provided.
        Expected: classes/functions/imports default to empty lists, independent across instances.
        Checks: default_factory behavior for Module lists.
        """
        path1 = str(tmp_path / "m1.py")
        path2 = str(tmp_path / "m2.py")
        m1 = Module(name="pkg.m1", path=path1)
        m2 = Module(name="pkg.m2", path=path2)

        assert m1.classes == [] and m1.functions == [] and m1.imports == []
        assert m2.classes == [] and m2.functions == [] and m2.imports == []

        m1.classes.append(Class("A", 1))
        m1.functions.append(Function("f", 2))
        m1.imports.append("os")

        assert [c.name for c in m1.classes] == ["A"]
        assert [f.name for f in m1.functions] == ["f"]
        assert m1.imports == ["os"]
        # m2 unchanged
        assert m2.classes == [] and m2.functions == [] and m2.imports == []

    def test_populated_module_uses_realistic_paths(self):
        """Inputs: Construct a Module referencing an actual file under tests/data/test-package-1.
        Expected: The provided absolute path is preserved in the dataclass `path` attribute.
        Checks: Path assignment correctness; not validating existence logic in data model, only storage.
        """
        file_path = "tests/data/test-package-1/core.py"
        mod = Module(name="pkg.core", path=str(file_path))
        assert mod.path == "tests/data/test-package-1/core.py"
