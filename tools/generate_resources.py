#!/usr/bin/env python3
"""Generate resources_rc.py from resources.qrc"""
import sys
import os

# Add the PySide6 package to path
pyside6_path = os.path.join(os.path.dirname(__file__), 
    '../../bazel-bin/blender_launcher.runfiles/blender_launcher_pip_311_pyside6_essentials/site-packages')

if os.path.exists(pyside6_path):
    sys.path.insert(0, pyside6_path)

try:
    from PySide6.scripts.pyside_tool import rcc_main
    sys.exit(rcc_main())
except ImportError as e:
    print(f"Error: Cannot import PySide6: {e}")
    print(f"Looked in: {pyside6_path}")
    sys.exit(1)
