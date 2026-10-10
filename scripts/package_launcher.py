#!/usr/bin/env python3
"""
LSJ Elite Video Editor — Standalone Windows RC1 Launcher Entrypoint
Initializes clean execution environment, discovers bundled bin/ (embedded FFmpeg),
configures offline model cache, and launches the desktop editor.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Resolve root application directory
APP_DIR = Path(__file__).resolve().parent
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent

# 1. Enforce clean Windows PATH without relying on developer PATH entries
system_root = os.environ.get("SystemRoot", r"C:\Windows")
clean_path_entries = [
    str(APP_DIR / "bin"),
    os.path.join(system_root, "System32"),
    system_root,
    os.path.join(system_root, "System32", "Wbem"),
    os.path.join(system_root, "System32", "WindowsPowerShell", "v1.0")
]
# Retain Python directory if running under external python
if not getattr(sys, "frozen", False):
    clean_path_entries.insert(1, str(Path(sys.executable).parent))
    clean_path_entries.insert(2, str(Path(sys.executable).parent / "Scripts"))

os.environ["PATH"] = ";".join(clean_path_entries)

# 2. Configure isolated local model cache if provisioned in bundle
bundled_models = APP_DIR / "models"
if bundled_models.is_dir():
    os.environ["HF_HOME"] = str(bundled_models)
    os.environ["TRANSFORMERS_CACHE"] = str(bundled_models / "hub")

# 3. Add windows/ module directory to sys.path and launch editor
windows_dir = APP_DIR / "windows"
if windows_dir.is_dir():
    sys.path.insert(0, str(windows_dir))

import lsj_video_editor  # type: ignore

if __name__ == "__main__":
    lsj_video_editor.main()
