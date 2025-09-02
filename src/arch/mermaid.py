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
