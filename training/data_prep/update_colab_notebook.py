"""Updates colab_training_and_transfer.ipynb with dynamic class resolution, fast training parameters, and visual benchmark diagnostics.
"""

import json
from pathlib import Path

nb_path = Path(__file__).resolve().parents[1] / "notebooks" / "colab_training_and_transfer.ipynb"

with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Improved Step 3: Dynamic Class Name Mapping
new_step_3 = [
    "import shutil\n",
    "from pathlib import Path\n",
    "import yaml\n",
    "\n",
    "def get_onion_class_indices(raw_dir: str) -> list[int]:\n",
    "    yaml_path = Path(raw_dir) / \"data.yaml\"\n",
    "    if not yaml_path.exists():\n",
    "        return [0]\n",
    "    with open(yaml_path) as f:\n",
    "        cfg = yaml.safe_load(f)\n",
    "    names = cfg.get(\"names\", [])\n",
    "    print(f\"Classes found in {Path(raw_dir).name}: {names}\")\n",
    "    if isinstance(names, dict):\n",
    "        matches = [int(idx) for idx, name in names.items() if \"not\" not in str(name).lower() and \"onion\" in str(name).lower()]\n",
    "        return matches if matches else [0]\n",
    "    elif isinstance(names, list):\n",
    "        matches = [idx for idx, name in enumerate(names) if \"not\" not in str(name).lower() and \"onion\" in str(name).lower()]\n",
    "        return matches if matches else [0]\n",
    "    return [0]\n",
    "\n",
    "def prepare_model1_split(src_img_dir, src_lbl_dir, dst_img_dir, dst_lbl_dir, target_classes=[0]):\n",
    "    Path(dst_img_dir).mkdir(parents=True, exist_ok=True)\n",
    "    Path(dst_lbl_dir).mkdir(parents=True, exist_ok=True)\n",
    "    \n",
    "    count = 0\n",
    "    for img_p in Path(src_img_dir).glob(\"*.jpg\"):\n",
    "        lbl_p = Path(src_lbl_dir) / f\"{img_p.stem}.txt\"\n",
    "        dest_img = Path(dst_img_dir) / img_p.name\n",
    "        dest_lbl = Path(dst_lbl_dir) / f\"{img_p.stem}.txt\"\n",
    "        \n",
    "        shutil.copy2(img_p, dest_img)\n",
    "        if not lbl_p.exists():\n",
    "            dest_lbl.touch()\n",
    "            continue\n",
    "            \n",
    "        with open(lbl_p, \"r\") as f:\n",
    "            lines = f.readlines()\n",
    "        valid = []\n",
    "        for line in lines:\n",
    "            parts = line.strip().split()\n",
    "            if len(parts) >= 6 and int(parts[0]) in target_classes:\n",
    "                valid.append(\"0 \" + \" \".join(parts[1:]) + \"\\n\")\n",
    "        with open(dest_lbl, \"w\") as f:\n",
    "            f.writelines(valid)\n",
    "        count += 1\n",
    "    return count\n",
    "\n",
    "d1a_classes = get_onion_class_indices(\"/content/data/raw/D1A_instance_seg\")\n",
    "d1b_classes = get_onion_class_indices(\"/content/data/raw/D1B_onionthesis1\")\n",
    "print(f\"\\nTarget onion class IDs -> D1-A: {d1a_classes}, D1-B: {d1b_classes}\")\n",
    "\n",
    "# Check D1-B available split folders\n",
    "d1b_root = Path(\"/content/data/raw/D1B_onionthesis1\")\n",
    "d1b_test_img = d1b_root / \"test\" / \"images\"\n",
    "d1b_test_lbl = d1b_root / \"test\" / \"labels\"\n",
    "if not d1b_test_img.exists():\n",
    "    d1b_test_img = d1b_root / \"valid\" / \"images\"\n",
    "    d1b_test_lbl = d1b_root / \"valid\" / \"labels\"\n",
    "if not d1b_test_img.exists():\n",
    "    d1b_test_img = d1b_root / \"train\" / \"images\"\n",
    "    d1b_test_lbl = d1b_root / \"train\" / \"labels\"\n",
    "\n",
    "print(\"Formatting Model 1 dataset with dynamic class resolution...\")\n",
    "prepare_model1_split(\"/content/data/raw/D1A_instance_seg/train/images\", \"/content/data/raw/D1A_instance_seg/train/labels\", \"/content/data/model1/train/images\", \"/content/data/model1/train/labels\", target_classes=d1a_classes)\n",
    "prepare_model1_split(\"/content/data/raw/D1A_instance_seg/valid/images\", \"/content/data/raw/D1A_instance_seg/valid/labels\", \"/content/data/model1/val/images\", \"/content/data/model1/val/labels\", target_classes=d1a_classes)\n",
    "prepare_model1_split(d1b_test_img, d1b_test_lbl, \"/content/data/model1/test/images\", \"/content/data/model1/test/labels\", target_classes=d1b_classes)\n",
    "\n",
    "data_yaml = {\n",
    "    \"path\": \"/content/data/model1\",\n",
    "    \"train\": \"train/images\",\n",
    "    \"val\": \"val/images\",\n",
    "    \"test\": \"test/images\",\n",
    "    \"names\": {0: \"onion\"}\n",
    "}\n",
    "with open(\"/content/data/model1/data.yaml\", \"w\") as f:\n",
    "    yaml.dump(data_yaml, f)\n",
    "\n",
    "print(\"\\n Model 1 data.yaml ready at /content/data/model1/data.yaml\")"
]

