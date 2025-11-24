# phobics/utils.py
import os
import sys

def resource_path(rel):
    # PyInstaller safe path
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))
        base_path = os.path.dirname(base_path)  # go up to project root
    return os.path.join(base_path, rel)
