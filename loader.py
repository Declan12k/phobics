# phobics/loader.py
import os
import pygame

from .settings import TEX_DIR, SND_DIR

class SafeLoader:
    def __init__(self):
        # assume pygame.init has been called by the caller
        self.textures = {}
        self.sounds = {}
        self._create_fallbacks()

    def _create_fallbacks(self):
        def make_surf(color, size=(32,32)):
            s = pygame.Surface(size, pygame.SRCALPHA)
            s.fill(color)
            return s
        self.textures["player"] = make_surf((200,200,200),(24,24))
        self.textures["enemy"] = make_surf((180,40,40),(32,32))
        self.textures["collect"] = make_surf((200,170,80),(20,20))
        self.textures["proj"] = make_surf((0,200,200),(10,10))
        self.textures["arrow"] = make_surf((0,200,200),(18,4))
        self.sounds["shoot"] = None
        self.sounds["hit"] = None
        self.sounds["collect"] = None
        self.sounds["select"] = None

    def load_image_safe(self, filename):
        path = os.path.join(TEX_DIR, filename)
        key = os.path.splitext(filename)[0]
        if not os.path.exists(path):
            return self.textures.get(key)
        try:
            img = pygame.image.load(path)
            # convert_alpha only if display initialized
            if pygame.display.get_surface():
                img = img.convert_alpha()
            return img
        except Exception:
            return self.textures.get(key)

    def load_sound_safe(self, filename):
        path = os.path.join(SND_DIR, filename)
        if not os.path.exists(path):
            return None
        try:
            return pygame.mixer.Sound(path)
        except Exception:
            return None

    def reload_all(self):
        mapping = {
            "player":"player.png",
            "enemy":"enemy.png",
            "collect":"collectible.png",
            "proj":"projectile.png",
            "arrow":"arrow.png",
        }
        for k,f in mapping.items():
            surf = self.load_image_safe(f)
            if surf is None:
                surf = self.textures.get(k)
            self.textures[k]=surf

        sound_map = {
            "shoot":"shoot.wav",
            "hit":"hit.wav",
            "collect":"collect.wav",
            "select":"select.wav",
        }
        for k,f in sound_map.items():
            snd = self.load_sound_safe(f)
            self.sounds[k]=snd
