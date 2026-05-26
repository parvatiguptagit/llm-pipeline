"""Train entrypoint — delegates to Nomic Embed fine-tuning."""
import subprocess
import sys
from pathlib import Path

def train():
    script = Path(__file__).resolve().parent / "train_nomic.py"
    result = subprocess.run([sys.executable, str(script)], check=False)
    if result.returncode != 0:
        raise RuntimeError("Nomic training failed")

if __name__ == "__main__":
    train()
