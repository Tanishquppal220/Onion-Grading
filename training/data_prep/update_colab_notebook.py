"""Updates colab_training_and_transfer.ipynb with robust ONNX export and comprehensive run plots/graphs zipping.
"""

import json
from pathlib import Path

nb_path = Path(__file__).resolve().parents[1] / "notebooks" / "colab_training_and_transfer.ipynb"

with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Step 8: Safe ONNX export for both models
step_8_src = [
    "from ultralytics import YOLO\n",
    "import glob\n",
    "\n",
    "# Ensure model1 is loaded from best weights if not already in session\n",
    "if 'model1' not in locals() or model1 is None:\n",
    "    m1_pts = sorted(glob.glob('/content/runs/model1/**/weights/best.pt', recursive=True))\n",
    "    if m1_pts:\n",
    "        model1 = YOLO(m1_pts[-1])\n",
    "        print(f\"Loaded Model 1 from: {m1_pts[-1]}\")\n",
    "\n",
    "# Ensure model2 is loaded from best weights if not already in session\n",
    "if 'model2' not in locals() or model2 is None:\n",
    "    m2_pts = sorted(glob.glob('/content/runs/model2/**/weights/best.pt', recursive=True))\n",
    "    if m2_pts:\n",
    "        model2 = YOLO(m2_pts[-1])\n",
    "        print(f\"Loaded Model 2 from: {m2_pts[-1]}\")\n",
    "\n",
    "# Export Model 1 (detection + segmentation) with dynamic shape for mobile resolution flexibility\n",
    "onnx_m1 = model1.export(format=\"onnx\", dynamic=True)\n",
    "# Export Model 2 (defect classifier) at fixed 224x224\n",
    "onnx_m2 = model2.export(format=\"onnx\", imgsz=224)\n",
    "\n",
    "print(f\"\\n Exported Model 1 ONNX: {onnx_m1}\")\n",
    "print(f\" Exported Model 2 ONNX: {onnx_m2}\")\n"
]

# Step 9: Package weights + ONNX + all training curves, confusion matrices, CSVs, and entire runs directory
step_9_src = [
    "import os\n",
    "import glob\n",
    "import shutil\n",
    "import subprocess\n",
    "\n",
    "# 1. Organize exports directory\n",
    "os.makedirs(\"/content/exports/weights\", exist_ok=True)\n",
    "os.makedirs(\"/content/exports/onnx\", exist_ok=True)\n",
    "os.makedirs(\"/content/exports/eval_plots\", exist_ok=True)\n",
    "os.makedirs(\"/content/exports/training_runs\", exist_ok=True)\n",
    "\n",
    "# Copy latest best.pt for Model 1 and Model 2\n",
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
    "# Copy exported ONNX files\n",
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
    "# Copy all training evaluation plots, loss curves, confusion matrices, and metrics CSVs\n",
    "plots_copied = 0\n",
    "for ext in [\"*.png\", \"*.jpg\", \"*.csv\", \"*.yaml\"]:\n",
    "    for p in glob.glob(f\"/content/runs/**/{ext}\", recursive=True):\n",
    "        dest_name = os.path.basename(p)\n",
    "        parent_tag = os.path.basename(os.path.dirname(p))\n",
    "        shutil.copy(p, f\"/content/exports/eval_plots/{parent_tag}_{dest_name}\")\n",
    "        plots_copied += 1\n",
    "print(f\" Bundled {plots_copied} training plots, loss curves, confusion matrices, and metrics CSVs into eval_plots.\")\n",
    "\n",
    "# Copy the entire runs directory structure so all raw subfolders and logs are preserved\n",
    "!cp -r /content/runs /content/exports/training_runs/\n",
    "\n",
    "# 2. Zip archive containing /content/exports (weights, onnx, eval_plots, and training_runs)\n",
    "archive_path = \"/content/onion_model_artifacts.zip\"\n",
    "!zip -r {archive_path} /content/exports\n",
    "\n",
    "# 3. Programmatic CLI Download via transfer.sh\n",
    "print(\"\\nUploading complete package (weights + ONNX + all plots & graphs) to transfer.sh...\")\n",
    "res = subprocess.run(f\"curl --upload-file {archive_path} https://transfer.sh/onion_model_artifacts.zip\", shell=True, capture_output=True, text=True)\n",
    "url = res.stdout.strip()\n",
    "\n",
    "print(\"\\n\" + \"=\"*80)\n",
    "print(\" TRAINING COMPLETE! DOWNLOAD ALL ARTIFACTS TO YOUR PC WITH THIS COMMAND:\")\n",
    "print(\"=\"*80)\n",
    "print(f\"\\nmkdir -p ~/Projects/Onion_grading_new/runs && curl -o ~/Projects/Onion_grading_new/runs/onion_model_artifacts.zip {url} && unzip -o ~/Projects/Onion_grading_new/runs/onion_model_artifacts.zip -d ~/Projects/Onion_grading_new/runs/\\n\")\n",
    "print(\"=\"*80)\n"
]

for cell in nb["cells"]:
    if cell.get("cell_type") == "code":
        src = "".join(cell.get("source", []))
        if "onnx_m1 = model1.export" in src:
            cell["source"] = step_8_src
            cell["outputs"] = []
            cell["execution_count"] = None
            print("Step 8 updated with resilient ONNX export.")
        elif "transfer.sh" in src or "archive_path =" in src:
            cell["source"] = step_9_src
            cell["outputs"] = []
            cell["execution_count"] = None
            print("Step 9 updated with full runs and graphs archiving.")

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)

print("Notebook updated successfully!")
