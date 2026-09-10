"""Bundle main.py + kag/ into a Kaggle tar.gz (< 100 MiB)."""

from __future__ import annotations

import os
import tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "submission.tar.gz")


def main():
    with tarfile.open(OUT, "w:gz") as tar:
        tar.add(os.path.join(ROOT, "main.py"), arcname="main.py")
        kag = os.path.join(ROOT, "kag")
        for dirpath, _, files in os.walk(kag):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, ROOT).replace("\\", "/")
                tar.add(full, arcname=rel)
    size = os.path.getsize(OUT)
    print(f"wrote {OUT} ({size} bytes, {size/1024/1024:.3f} MiB)")


if __name__ == "__main__":
    main()