# Improved Step 5: Dual Evaluation & Visual Prediction Overlays
new_step_5 = [
    "# 1. Benchmark on D1-B test split\n",
    "print(\"Evaluating on D1-B cross-source test set...\")\n",
    "metrics_m1 = model1.val(data=\"/content/data/model1/data.yaml\", split=\"test\")\n",
    "print(\"=\" * 60)\n",
    "print(f\"Model 1 D1-B Benchmark Box mAP@0.5:  {metrics_m1.box.map50:.4f}\")\n",
    "print(f\"Model 1 D1-B Benchmark Mask mAP@0.5: {metrics_m1.seg.map50:.4f}\")\n",
    "print(\"=\" * 60)\n",
    "\n",
    "# 2. Compare against D1-A held-out test split (if present)\n",
    "if Path(\"/content/data/raw/D1A_instance_seg/data.yaml\").exists():\n",
    "    try:\n",
    "        metrics_d1a = model1.val(data=\"/content/data/raw/D1A_instance_seg/data.yaml\", split=\"test\")\n",
    "        print(f\"Model 1 on D1-A Test Split Mask mAP@0.5: {metrics_d1a.seg.map50:.4f}\")\n",
    "        print(\"=\" * 60)\n",
    "    except Exception as e:\n",
    "        print(f\"D1-A test split check note: {e}\")\n",
    "\n",
    "# 3. Visual Inspection: Predict and overlay masks on 3 sample D1-B test images\n",
    "test_images = list(Path(\"/content/data/model1/test/images\").glob(\"*.jpg\"))[:3]\n",
    "if test_images:\n",
    "    preds = model1.predict(source=test_images, save=True, project=\"/content/runs/model1\", name=\"d1b_sample_preds\", conf=0.25)\n",
    "    print(f\"Visual sample overlays saved to: /content/runs/model1/d1b_sample_preds/\")"
]

for cell in nb["cells"]:
    if cell.get("cell_type") == "code":
        src = "".join(cell.get("source", []))
        if "def prepare_model1_split(" in src:
            cell["source"] = new_step_3
            cell["outputs"] = []
            cell["execution_count"] = None
            print("Step 3 updated.")
        elif "metrics_m1 = model1.val(" in src:
            cell["source"] = new_step_5
            cell["outputs"] = []
            cell["execution_count"] = None
            print("Step 5 updated.")

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)

print("Notebook successfully updated!")
