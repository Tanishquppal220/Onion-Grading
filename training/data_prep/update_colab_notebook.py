"""Updates colab_training_and_transfer.ipynb with multi-source defect datasets and robust transfer.
"""

import json
from pathlib import Path

nb_path = Path(__file__).resolve().parents[1] / "notebooks" / "colab_training_and_transfer.ipynb"

with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# 1. Update Step 2: Download D1-A, D1-B (skip if existing), and D2 defect sources (veg1-hcqsf-2 + project_onion)
step_2_src = [
    "import os\n",
    "from roboflow import Roboflow\n",
    "\n",
    "# Enter your Roboflow Private API Key here:\n",
    "ROBOFLOW_API_KEY = os.getenv(\"ROBOFLOW_API_KEY\", \"Iro3JVh4TIt3iqgCNxpl\")\n",
    "\n",
    "os.makedirs(\"/content/data/raw\", exist_ok=True)\n",
    "os.makedirs(\"/content/runs\", exist_ok=True)\n",
    "os.makedirs(\"/content/exports\", exist_ok=True)\n",
    "\n",
    "rf = Roboflow(api_key=ROBOFLOW_API_KEY)\n",
    "\n",
    "# Check D1-A and D1-B (already downloaded in earlier steps)\n",
    "if not os.path.exists(\"/content/data/raw/D1A_instance_seg\"):\n",
    "    print(\"1. Downloading D1-A (YOLOv8 instance segmentation)... \")\n",
    "    d1a_project = rf.workspace(\"yolo-custom-object-detection\").project(\"instance-segmentation-wagk9\")\n",
    "    d1a_data = d1a_project.version(12).download(\"yolov8\", location=\"/content/data/raw/D1A_instance_seg\")\n",
    "else:\n",
    "    print(\"1. D1-A already present, skipping re-download.\")\n",
    "\n",
    "if not os.path.exists(\"/content/data/raw/D1B_onionthesis1\"):\n",
    "    print(\"\\n2. Downloading D1-B (onionthesis1 - cross-source test set)... \")\n",
    "    d1b_project = rf.workspace(\"paul-angelo-lavarias-ii\").project(\"onionthesis1\")\n",
    "    d1b_data = d1b_project.version(1).download(\"yolov8\", location=\"/content/data/raw/D1B_onionthesis1\")\n",
    "else:\n",
    "    print(\"2. D1-B already present, skipping re-download.\")\n",
    "\n",
    "print(\"\\n3. Downloading D2 Defect Datasets for Model 2...\")\n",
    "print(\" - Downloading veg1-hcqsf-2 (rotten, sprout, healthy)... \")\n",
    "d2_veg_project = rf.workspace(\"onion-grading-nx\").project(\"veg1-hcqsf-2\")\n",
    "d2_veg_data = d2_veg_project.version(1).download(\"yolov8\", location=\"/content/data/raw/D2_veg1\")\n",
    "\n",
    "print(\" - Downloading project_onion (damaged, rotten, healthy)... \")\n",
    "d2_dmg_project = rf.workspace(\"rishabh-raj-2k8ng\").project(\"project_onion\")\n",
    "d2_dmg_data = d2_dmg_project.version(1).download(\"yolov8\", location=\"/content/data/raw/D2_project_onion\")\n",
    "\n",
    "print(\"\\n All datasets downloaded successfully into /content/data/raw/\")\n"
]

