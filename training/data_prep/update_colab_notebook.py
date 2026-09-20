"""Updates colab_training_and_transfer.ipynb with robust Drive transfer and Cloudflare tunnel options.
"""

import json
from pathlib import Path

nb_path = Path(__file__).resolve().parents[1] / "notebooks" / "colab_training_and_transfer.ipynb"

with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Update Cell 19 Markdown
cell_19_src = [
    "### Step 10: Copy Artifacts to Google Drive (Or Download Directly)\n",
    "If Drive is mounted, this saves the zip to `MyDrive/onion_grading_runs/onion_model_artifacts.zip`.\n"
]

# Update Cell 20 Code: Resilient Drive copy
cell_20_src = [
    "import os\n",
    "import shutil\n",
    "\n",
    "drive_dest = \"/content/drive/MyDrive/onion_grading_runs\"\n",
    "zip_src = \"/content/onion_model_artifacts.zip\"\n",
    "\n",
    "if os.path.exists(\"/content/drive/MyDrive\"):\n",
    "    os.makedirs(drive_dest, exist_ok=True)\n",
    "    shutil.copy(zip_src, f\"{drive_dest}/onion_model_artifacts.zip\")\n",
    "    print(\"=\"*80)\n",
    "    print(f\" SUCCESS! Artifacts copied to Google Drive at:\")\n",
    "    print(f\" {drive_dest}/onion_model_artifacts.zip\")\n",
    "    print(\"=\"*80)\n",
    "else:\n",
    "    print(\"=\"*80)\n",
    "    print(\" Google Drive is not mounted yet.\")\n",
    "    print(\" To mount Drive in 5 seconds:\")\n",
    "    print(\" 1. Open your browser tab where Colab is running.\")\n",
    "    print(\" 2. In the left panel, click the Folder icon -> click the 'Mount Drive' button (folder with Drive logo).\")\n",
    "    print(\" 3. Click 'Connect to Google Drive' on the popup.\")\n",
    "    print(\" 4. Re-run this cell to immediately copy the file into your Drive!\")\n",
    "    print(\"=\"*80)\n"
]

# Optional Cell 21 & 22: Cloudflare tunnel for direct terminal download
cell_21_md = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "### (Alternative) Direct Download via Cloudflare Tunnel (No Browser / No Drive needed)\n",
        "Generates a direct, secure HTTPS link to download `onion_model_artifacts.zip` straight from Colab into your PC terminal.\n"
    ]
}

cell_22_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "import os\n",
        "import subprocess\n",
        "import threading\n",
        "import http.server\n",
        "import socketserver\n",
        "\n",
        "# 1. Install static cloudflared binary\n",
        "!curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared\n",
        "\n",
        "# 2. Start quiet local HTTP server on port 8080\n",
        "!fuser -k 8080/tcp 2>/dev/null || true\n",
        "os.chdir(\"/content\")\n",
        "class QuietHandler(http.server.SimpleHTTPRequestHandler):\n",
        "    def log_message(self, format, *args): pass\n",
        "\n",
        "server = socketserver.TCPServer((\"\", 8080), QuietHandler)\n",
        "threading.Thread(target=server.serve_forever, daemon=True).start()\n",
        "\n",
        "# 3. Start Cloudflare tunnel\n",
        "p = subprocess.Popen([\"cloudflared\", \"tunnel\", \"--url\", \"http://localhost:8080\"], stderr=subprocess.PIPE, text=True)\n",
        "tunnel_url = None\n",
        "for line in p.stderr:\n",
        "    if \"trycloudflare.com\" in line:\n",
        "        for part in line.split():\n",
        "            if \"trycloudflare.com\" in part and part.startswith(\"http\"):\n",
        "                tunnel_url = part.strip()\n",
        "                break\n",
        "        if tunnel_url: break\n",
        "\n",
        "print(\"\\n\" + \"=\"*80)\n",
        "print(\" DIRECT DOWNLOAD LINK ACTIVE:\")\n",
        "print(f\" {tunnel_url}/onion_model_artifacts.zip\")\n",
        "print(\"=\"*80)\n",
        "print(f\"\\nRun this command in your PC terminal to download:\\n\")\n",
        "print(f\"mkdir -p ~/Projects/Onion_grading_new/runs && curl -o ~/Projects/Onion_grading_new/runs/onion_model_artifacts.zip {tunnel_url}/onion_model_artifacts.zip && unzip -o ~/Projects/Onion_grading_new/runs/onion_model_artifacts.zip -d ~/Projects/Onion_grading_new/runs/\\n\")\n"
    ]
}

# Apply to notebook
nb["cells"][19]["source"] = cell_19_src
nb["cells"][20]["source"] = cell_20_src
nb["cells"][20]["outputs"] = []
nb["cells"][20]["execution_count"] = None

# If tunnel cells not present, append them
has_tunnel = any("cloudflared" in "".join(c.get("source", [])) for c in nb["cells"])
if not has_tunnel:
    nb["cells"].append(cell_21_md)
    nb["cells"].append(cell_22_code)
    print("Added Cloudflare tunnel direct download cells.")

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)

print("Notebook updated successfully with Drive copy and Cloudflare tunnel options!")
