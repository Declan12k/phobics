# phobics/main.py
import os
import sys
import time
import pygame

from .engine import Engine

def main():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    pygame.font.init()

    # center
    os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
    info = pygame.display.Info()
    window_w, window_h = info.current_w, info.current_h

    screen = pygame.display.set_mode((window_w, window_h))
    pygame.display.set_caption("PHOBICS")

    engine = Engine(screen)
    engine.build_front_menu()

    clock = pygame.time.Clock()
    while True:
        dt = clock.tick(engine.FPS)/1000.0
        # event loop
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                engine.quit_game()
            elif ev.type == pygame.KEYDOWN:
                # title -> front menu
                if engine.on_title:
                    engine.on_title=False; engine.on_front_menu=True; engine.build_front_menu(); continue
                if engine.on_front_menu:
                    if ev.key == pygame.K_RETURN:
                        engine.open_new_game_slot_menu(); continue
                    if ev.key == pygame.K_ESCAPE:
                        engine.back_to_title(); continue
                if engine.on_slot_menu:
                    if ev.key == pygame.K_ESCAPE:
                        engine.on_slot_menu=False; engine.on_front_menu=True; engine.slot_menu_mode=None; engine.build_front_menu(); continue
                if engine.on_stage_select:
                    if ev.key == pygame.K_ESCAPE:
                        engine.on_stage_select=False; engine.on_slot_menu=True; engine.build_slot_buttons(); continue

                if ev.key == pygame.K_ESCAPE:
                    if engine.in_options:
                        pass
                    else:
                        if engine.in_menu:
                            engine.close_menu()
                        else:
                            engine.open_menu()
                elif ev.key == pygame.K_SPACE:
                    if not (engine.paused or engine.in_menu or engine.in_options or engine.on_front_menu or engine.on_slot_menu or engine.on_stage_select) and engine.shot_available:
                        mx,my = pygame.mouse.get_pos(); wx = mx - (engine.window_w - engine.world_w)//2; wy = my - (engine.window_h - engine.world_h)//2
                        engine.fire_projectile(wx,wy)
                elif ev.key == pygame.K_r:
                    print("[engine] reload assets"); engine.loader.reload_all(); engine.assets.update({
                        "player": engine.loader.textures["player"],
                        "enemy": engine.loader.textures["enemy"],
                        "collect": engine.loader.textures["collect"],
                        "proj": engine.loader.textures["proj"],
                        "arrow": engine.loader.textures["arrow"],
                        "shoot": engine.loader.sounds.get("shoot"),
                        "hit": engine.loader.sounds.get("hit"),
                        "collect_snd": engine.loader.sounds.get("collect"),
                        "select": engine.loader.sounds.get("select"),
                    }); engine.stages_config = engine.load_stages_config()

            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mx,my = ev.pos
                if engine.on_title:
                    engine.on_title=False; engine.on_front_menu=True; engine.build_front_menu(); continue
                if engine.on_front_menu:
                    for rect,label,action in engine.front_menu_buttons:
                        if rect.collidepoint((mx,my)):
                            engine.play_select_sound()
                            # map labels to methods:
                            if label == "New Game":
                                engine.open_new_game_slot_menu()
                            elif label == "Continue":
                                engine.continue_most_recent()
                            elif label == "Load":
                                engine.open_load_slot_menu()
                            elif label == "Back":
                                engine.back_to_title()
                            elif label == "Quit":
                                engine.quit_game()
                            break
                    continue

                if engine.on_slot_menu:
                    for rect,label,idx in engine.slot_buttons:
                        if rect.collidepoint((mx,my)):
                            if idx == 0:
                                engine.on_slot_menu=False; engine.on_front_menu=True; engine.slot_menu_mode=None; engine.build_front_menu(); break
                            engine.selected_slot = idx
                            if engine.slot_menu_mode == "new":
                                engine.on_slot_menu=False; engine.on_stage_select=True; engine.build_stage_buttons_for_slot(idx, mode="new"); break
                            elif engine.slot_menu_mode == "load":
                                ok = engine.load_from_slot(idx)
                                if ok: break
                            elif engine.slot_menu_mode == "save":
                                engine.save_to_slot(idx); break
                    continue

                if engine.on_stage_select:
                    for rect,label,stage_idx,selectable in engine.stage_buttons:
                        if rect.collidepoint((mx,my)):
                            if stage_idx == -1:
                                engine.on_stage_select=False; engine.on_slot_menu=True; engine.build_slot_buttons(); break
                            if selectable:
                                engine.stage = int(stage_idx)
                                unlocked_list = list(range(1, min(engine.stage+1, engine.MAX_STAGES)+1))
                                save_data = {"stage": int(engine.stage), "unlocked": unlocked_list, "timestamp": time.time()}
                                if engine.selected_slot:
                                    engine.write_slot(engine.selected_slot, save_data)
                                print(f"[new] Created new game in slot {engine.selected_slot} stage {engine.stage}")
                                engine.on_stage_select=False; engine.on_slot_menu=False; engine.on_front_menu=False
                                engine.play_game_music(); engine.reset_stage(); break
                    continue

                if engine.in_menu:
                    for rect,label,action in engine.menu_buttons:
                        if rect.collidepoint((mx,my)):
                            engine.play_select_sound()
                            # wire actions by label
                            if label == "Continue":
                                engine.close_menu()
                            elif label == "Save Game":
                                engine.open_save_slot_menu()
                            elif label == "Load Game":
                                engine.open_load_slot_menu()
                            elif label == "Restart":
                                engine.restart_game()
                            elif label == "Options":
                                engine.open_options()
                            elif label == "Quit":
                                engine.quit_game()
                            break
                    continue

                if engine.in_options:
                    for rect,label,action in engine.options_buttons:
                        if rect.collidepoint((mx,my)):
                            engine.play_select_sound()
                            engine.close_options()
                            break
                    continue

                # gameplay click
                if not (engine.paused or engine.in_menu or engine.in_options or engine.on_front_menu or engine.on_slot_menu or engine.on_stage_select):
                    wx = mx - (engine.window_w - engine.world_w)//2; wy = my - (engine.window_h - engine.world_h)//2
                    if engine.shot_available: engine.fire_projectile(wx,wy)

        # update and draw
        engine.update(dt)
        engine.screen.fill((0,0,0))
        engine.draw()
        pygame.display.flip()

if __name__ == "__main__":
    main()
