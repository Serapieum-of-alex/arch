import re
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class Style:
    name: Optional[str] = None
    fill_color: str = "#eef6ff"
    stroke_color: str = "#2b6cb0"
    stroke_width: str = "1px"
    color: str = "#1a365d"

    @property
    def class_def(self):
        return f"classDef {self.name} fill:{self.fill_color},stroke:{self.stroke_color},stroke-width:1px,color:{self.color};"

    def apply_style(self, class_names: List[str]) -> List[str]:
        lines = []
        style_name = re.sub(r"[^A-Za-z0-9_]", "_", f"{self.name}_style")
        # Define a pleasant, distinct style for module classes
        # Apply style per-class using official classDiagram 'class' directive
        for cname in class_names:
            lines.append(f"class {cname}:::{style_name}")

        lines.append(self.class_def)
        # Attach a label to the first class to indicate module ownership
        first_cls = class_names[0]
        lines.append(f"note for {first_cls} \"module: {self.name}\"")

        return lines


# Mermaid rendering helpers extracted from data models to improve separation of concerns
# We keep functions simple and side-effect free; they accept plain data model instances.

def render_function_diagram(func, detail_level: str = "all", include_decorators: bool = False) -> str:
    allowed_levels = {"all", "public", "none"}
    if detail_level not in allowed_levels:
        raise ValueError(
            f"Unsupported detail_level '{detail_level}'. Expected one of {sorted(allowed_levels)}"
        )

    lines: List[str] = ["classDiagram"]

    if detail_level == "none":
        return "\n".join(lines)
    if detail_level == "public" and getattr(func, "name", "").startswith("_"):
        return "\n".join(lines)

    s = "{\n    }"
    lines.append(f"    class {func.name} {s}")

    if include_decorators and getattr(func, "decorators", None):
        decos = ", ".join(
            f"@{d}" if not str(d).startswith("@") else str(d) for d in func.decorators
        )
        lines.append(f"note for {func.name} \"decorators: {decos}\"")

    return "\n".join(lines)


def render_class_diagram(cls, include_relations: bool = True, detail_level: str = "all") -> str:
    allowed_levels = {"all", "public", "none"}
    if detail_level not in allowed_levels:
        raise ValueError(
            f"Unsupported detail_level '{detail_level}'. Expected one of {sorted(allowed_levels)}"
        )

    lines: List[str] = ["classDiagram"]

    lines.append(f"class {cls.name} {{")

    if detail_level == "all":
        selected_methods = getattr(cls, "methods", [])
    elif detail_level == "public":
        selected_methods = [m for m in getattr(cls, "methods", []) if not m.name.startswith("_")]
    else:
        selected_methods = []

    for m in sorted(selected_methods, key=lambda mm: mm.name):
        lines.append(f"  +{m.name}()")
    lines.append("}")

    if include_relations:
        for base in sorted(getattr(cls, "bases", [])):
            lines.append(f"{base} <|-- {cls.name}")

    return "\n".join(lines)


def render_module_diagram(module, include_relations: bool = True, class_detail_level: str = "all", function_detail_level: str = "all", include_decorators: bool = True, style: Optional[Style] = None) -> str:
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
    for cls in sorted(getattr(module, "classes", []), key=lambda c: c.name):
        parts = render_class_diagram(cls, include_relations=False, detail_level=class_detail_level).splitlines()
        if parts and parts[0].strip().lower() == "classdiagram":
            parts = parts[1:]
        lines.extend(parts)

    # Render inheritance relations
    if include_relations:
        for cls in sorted(getattr(module, "classes", []), key=lambda c: c.name):
            for base in sorted(getattr(cls, "bases", [])):
                lines.append(f"{base} <|-- {cls.name}")

    # Render top-level functions
    if function_detail_level != "none":
        if function_detail_level == "all":
            funcs = getattr(module, "functions", [])
        else:
            funcs = [f for f in getattr(module, "functions", []) if not f.name.startswith("_")]
        for f in sorted(funcs, key=lambda ff: ff.name):
            parts = render_function_diagram(f, detail_level=function_detail_level, include_decorators=include_decorators).splitlines()
            if parts and parts[0].strip().lower() == "classdiagram":
                parts = parts[1:]
            lines.extend(parts)

    # Apply style if requested
    if style and getattr(module, "classes", None):
        class_names = sorted([c.name for c in module.classes])
        style.name = getattr(module, "name", style.name)
        lines.extend(style.apply_style(class_names))

    return "\n".join(lines)


def render_module_dependency(module) -> str:
    lines: List[str] = ["classDiagram"]
    added_imports = set()
    for imp in getattr(module, "imports", []):
        edge = (getattr(module, "name", ""), imp)
        if edge not in added_imports:
            lines.append(f"{module.name} ..> {imp} : imports")
            added_imports.add(edge)
    return "\n".join(lines)


def render_package_diagram(package, include_class_relations: bool = True, class_detail_level: str = "all", function_detail_level: str = "all", include_decorators: bool = True, include_module_styling: bool = True) -> str:
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

    # Render each module
    for _, module in sorted(getattr(package, "modules", {}).items(), key=lambda kv: kv[0]):
        style = Style(name=module.name) if include_module_styling else None
        parts = render_module_diagram(
            module,
            include_relations=False,
            class_detail_level=class_detail_level,
            function_detail_level=function_detail_level,
            include_decorators=include_decorators,
            style=style,
        ).splitlines()
        if parts and parts[0].strip().lower() == "classdiagram":
            parts = parts[1:]
        lines.extend(parts)

    # Aggregate inheritance relations across all classes
    if include_class_relations:
        added_rel = set()
        for _, module in sorted(getattr(package, "modules", {}).items(), key=lambda kv: kv[0]):
            for cls in getattr(module, "classes", []):
                for base in getattr(cls, "bases", []):
                    rel = (base, cls.name)
                    if rel not in added_rel:
                        lines.append(f"{base} <|-- {cls.name}")
                        added_rel.add(rel)

    return "\n".join(lines)