# 2. Update Step 6: Multi-source crop extraction for all 4 defect classes
step_6_src = [
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
    "    if \"damag\" in name or \"cut\" in name: return \"mechanical_damage\"\n",
    "    if \"health\" in name or name == \"onion\": return \"healthy\"\n",
    "    return None\n",
    "\n",
    "classes = [\"healthy\", \"sprouted\", \"rotten\", \"mechanical_damage\"]\n",
    "for s in [\"train\", \"val\", \"test\"]:\n",
    "    for c in classes:\n",
    "        Path(f\"/content/data/model2/{s}/{c}\").mkdir(parents=True, exist_ok=True)\n",
    "\n",
    "d2_source_dirs = [\n",
    "    Path(\"/content/data/raw/D2_veg1\"),\n",
    "    Path(\"/content/data/raw/D2_project_onion\"),\n",
    "]\n",
    "\n",
    "crops_by_class = {c: [] for c in classes}\n",
    "img_extensions = {\".jpg\", \".jpeg\", \".png\"}\n",
    "\n",
    "for src_dir in d2_source_dirs:\n",
    "    if not src_dir.exists(): continue\n",
    "    \n",
    "    # Read data.yaml for this dataset\n",
    "    yaml_p = src_dir / \"data.yaml\"\n",
    "    raw_names = []\n",
    "    if yaml_p.exists():\n",
    "        with open(yaml_p) as f:\n",
    "            d_cfg = yaml.safe_load(f)\n",
    "        raw_names = d_cfg.get(\"names\", [])\n",
    "        if isinstance(raw_names, dict):\n",
    "            raw_names = [raw_names[k] for k in sorted(raw_names.keys())]\n",
    "    \n",
    "    print(f\"\\nProcessing {src_dir.name} with classes: {raw_names}\")\n",
    "    images = [p for p in src_dir.rglob(\"*\") if p.suffix.lower() in img_extensions]\n",
    "    print(f\"Found {len(images)} images in {src_dir.name}. Extracting crops...\")\n",
    "    \n",
    "    for img_p in images:\n",
    "        lbl_p = find_label_file(img_p)\n",
    "        if not lbl_p or not lbl_p.exists(): continue\n",
    "        img = cv2.imread(str(img_p))\n",
    "        if img is None: continue\n",
    "        h, w = img.shape[:2]\n",
    "        \n",
    "        with open(lbl_p) as f: lines = f.readlines()\n",
    "        for idx, l in enumerate(lines):\n",
    "            p = l.strip().split()\n",
    "            if len(p) < 5: continue\n",
    "            cid = int(p[0])\n",
    "            cname = raw_names[cid] if raw_names and cid < len(raw_names) else str(cid)\n",
    "            target_cls = map_defect_class(cname)\n",
    "            if not target_cls: continue\n",
    "            \n",
    "            cx, cy, bw, bh = float(p[1]), float(p[2]), float(p[3]), float(p[4])\n",
    "            # 8% margin padding\n",
    "            x1, y1 = max(0, int((cx - bw*0.54)*w)), max(0, int((cy - bh*0.54)*h))\n",
    "            x2, y2 = min(w, int((cx + bw*0.54)*w)), min(h, int((cy + bh*0.54)*h))\n",
    "            if x2 > x1 and y2 > y1:\n",
    "                crop = cv2.resize(img[y1:y2, x1:x2], (224, 224), interpolation=cv2.INTER_AREA)\n",
    "                crops_by_class[target_cls].append((crop, f\"{src_dir.name}_{img_p.stem}_c{idx}.jpg\"))\n",
    "\n",
    "# Balance and save train (70%), val (15%), test (15%)\n",
    "print(\"\\nBalancing and saving crops across splits:\")\n",
    "for c, items in crops_by_class.items():\n",
    "    random.shuffle(items)\n",
    "    # Cap healthy crops to at most 500 for balance\n",
    "    if c == \"healthy\" and len(items) > 500:\n",
    "        items = items[:500]\n",
    "    n1 = int(len(items)*0.70)\n",
    "    n2 = int(len(items)*0.85)\n",
    "    for crop, name in items[:n1]: cv2.imwrite(f\"/content/data/model2/train/{c}/{name}\", crop)\n",
    "    for crop, name in items[n1:n2]: cv2.imwrite(f\"/content/data/model2/val/{c}/{name}\", crop)\n",
    "    for crop, name in items[n2:]: cv2.imwrite(f\"/content/data/model2/test/{c}/{name}\", crop)\n",
    "    print(f\"  - {c}: {len(items)} crops (train: {n1}, val: {n2-n1}, test: {len(items)-n2})\")\n",
    "\n",
    "print(\"\\n Model 2 ImageFolder dataset ready at /content/data/model2\")\n"
]

