import tempfile
from pathlib import Path


from arch.data_models import ModuleInfo  # noqa: E402


class TestModuleNameFromPath:
    def test_regular_module_from_parent_root(self):
        """
        parent root -> pkg/mod.py -> "pkg.mod
        """
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            pkg = parent / "pkg"
            pkg.mkdir()
            (pkg / "__init__.py").write_text("", encoding="utf-8")
            mod = pkg / "mod.py"
            mod.write_text("", encoding="utf-8")

            dotted = ModuleInfo._module_name_from_path(str(parent), str(mod))
            assert dotted == "pkg.mod"

    def test_package_init_from_parent_root(self):
        """
        parent root -> pkg/__init__.py -> "pkg"
        """
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            pkg = parent / "pkg"
            pkg.mkdir()
            init = pkg / "__init__.py"
            init.write_text("", encoding="utf-8")

            dotted = ModuleInfo._module_name_from_path(str(parent), str(init))
            assert dotted == "pkg"

    def test_nested_module_from_parent_root(self):
        """
        parent root -> pkg/sub/mod2.py -> "pkg.sub.mod2"
        """
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            pkg = parent / "pkg"
            sub = pkg / "sub"
            sub.mkdir(parents=True)
            (pkg / "__init__.py").write_text("", encoding="utf-8")
            (sub / "__init__.py").write_text("", encoding="utf-8")
            mod2 = sub / "mod2.py"
            mod2.write_text("", encoding="utf-8")

            dotted = ModuleInfo._module_name_from_path(str(parent), str(mod2))
            assert dotted == "pkg.sub.mod2"

    def test_root_init_when_root_is_package_dir_returns_empty(self):
        """
        root is the package directory itself -> __init__.py -> ""
        """
        with tempfile.TemporaryDirectory() as d:
            pkg = Path(d) / "pkg"
            pkg.mkdir()
            init = pkg / "__init__.py"
            init.write_text("", encoding="utf-8")

            dotted = ModuleInfo._module_name_from_path(str(pkg), str(init))
            assert dotted == ""

    def test_module_when_root_is_package_dir_is_bare_name(self):
        """
        root is the package directory itself -> mod.py -> "mod"
        """
        with tempfile.TemporaryDirectory() as d:
            pkg = Path(d) / "pkg"
            pkg.mkdir()
            (pkg / "__init__.py").write_text("", encoding="utf-8")
            mod = pkg / "mod.py"
            mod.write_text("", encoding="utf-8")

            dotted = ModuleInfo._module_name_from_path(str(pkg), str(mod))
            assert dotted == "mod"

    def test_file_not_under_root_fallback_endswith_pkg_mod(self):
        """
        When file is outside the root, function uses a fallback; ensure it still ends with "pkg.mod"
        """
        with tempfile.TemporaryDirectory() as d_root, tempfile.TemporaryDirectory() as d_other:
            root = Path(d_root)
            other = Path(d_other)

            pkg = other / "pkg"
            pkg.mkdir()
            (pkg / "__init__.py").write_text("", encoding="utf-8")
            mod = pkg / "mod.py"
            mod.write_text("", encoding="utf-8")

            dotted = ModuleInfo._module_name_from_path(str(root), str(mod))
            assert dotted.endswith("pkg.mod"), f"unexpected dotted name: {dotted}"
