# phobics/engine.py
import os
import sys
import math
import random
import json
import time
import pygame
from pygame import Rect

from .loader import SafeLoader
from .settings import MUSIC_DIR, STAGES_JSON, SAVES_DIR
from . import ui

class Engine:
    FPS = 60
    MAX_STAGES = 10
    SLOT_COUNT = 3

    def __init__(self, screen):
        # screen: initialized pygame display surface
        pygame.mixer.pre_init(44100, -16, 2, 512)
        self.screen = screen
        self.window_w, self.window_h = screen.get_size()
        self.clock = pygame.time.Clock()

        # stage/world defaults
        self.stage = 1
        self.base_w = 800
        self.base_h = 600

        self.loader = SafeLoader()
        self.loader.reload_all()
        self.assets = {
            "player": self.loader.textures["player"],
            "enemy": self.loader.textures["enemy"],
            "collect": self.loader.textures["collect"],
            "proj": self.loader.textures["proj"],
            "arrow": self.loader.textures["arrow"],
            "shoot": self.loader.sounds.get("shoot"),
            "hit": self.loader.sounds.get("hit"),
            "collect_snd": self.loader.sounds.get("collect"),
            "select": self.loader.sounds.get("select"),
        }

        self.title_music = os.path.join(MUSIC_DIR, "titlescreen.mp3")
        self.game_music = os.path.join(MUSIC_DIR, "gamemusic.mp3")

        self.stages_config = self.load_stages_config()

        # UI states
        self.paused = False
        self.in_menu = False
        self.in_options = False
        self.menu_buttons = []
        self.options_buttons = []

        self.on_title = True
        self.on_front_menu = False
        self.front_menu_buttons = []

        self.on_slot_menu = False
        self.slot_menu_mode = None
        self.slot_buttons = []
        self.on_stage_select = False
        self.stage_buttons = []
        self.selected_slot = None

        # world
        self.world_w, self.world_h = self.base_w, self.base_h
        self.reset_stage()

        # projectiles
        self.shot_available = True
        self.projectile = None
        self.projectile_v = (0,0)
        self.arrow_end = (0,0)

        # title animation
        self.title_alpha = 0.0
        self.title_fade_in_time = 1.8  # seconds
        self.title_start_time = time.time()
        self.title_prompt_visible = False
        self.title_prompt_time = 0.0

        # audio & saves dir
        os.makedirs(SAVES_DIR, exist_ok=True)

        # start music
        self.play_title_music()

    # ---------- stage / saves ----------
    def load_stages_config(self):
        try:
            if os.path.exists(STAGES_JSON):
                with open(STAGES_JSON,"r",encoding="utf-8") as f:
                    data=json.load(f)
                    return {int(s.get("stage",i+1)):s for i,s in enumerate(data)}
        except Exception:
            pass
        return {}

    def world_size(self):
        cfg = self.stages_config.get(self.stage)
        if cfg and "world_w" in cfg and "world_h" in cfg:
            w=int(cfg["world_w"]); h=int(cfg["world_h"])
        else:
            growth_factor = math.log(self.stage+1, 1.45)
            w = self.base_w + int(180 * growth_factor)
            h = self.base_h + int(130 * growth_factor)
        pad=40
        w=min(w, self.window_w-pad)
        h=min(h, self.window_h-pad)
        return w,h

    def reset_stage(self):
        self.stages_config = self.load_stages_config()
        self.world_w, self.world_h = self.world_size()
        self.player = Rect(40,40,24,24)
        self.arrow_end = (self.player.centerx+10, self.player.centery)
        cfg = self.stages_config.get(self.stage,{})
        num_collect = int(cfg.get("collectibles", 3 + self.stage)) if cfg else 3 + self.stage
        self.collectibles=[]
        for _ in range(num_collect):
            x = random.randint(30, max(30,self.world_w-30))
            y = random.randint(30, max(30,self.world_h-30))
            self.collectibles.append(Rect(x-10,y-10,20,20))
        num_enemies = int(cfg.get("enemies",2 + self.stage)) if cfg else 2 + self.stage
        self.enemies=[]
        for _ in range(num_enemies):
            x=random.randint(50, max(50, self.world_w-50))
            y=random.randint(50, max(50, self.world_h-50))
            vx=random.choice([-3,-2,2,3]); vy=random.choice([-3,-2,2,3])
            self.enemies.append([Rect(x-16,y-16,32,32), vx, vy])

    # saves
    def slot_filename(self, slot_index):
        return os.path.join(SAVES_DIR, f"save_slot{slot_index}.json")

    def read_slot(self, slot_index):
        path=self.slot_filename(slot_index)
        try:
            if os.path.exists(path):
                with open(path,"r",encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def write_slot(self, slot_index, data):
        path=self.slot_filename(slot_index)
        try:
            with open(path,"w",encoding="utf-8") as f:
                json.dump(data,f)
            return True
        except Exception as e:
            print("[save] failed:", e)
            return False

    def list_slots(self):
        slots=[]
        for i in range(1, self.SLOT_COUNT+1):
            info={"index":i,"exists":False,"stage":None,"unlocked":[1],"timestamp":None}
            d=self.read_slot(i)
            if d:
                info["exists"]=True
                info["stage"]=int(d.get("stage",1))
                info["unlocked"]=list(set(int(x) for x in d.get("unlocked",[1])))
                info["timestamp"]=float(d.get("timestamp",0.0))
            slots.append(info)
        return slots

    def most_recent_slot_index(self):
        slots=self.list_slots(); recent=None; recent_ts=0.0
        for s in slots:
            if s["exists"] and s["timestamp"]:
                if s["timestamp"] > recent_ts:
                    recent_ts = s["timestamp"]; recent = s["index"]
        return recent

    # ---------- projectile / gameplay ----------
    def fire_projectile(self, tx, ty):
        if not self.shot_available: return
        cx,cy = self.player.center
        angle = math.atan2(ty-cy, tx-cx)
        speed = 14.0
        vx = math.cos(angle)*speed; vy = math.sin(angle)*speed
        self.projectile = Rect(cx-5, cy-5, 10,10)
        self.projectile_v = (vx, vy)
        self.shot_available = False
        snd = self.assets.get("shoot")
        if snd:
            try: snd.play()
            except Exception: pass

    def move_projectile(self):
        if not self.projectile: return
        vx,vy = self.projectile_v
        self.projectile.x += int(vx); self.projectile.y += int(vy)
        if (self.projectile.right < 0 or self.projectile.left > self.world_w or
            self.projectile.bottom < 0 or self.projectile.top > self.world_h):
            self.projectile=None; return
        for ent in list(self.enemies):
            r = ent[0]
            if self.projectile.colliderect(r):
                try: self.enemies.remove(ent)
                except Exception: pass
                self.projectile=None
                snd=self.assets.get("hit")
                if snd:
                    try: snd.play()
                    except Exception: pass
                break

    def update(self, dt):
        # menus / title halt the world update
        if self.on_title or self.on_front_menu or self.on_slot_menu or self.on_stage_select or self.in_menu or self.in_options:
            return
        if self.paused: return

        keys = pygame.key.get_pressed()
        speed = 250 * dt
        dx = (keys[pygame.K_d] - keys[pygame.K_a]) * speed
        dy = (keys[pygame.K_s] - keys[pygame.K_w]) * speed
        if dx or dy:
            self.player.x += int(dx); self.player.y += int(dy)
        self.player.clamp_ip(Rect(0,0,self.world_w,self.world_h))

        for ent in list(self.enemies):
            r,vx,vy = ent
            r.x += vx; r.y += vy
            if r.left <= 0 or r.right >= self.world_w: ent[1] = -vx
            if r.top <= 0 or r.bottom >= self.world_h: ent[2] = -vy

        self.move_projectile()
        for c in list(self.collectibles):
            if self.player.colliderect(c):
                try: self.collectibles.remove(c)
                except Exception: pass
                snd=self.assets.get("collect_snd")
                if snd:
                    try: snd.play()
                    except Exception: pass

        for ent in list(self.enemies):
            r=ent[0]
            if self.player.colliderect(r):
                self.restart_stage(); return

        if not self.collectibles:
            if self.stage < self.MAX_STAGES: self.stage += 1
            self.reset_stage()

        mx,my = pygame.mouse.get_pos()
        wx = mx - (self.window_w - self.world_w)//2
        wy = my - (self.window_h - self.world_h)//2
        cx,cy = self.player.center
        angle = math.atan2(wy-cy, wx-cx)
        length = 18
        self.arrow_end = (cx + math.cos(angle)*length, cy + math.sin(angle)*length)

    # ---------- drawing ----------
    def draw(self):
        # Title fade and prompt
        if self.on_title:
            elapsed = time.time() - self.title_start_time
            t = min(1.0, elapsed / max(0.0001, self.title_fade_in_time))
            self.title_alpha = int(255 * (t))
            if t >= 1.0:
                self.title_prompt_visible = True
                self.title_prompt_time = time.time()
            self.draw_title()
            if self.title_prompt_visible:
                small = pygame.font.SysFont(None, 24)
                prompt = small.render("Press any key to continue", True, (230,230,230))
                pr = prompt.get_rect(center=(self.window_w//2, int(self.window_h*0.88)))
                self.screen.blit(prompt, pr)
            return

        is_menu = (self.on_front_menu or self.on_slot_menu or self.in_menu or self.in_options or self.on_stage_select)
        if is_menu:
            self.draw_title()

        if not is_menu:
            # simplified world rendering (keeps your look)
            base = pygame.Surface((self.window_w, self.window_h))
            base.fill((28,28,28))
            for i in range(200):
                x=random.randrange(0,self.window_w); y=random.randrange(0,self.window_h)
                a=random.randint(8,22); base.fill((40,40,40,a),(x,y,1,1))
            small = pygame.transform.smoothscale(base,(max(1,self.window_w//20), max(1,self.window_h//20)))
            blurred = pygame.transform.smoothscale(small, (self.window_w, self.window_h))
            self.screen.blit(blurred,(0,0))

            offset_x = (self.window_w - self.world_w)//2
            offset_y = (self.window_h - self.world_h)//2

            vign = pygame.Surface((self.window_w, self.window_h), pygame.SRCALPHA)
            vign.fill((0,0,0,90))
            pygame.draw.rect(vign, (0,0,0,0), (offset_x+3, offset_y+3, self.world_w-6, self.world_h-6))
            self.screen.blit(vign,(0,0))

            world_bg = pygame.Surface((self.world_w, self.world_h))
            world_bg.fill((10,10,10))
            self.screen.blit(world_bg,(offset_x, offset_y))

            pygame.draw.rect(self.screen, (200,200,200), (offset_x, offset_y, self.world_w, self.world_h), 3)

            for c in self.collectibles:
                pygame.draw.ellipse(self.screen, (180,140,60), (c.x+offset_x, c.y+offset_y, c.width, c.height))

            for ent in self.enemies:
                r=ent[0]; img=self.assets.get("enemy")
                if isinstance(img, pygame.Surface):
                    surf = pygame.transform.smoothscale(img, (r.width, r.height)); self.screen.blit(surf,(r.x+offset_x, r.y+offset_y))
                else:
                    pygame.draw.rect(self.screen, (180,40,40), (r.x+offset_x, r.y+offset_y, r.width, r.height))

            if self.projectile:
                p=self.projectile; img=self.assets.get("proj")
                if isinstance(img, pygame.Surface):
                    surf = pygame.transform.smoothscale(img, (p.width, p.height)); self.screen.blit(surf,(p.x+offset_x,p.y+offset_y))
                else:
                    pygame.draw.ellipse(self.screen, (0,200,200), (p.x+offset_x,p.y+offset_y,p.width,p.height))

            pimg = self.assets.get("player")
            if isinstance(pimg, pygame.Surface):
                surf = pygame.transform.smoothscale(pimg, (self.player.width, self.player.height)); self.screen.blit(surf,(self.player.x+offset_x,self.player.y+offset_y))
            else:
                pygame.draw.rect(self.screen, (230,230,230), (self.player.x+offset_x, self.player.y+offset_y, self.player.width, self.player.height))

            cx,cy = self.player.center; ax,ay = self.arrow_end
            pygame.draw.line(self.screen, (0,200,200), (cx+offset_x, cy+offset_y), (ax+offset_x, ay+offset_y), 3)

            font = pygame.font.SysFont(None, 24)
            text = font.render(f"Stage: {self.stage}", True, (240,240,240)); self.screen.blit(text,(8,8))
            shot_text = "Shot: READY" if self.shot_available else "Shot: USED"
            st = font.render(shot_text, True, (200,200,200)); self.screen.blit(st,(8,32))

            if self.paused and not self.in_menu and not self.in_options:
                big = pygame.font.SysFont(None,64); p = big.render("PAUSED", True, (200,40,40))
                pr = p.get_rect(center=(self.window_w//2, 40)); self.screen.blit(p, pr)

            # CRT
            crt = pygame.Surface((self.window_w, self.window_h), pygame.SRCALPHA)
            for y in range(0, self.window_h, 2):
                pygame.draw.line(crt, (0,0,0,40), (0,y), (self.window_w,y))
            tint = pygame.Surface((self.window_w, self.window_h), pygame.SRCALPHA); tint.fill((5,0,0,20)); self.screen.blit(tint, (-1,0))
            tint2 = pygame.Surface((self.window_w, self.window_h), pygame.SRCALPHA); tint2.fill((0,0,5,20)); self.screen.blit(tint2, (1,0))
            self.screen.blit(crt,(0,0))

        # Menus: draw overlays and buttons (kept minimal; actions are wired in main)
        if self.in_menu:
            overlay = pygame.Surface((self.window_w, self.window_h), pygame.SRCALPHA); overlay.fill((0,0,0,140)); self.screen.blit(overlay,(0,0))
            fontm = pygame.font.SysFont(None,24)
            for rect,label,_ in self.menu_buttons:
                pygame.draw.rect(self.screen, (60,60,60), rect); pygame.draw.rect(self.screen, (180,180,180), rect,2)
                lbl = fontm.render(label, True, (240,240,240)); self.screen.blit(lbl, (rect.x+12, rect.y+8))

        if self.in_options:
            overlay = pygame.Surface((self.window_w, self.window_h), pygame.SRCALPHA); overlay.fill((0,0,0,180)); self.screen.blit(overlay,(0,0))
            fonto = pygame.font.SysFont(None,22)
            for rect,label,_ in self.options_buttons:
                pygame.draw.rect(self.screen, (50,50,50), rect); pygame.draw.rect(self.screen,(200,200,200),rect,2)
                lbl = fonto.render(label, True, (240,240,240)); self.screen.blit(lbl,(rect.x+8,rect.y+6))

        if self.on_front_menu:
            overlay = pygame.Surface((self.window_w, self.window_h), pygame.SRCALPHA); overlay.fill((0,0,0,180)); self.screen.blit(overlay,(0,0))
            font = pygame.font.SysFont(None,36)
            title = pygame.font.SysFont(None,80).render("PHOBICS", True, (230,230,230)); tr = title.get_rect(center=(self.window_w//2, self.window_h//4)); self.screen.blit(title,tr)
            for rect,label,_ in self.front_menu_buttons:
                pygame.draw.rect(self.screen,(60,60,60),rect); pygame.draw.rect(self.screen,(180,180,180),rect,2)
                txt = font.render(label, True, (240,240,240)); self.screen.blit(txt,(rect.x+14, rect.y+8))

        if self.on_slot_menu:
            overlay = pygame.Surface((self.window_w, self.window_h), pygame.SRCALPHA); overlay.fill((0,0,0,200)); self.screen.blit(overlay,(0,0))
            font = pygame.font.SysFont(None,32)
            title_txt = "Choose Slot"
            if self.slot_menu_mode == "new": title_txt = "Choose Slot to Start New Game"
            elif self.slot_menu_mode == "load": title_txt = "Choose Slot to Load"
            elif self.slot_menu_mode == "save": title_txt = "Choose Slot to Save Current Progress"
            title = pygame.font.SysFont(None,64).render(title_txt, True, (230,230,230)); tr = title.get_rect(center=(self.window_w//2, self.window_h//6)); self.screen.blit(title,tr)
            for rect,label,idx in self.slot_buttons:
                pygame.draw.rect(self.screen,(50,50,50),rect); pygame.draw.rect(self.screen,(190,190,190),rect,2)
                txt = font.render(label, True, (230,230,230)); self.screen.blit(txt,(rect.x+16, rect.y+12))

        if self.on_stage_select:
            overlay = pygame.Surface((self.window_w, self.window_h), pygame.SRCALPHA); overlay.fill((0,0,0,210)); self.screen.blit(overlay,(0,0))
            title = pygame.font.SysFont(None,56).render("Select Stage", True, (230,230,230)); tr=title.get_rect(center=(self.window_w//2, self.window_h//8)); self.screen.blit(title,tr)
            font = pygame.font.SysFont(None,28)
            for rect,label,idx,sel in self.stage_buttons:
                bg_col = (60,60,60) if sel else (35,35,35)
                border_col = (200,200,200) if sel else (110,110,110)
                txt_col = (240,240,240) if sel else (140,140,140)
                pygame.draw.rect(self.screen, bg_col, rect); pygame.draw.rect(self.screen, border_col, rect,2)
                txt = font.render(label, True, txt_col)
                tx = rect.x + (rect.width - txt.get_width())//2; ty = rect.y + (rect.height - txt.get_height())//2
                self.screen.blit(txt, (tx, ty))

    # ---------- title drawing ----------
    def draw_title(self):
        big = pygame.font.SysFont(None,96)
        title_surf = big.render("PHOBICS", True, (220,220,220))
        try:
            title_surf.set_alpha(int(self.title_alpha))
        except Exception:
            pass
        title_rect = title_surf.get_rect(center=(self.window_w//2, self.window_h//2 - 40))
        # background noise
        bg = pygame.Surface((self.window_w, self.window_h))
        flicker = random.randint(-8,8)
        gray = max(0, min(25 + flicker, 255)); bg.fill((gray,gray,gray))
        for _ in range(400):
            x=random.randrange(0,self.window_w); y=random.randrange(0,self.window_h); c=random.randint(0,40); bg.set_at((x,y),(c,c,c))
        self.screen.blit(bg,(0,0))
        # subtle vignette
        vign = pygame.Surface((self.window_w, self.window_h), pygame.SRCALPHA)
        pygame.draw.rect(vign, (0,0,0,150), (30,30,self.window_w-60, self.window_h-60))
        pygame.draw.rect(vign, (0,0,0,0), (70,70,self.window_w-140, self.window_h-140))
        self.screen.blit(vign,(0,0))
        self.screen.blit(title_surf, title_rect)
        small = pygame.font.SysFont(None,24)
        sub = small.render("a bleak, short game", True, (180,180,180))
        self.screen.blit(sub, (title_rect.centerx - sub.get_width()//2, title_rect.bottom + 6))

    # ---------- audio ----------
    def play_title_music(self):
        try:
            if os.path.exists(self.title_music):
                pygame.mixer.music.stop()
                try: pygame.mixer.music.unload()
                except Exception: pass
                pygame.mixer.music.load(self.title_music); pygame.mixer.music.set_volume(0.35); pygame.mixer.music.play(-1)
        except Exception as e:
            print("[music] couldn't play title music:", e)

    def play_game_music(self):
        try:
            if os.path.exists(self.game_music):
                pygame.mixer.music.stop()
                try: pygame.mixer.music.unload()
                except Exception: pass
                pygame.mixer.music.load(self.game_music); pygame.mixer.music.set_volume(0.45); pygame.mixer.music.play(-1)
        except Exception as e:
            print("[music] couldn't play game music:", e)

    def play_select_sound(self):
        snd = self.assets.get("select")
        if snd:
            try: snd.play()
            except Exception: pass

    # ---------- menu actions (light wrappers) ----------
    def open_menu(self):
        self.paused=True; self.in_menu=True; self.menu_buttons=ui.build_menu_buttons(self.window_w, self.window_h)

    def close_menu(self):
        self.in_menu=False; self.paused=False; self.menu_buttons=[]

    def open_options(self):
        self.menu_buttons=[]; self.in_menu=False; self.in_options=True; self.paused=True; self.options_buttons=ui.build_options_buttons(self.window_w, self.window_h)

    def close_options(self):
        self.in_options=False; self.open_menu(); self.options_buttons=[]

    def back_to_title(self):
        self.on_title=True; self.on_front_menu=False; self.on_slot_menu=False; self.on_stage_select=False; self.in_menu=False; self.in_options=False; self.play_title_music(); self.title_start_time=time.time(); self.title_alpha=0.0; self.title_prompt_visible=False

    def quit_game(self):
        try: pygame.mixer.music.stop()
        except Exception: pass
        pygame.quit(); sys.exit()

    def open_new_game_slot_menu(self):
        self.on_front_menu=False; self.on_slot_menu=True; self.slot_menu_mode="new"; self.selected_slot=None; self.build_slot_buttons()

    def open_load_slot_menu(self):
        self.on_front_menu=False; self.on_slot_menu=True; self.slot_menu_mode="load"; self.selected_slot=None; self.build_slot_buttons()

    def open_save_slot_menu(self):
        self.on_slot_menu=True; self.slot_menu_mode="save"; self.on_front_menu=False; self.selected_slot=None; self.build_slot_buttons()

    def save_to_slot(self, slot_index):
        data = {"stage": int(self.stage), "unlocked": list(range(1, min(self.stage+1, self.MAX_STAGES)+1)), "timestamp": time.time()}
        ok = self.write_slot(slot_index, data)
        if ok: print(f"[save] saved to slot {slot_index} stage {self.stage}")
        if self.slot_menu_mode == "save":
            self.on_slot_menu=False; self.close_menu()

    def load_from_slot(self, slot_index):
        data = self.read_slot(slot_index)
        if not data: print(f"[load] empty"); return False
        self.stage = int(data.get("stage",1))
        self.reset_stage()
        self.on_slot_menu=False; self.on_stage_select=False; self.on_front_menu=False; self.in_menu=False; self.paused=False; self.play_game_music()
        print(f"[load] loaded slot {slot_index} stage {self.stage}")
        return True

    def continue_most_recent(self):
        idx=self.most_recent_slot_index()
        if idx:
            ok=self.load_from_slot(idx)
            if ok: return
        self.open_new_game_slot_menu()

    def restart_stage(self):
        self.reset_stage()

    def restart_game(self):
        self.stage=1; self.reset_stage(); self.close_menu()

    # ---------- convenient builders ----------
    def build_front_menu(self):
        # produce button list and optionally populate actions in main (actions are bound in main)
        self.front_menu_buttons = ui.build_front_menu(self.window_w, self.window_h)

    def build_slot_buttons(self):
        slots = self.list_slots()
        self.slot_buttons = ui.build_slot_buttons(self.window_w, self.window_h, slots)

    def build_stage_buttons_for_slot(self, slot_index, mode="new"):
        unlocked = {1}
        if mode!="new":
            data=self.read_slot(slot_index)
            if data:
                unlocked=set(int(x) for x in data.get("unlocked",[1]))
        self.stage_buttons = ui.build_stage_buttons_for_slot(self.window_w, self.window_h, self.MAX_STAGES, unlocked)
