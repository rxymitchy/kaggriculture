"""Bundle a single-file main.py (Kaggle exec-safe) and optionally tar it."""

from __future__ import annotations

import os
import tarfile
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "submission.tar.gz")


def main():
    subprocess.check_call([sys.executable, os.path.join(ROOT, "scripts", "bundle_main.py")])
    main_py = os.path.join(ROOT, "main.py")
    with tarfile.open(OUT, "w:gz") as tar:
        tar.add(main_py, arcname="main.py")
    size = os.path.getsize(OUT)
    print(f"wrote {OUT} ({size} bytes, {size/1024/1024:.3f} MiB)")


if __name__ == "__main__":
    main()
