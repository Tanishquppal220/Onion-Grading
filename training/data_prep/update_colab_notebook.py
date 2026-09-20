"""Updates colab_training_and_transfer.ipynb with robust label finding for Step 6.
"""

import json
from pathlib import Path

nb_path = Path(__file__).resolve().parents[1] / "notebooks" / "colab_training_and_transfer.ipynb"

with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

new_step_6 = [
    "import cv2\n",
    "from pathlib import Path\n",
    "import random\n",
    "import yaml\n",
    "\n",
    "def find_label_file(img_path: Path) -> Path | None:\n",
    "    # 1. Same directory\n",
    "    lbl = img_path.with_suffix(\".txt\")\n",
    "    if lbl.exists(): return lbl\n",
    "    # 2. Path replacing /images/ with /labels/\n",
    "    parts = list(img_path.parts)\n",
    "    if \"images\" in parts:\n",
    "        idx = len(parts) - 1 - parts[::-1].index(\"images\")\n",
    "        parts[idx] = \"labels\"\n",
    "        lbl = Path(*parts).with_suffix(\".txt\")\n",
    "        if lbl.exists(): return lbl\n",
    "    # 3. Sibling labels folder\n",
    "    lbl = img_path.parent.parent / \"labels\" / f\"{img_path.stem}.txt\"\n",
    "    if lbl.exists(): return lbl\n",
    "    return None\n",
    "\n",
    "def map_defect_class(raw_name: str) -> str | None:\n",
    "    name = str(raw_name).strip().lower()\n",
    "    if \"rot\" in name: return \"rotten\"\n",
    "    if \"sprout\" in name or \"root\" in name: return \"sprouted\"\n",
    "    if \"cut\" in name or \"damage\" in name: return \"mechanical_damage\"\n",
    "    if \"healthy\" in name or name == \"onion\": return \"healthy\"\n",
    "    return None\n",
    "\n",
    "classes = [\"healthy\", \"sprouted\", \"rotten\", \"mechanical_damage\"]\n",
    "for s in [\"train\", \"val\", \"test\"]:\n",
    "    for c in classes:\n",
    "        Path(f\"/content/data/model2/{s}/{c}\").mkdir(parents=True, exist_ok=True)\n",
    "\n",
    "# Read data.yaml from D2A\n",
    "yaml_p = Path(\"/content/data/raw/D2A_onion_disease/data.yaml\")\n",
    "raw_names = []\n",
    "if yaml_p.exists():\n",
    "    with open(yaml_p) as f:\n",
    "        d2a_cfg = yaml.safe_load(f)\n",
    "    raw_names = d2a_cfg.get(\"names\", [])\n",
    "    if isinstance(raw_names, dict):\n",
    "        raw_names = [raw_names[k] for k in sorted(raw_names.keys())]\n",
    "\n",
    "print(f\"D2-A Class Names from data.yaml: {raw_names}\")\n",
    "\n",
    "crops_by_class = {c: [] for c in classes}\n",
    "img_extensions = {\".jpg\", \".jpeg\", \".png\"}\n",
    "images = [p for p in Path(\"/content/data/raw/D2A_onion_disease\").rglob(\"*\") if p.suffix.lower() in img_extensions]\n",
    "print(f\"Found {len(images)} images in D2-A. Extracting crops...\")\n",
    "\n",
    "for img_p in images:\n",
    "    lbl_p = find_label_file(img_p)\n",
    "    if not lbl_p or not lbl_p.exists(): continue\n",
    "    img = cv2.imread(str(img_p))\n",
    "    if img is None: continue\n",
    "    h, w = img.shape[:2]\n",
    "    \n",
    "    with open(lbl_p) as f: lines = f.readlines()\n",
    "    for idx, l in enumerate(lines):\n",
    "        p = l.strip().split()\n",
    "        if len(p) < 5: continue\n",
    "        cid = int(p[0])\n",
    "        cname = raw_names[cid] if raw_names and cid < len(raw_names) else str(cid)\n",
    "        target_cls = map_defect_class(cname)\n",
    "        if not target_cls: continue\n",
    "        \n",
    "        cx, cy, bw, bh = float(p[1]), float(p[2]), float(p[3]), float(p[4])\n",
    "        x1, y1 = max(0, int((cx - bw*0.54)*w)), max(0, int((cy - bh*0.54)*h))\n",
    "        x2, y2 = min(w, int((cx + bw*0.54)*w)), min(h, int((cy + bh*0.54)*h))\n",
    "        if x2 > x1 and y2 > y1:\n",
    "            crop = cv2.resize(img[y1:y2, x1:x2], (224, 224))\n",
    "            crops_by_class[target_cls].append((crop, f\"{img_p.stem}_c{idx}.jpg\"))\n",
    "\n",
    "# Save train (70%), val (15%), test (15%)\n",
    "for c, items in crops_by_class.items():\n",
    "    random.shuffle(items)\n",
    "    n1 = int(len(items)*0.70)\n",
    "    n2 = int(len(items)*0.85)\n",
    "    for crop, name in items[:n1]: cv2.imwrite(f\"/content/data/model2/train/{c}/{name}\", crop)\n",
    "    for crop, name in items[n1:n2]: cv2.imwrite(f\"/content/data/model2/val/{c}/{name}\", crop)\n",
    "    for crop, name in items[n2:]: cv2.imwrite(f\"/content/data/model2/test/{c}/{name}\", crop)\n",
    "    print(f\"  - {c}: {len(items)} crops\")\n",
    "\n",
    "print(\"\\n Model 2 ImageFolder dataset ready at /content/data/model2\")"
]

for cell in nb["cells"]:
    if cell.get("cell_type") == "code":
        src = "".join(cell.get("source", []))
        if "CLASS_MAP = {" in src or "crops_by_class = {" in src:
            cell["source"] = new_step_6
            cell["outputs"] = []
            cell["execution_count"] = None
            print("Step 6 updated with robust label resolution and keyword class mapping.")

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)

print("Notebook updated successfully!")
