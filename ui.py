"""
Mô-đun giao diện người dùng (UI) của trò chơi Kingdom Guardians.

Mô-đun này tập trung toàn bộ logic hiển thị giao diện, tách biệt hoàn toàn
với logic gameplay để đảm bảo nguyên tắc Single Responsibility.

Điểm nhấn đồ họa (Đã được đại tu):
    - Toàn bộ giao diện áp dụng phong cách gỗ sồi (Wood grain) nẹp viền Vàng hoàng gia.
    - Bảng thông tin tháp có đóng đinh tán (Rivets), thiết kế hộp chìm 3D đẹp mắt.
    - Card chọn bản đồ có hiệu ứng nhịp tim (Pulse) mượt mà khi hover chuột.

Lớp:
    UI: Quản lý và vẽ mọi thành phần giao diện. Gồm các phương thức:
        draw_top_bar()         : Thanh thông tin trên cùng (gỗ/vàng) — vàng, mạng, wave.
        draw_menu()            : Màn hình tiêu đề khởi động.
        draw_map_select()      : Màn hình chọn bản đồ với 3 card thumbnail có hiệu ứng pulse.
        draw_tower_selection() : Thanh chọn tháp gỗ nổi ở mép dưới màn hình.
        draw_tower_popup()     : Bảng nâng cấp/bán/chỉnh mục tiêu hiện trên đầu tháp.
        draw_placement_effect(): Vẽ vòng tròn định vị khi chuẩn bị đặt tháp.
        draw_pause()           : Overlay bán trong suốt khi tạm dừng.
"""
import pygame
from settings import *
from map import MAP_NAMES, MAP_THEMES

