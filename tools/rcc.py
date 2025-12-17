"""Generate resources_rc.py from resources.qrc"""
import sys
from PySide6.scripts import pyside_tool

if __name__ == "__main__":
    sys.argv[0] = 'pyside6-rcc'
    sys.exit(pyside_tool.rcc())