# 3. Update Step 9: Robust file paths for export and packaging
step_9_src = [
    "import os\n",
    "import glob\n",
    "import shutil\n",
    "import subprocess\n",
    "\n",
    "# 1. Organize exports\n",
    "os.makedirs(\"/content/exports/weights\", exist_ok=True)\n",
    "os.makedirs(\"/content/exports/onnx\", exist_ok=True)\n",
    "os.makedirs(\"/content/exports/eval_plots\", exist_ok=True)\n",
    "\n",
    "# Find latest best.pt for Model 1 and Model 2\n",
    "m1_pts = sorted(glob.glob(\"/content/runs/model1/**/weights/best.pt\", recursive=True), key=os.path.getmtime)\n",
    "m2_pts = sorted(glob.glob(\"/content/runs/model2/**/weights/best.pt\", recursive=True), key=os.path.getmtime)\n",
    "\n",
    "if m1_pts:\n",
    "    shutil.copy(m1_pts[-1], \"/content/exports/weights/model1_yolov8_seg.pt\")\n",
    "    print(f\" Copied Model 1 weights from: {m1_pts[-1]}\")\n",
    "if m2_pts:\n",
    "    shutil.copy(m2_pts[-1], \"/content/exports/weights/model2_defect_cls.pt\")\n",
    "    print(f\" Copied Model 2 weights from: {m2_pts[-1]}\")\n",
    "\n",
    "# Find exported ONNX files\n",
    "m1_onnx = sorted(glob.glob(\"/content/runs/model1/**/weights/*.onnx\", recursive=True) + glob.glob(\"/content/*.onnx\"), key=os.path.getmtime)\n",
    "m2_onnx = sorted(glob.glob(\"/content/runs/model2/**/weights/*.onnx\", recursive=True), key=os.path.getmtime)\n",
    "\n",
    "for f in m1_onnx:\n",
    "    if \"seg\" in f.lower() or \"best\" in f.lower():\n",
    "        shutil.copy(f, \"/content/exports/onnx/model1_yolov8_seg.onnx\")\n",
    "        print(f\" Copied Model 1 ONNX: {f}\")\n",
    "        break\n",
    "for f in m2_onnx:\n",
    "    shutil.copy(f, \"/content/exports/onnx/model2_defect_cls.onnx\")\n",
    "    print(f\" Copied Model 2 ONNX: {f}\")\n",
    "    break\n",
    "\n",
    "# Copy evaluation plots\n",
    "for p in glob.glob(\"/content/runs/model1/**/*.png\", recursive=True):\n",
    "    shutil.copy(p, \"/content/exports/eval_plots/\")\n",
    "for p in glob.glob(\"/content/runs/model2/**/*.png\", recursive=True):\n",
    "    shutil.copy(p, \"/content/exports/eval_plots/\")\n",
    "\n",
    "# 2. Zip archive\n",
    "archive_path = \"/content/onion_model_artifacts.zip\"\n",
    "!zip -r {archive_path} /content/exports\n",
    "\n",
    "# 3. Programmatic CLI Download via transfer.sh\n",
    "print(\"\\nUploading package to transfer.sh for direct terminal download...\")\n",
    "res = subprocess.run(f\"curl --upload-file {archive_path} https://transfer.sh/onion_model_artifacts.zip\", shell=True, capture_output=True, text=True)\n",
    "url = res.stdout.strip()\n",
    "\n",
    "print(\"\\n\" + \"=\"*80)\n",
    "print(\" TRAINING COMPLETE! DOWNLOAD ARTIFACTS TO YOUR PC WITH THIS COMMAND:\")\n",
    "print(\"=\"*80)\n",
    "print(f\"\\nmkdir -p ~/Projects/Onion_grading_new/runs && curl -o ~/Projects/Onion_grading_new/runs/onion_model_artifacts.zip {url} && unzip -o ~/Projects/Onion_grading_new/runs/onion_model_artifacts.zip -d ~/Projects/Onion_grading_new/runs/\\n\")\n",
    "print(\"=\"*80)\n"
]

for cell in nb["cells"]:
    if cell.get("cell_type") == "code":
        src = "".join(cell.get("source", []))
        if "Downloading D1-A" in src or "anas-kadiri-ffnxr" in src:
            cell["source"] = step_2_src
            cell["outputs"] = []
            cell["execution_count"] = None
            print("Step 2 updated with multi-source defect datasets.")
        elif "find_label_file" in src or "crops_by_class = {" in src:
            cell["source"] = step_6_src
            cell["outputs"] = []
            cell["execution_count"] = None
            print("Step 6 updated with multi-source crop extraction.")
        elif "transfer.sh" in src or "archive_path =" in src:
            cell["source"] = step_9_src
            cell["outputs"] = []
            cell["execution_count"] = None
            print("Step 9 updated with robust paths.")

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)

print("Notebook updated successfully!")
