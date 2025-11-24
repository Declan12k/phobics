# phobics/settings.py
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ASSETS = HERE / "assets"
TEX_DIR = ASSETS / "textures"
SND_DIR = ASSETS / "sounds"
MUSIC_DIR = ASSETS / "music"
STAGES_JSON = ASSETS / "stages.json"
SAVES_DIR = HERE / "saves"

# Ensure saves folder exists
os.makedirs(SAVES_DIR, exist_ok=True)
