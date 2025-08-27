from __future__ import annotations

import os
from arch.crawler import crawl_package, render_tree, to_json

# Path to the target Python package/repository to crawl
path = r"C:\gdrive\algorithms\deltares\HYDROLIB-core\hydrolib\core\base"


model = crawl_package(path)
print(render_tree(model))

# Optionally save a JSON snapshot next to this script for further analysis
out_dir = os.path.dirname(os.path.abspath(__file__))
out_json = os.path.join(out_dir, "structure.json")
with open(out_json, "w", encoding="utf-8") as f:
    f.write(to_json(model, indent=2))
print(f"\nJSON structure written to: {out_json}")
