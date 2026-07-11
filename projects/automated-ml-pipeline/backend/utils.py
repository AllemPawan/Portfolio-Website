import os
import uuid
import logging
import io
import base64
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams["figure.facecolor"] = "#0f172a"
plt.rcParams["axes.facecolor"] = "#1e293b"
plt.rcParams["axes.edgecolor"] = "#334155"
plt.rcParams["axes.labelcolor"] = "#cbd5e1"
plt.rcParams["xtick.color"] = "#cbd5e1"
plt.rcParams["ytick.color"] = "#cbd5e1"
plt.rcParams["text.color"] = "#e2e8f0"
plt.rcParams["grid.color"] = "#334155"
plt.rcParams["grid.alpha"] = 0.3
plt.rcParams["figure.dpi"] = 100

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

sns.set_style("darkgrid")


def generate_session_id():
    return uuid.uuid4().hex[:12]


def save_upload(file, session_id):
    ext = os.path.splitext(file.filename)[1] or ".csv"
    filename = f"{session_id}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(file.file.read())
    return path


def cleanup_session(session_id):
    for f in os.listdir(UPLOAD_DIR):
        if f.startswith(session_id):
            os.remove(os.path.join(UPLOAD_DIR, f))


def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return encoded


def format_timestamp():
    return datetime.now().isoformat()
