"""
rename_vivado_project.py — rename an hls4ml-generated Vivado project from
"project_1" to a meaningful name (e.g. ecg_v1_uniform_8bit).

Renames:
  - project_1.xpr                  -> <new>.xpr
  - project_1.runs/                -> <new>.runs/
  - project_1.srcs/                -> <new>.srcs/
  - project_1.cache/               -> <new>.cache/
  - project_1.hbs/                 -> <new>.hbs/
  - project_1.hw/                  -> <new>.hw/
  - project_1.ip_user_files/       -> <new>.ip_user_files/

And updates internal text refs inside .xpr / .tcl / .runs/.../*.tcl that
mention "project_1" verbatim.

Usage:
  python rename_vivado_project.py <myproject_vivado_accelerator dir> <new name>
"""

import os
import sys
import shutil


def main():
    if len(sys.argv) != 3:
        print("Usage: python rename_vivado_project.py <vivado_dir> <new_name>")
        sys.exit(1)

    vivado_dir, new_name = sys.argv[1], sys.argv[2]
    if not os.path.isdir(vivado_dir):
        print(f"ERROR: {vivado_dir} is not a directory")
        sys.exit(1)

    old = "project_1"
    new = new_name

    # 1. Rename directories first (longest first so we don't mangle)
    for entry in sorted(os.listdir(vivado_dir), key=len, reverse=True):
        if entry.startswith(old):
            src = os.path.join(vivado_dir, entry)
            dst = os.path.join(vivado_dir, entry.replace(old, new, 1))
            if src != dst:
                print(f"rename: {entry}  ->  {os.path.basename(dst)}")
                os.rename(src, dst)

    # 2. Patch text files that may reference "project_1"
    patched = 0
    for root, _, files in os.walk(vivado_dir):
        for f in files:
            if not f.endswith((".xpr", ".tcl", ".prj", ".rpt")):
                continue
            path = os.path.join(root, f)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    s = fh.read()
            except (UnicodeDecodeError, PermissionError):
                continue
            if old in s:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(s.replace(old, new))
                patched += 1
    print(f"Patched {patched} text files")

    # 3. Final rename of .xpr
    print("\nFinal layout:")
    for e in sorted(os.listdir(vivado_dir)):
        print(f"  {e}")


if __name__ == "__main__":
    main()
