"""
Điểm điều khiển trung tâm (Entry Point) của trò chơi Kingdom Guardians.

Mô-đun này khởi tạo môi trường Pygame, thiết lập các biến toàn cục (tiền, mạng)
và quản lý Vòng lặp trò chơi (Main Game Loop) cùng hệ thống trạng thái
như MENU, MAP_SELECT, PLAYING, PAUSED, GAMEOVER, VICTORY.

Điểm nhấn (Đã được nâng cấp):
    - Tối ưu hóa render bằng dirty_rects giúp tăng FPS đáng kể.
    - Render bản đồ tĩnh (Static Background Cache) tránh tính toán lại nền mỗi frame.
    - Giao diện và các nút điều khiển được quản lý tách biệt qua ui.py.

Hàm xử lý:
    place_tower(x, y): Kiểm tra tính hợp lệ về mặt không gian và tài nguyên
        để đặt một tháp mới vào danh sách phòng thủ.
    upgrade_tower(x, y): Duyệt tọa độ nhấp chuột của người dùng để tìm tháp
        tương ứng và thực thi khấu trừ tiền vàng để nâng cấp tháp đó lên mức
        cao hơn.
    reset_game(): Làm mới hoàn toàn bộ nhớ lưu trữ điểm số, tiền tệ, sinh mệnh
        và xóa toàn bộ trụ/kẻ địch để trò chơi bắt đầu lại từ đầu.
"""
import pygame
import sys
import math
from settings import *
from map import Map, MAP_NAMES
from enemies import WaveManager
from towers import Tower, MagicTower
from ui import UI

pygame.init()
pygame.font.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Kingdom Guardians")
clock = pygame.time.Clock()

ui = UI()

# ── Trạng thái game ──────────────────────────────────────────────────────────
# State machine: MENU → MAP_SELECT → PLAYING / PAUSED / GAMEOVER / VICTORY
state          = "MENU"
selected_map   = 0          # Chỉ số map đang hover trong MAP_SELECT
current_map_idx = 0         # Chỉ số map đã chọn để chơi

game_map     = Map(0)
wave_manager = WaveManager(game_map.paths)

towers  = []
bullets = []
gold    = 100
lives   = 5

# ── Biến trạng thái UI mới ──────────────────────────────────────────────────
selected_build_type = None      # None = Chế độ quan sát, 'archer'/'magic' = Chế độ xây
popup_tower = None              # Tháp đang được chọn để hiển thị popup
game_speed = 1                  # 1x hoặc 2x tốc độ

# ── Hiệu ứng đặt tháp (placement ripple) ─────────────────────────────────────
# Mỗi phần tử: [x, y, timer, max_timer, (r,g,b)]
placement_effects = []
PLACEMENT_DURATION = 22

