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
from audio import init_audio, play_sound

pygame.init()
pygame.font.init()
init_audio()

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

game_particles = []
screen_shake = 0
transition_alpha = 0
transition_state = None
transition_step = 0
transition_map_idx = None
render_surface = pygame.Surface((WIDTH, HEIGHT))

def change_state(new_state, do_reset_idx=None):
    global transition_state, transition_step, transition_map_idx
    transition_state = new_state
    transition_step = 1
    transition_map_idx = do_reset_idx

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
        play_sound("build")
        import random
        for _ in range(15):
            l = random.randint(15,30)
            game_particles.append([snap_x, snap_y, random.uniform(-4,4), random.uniform(-4,4), l, l, color])

# (Đã xoá upgrade_tower() cũ, logic giờ nằm trong sự kiện click của popup)

def reset_game(map_idx=None):
    global gold, lives, towers, bullets, wave_manager, game_map, placement_effects
    global current_map_idx, popup_tower, game_speed, selected_build_type
    global bg_surface, old_rects, game_particles
    if map_idx is not None:
        current_map_idx = map_idx
    gold    = 150
    lives   = 5
    towers  = []
    bullets = []
    placement_effects = []
    game_particles = []
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
            
        if transition_step != 0:
            continue

        # ── MENU ──────────────────────────────────────────────────────────────
        if state == "MENU":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                play_sound("click")
                change_state("MAP_SELECT")
                selected_map = 0

        # ── MAP_SELECT ────────────────────────────────────────────────────────
        elif state == "MAP_SELECT":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    play_sound("click")
                    change_state("MENU")
                elif event.key == pygame.K_LEFT:
                    play_sound("click")
                    selected_map = (selected_map - 1) % 3
                elif event.key == pygame.K_RIGHT:
                    play_sound("click")
                    selected_map = (selected_map + 1) % 3
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    play_sound("click")
                    change_state("PLAYING", do_reset_idx=selected_map)

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
                        play_sound("click")
                        change_state("PLAYING", do_reset_idx=i)
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
                        play_sound("click")
                        game_speed = 2 if game_speed == 1 else 1
                        continue
                        
                    if archer_rect.collidepoint(mx, my):
                        play_sound("click")
                        selected_build_type = 'archer' if selected_build_type != 'archer' else None
                        continue
                        
                    if magic_rect.collidepoint(mx, my):
                        play_sound("click")
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
                                play_sound("build")
                            # Không tắt popup ngay để người chơi thấy đã lên Max Level
                            continue
                        elif sell_rect.collidepoint(mx, my):
                            refund = int(popup_tower.total_gold_spent * 0.7)
                            gold += refund
                            towers.remove(popup_tower)
                            popup_tower = None
                            play_sound("click")
                            continue
                        elif len(action_rects) == 3 and action_rects[2].collidepoint(mx, my):
                            modes = ["First", "Nearest", "Strongest", "Weakest"]
                            idx = modes.index(popup_tower.target_mode)
                            popup_tower.target_mode = modes[(idx + 1) % len(modes)]
                            play_sound("click")
                            continue
                        else:
                            # Nhấn ra ngoài thì tắt popup
                            popup_tower = None
                            continue

                    # Nếu không click vào UI thì đặt tháp
                    if selected_build_type == 'archer':
                        place_tower(mx, my, Tower, cost=65)
                    elif selected_build_type == 'magic':
                        place_tower(mx, my, MagicTower, cost=110)

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
                    change_state("PLAYING", do_reset_idx=current_map_idx)
                elif event.key == pygame.K_ESCAPE:
                    change_state("MAP_SELECT")

    # ── Logic cập nhật (chỉ khi PLAYING) ─────────────────────────────────────
    if state == "PLAYING":
        # Chạy logic n lần tuỳ theo tốc độ
        for _ in range(game_speed):
            gold_earned, escaped, newly_dead = wave_manager.update()
            gold  += gold_earned
            lives -= escaped
            
            import random
            for d in newly_dead:
                for _ in range(random.randint(8, 12)):
                    vx = random.uniform(-3, 3)
                    vy = random.uniform(-3, 3)
                    life = random.randint(20, 40)
                    game_particles.append([d.x, d.y, vx, vy, life, life, (150, 40, 20)])

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
                was_exploding = getattr(bullet, 'exploding', False)
                was_alive = bullet.alive
                bullet.update()
                is_exploding = getattr(bullet, 'exploding', False)
                if not bullet.alive and was_alive and not is_exploding and bullet.b_type != "aoe":
                    import math
                    for _ in range(random.randint(3, 5)):
                        ang = math.radians(bullet.angle) + random.uniform(-0.5, 0.5) + math.pi
                        spd = random.uniform(2, 5)
                        vx = math.cos(ang) * spd
                        vy = math.sin(ang) * spd
                        c = (200,200,200) if bullet.b_type == "arrow" else (100,200,255)
                        l = random.randint(10,20)
                        game_particles.append([bullet.x, bullet.y, vx, vy, l, l, c])
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
        
        for p in game_particles:
            p[0] += p[2]
            p[1] += p[3]
            p[4] -= 1
        game_particles = [p for p in game_particles if p[4] > 0]

    # ── Render ────────────────────────────────────────────────────────────────
    if state == "MENU":
        ui.draw_menu(screen)

    elif state == "MAP_SELECT":
        ui.draw_map_select(screen, selected_map, tick)
        
    elif state in ("GAMEOVER", "VICTORY", "PAUSED"):
        game_map.draw(screen)
        drawables = []
        for t in towers: drawables.append(('tower', t, t.y))
        for e in wave_manager.enemies: drawables.append(('enemy', e, e.y))
        for d in wave_manager.dying_enemies: drawables.append(('dying', d, d.y))
        drawables.sort(key=lambda item: item[2])
        for dtype, obj, _ in drawables:
            if dtype == 'tower': obj.draw(screen)
            elif dtype == 'enemy': obj.draw(screen)
            elif dtype == 'dying': obj.draw(screen, is_dying=True)
        for bullet in bullets: bullet.draw(screen)
        ui.draw_top_bar(screen, gold, lives, min(wave_manager.wave, MAX_WAVES), MAP_NAMES[current_map_idx])
        if state == "PAUSED": ui.draw_pause(screen)
        elif state == "GAMEOVER": ui.draw_game_over(screen)
        elif state == "VICTORY": ui.draw_victory(screen)

    elif state == "PLAYING":
        # Khởi tạo bản đồ tĩnh (Static Background)
        if bg_surface is None:
            bg_surface = pygame.Surface((WIDTH, HEIGHT))
            temp_p = game_map.particles
            game_map.particles = [] # Xoá particle để làm bản đồ tĩnh, tiết kiệm CPU
            game_map.draw(bg_surface)
            game_map.particles = temp_p
            render_surface.blit(bg_surface, (0, 0))
            screen.blit(bg_surface, (0, 0))
            pygame.display.flip()
            old_rects = [pygame.Rect(0, 0, WIDTH, HEIGHT)]
            
        shake_dx, shake_dy = 0, 0
        if screen_shake > 0:
            import math
            screen_shake -= 1
            shake_dx = int(math.sin(pygame.time.get_ticks() * 0.05) * 5)
            shake_dy = int(math.cos(pygame.time.get_ticks() * 0.04) * 5)
            
        # 1. Xoá vùng cũ (Erase)
        for r in old_rects:
            r_clip = r.clip(pygame.Rect(0, 0, WIDTH, HEIGHT))
            render_surface.blit(bg_surface, r_clip, r_clip)
            
        dirty_rects = []
        
        # 2. Vẽ đối tượng và thu thập Rects (Sắp xếp theo Y để không bị xuyên)
        drawables = []
        for tower in towers: drawables.append(('tower', tower, tower.y))
        for e in wave_manager.enemies: drawables.append(('enemy', e, e.y))
        for d in wave_manager.dying_enemies: drawables.append(('dying', d, d.y))
        drawables.sort(key=lambda item: item[2])
        
        for dtype, obj, _ in drawables:
            if dtype == 'tower':
                obj.draw(render_surface)
                dirty_rects.append(pygame.Rect(obj.x - 40, obj.y - 60, 80, 100))
            elif dtype == 'enemy':
                obj.draw(render_surface)
                if getattr(obj, 'enemy_type', '') == 'tank':
                    dirty_rects.append(pygame.Rect(obj.x - 50, obj.y - 60, 100, 110))
                else:
                    dirty_rects.append(pygame.Rect(obj.x - 35, obj.y - 45, 70, 80))
            elif dtype == 'dying':
                obj.draw(render_surface, is_dying=True)
                if getattr(obj, 'enemy_type', '') == 'tank':
                    dirty_rects.append(pygame.Rect(obj.x - 60, obj.y - 70, 120, 130))
                else:
                    dirty_rects.append(pygame.Rect(obj.x - 45, obj.y - 55, 90, 100))
            
        for bullet in bullets:
            bullet.draw(render_surface)
            rs = bullet.aoe_radius if bullet.b_type == "aoe" else 15
            dirty_rects.append(pygame.Rect(bullet.x - rs - 10, bullet.y - rs - 10, rs*2 + 20, rs*2 + 20))
            if bullet.exploding:
                dirty_rects.append(pygame.Rect(bullet.explode_x - rs - 10, bullet.explode_y - rs - 10, rs*2 + 20, rs*2 + 20))
                
        ui.draw_placement_effect(render_surface, placement_effects)
        for eff in placement_effects:
            r = int(28 * (1.0 - eff[2]/eff[3])) + 5
            dirty_rects.append(pygame.Rect(eff[0] - r, eff[1] - r, r*2, r*2))
            
        for p in game_particles:
            x_p, y_p, vx, vy, life, max_life, color = p
            alpha = max(0, min(255, int(255 * (life / max_life))))
            radius = max(1, int(3 * (life / max_life)))
            if radius > 0:
                s = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*color, alpha), (radius, radius), radius)
                render_surface.blit(s, (int(x_p) - radius, int(y_p) - radius))
                dirty_rects.append(pygame.Rect(int(x_p) - radius - 2, int(y_p) - radius - 2, radius*2 + 4, radius*2 + 4))
            
        ui.draw_top_bar(render_surface, gold, lives, min(wave_manager.wave, MAX_WAVES), MAP_NAMES[current_map_idx])
        dirty_rects.append(pygame.Rect(0, 0, WIDTH, 50))
        
        ui.draw_tower_selection(render_surface, selected_build_type)
        dirty_rects.append(pygame.Rect(WIDTH//2 - 90, HEIGHT - 90, 180, 90))
        
        ui.draw_speed_toggle(render_surface, game_speed)
        dirty_rects.append(pygame.Rect(WIDTH - 80, HEIGHT - 60, 70, 50))
        
        if popup_tower:
            ui.draw_tower_popup(render_surface, popup_tower)
            dirty_rects.append(pygame.Rect(popup_tower.x, popup_tower.y - 75, 180, 160))
            
        if not popup_tower and selected_build_type is not None:
            mx, my = pygame.mouse.get_pos()
            if 40 < my < HEIGHT - 80:
                snap_x = (mx // TILE_SIZE) * TILE_SIZE + TILE_SIZE // 2
                snap_y = (my // TILE_SIZE) * TILE_SIZE + TILE_SIZE // 2
                is_valid = game_map.is_placeable(snap_x, snap_y)
                for t in towers:
                    if math.hypot(t.x - snap_x, t.y - snap_y) < TILE_SIZE:
                        is_valid = False; break
                if gold < (65 if selected_build_type == 'archer' else 110): is_valid = False
                radius = Tower(0,0).range if selected_build_type == 'archer' else MagicTower(0,0).range
                ui.draw_hover_preview(render_surface, snap_x, snap_y, radius, is_valid)
                dirty_rects.append(pygame.Rect(snap_x - radius - 5, snap_y - radius - 5, radius*2 + 10, radius*2 + 10))
                
        # 3. Cập nhật Dirty Rects
        all_dirty = dirty_rects + old_rects
        old_rects = dirty_rects.copy()
        
        screen.fill(BLACK)
        screen.blit(render_surface, (shake_dx, shake_dy))

    if transition_step == 1:
        transition_alpha += 15
        if transition_alpha >= 255:
            transition_alpha = 255
            state = transition_state
            if transition_map_idx is not None:
                reset_game(transition_map_idx)
            transition_step = -1
    elif transition_step == -1:
        transition_alpha -= 15
        if transition_alpha <= 0:
            transition_alpha = 0
            transition_step = 0

    if transition_alpha > 0:
        s = pygame.Surface((WIDTH, HEIGHT))
        s.fill((0, 0, 0))
        s.set_alpha(transition_alpha)
        screen.blit(s, (0, 0))

    if state != "PLAYING" or transition_alpha > 0 or screen_shake > 0:
        pygame.display.flip()
    elif state == "PLAYING":
        for r in all_dirty:
            r_clip = r.clip(pygame.Rect(0, 0, WIDTH, HEIGHT))
            screen.blit(render_surface, r_clip, r_clip)
        pygame.display.update(all_dirty)

    clock.tick(FPS)

pygame.quit()
sys.exit()
