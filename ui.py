# phobics/ui.py
import pygame
from pygame import Rect

# helper builders that return lists used by Engine (kept similar to original)

def build_menu_buttons(window_w, window_h):
    w,h = 260,40
    sx=(window_w - w)//2
    sy=(window_h - 260)//2
    return [
        (Rect(sx, sy + 0*52, w, h), "Continue", None),
        (Rect(sx, sy + 1*52, w, h), "Save Game", None),
        (Rect(sx, sy + 2*52, w, h), "Load Game", None),
        (Rect(sx, sy + 3*52, w, h), "Restart", None),
        (Rect(sx, sy + 4*52, w, h), "Options", None),
        (Rect(sx, sy + 5*52, w, h), "Quit", None),
    ]

def build_options_buttons(window_w, window_h):
    w,h=220,36
    sx=(window_w - w)//2
    sy=(window_h - 220)//2
    return [(Rect(sx, sy, w, h), "Back", None)]

def build_front_menu(window_w, window_h):
    w,h=300,48
    sx=(window_w - w)//2
    sy=(window_h - 240)//2
    return [
        (Rect(sx, sy + 0*64, w, h), "New Game", None),
        (Rect(sx, sy + 1*64, w, h), "Continue", None),
        (Rect(sx, sy + 2*64, w, h), "Load", None),
        (Rect(sx, sy + 3*64, w, h), "Back", None),
        (Rect(sx, sy + 4*64, w, h), "Quit", None),
    ]

# slot and stage builders are below so Engine can populate actions/behavior
def build_slot_buttons(window_w, window_h, slots):
    buttons=[]
    w,h=360,56
    sx=(window_w - w)//2
    sy=(window_h - 300)//2
    for i,s in enumerate(slots):
        idx=s["index"]
        label=f"Slot {idx}"
        if s["exists"]:
            label += f" — Stage {s['stage']}"
        rect=Rect(sx, sy + i*72, w, h)
        buttons.append((rect, label, idx))
    back_rect=Rect(sx, sy + len(slots)*72, w, 44)
    buttons.append((back_rect, "Back", 0))
    return buttons

def build_stage_buttons_for_slot(window_w, window_h, MAX_STAGES, unlocked, cols=5):
    buttons=[]
    w,h=140,48
    gapx=20; gapy=16
    total_width = cols*w + (cols-1)*gapx
    sx=(window_w - total_width)//2
    sy=(window_h - 240)//2
    for i in range(1, MAX_STAGES+1):
        col=(i-1)%cols; row=(i-1)//cols
        rx = sx + col*(w+gapx); ry = sy + row*(h+gapy)
        selectable = i in unlocked
        buttons.append((Rect(rx, ry, w, h), str(i), i, selectable))
    back_rect = Rect((window_w - 220)//2, sy + ((MAX_STAGES + cols - 1)//cols)*(h+gapy) + 24, 220, 44)
    buttons.append((back_rect, "Back", -1, True))
    return buttons