# ── Hàm tiện ích ─────────────────────────────────────────────────────────────
def place_tower(x, y, tower_class=Tower, cost=50):
    """Đặt tháp tại toạ độ click. Dùng tower_class để hỗ trợ đa hình."""
    global gold
    if not game_map.is_placeable(x, y):
        return
    # v. Tối ưu: chỉ so khoảng cách khi vị trí hợp lệ — dừng sớm khi đã trùng
    snap_x = (x // TILE_SIZE) * TILE_SIZE + TILE_SIZE // 2
    snap_y = (y // TILE_SIZE) * TILE_SIZE + TILE_SIZE // 2
    for t in towers:
        if math.hypot(t.x - snap_x, t.y - snap_y) < TILE_SIZE:
            return
    if gold >= cost:
        gold -= cost
        towers.append(tower_class(x, y))
        # Màu ripple: vàng cho Archer, tím cho MagicTower
        color = (200, 100, 255) if tower_class is MagicTower else (255, 215, 0)
        placement_effects.append([snap_x, snap_y, PLACEMENT_DURATION, PLACEMENT_DURATION, color])

# (Đã xoá upgrade_tower() cũ, logic giờ nằm trong sự kiện click của popup)

def reset_game(map_idx=None):
    global gold, lives, towers, bullets, wave_manager, game_map, placement_effects
    global current_map_idx, popup_tower, game_speed, selected_build_type
    global bg_surface, old_rects
    if map_idx is not None:
        current_map_idx = map_idx
    gold    = 100
    lives   = 5
    towers  = []
    bullets = []
    placement_effects = []
    game_map          = Map(current_map_idx)
    wave_manager      = WaveManager(game_map.paths)
    popup_tower = None
    game_speed = 1
    selected_build_type = None
    bg_surface = None
    old_rects = []

# ── Vòng lặp chính ───────────────────────────────────────────────────────────
running = True
while running:
    tick = pygame.time.get_ticks()

    # ── Xử lý sự kiện ────────────────────────────────────────────────────────
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # ── MENU ──────────────────────────────────────────────────────────────
        if state == "MENU":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                state = "MAP_SELECT"
                selected_map = 0

        # ── MAP_SELECT ────────────────────────────────────────────────────────
        elif state == "MAP_SELECT":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    state = "MENU"
                elif event.key == pygame.K_LEFT:
                    selected_map = (selected_map - 1) % 3
                elif event.key == pygame.K_RIGHT:
                    selected_map = (selected_map + 1) % 3
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    reset_game(selected_map)
                    state = "PLAYING"

            elif event.type == pygame.MOUSEMOTION:
                # Hover card: cập nhật selected_map theo vị trí chuột
                mx, _ = event.pos
                card_w, gap = 200, 30
                total_w     = 3 * card_w + 2 * gap
                start_x     = (WIDTH - total_w) // 2
                for i in range(3):
                    cx = start_x + i * (card_w + gap)
                    if cx <= mx <= cx + card_w:
                        selected_map = i

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                card_w, gap = 200, 30
                total_w     = 3 * card_w + 2 * gap
                start_x     = (WIDTH - total_w) // 2
                card_y      = 120
                for i in range(3):
                    cx = start_x + i * (card_w + gap)
                    if cx <= mx <= cx + card_w and card_y <= my <= card_y + 280:
                        reset_game(i)
                        state = "PLAYING"
                        break

        # ── PLAYING ───────────────────────────────────────────────────────────
        elif state == "PLAYING":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    state = "PAUSED"
                elif event.key == pygame.K_1:
                    selected_build_type = 'archer' if selected_build_type != 'archer' else None
                elif event.key == pygame.K_2:
                    selected_build_type = 'magic' if selected_build_type != 'magic' else None
                elif event.key == pygame.K_ESCAPE:
                    selected_build_type = None
                    popup_tower = None

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                
                # Check UI rects
                archer_rect, magic_rect = ui.get_tower_selection_rects()
                speed_rect = ui.get_speed_toggle_rect()
                
                if event.button == 1: # Chuột TRÁI
                    if speed_rect.collidepoint(mx, my):
                        game_speed = 2 if game_speed == 1 else 1
                        continue
                        
                    if archer_rect.collidepoint(mx, my):
                        selected_build_type = 'archer' if selected_build_type != 'archer' else None
                        continue
                        
                    if magic_rect.collidepoint(mx, my):
                        selected_build_type = 'magic' if selected_build_type != 'magic' else None
                        continue
                        
                    # Handle popup clicks if active
                    if popup_tower:
                        action_rects = ui.get_tower_popup_rects(popup_tower)
                        up_rect = action_rects[0]
                        sell_rect = action_rects[1]
                        
                        if up_rect.collidepoint(mx, my):
                            if popup_tower.level < 2 and gold >= popup_tower.upgrade_cost:
                                gold -= popup_tower.upgrade_cost
                                popup_tower.upgrade()
                            # Không tắt popup ngay để người chơi thấy đã lên Max Level
                            continue
                        elif sell_rect.collidepoint(mx, my):
                            refund = int(popup_tower.total_gold_spent * 0.7)
                            gold += refund
                            towers.remove(popup_tower)
                            popup_tower = None
                            continue
                        elif len(action_rects) == 3 and action_rects[2].collidepoint(mx, my):
                            modes = ["First", "Nearest", "Strongest", "Weakest"]
                            idx = modes.index(popup_tower.target_mode)
                            popup_tower.target_mode = modes[(idx + 1) % len(modes)]
                            continue
                        else:
                            # Nhấn ra ngoài thì tắt popup
                            popup_tower = None
                            continue

                    # Nếu không click vào UI thì đặt tháp
                    if selected_build_type == 'archer':
                        place_tower(mx, my, Tower, cost=50)
                    elif selected_build_type == 'magic':
                        place_tower(mx, my, MagicTower, cost=80)

                elif event.button == 3: # Chuột PHẢI -> Bật popup nâng cấp/bán, huỷ build mode
                    popup_tower = None # reset if click elsewhere
                    selected_build_type = None # Cancel build mode
                    for t in towers:
                        if math.hypot(t.x - mx, t.y - my) < TILE_SIZE:
                            popup_tower = t
                            break

        # ── PAUSED ────────────────────────────────────────────────────────────
        elif state == "PAUSED":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                state = "PLAYING"

        # ── GAMEOVER / VICTORY ────────────────────────────────────────────────
        elif state in ("GAMEOVER", "VICTORY"):
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    reset_game()
                    state = "PLAYING"
                elif event.key == pygame.K_ESCAPE:
                    state = "MAP_SELECT"
                    selected_map = current_map_idx

    # ── Logic cập nhật (chỉ khi PLAYING) ─────────────────────────────────────
    if state == "PLAYING":
        # Chạy logic n lần tuỳ theo tốc độ
        for _ in range(game_speed):
            gold_earned, escaped = wave_manager.update()
            gold  += gold_earned
            lives -= escaped

            if lives <= 0:
                if state != "GAMEOVER":
                    state = "GAMEOVER"
                    ui.state_timer = 0
                    ui.particles = []

            # v. Đa hình: tower.update() gọi đúng phiên bản Tower / MagicTower
            for tower in towers:
                tower.update(wave_manager, bullets)

            # v. Tối ưu: chỉ giữ đạn còn sống (list comprehension một lần)
            for bullet in bullets:
                bullet.update()
            bullets = [b for b in bullets if b.alive]

            # Sang wave tiếp theo
            if len(wave_manager.enemies) == 0 and wave_manager.enemies_to_spawn == 0:
                if wave_manager.wave >= MAX_WAVES:
                    if state != "VICTORY":
                        state = "VICTORY"
                        ui.state_timer = 0
                        ui.particles = []
                else:
                    wave_manager.wave            += 1
                    wave_manager.enemies_to_spawn = 5 + wave_manager.wave * 2
                    wave_manager.hp_multiplier   += 0.4
                    gold += 50

        # Cập nhật hiệu ứng đặt tháp (không phụ thuộc tốc độ game nhiều, để tránh biến mất quá nhanh)
        for eff in placement_effects:
            eff[2] -= 1
        placement_effects = [e for e in placement_effects if e[2] > 0]

    # ── Render ────────────────────────────────────────────────────────────────
    if state == "MENU":
        ui.draw_menu(screen)
        pygame.display.flip()

    elif state == "MAP_SELECT":
        ui.draw_map_select(screen, selected_map, tick)
        pygame.display.flip()
        
    elif state in ("GAMEOVER", "VICTORY", "PAUSED"):
        game_map.draw(screen)
        for tower in towers: tower.draw(screen)
        wave_manager.draw(screen)
        for bullet in bullets: bullet.draw(screen)
        ui.draw_top_bar(screen, gold, lives, min(wave_manager.wave, MAX_WAVES), MAP_NAMES[current_map_idx])
        if state == "PAUSED": ui.draw_pause(screen)
        elif state == "GAMEOVER": ui.draw_game_over(screen)
        elif state == "VICTORY": ui.draw_victory(screen)
        pygame.display.flip()

    elif state == "PLAYING":
        # Khởi tạo bản đồ tĩnh (Static Background)
        if bg_surface is None:
            bg_surface = pygame.Surface((WIDTH, HEIGHT))
            temp_p = game_map.particles
            game_map.particles = [] # Xoá particle để làm bản đồ tĩnh, tiết kiệm CPU
            game_map.draw(bg_surface)
            game_map.particles = temp_p
            screen.blit(bg_surface, (0, 0))
            pygame.display.flip()
            old_rects = [pygame.Rect(0, 0, WIDTH, HEIGHT)]
            
        # 1. Xoá vùng cũ (Erase)
        for r in old_rects:
            r_clip = r.clip(pygame.Rect(0, 0, WIDTH, HEIGHT))
            screen.blit(bg_surface, r_clip, r_clip)
            
        dirty_rects = []
        
        # 2. Vẽ đối tượng và thu thập Rects
        for tower in towers:
            tower.draw(screen)
            dirty_rects.append(pygame.Rect(tower.x - 40, tower.y - 60, 80, 100))
            
        wave_manager.draw(screen)
        for e in wave_manager.enemies:
            dirty_rects.append(pygame.Rect(e.x - 30, e.y - 40, 60, 70))
        for d in wave_manager.dying_enemies:
            dirty_rects.append(pygame.Rect(d.x - 30, d.y - 40, 60, 70))
            
        for bullet in bullets:
            bullet.draw(screen)
            rs = bullet.aoe_radius if bullet.b_type == "aoe" else 15
            dirty_rects.append(pygame.Rect(bullet.x - rs - 10, bullet.y - rs - 10, rs*2 + 20, rs*2 + 20))
            if bullet.exploding:
                dirty_rects.append(pygame.Rect(bullet.explode_x - rs - 10, bullet.explode_y - rs - 10, rs*2 + 20, rs*2 + 20))
                
        ui.draw_placement_effect(screen, placement_effects)
        for eff in placement_effects:
            r = int(28 * (1.0 - eff[2]/eff[3])) + 5
            dirty_rects.append(pygame.Rect(eff[0] - r, eff[1] - r, r*2, r*2))
            
        ui.draw_top_bar(screen, gold, lives, min(wave_manager.wave, MAX_WAVES), MAP_NAMES[current_map_idx])
        dirty_rects.append(pygame.Rect(0, 0, WIDTH, 50))
        
        ui.draw_tower_selection(screen, selected_build_type)
        dirty_rects.append(pygame.Rect(WIDTH//2 - 90, HEIGHT - 90, 180, 90))
        
        ui.draw_speed_toggle(screen, game_speed)
        dirty_rects.append(pygame.Rect(WIDTH - 80, HEIGHT - 60, 70, 50))
        
        if popup_tower:
            ui.draw_tower_popup(screen, popup_tower)
            dirty_rects.append(pygame.Rect(popup_tower.x, popup_tower.y - 45, 160, 140))
            
        if not popup_tower and selected_build_type is not None:
            mx, my = pygame.mouse.get_pos()
            if 40 < my < HEIGHT - 80:
                snap_x = (mx // TILE_SIZE) * TILE_SIZE + TILE_SIZE // 2
                snap_y = (my // TILE_SIZE) * TILE_SIZE + TILE_SIZE // 2
                is_valid = game_map.is_placeable(snap_x, snap_y)
                for t in towers:
                    if math.hypot(t.x - snap_x, t.y - snap_y) < TILE_SIZE:
                        is_valid = False; break
                if gold < (50 if selected_build_type == 'archer' else 80): is_valid = False
                radius = Tower(0,0).range if selected_build_type == 'archer' else MagicTower(0,0).range
                ui.draw_hover_preview(screen, snap_x, snap_y, radius, is_valid)
                dirty_rects.append(pygame.Rect(snap_x - radius - 5, snap_y - radius - 5, radius*2 + 10, radius*2 + 10))
                
        # 3. Cập nhật Dirty Rects
        all_dirty = dirty_rects + old_rects
        pygame.display.update(all_dirty)
        old_rects = dirty_rects.copy()
        
        clock.tick(FPS)
        continue
    clock.tick(FPS)

pygame.quit()
sys.exit()