class UI:
    """Quản lý toàn bộ giao diện người dùng: top bar, menu, map select, overlay."""

    def __init__(self):
        pygame.font.init()
        # Chỉ sử dụng 'georgia' để đảm bảo Pygame không bị lỗi render font mặc định xấu xí
        font_name = 'georgia'
        self.font       = pygame.font.SysFont(font_name, 20, bold=True)
        self.big_font   = pygame.font.SysFont(font_name, 48, bold=True)
        self.small_font = pygame.font.SysFont(font_name, 16)
        self.title_font = pygame.font.SysFont(font_name, 28, bold=True)
        
        # Biến trạng thái cho hiệu ứng GameOver / Victory
        self.state_timer = 0
        self.particles = []

        # Tải hình ảnh UI
        self.images = {}
        import os
        img_dir = "assets/images"
        if os.path.exists(img_dir):
            if os.path.exists(os.path.join(img_dir, "menu_bg.png")):
                img = pygame.image.load(os.path.join(img_dir, "menu_bg.png")).convert_alpha()
                self.images["menu_bg"] = pygame.transform.scale(img, (WIDTH, HEIGHT))
            for i in range(1, 4):
                name = f"map{i}_full.png"
                if os.path.exists(os.path.join(img_dir, name)):
                    img = pygame.image.load(os.path.join(img_dir, name)).convert_alpha()
                    self.images[f"map{i}"] = pygame.transform.scale(img, (180, 130))

    # ── Top bar trong trận ───────────────────────────────────────────────────
    def draw_top_bar(self, screen, gold, lives, wave, map_name=""):
        bar_height = 40
        panel_rect = pygame.Rect(0, 0, WIDTH, bar_height)
        # Nền gỗ đậm
        pygame.draw.rect(screen, (40, 25, 15), panel_rect)
        # Vân gỗ ngang dọc
        for i in range(10, WIDTH, 40):
            pygame.draw.line(screen, (60, 40, 25), (i, 4), (i, bar_height-4), 2)
        # Viền vàng hoàng gia
        pygame.draw.rect(screen, (200, 160, 50), panel_rect, 3)
        pygame.draw.line(screen, (255, 220, 100), (0, 2), (WIDTH, 2), 1)

        # Tên bản đồ (Góc trái)
        title_text = self.font.render(map_name.upper() if map_name else "KINGDOM GUARDIANS", True, WHITE)
        screen.blit(title_text, (20, 8))

        # Vàng (Gold) - Đặt cố định tọa độ X để không bị đẩy lệch
        gx = 220
        pygame.draw.circle(screen, GOLD_COLOR, (gx, 20), 10)
        pygame.draw.circle(screen, WHITE,      (gx + 2, 18),  3)
        screen.blit(self.font.render(str(gold), True, GOLD_COLOR), (gx + 16, 8))

        # Wave - Căn giữa cố định ở tọa độ X = 400
        wave_txt = self.font.render(f"WAVE {wave}/{MAX_WAVES}", True, WHITE)
        screen.blit(wave_txt, (WIDTH // 2 - wave_txt.get_width() // 2, 8))

        # Mạng sống (Lives) - Đặt cố định góc phải
        hx = WIDTH - 120
        pygame.draw.polygon(screen, RED, [(hx, 26), (hx-8, 16), (hx+8, 16)])
        pygame.draw.circle(screen, RED, (hx-4, 16), 5)
        pygame.draw.circle(screen, RED, (hx+4, 16), 5)
        screen.blit(self.font.render(str(lives), True, RED), (hx + 12, 8))

        # Hướng dẫn (Góc phải trên cùng, chỉ để Pause cho gọn)
        inst = self.small_font.render("P: Pause", True, (200,200,200))
        screen.blit(inst, (WIDTH - inst.get_width() - 15, 12))

    # ── Màn hình chính ────────────────────────────────────────────────────────
    def draw_menu(self, screen, tick=None):
        if tick is None:
            tick = pygame.time.get_ticks()
            
        import math, random
        if "menu_bg" in self.images:
            screen.blit(self.images["menu_bg"], (0, 0))
        else:
            screen.fill((100, 180, 250))

        # Hạt đom đóm
        if not hasattr(self, 'menu_particles') or len(self.menu_particles) < 30:
            self.menu_particles = [[random.randint(0, WIDTH), random.randint(HEIGHT//2, HEIGHT), 
                                    random.uniform(-1, 1), random.uniform(-1, 1)] for _ in range(30)]
        for p in self.menu_particles:
            p[0] += p[2] + math.sin(tick*0.001 + p[1])*0.5
            p[1] += p[3]
            if p[0] < 0: p[0] = WIDTH
            if p[0] > WIDTH: p[0] = 0
            if p[1] < HEIGHT//2: p[1] = HEIGHT
            if p[1] > HEIGHT: p[1] = HEIGHT//2
            a = int(155 + 100 * math.sin(tick*0.005 + p[0]))
            pygame.draw.circle(screen, (200, 255, 100, max(0, min(255, a))), (int(p[0]), int(p[1])), 2)

        # Logo có viền dày và đổ bóng
        title_txt = "KINGDOM GUARDIANS"
        title = self.big_font.render(title_txt, True, GOLD_COLOR)
        bob_y = math.sin(tick * 0.003) * 10
        tx = WIDTH//2 - title.get_width()//2
        ty = HEIGHT//2 - 100 + bob_y
        
        # Outline 8 hướng
        for ox, oy in [(-2,0),(2,0),(0,-2),(0,2),(-2,-2),(2,-2),(-2,2),(2,2)]:
            screen.blit(self.big_font.render(title_txt, True, (40, 20, 10)), (tx+ox, ty+oy))
        # Bóng đổ sâu
        screen.blit(self.big_font.render(title_txt, True, (0, 0, 0)), (tx+4, ty+8))
        screen.blit(title, (tx, ty))

        # Nút Start nhấp nháy
        sub_txt = "Press SPACE to Select Map"
        sub = self.font.render(sub_txt, True, WHITE)
        alpha = int(180 + 75 * math.sin(tick * 0.005))
        s_rect = pygame.Rect(WIDTH//2 - sub.get_width()//2 - 20, HEIGHT//2 + 40, sub.get_width() + 40, 46)
        
        s = pygame.Surface((s_rect.w, s_rect.h), pygame.SRCALPHA)
        pygame.draw.rect(s, (0, 0, 0, 150), (0, 0, s_rect.w, s_rect.h), border_radius=8)
        pygame.draw.rect(s, (255, 215, 0, alpha), (0, 0, s_rect.w, s_rect.h), 2, border_radius=8)
        screen.blit(s, s_rect.topleft)
        screen.blit(sub, (WIDTH//2 - sub.get_width()//2, HEIGHT//2 + 50))

    # ── Màn hình chọn bản đồ ────────────────────────────────────────────────
    def draw_map_select(self, screen, selected_index, tick):
        """
        Vẽ màn hình lựa chọn bản đồ với 3 card nằm ngang.
        selected_index: chỉ số map đang hover/chọn (0/1/2).
        tick: pygame.time.get_ticks() để tạo hiệu ứng nhịp.
        """
        screen.fill((20, 18, 30))

        # Tiêu đề
        title = self.big_font.render("SELECT MAP", True, GOLD_COLOR)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 30))

        sub = self.small_font.render("Click a map to start  |  ESC: Back to Menu", True, (180,180,180))
        screen.blit(sub, (WIDTH//2 - sub.get_width()//2, 90))

        # 3 card bản đồ
        card_w, card_h = 200, 280
        gap = 30
        total_w = 3 * card_w + 2 * gap
        start_x = (WIDTH - total_w) // 2
        card_y   = 120

        themes = MAP_THEMES
        descs = [
            ["Classic straight path", "Good for beginners", "3 sharp corners"],
            ["Long zigzag route", "Maximum tower slots", "Watch the flanks!"],
            ["Tight spiral maze", "Enemies travel far", "AoE towers shine"],
        ]

        for i in range(3):
            cx = start_x + i * (card_w + gap)
            is_sel = (i == selected_index)

            # Hiệu ứng nhịp nhẹ khi được chọn
            pulse = int(4 * abs(__import__('math').sin(tick * 0.003))) if is_sel else 0

            # Viền phát sáng nếu được chọn
            border_col = GOLD_COLOR if is_sel else (80, 80, 100)
            border_w   = 3 if is_sel else 2

            # Nền card (Gỗ sồi sẫm)
            card_rect = pygame.Rect(cx - pulse, card_y - pulse, card_w + pulse*2, card_h + pulse*2)
            pygame.draw.rect(screen, (50, 35, 20), card_rect, border_radius=12)
            # Vân gỗ nhẹ
            pygame.draw.rect(screen, (60, 45, 25), (card_rect.x+10, card_rect.y+10, card_rect.w-20, card_rect.h-20), border_radius=8)
            # Giấy da bên trong
            pygame.draw.rect(screen, (230, 215, 180), (card_rect.x+15, card_rect.y+150, card_rect.w-30, card_rect.h-165), border_radius=6)
            # Đinh tán (Rivets) 4 góc
            for rx, ry in [(card_rect.x+6, card_rect.y+6), (card_rect.right-6, card_rect.y+6), 
                           (card_rect.x+6, card_rect.bottom-6), (card_rect.right-6, card_rect.bottom-6)]:
                pygame.draw.circle(screen, (30,30,30), (rx, ry), 4)
                pygame.draw.circle(screen, (100,100,100), (rx-1, ry-1), 2)
            # Viền vàng nếu chọn
            pygame.draw.rect(screen, border_col, card_rect, border_w, border_radius=12)

            # Thumbnail mini-map
            thumb_w = card_w - 20
            thumb_h = 130
            thumb_x = cx - pulse + 10
            thumb_y = card_y - pulse + 15
            
            img_key = f"map{i+1}"
            if img_key in self.images:
                # Nếu ảnh tồn tại, blit ảnh (ảnh đã scale 180x130 trong init)
                # Dùng một surface tạm có border radius để mask ảnh nếu cần, hoặc đơn giản vẽ border lên trên
                screen.blit(self.images[img_key], (thumb_x, thumb_y))
                pygame.draw.rect(screen, (30, 20, 10), (thumb_x, thumb_y, thumb_w, thumb_h), 3, border_radius=6)
            else:
                # Fallback: vẽ grid thô như cũ nếu không có ảnh
                th      = themes[i]
                pygame.draw.rect(screen, th["grass_l"],
                                 (thumb_x, thumb_y, thumb_w, thumb_h), border_radius=6)
                from map import ALL_LEVELS
                grid   = ALL_LEVELS[i]
                grid_h = len(grid)
                grid_w = len(grid[0])
                cell_w = thumb_w / grid_w
                cell_h = thumb_h / grid_h
                for r in range(grid_h):
                    for c in range(grid_w):
                        t = grid[r][c]
                        rx = int(thumb_x + c * cell_w)
                        ry = int(thumb_y + r * cell_h)
                        rw = max(1, int(cell_w))
                        rh = max(1, int(cell_h))
                        if t in (0, 2, 3):
                            pygame.draw.rect(screen, th["dirt"], (rx, ry, rw, rh))
                        if t == 2:
                            pygame.draw.circle(screen, GREEN, (rx+rw//2, ry+rh//2), 4)
                        if t == 3:
                            pygame.draw.circle(screen, RED,   (rx+rw//2, ry+rh//2), 4)

            # Tên bản đồ
            name_surf = self.title_font.render(MAP_NAMES[i], True, (40, 20, 10))
            ny = card_y - pulse + thumb_h + 22
            screen.blit(name_surf, (cx - pulse + (card_w - name_surf.get_width())//2, ny))

            # Mô tả (Chữ tối trên giấy da)
            for j, line in enumerate(descs[i]):
                ls = self.small_font.render(line, True, (80, 50, 30))
                screen.blit(ls, (cx - pulse + (card_w - ls.get_width())//2, ny + 34 + j*20))

            # Số map
            num_surf = self.font.render(f"MAP {i+1}", True, (150, 40, 20) if is_sel else (100, 80, 60))
            screen.blit(num_surf, (cx - pulse + (card_w - num_surf.get_width())//2,
                                   card_y - pulse + card_h - 26))

    # ── Hiệu ứng đặt tháp (placement ripple) ────────────────────────────────
    def draw_placement_effect(self, screen, effects):
        """
        Vẽ hiệu ứng vòng lan khi đặt tháp mới.
        effects: list of [x, y, timer, max_timer, color]
        """
        for eff in effects:
            x, y, timer, max_t, color = eff
            progress = 1.0 - timer / max_t
            radius   = int(28 * progress)
            alpha    = int(220 * (timer / max_t))
            if radius > 0:
                s = pygame.Surface((radius*2+4, radius*2+4), pygame.SRCALPHA)
                r2, g2, b2 = color
                pygame.draw.circle(s, (r2, g2, b2, alpha//3), (radius+2, radius+2), radius)
                pygame.draw.circle(s, (r2, g2, b2, alpha),    (radius+2, radius+2), radius, 3)
                screen.blit(s, (x - radius - 2, y - radius - 2))

    # ── Overlay màn hình ─────────────────────────────────────────────────────
    def draw_pause(self, screen):
        overlay = pygame.Surface((WIDTH, HEIGHT)); overlay.set_alpha(150)
        overlay.fill(BLACK); screen.blit(overlay, (0,0))
        self._centered(screen, self.big_font, "PAUSED",            GOLD_COLOR, -30)
        self._centered(screen, self.font,     "Press P to Resume", WHITE,       30)

    def draw_game_over(self, screen):
        self.state_timer += 1
        alpha = min(180, self.state_timer * 2)
        overlay = pygame.Surface((WIDTH, HEIGHT)); overlay.set_alpha(alpha)
        overlay.fill(BLACK); screen.blit(overlay, (0,0))
        
        import random
        # Mưa tro rơi
        if self.state_timer % 3 == 0:
            self.particles.append([random.randint(0, WIDTH), -10, random.uniform(-1, 1), random.uniform(2, 5)])
            
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            pygame.draw.circle(screen, (100, 100, 100), (int(p[0]), int(p[1])), 2)
            
        self.particles = [p for p in self.particles if p[1] < HEIGHT]
        
        if self.state_timer > 60:
            self._centered(screen, self.big_font, "DEFEAT!", RED, -30)
            self._centered(screen, self.font, "The kingdom has fallen. SPACE = Retry", WHITE, 30)

    def draw_victory(self, screen):
        self.state_timer += 1
        alpha = min(200, self.state_timer * 2)
        overlay = pygame.Surface((WIDTH, HEIGHT)); overlay.set_alpha(alpha)
        overlay.fill((30,20,10)); screen.blit(overlay, (0,0))
        
        import random, math
        # Pháo hoa
        if random.random() < 0.1:
            cx, cy = random.randint(100, WIDTH-100), random.randint(50, HEIGHT//2)
            color = random.choice([GOLD_COLOR, (100,255,100), (100,100,255), (255,100,100), (255,150,255)])
            for _ in range(25):
                ang = random.uniform(0, math.pi*2)
                spd = random.uniform(1, 4)
                self.particles.append([cx, cy, math.cos(ang)*spd, math.sin(ang)*spd, color, random.randint(20, 40)])
                
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.05 # trọng lực
            p[5] -= 1    # thời gian sống
            if p[5] > 0:
                pygame.draw.circle(screen, p[4], (int(p[0]), int(p[1])), max(1, p[5]//10))
                
        self.particles = [p for p in self.particles if p[5] > 0]
        
        if self.state_timer > 60:
            self._centered(screen, self.big_font, "VICTORY!", GOLD_COLOR, -30)
            self._centered(screen, self.font, "Realm secured! SPACE = Play Again", WHITE, 30)

    # ── Helper ───────────────────────────────────────────────────────────────
    def _centered(self, screen, font, text, color, y_offset=0):
        surf = font.render(text, True, color)
        screen.blit(surf, (WIDTH//2 - surf.get_width()//2, HEIGHT//2 + y_offset))

    # ── Tower Selection ───────────────────────────────────────────────────────
    def get_tower_selection_rects(self):
        bar_w = 160
        bar_h = 70
        start_x = WIDTH // 2 - bar_w // 2
        start_y = HEIGHT - bar_h - 10
        return pygame.Rect(start_x + 10, start_y + 10, 60, 50), \
               pygame.Rect(start_x + 80, start_y + 10, 60, 50)

    def draw_tower_selection(self, screen, selected_type):
        bar_w = 160
        bar_h = 70
        start_x = WIDTH // 2 - bar_w // 2
        start_y = HEIGHT - bar_h - 10
        
        rect = pygame.Rect(start_x, start_y, bar_w, bar_h)
        # Nền gỗ cho bảng chọn tháp
        pygame.draw.rect(screen, (50, 35, 20), rect, border_radius=8)
        for i in range(10, bar_w-10, 25):
            pygame.draw.line(screen, (30, 20, 10), (start_x + i, start_y + 4), (start_x + i, start_y + bar_h - 4), 2)
        # Viền vàng bọc quanh
        pygame.draw.rect(screen, (200, 160, 50), rect, 4, border_radius=8)
        pygame.draw.rect(screen, (255, 220, 100), rect, 1, border_radius=8)
        
        # Hướng dẫn thao tác đặt tháp được đưa xuống đây để thanh trên cùng gọn gàng
        inst_txt = self.small_font.render("1/2: Select Tower   |   Right-Click: Cancel / Menu", True, (220, 220, 220))
        screen.blit(inst_txt, (WIDTH // 2 - inst_txt.get_width() // 2, start_y - 25))
        
        archer_rect, magic_rect = self.get_tower_selection_rects()
        
        # Draw Archer box
        a_col = (80, 80, 80) if selected_type == 'archer' else (50, 50, 50)
        pygame.draw.rect(screen, a_col, archer_rect, border_radius=5)
        if selected_type == 'archer':
            pygame.draw.rect(screen, GOLD_COLOR, archer_rect, 2, border_radius=5)
        t1 = self.small_font.render("Archer", True, WHITE)
        t1c = self.small_font.render("65 Gold", True, GOLD_COLOR)
        screen.blit(t1, (archer_rect.x + 30 - t1.get_width()//2, archer_rect.y + 5))
        screen.blit(t1c, (archer_rect.x + 30 - t1c.get_width()//2, archer_rect.y + 25))
        
        # Draw Magic box
        m_col = (80, 80, 80) if selected_type == 'magic' else (50, 50, 50)
        pygame.draw.rect(screen, m_col, magic_rect, border_radius=5)
        if selected_type == 'magic':
            pygame.draw.rect(screen, GOLD_COLOR, magic_rect, 2, border_radius=5)
        t2 = self.small_font.render("Magic", True, WHITE)
        t2c = self.small_font.render("110 Gold", True, GOLD_COLOR)
        screen.blit(t2, (magic_rect.x + 30 - t2.get_width()//2, magic_rect.y + 5))
        screen.blit(t2c, (magic_rect.x + 30 - t2c.get_width()//2, magic_rect.y + 25))

    # ── Speed Toggle ──────────────────────────────────────────────────────────
    def get_speed_toggle_rect(self):
        return pygame.Rect(WIDTH - 70, HEIGHT - 50, 50, 30)

    def draw_speed_toggle(self, screen, speed):
        rect = self.get_speed_toggle_rect()
        pygame.draw.rect(screen, (60, 60, 80), rect, border_radius=5)
        pygame.draw.rect(screen, WHITE, rect, 2, border_radius=5)
        text = self.small_font.render(f"{speed}x", True, WHITE)
        screen.blit(text, (rect.x + (rect.w - text.get_width())//2, rect.y + 5))

    # ── Hover Preview ─────────────────────────────────────────────────────────
    def draw_hover_preview(self, screen, x, y, range_radius, is_valid):
        s = pygame.Surface((range_radius*2, range_radius*2), pygame.SRCALPHA)
        
        # Phối màu hiện đại hơn
        if is_valid:
            fill_color = (80, 255, 120, 35)      # Xanh ngọc mờ
            border_color = (80, 255, 120, 180)   # Xanh ngọc viền rõ
            foot_fill = (80, 255, 120, 60)
            foot_border = (80, 255, 120, 220)
        else:
            fill_color = (255, 60, 60, 35)       # Đỏ mờ
            border_color = (255, 60, 60, 180)    # Đỏ viền rõ
            foot_fill = (255, 60, 60, 60)
            foot_border = (255, 60, 60, 220)
            
        # Hình tròn tầm bắn: Nền mờ + Viền rõ + Vòng radar mờ ở giữa
        pygame.draw.circle(s, fill_color, (range_radius, range_radius), range_radius)
        pygame.draw.circle(s, border_color, (range_radius, range_radius), range_radius, 2)
        pygame.draw.circle(s, (border_color[0], border_color[1], border_color[2], 40), 
                           (range_radius, range_radius), int(range_radius * 0.6), 1)
        
        # Vẽ vạch chéo (crosshair) nhẹ
        pygame.draw.line(s, (border_color[0], border_color[1], border_color[2], 30), 
                         (range_radius, 0), (range_radius, range_radius * 2), 1)
        pygame.draw.line(s, (border_color[0], border_color[1], border_color[2], 30), 
                         (0, range_radius), (range_radius * 2, range_radius), 1)
                         
        screen.blit(s, (x - range_radius, y - range_radius))
        
        # Ô đặt tháp (footprint): Ô vuông thay vì hình tròn, có các góc trắng "công nghệ"
        f_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        f_surf.fill(foot_fill)
        pygame.draw.rect(f_surf, foot_border, (0, 0, TILE_SIZE, TILE_SIZE), 2)
        
        # Vẽ 4 góc định vị (marker corners)
        cl = 8 # corner length
        white_alpha = (255, 255, 255, 200)
        pygame.draw.line(f_surf, white_alpha, (0, 0), (cl, 0), 2)
        pygame.draw.line(f_surf, white_alpha, (0, 0), (0, cl), 2)
        
        pygame.draw.line(f_surf, white_alpha, (TILE_SIZE-2, 0), (TILE_SIZE-2-cl, 0), 2)
        pygame.draw.line(f_surf, white_alpha, (TILE_SIZE-2, 0), (TILE_SIZE-2, cl), 2)
        
        pygame.draw.line(f_surf, white_alpha, (0, TILE_SIZE-2), (cl, TILE_SIZE-2), 2)
        pygame.draw.line(f_surf, white_alpha, (0, TILE_SIZE-2), (0, TILE_SIZE-2-cl), 2)
        
        pygame.draw.line(f_surf, white_alpha, (TILE_SIZE-2, TILE_SIZE-2), (TILE_SIZE-2-cl, TILE_SIZE-2), 2)
        pygame.draw.line(f_surf, white_alpha, (TILE_SIZE-2, TILE_SIZE-2), (TILE_SIZE-2, TILE_SIZE-2-cl), 2)

        screen.blit(f_surf, (x - TILE_SIZE//2, y - TILE_SIZE//2))

    # ── Tower Popup (Upgrade/Sell/Target) ────────────────────────────────────
    def get_tower_popup_rects(self, tower):
        px = tower.x + 20
        py = tower.y - 40
        popup_w = 160
        return pygame.Rect(px + 5, py + 38, popup_w - 10, 26), \
               pygame.Rect(px + 5, py + 68, popup_w - 10, 26), \
               pygame.Rect(px + 5, py + 98, popup_w - 10, 26)

    def draw_tower_popup(self, screen, tower):
        px = tower.x + 20
        py = tower.y - 40
        popup_w = 160
        popup_h = 130
        rect = pygame.Rect(px, py, popup_w, popup_h)
        # Nền gỗ menu popup
        pygame.draw.rect(screen, (60, 40, 25), rect, border_radius=6)
        # Viền vàng đồng
        pygame.draw.rect(screen, (200, 160, 50), rect, 3, border_radius=6)
        # Đinh tán 4 góc
        for dx, dy in [(6,6), (popup_w-6,6), (6,popup_h-6), (popup_w-6,popup_h-6)]:
            pygame.draw.circle(screen, (220, 180, 60), (px+dx, py+dy), 4)
            pygame.draw.circle(screen, (100, 80, 20), (px+dx, py+dy), 4, 1)
        
        # Preview chỉ số
        if tower.level < 2:
            new_dmg = tower.damage + (25 if tower.__class__.__name__ == "Tower" else 20)
            new_rng = tower.range + (40 if tower.__class__.__name__ == "Tower" else 20)
            
            # Icon Sword
            pygame.draw.line(screen, (200, 200, 200), (px + 10, py + 16), (px + 16, py + 10), 2)
            pygame.draw.line(screen, GOLD_COLOR, (px + 10, py + 14), (px + 12, py + 16), 2)
            
            t_dmg1 = self.small_font.render(f" {tower.damage}", True, WHITE)
            t_dmg2 = self.small_font.render(f" -> {new_dmg}", True, GREEN)
            screen.blit(t_dmg1, (px + 20, py + 5))
            screen.blit(t_dmg2, (px + 20 + t_dmg1.get_width(), py + 5))
            
            # Icon Target
            pygame.draw.circle(screen, WHITE, (px + 13, py + 27), 4, 1)
            pygame.draw.circle(screen, RED, (px + 13, py + 27), 1)
            
            t_rng1 = self.small_font.render(f" {tower.range}", True, WHITE)
            t_rng2 = self.small_font.render(f" -> {new_rng}", True, GREEN)
            screen.blit(t_rng1, (px + 20, py + 20))
            screen.blit(t_rng2, (px + 20 + t_rng1.get_width(), py + 20))
        else:
            t_max = self.small_font.render("MAX LEVEL", True, GOLD_COLOR)
            screen.blit(t_max, (px + (popup_w - t_max.get_width())//2, py + 12))
        
        up_rect, sell_rect, target_rect = self.get_tower_popup_rects(tower)
        
        # Upgrade button
        if tower.level >= 2:
            pygame.draw.rect(screen, (80, 80, 80), up_rect, border_radius=3)
            up_text = self.small_font.render("Max Level", True, (180, 180, 180))
        else:
            pygame.draw.rect(screen, (50, 150, 50), up_rect, border_radius=3)
            up_text = self.small_font.render(f"Up ({tower.upgrade_cost} Gold)", True, WHITE)
        screen.blit(up_text, (up_rect.x + (up_rect.w - up_text.get_width())//2, up_rect.y + 5))
        
        # Sell button
        refund = int(tower.total_gold_spent * 0.7)
        pygame.draw.rect(screen, (200, 50, 50), sell_rect, border_radius=3)
        sell_text = self.small_font.render(f"Sell (+{refund} Gold)", True, WHITE)
        screen.blit(sell_text, (sell_rect.x + (sell_rect.w - sell_text.get_width())//2, sell_rect.y + 5))

        # Target Mode button
        pygame.draw.rect(screen, (50, 100, 200), target_rect, border_radius=3)
        target_text = self.small_font.render(f"Target: {tower.target_mode}", True, WHITE)
        screen.blit(target_text, (target_rect.x + (target_rect.w - target_text.get_width())//2, target_rect.y + 5))

