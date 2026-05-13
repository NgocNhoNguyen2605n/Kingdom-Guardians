"""
Mô-đun quản lý Kẻ Địch (Enemy) và Làn Sóng (Wave) của trò chơi Kingdom Guardians.

Mô-đun này triển khai hệ thống kẻ địch theo hướng đối tượng với kế thừa và đa hình,
cùng bảng tra cứu cấu hình tập trung để dễ mở rộng thêm loại kẻ địch mới.

Điểm nhấn thuật toán & đồ họa:
    - Quản lý kẻ địch bằng Spatial Hashing (Lưới không gian) để tối ưu tính toán sát thương AoE.
    - Kẻ địch được vẽ chi tiết bằng nhiều lớp đa giác (Polygons) với hiệu ứng bước đi và ngã gục.
    - Thanh máu (Health Bar) tự động nội suy màu theo phần trăm sinh mệnh còn lại.

Hằng số:
    ENEMY_CONFIG: Bảng Dictionary ánh xạ tên loại kẻ địch sang chỉ số HP,
        tốc độ và phần thưởng vàng. Thêm loại mới chỉ cần bổ sung một dòng.

Lớp:
    Enemy     : Lớp cơ sở — Hiệp sĩ giáp sắt. Định nghĩa giao diện chung update() và draw().
    FastEnemy : Kế thừa Enemy — Sát thủ áo choàng. Tốc độ cao, máu thấp.
    TankEnemy : Kế thừa Enemy — Golem khổng lồ. Bọc thép, máu cực cao, tốc độ chậm.
    WaveManager: Quản lý vòng đời làn sóng — sinh kẻ địch, đưa vào Spatial Hash và xử lý thu hồi phần thưởng.
"""
import pygame
import math
import random
from settings import *
from audio import play_sound

def draw_with_outline(screen, surface, center_x, center_y, outline_color=(0,0,0), outline_width=2):
    """
    Vẽ sprite với viền đen bao quanh — phong cách Kingdom Rush / BTD6 cel-shading.
    Dùng pygame.mask để tự động detect shape, blit shadow 8 hướng rồi blit sprite lên trên.
    """
    mask = pygame.mask.from_surface(surface)
    outline_surf = mask.to_surface(setcolor=(*outline_color, 255), unsetcolor=(0,0,0,0))
    outline_surf.set_colorkey((0,0,0))
    rect = surface.get_rect(center=(center_x, center_y))
    for dx in range(-outline_width, outline_width+1):
        for dy in range(-outline_width, outline_width+1):
            if dx == 0 and dy == 0: continue
            if abs(dx) + abs(dy) > outline_width + 1: continue
            screen.blit(outline_surf, (rect.x + dx, rect.y + dy))
    screen.blit(surface, rect.topleft)


def shade(base, factor):
    """
    Hue-shift shading — Stardew Valley / Hades technique:
    - factor < 0: tối hơn, shift COOL (thêm blue/purple) — như bóng trong Hades
    - factor > 0: sáng hơn, shift WARM (thêm red/yellow) — như highlight trong Stardew
    """
    r, g, b = base
    f = abs(factor)
    if factor < 0:  # Shadow: cool blue-shift
        r = max(0,   int(r * (1-f) - int(18*f)))
        g = max(0,   int(g * (1-f) -  int(5*f)))
        b = min(255, int(b * (1-f*0.6) + int(38*f)))
    else:           # Highlight: warm yellow-shift
        r = min(255, int(r + (255-r)*factor + int(28*factor)))
        g = min(255, int(g + (255-g)*factor + int(12*factor)))
        b = min(255, int(b + (255-b)*factor * 0.35))
    return (r, g, b)


# ── iii. Bảng tra cứu (Dictionary / HashMap) cấu hình kẻ địch ────────────────
# Mọi tham số HP, tốc độ, phần thưởng được lưu tập trung theo khoá tên loại.
# WaveManager tra bảng này khi sinh kẻ địch — thêm loại mới chỉ cần 1 dòng.
ENEMY_CONFIG = {
    "normal": {"hp": 150, "speed": 1.4, "reward": 10},
    "fast":   {"hp":  90, "speed": 3.0, "reward": 12},
    "tank":   {"hp": 380, "speed": 0.8, "reward": 20},
}

# ── i. Lớp cơ sở Enemy ───────────────────────────────────────────────────────
class Enemy:
    """
    Lớp CƠ SỞ cho mọi kẻ địch.
    Định nghĩa giao diện chung update() và draw() để vòng lặp chính
    xử lý đồng nhất qua đa hình — không cần if-else phân loại.
    """
    def __init__(self, path, enemy_type="normal"):
        cfg = ENEMY_CONFIG[enemy_type]      # Tra bảng Dictionary
        self.path = path
        self.path_index = 0
        self.x, self.y = self.path[0] if self.path else (0, 0)
        self.speed   = cfg["speed"]
        self.max_hp  = cfg["hp"]
        self.hp      = cfg["hp"]
        self.reward  = cfg["reward"]
        self.alive   = True
        self.walk_timer  = 0
        self.move_angle  = 0
        self.death_timer = 0
        self.dust_timer  = 0       # Bụi chân
        self.dust_particles = []   # [(x,y,vx,vy,life,max_life)]
        self.enemy_type = enemy_type

    def _move(self):
        """Logic di chuyển dọc path — dùng chung cho mọi lớp con."""
        self.walk_timer += 1
        if self.path_index < len(self.path) - 1:
            target_x, target_y = self.path[self.path_index + 1]
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy)
            if dx < -0.1:
                self.flip = True
            elif dx > 0.1:
                self.flip = False
            
            # Chỉ xoay nhẹ khi đi chéo (nếu muốn), nhưng ở đây tắt hẳn rotate
            self.move_angle = 0
            if dist < self.speed:
                self.path_index += 1
            else:
                self.x += (dx / dist) * self.speed
                self.y += (dy / dist) * self.speed
        else:
            self.alive = False

    def _emit_dust(self, interval=8, count=2, color=(200, 175, 130)):
        """Sinh hạt bụi dưới chân mỗi `interval` frame."""
        self.dust_timer += 1
        if self.dust_timer >= interval:
            self.dust_timer = 0
            for _ in range(count):
                import random as _r
                vx = _r.uniform(-0.8, 0.8)
                vy = _r.uniform(-0.5, 0.2)
                life = _r.randint(10, 18)
                self.dust_particles.append([self.x + _r.uniform(-6,6),
                                            self.y + 6 + _r.uniform(-2,2),
                                            vx, vy, life, life, color])
        # Cập nhật và loại bỏ hạt hết tuổi thọ
        for d in self.dust_particles:
            d[0] += d[2]; d[1] += d[3]; d[4] -= 1
        self.dust_particles = [d for d in self.dust_particles if d[4] > 0]

    def _draw_dust(self, screen):
        """Vẽ các hạt bụi (gọi TRƯỚC khi vẽ nhân vật)."""
        for d in self.dust_particles:
            alpha = max(0, min(255, int(180 * (d[4] / d[5]))))
            r_size = max(1, int(4 * (d[4] / d[5])))
            ds = pygame.Surface((r_size*2, r_size*2), pygame.SRCALPHA)
            pygame.draw.circle(ds, (*d[6], alpha), (r_size, r_size), r_size)
            screen.blit(ds, (int(d[0]) - r_size, int(d[1]) - r_size))

    def update(self):
        """
        Giao diện đa hình — vòng lặp chính gọi enemy.update() không phân biệt loại.
        Lớp con ghi đè để thêm hành vi riêng.
        """
        self._move()
        self._emit_dust(interval=8, count=2, color=(200, 175, 130))

    def _draw_health_bar(self, screen, bar_width=24, bar_height=5, y_offset=-22, icon=None):
        """Thanh máu chi tiết với viền đen bo góc, gradient, delayed damage và icon loại."""
        if not hasattr(self, 'display_hp'):
            self.display_hp = self.hp
            
        if self.display_hp > self.hp:
            self.display_hp -= max(0.1, (self.display_hp - self.hp) * 0.1)

        hp_perc = max(0, self.hp / self.max_hp)
        disp_perc = max(0, self.display_hp / self.max_hp)
        
        bx = int(self.x - bar_width // 2)
        by = int(self.y + y_offset)
        
        # Viền đen
        pygame.draw.rect(screen, (0,0,0), (bx-1, by-1, bar_width+2, bar_height+2), border_radius=2)
        pygame.draw.rect(screen, (40,40,40), (bx, by, bar_width, bar_height), border_radius=2)
        
        # Vàng nhạt (Delayed damage)
        disp_w = int(bar_width * disp_perc)
        if disp_w > 0:
            pygame.draw.rect(screen, (220, 200, 50), (bx, by, disp_w, bar_height), border_radius=2)
        
        fill_w = int(bar_width * hp_perc)
        if fill_w > 0:
            if hp_perc > 0.5:
                r = int(255 * (1.0 - (hp_perc - 0.5) * 2))
                g = 255
                b = 0
            else:
                r = 255
                g = int(255 * (hp_perc * 2))
                b = 0
            color = (r, g, b)
            pygame.draw.rect(screen, color, (bx, by, fill_w, bar_height), border_radius=2)
            light = tuple(min(255, c + 80) for c in color)
            pygame.draw.rect(screen, light, (bx, by, fill_w, max(1, bar_height//2)), border_radius=2)
        
        # Icon loại kẻ địch bên trái thanh máu
        if icon == 'fast':   # Lightning bolt
            ix, iy = bx - 9, by - 1
            pygame.draw.polygon(screen, (50, 220, 80), [(ix+3,iy), (ix,iy+4), (ix+3,iy+3), (ix,iy+7), (ix+5,iy+3), (ix+2,iy+4)])
        elif icon == 'tank': # Shield
            ix, iy = bx - 9, by - 1
            pygame.draw.polygon(screen, (200, 120, 30), [(ix+2,iy+1),(ix+5,iy+1),(ix+6,iy+4),(ix+3,iy+7),(ix,iy+4)])
            pygame.draw.polygon(screen, (240, 170, 60), [(ix+2,iy+1),(ix+5,iy+1),(ix+6,iy+4),(ix+3,iy+7),(ix,iy+4)], 1)

    def draw(self, screen, is_dying=False):
        """Hiệp sĩ 3-tone shading — kỹ thuật Hades (terminator line, specular) + Stardew Valley (hue-shift shadow)."""
        # ── Palette: Steel armor (Hades cool shadow, warm highlight)
        ST0 = ( 55,  62, 105)  # Shadow deep cool-blue
        ST1 = (135, 142, 165)  # Midtone silver
        ST2 = (210, 220, 242)  # Highlight warm-white
        STS = (252, 252, 230)  # Specular glint
        STT = (120,  80, 200)  # Terminator purple (Hades style)
        # Skin (subsurface scattering)
        SK0 = (190, 120,  80)  # Shadow warm orange (SSS)
        SK1 = (228, 182, 142)  # Midtone skin
        SK2 = (255, 218, 182)  # Highlight warm
        # Crest red
        CR0 = (160,   8,   8)  # Shadow deep red
        CR1 = (235,  22,  22)  # Midtone bright red
        CR2 = (255,  95,  65)  # Highlight orange-red (warm terminator)
        # Shield blue
        SH0 = (  8,  30, 115)  # Shadow deep navy
        SH1 = ( 22,  75, 210)  # Midtone royal blue
        SH2 = ( 75, 155, 255)  # Highlight sky blue
        SHT = ( 40, 210, 255)  # Terminator cyan (Hades)
        # Gold
        GD0 = (160, 110,  10); GD1 = (220, 175,  25); GD2 = (255, 230,  90)
        # Sword
        SW1 = (195, 200, 218); SW2 = (238, 245, 255); SWS = (255, 255, 240)

        if is_dying:
            alpha = int(255 * (self.death_timer / 15))
            self.move_angle += 12
            y_off = (15 - self.death_timer)
        else:
            alpha = 255
            y_off = math.sin(self.walk_timer * 0.3) * 2.5

        self._draw_dust(screen)

        # Drop shadow
        shadow_a = int(80 * (self.death_timer / 15)) if is_dying else 80
        shd = pygame.Surface((36, 13), pygame.SRCALPHA)
        pygame.draw.ellipse(shd, (0, 0, 0, shadow_a), (0, 0, 36, 13))
        screen.blit(shd, (int(self.x) - 18, int(self.y) + 7))

        sw_s, sh_s = 48, 56
        s = pygame.Surface((sw_s, sh_s), pygame.SRCALPHA)
        cx = 24

        if not is_dying:
            leg_y1 = int(math.sin(self.walk_timer * 0.4) * 4)
            leg_y2 = int(math.sin(self.walk_timer * 0.4 + math.pi) * 4)
        else:
            leg_y1 = leg_y2 = 0

        # ── GREAVES (3-tone) ──
        for lx, lo in [(cx-11, leg_y1), (cx+2, leg_y2)]:
            pygame.draw.rect(s, ST0, (lx, 36+lo, 8, 15), border_radius=3)   # Shadow
            pygame.draw.rect(s, ST1, (lx, 36+lo, 8, 10), border_radius=2)   # Midtone
            pygame.draw.rect(s, ST2, (lx, 36+lo, 5,  4), border_radius=2)   # Highlight
            pygame.draw.line(s, STT, (lx, 46+lo), (lx+8, 46+lo), 1)         # Terminator
            # Sabatons (foot plate)
            pygame.draw.rect(s, ST0, (lx-1, 48+lo, 10, 5), border_radius=2)
            pygame.draw.rect(s, ST1, (lx-1, 48+lo, 10, 3), border_radius=2)
            pygame.draw.circle(s, STS, (lx+3, 49+lo), 1)  # Specular

        # ── BREASTPLATE (3-tone, sharp metallic — Hades) ──
        pygame.draw.rect(s, ST0, (cx-12, 22, 24, 16), border_radius=4)  # Shadow base
        pygame.draw.rect(s, ST1, (cx-12, 22, 24, 10), border_radius=4)  # Midtone
        pygame.draw.rect(s, ST2, (cx-12, 22, 14,  5), border_radius=3)  # Highlight
        pygame.draw.line(s, STT, (cx-12, 32), (cx+12, 32), 1)           # Terminator line
        pygame.draw.line(s, ST0, (cx, 22), (cx, 38), 1)                 # Center seam
        pygame.draw.circle(s, STS, (cx-5, 24), 2)                       # Specular
        pygame.draw.circle(s, STS, (cx+5, 24), 1)                       # Secondary spec

        # ── BELT ──
        pygame.draw.rect(s, GD0, (cx-12, 37, 24, 4))
        pygame.draw.rect(s, GD1, (cx-12, 37, 24, 2))
        pygame.draw.circle(s, GD2, (cx, 39), 3)
        pygame.draw.circle(s, (255,248,180), (cx-1, 38), 1)  # Buckle specular

        # ── PAULDRONS (shoulders, 3-tone ellipse) ──
        for sx, hx in [(cx-19, cx-13), (cx+5, cx+8)]:
            pygame.draw.ellipse(s, ST0, (sx, 19, 14, 11))
            pygame.draw.ellipse(s, ST1, (sx, 19, 14,  8))
            pygame.draw.ellipse(s, ST2, (hx-sx, 19,  7,  4) if sx < cx else (sx, 19, 7, 4))
            pygame.draw.circle(s, STS, (sx + 5, 21), 1)  # Specular

        # ── HELMET DOME (3-tone circle — Stardew top-light, Hades rim) ──
        pygame.draw.circle(s, ST0, (cx, 12), 14)           # Shadow dome
        pygame.draw.circle(s, ST1, (cx-1, 11), 12)         # Midtone
        pygame.draw.circle(s, ST2, (cx-3,  9),  8)         # Highlight
        pygame.draw.circle(s, STS, (cx-5,  7),  2)         # Specular glint
        # Terminator arc (Hades signature)
        pygame.draw.arc(s, STT, (cx-14, 2, 28, 22), math.pi*0.55, math.pi*1.1, 1)
        # T-visor
        pygame.draw.rect(s, (15, 18, 38), (cx-8, 10, 16, 5), border_radius=2)
        pygame.draw.line(s, (45, 50, 78), (cx-7, 12), (cx+7, 12), 1)

        # ── CREST (3-tone plume) ──
        pygame.draw.polygon(s, CR0, [(cx-5,  2),(cx+5,  2),(cx, -7)])
        pygame.draw.polygon(s, CR1, [(cx-6,  6),(cx+6,  6),(cx, -1)])
        pygame.draw.polygon(s, CR2, [(cx-3,  5),(cx+3,  5),(cx,  1)])
        pygame.draw.line(s, (255,190,160), (cx, -5), (cx, 3), 1)  # Center spec

        # ── SHIELD (3-tone, Hades saturated navy) ──
        sh_pts  = [(cx-20,21),(cx-10,21),(cx-10,35),(cx-15,41),(cx-20,35)]
        sh_mid  = [(cx-20,21),(cx-10,21),(cx-10,30),(cx-15,35),(cx-20,30)]
        sh_hlt  = [(cx-20,21),(cx-10,21),(cx-10,26),(cx-20,26)]
        pygame.draw.polygon(s, SH0, sh_pts)
        pygame.draw.polygon(s, SH1, sh_mid)
        pygame.draw.polygon(s, SH2, sh_hlt)
        pygame.draw.line(s, SHT, (cx-20,21), (cx-20,35), 1)   # Cyan terminator edge
        pygame.draw.line(s, SHT, (cx-20,35), (cx-15,41), 1)
        # Emblem gold
        pygame.draw.circle(s, GD1, (cx-15, 30), 4)
        pygame.draw.circle(s, GD0, (cx-15, 30), 4, 1)
        pygame.draw.circle(s, GD2, (cx-16, 29), 1)            # Emblem specular
        pygame.draw.polygon(s, SH0, sh_pts, 1)                # Outline

        # ── SWORD (3-tone steel blade — Hades metallic) ──
        pygame.draw.rect(s,    GD0, (cx+10, 30, 5, 9), border_radius=1)  # Hilt wood
        pygame.draw.rect(s,    GD1, (cx+10, 30, 5, 4))
        pygame.draw.rect(s,    GD1, (cx+ 8, 27, 9, 3))   # Guard
        pygame.draw.line(s,    GD2, (cx+8, 27), (cx+17, 27), 1)          # Guard highlight
        pygame.draw.polygon(s, SW1, [(cx+11, 5),(cx+14, 5),(cx+12, 27)]) # Blade midtone
        pygame.draw.polygon(s, SW2, [(cx+11, 5),(cx+12, 5),(cx+12, 27)]) # Blade highlight edge
        pygame.draw.line(s,    SWS, (cx+11, 6), (cx+11, 24), 1)          # Specular edge
        pygame.draw.line(s,    ST0, (cx+13, 6), (cx+13, 26), 1)          # Shadow edge

        if is_dying:
            s.set_alpha(alpha)

        rotated = pygame.transform.rotate(s, self.move_angle)
        # Scale down for 32px paths (35% reduction)
        scale_f = 0.65
        final_size = (int(rotated.get_width() * scale_f), int(rotated.get_height() * scale_f))
        scaled = pygame.transform.smoothscale(rotated, final_size)
        
        cx_r, cy_r = int(self.x), int(self.y + y_off)
        if not is_dying:
            draw_with_outline(screen, scaled, cx_r, cy_r, (0,0,0), 2)
        else:
            screen.blit(scaled, scaled.get_rect(center=(cx_r, cy_r)).topleft)
        if not is_dying:
            self._draw_health_bar(screen, bar_width=20, bar_height=4)



# ── i. Lớp con FastEnemy — kế thừa Enemy ────────────────────────────────────
class FastEnemy(Enemy):
    """
    Kẻ địch TỐC ĐỘ — thân gọn, màu xanh lá neon, di chuyển rất nhanh.
    Ghi đè update() và draw() — đa hình với lớp cơ sở Enemy.
    """
    def __init__(self, path):
        super().__init__(path, "fast")      # Tra ENEMY_CONFIG["fast"]

    def update(self):
        """Ghi đè update — tốc độ cao, bụi xanh lá nhẹ hơn."""
        self._move()
        self._emit_dust(interval=5, count=1, color=(120, 200, 130))

    def draw(self, screen, is_dying=False):
        """Sát thủ rừng 3-tone — Hades terminator + Stardew hue-shift + Hollow Knight focal eyes."""
        # Palette: Forest green (cool-shift shadows, warm highlights)
        GR0 = ( 12,  68,  25)  # Deep forest shadow (cool)
        GR1 = ( 25, 130,  55)  # Midtone bright green
        GR2 = ( 80, 210, 110)  # Highlight warm lime
        GRT = (160, 255, 100)  # Terminator yellow-green (Hades warm edge)
        # Cloak fold shadow (darker, cooler)
        CF0 = (  8,  45,  18)  # Cloak shadow crease
        CF1 = ( 18,  95,  40)  # Cloak secondary
        # Dagger steel
        DG0 = ( 80,  85, 110)  # Blade shadow cool
        DG1 = (188, 195, 215)  # Blade midtone
        DG2 = (238, 245, 255)  # Blade highlight
        DGS = (255, 255, 235)  # Specular glint
        # Skin
        SK1 = (225, 180, 138)  # Warm skin mid
        SK2 = (255, 218, 178)  # Warm skin highlight
        # Belt
        BT0 = (110,  70,  15); BT1 = (180, 130,  30); BT2 = (230, 185,  60)

        if is_dying:
            alpha = int(255 * (self.death_timer / 15))
            self.move_angle += 15
            y_off = (15 - self.death_timer)
        else:
            alpha = 255
            y_off = math.sin(self.walk_timer * 0.6) * 3

        self._draw_dust(screen)

        shadow_a = int(60 * (self.death_timer / 15)) if is_dying else 60
        shd = pygame.Surface((28, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(shd, (0, 0, 0, shadow_a), (0, 0, 28, 10))
        screen.blit(shd, (int(self.x) - 14, int(self.y) + 6))

        sw, sh = 40, 50
        s = pygame.Surface((sw, sh), pygame.SRCALPHA)
        cx = 20

        if not is_dying:
            leg_y1 = int(math.sin(self.walk_timer * 0.7) * 5)
            leg_y2 = int(math.sin(self.walk_timer * 0.7 + math.pi) * 5)
        else:
            leg_y1 = leg_y2 = 0

        # ── LEGS (3-tone) ──
        for lx, lo in [(cx-8, leg_y1), (cx+2, leg_y2)]:
            pygame.draw.rect(s, GR0, (lx, 32+lo, 5, 12), border_radius=2)
            pygame.draw.rect(s, GR1, (lx, 32+lo, 5,  8), border_radius=2)
            pygame.draw.rect(s, GR2, (lx, 32+lo, 3,  4), border_radius=1)

        # ── CLOAK BODY (3-tone + fold lines — Stardew fabric technique) ──
        # Shadow base (full silhouette)
        pygame.draw.polygon(s, GR0, [(cx-14,16),(cx+14,16),(cx+16,30),(cx,38),(cx-16,30)])
        # Midtone layer
        pygame.draw.polygon(s, GR1, [(cx-12,16),(cx+12,16),(cx+14,28),(cx,36),(cx-14,28)])
        # Highlight (light from top-left)
        pygame.draw.polygon(s, GR2, [(cx-12,16),(cx-2,16),(cx-4,28),(cx-12,24)])
        # Terminator line at shadow edge
        pygame.draw.line(s, GRT, (cx+14,28), (cx,38), 1)
        pygame.draw.line(s, GRT, (cx-14,28), (cx,38), 1)
        # Fabric fold crease lines (Stardew style)
        pygame.draw.line(s, CF0, (cx-8, 20), (cx-12, 30), 1)
        pygame.draw.line(s, CF0, (cx+5, 20), (cx+10, 28), 1)
        pygame.draw.line(s, CF1, (cx-4, 20), (cx-6, 32), 1)

        # ── BELT ──
        pygame.draw.rect(s, BT0, (cx-11, 27, 22, 4))
        pygame.draw.rect(s, BT1, (cx-11, 27, 22, 2))
        pygame.draw.circle(s, BT2, (cx, 29), 3)
        pygame.draw.circle(s, (255,240,150), (cx-1, 28), 1)  # Buckle specular

        # ── HOOD HEAD (3-tone dome) ──
        pygame.draw.circle(s, GR0, (cx, 11), 12)     # Shadow
        pygame.draw.circle(s, GR1, (cx-1, 10), 10)   # Midtone
        pygame.draw.circle(s, GR2, (cx-3,  8),  6)   # Highlight
        # Hood peak (3-tone triangle)
        pygame.draw.polygon(s, GR0, [(cx-9,11),(cx+9,11),(cx, -2)])
        pygame.draw.polygon(s, GR1, [(cx-7,11),(cx+7,11),(cx,  0)])
        pygame.draw.circle(s, GR2, (cx-2, 8), 3)      # Hood specular

        # ── FACE (Stardew subsurface skin + Hollow Knight focal eyes) ──
        pygame.draw.circle(s, SK1, (cx, 11), 7)       # Skin midtone
        # Subsurface shadow (warm orange under hood — SSS)
        eye_shd = pygame.Surface((15, 7), pygame.SRCALPHA)
        pygame.draw.ellipse(eye_shd, (10, 55, 18, 170), (0,0,15,7))
        s.blit(eye_shd, (cx-7, 11))
        pygame.draw.circle(s, SK2, (cx-2, 9), 3)      # Nose/cheek highlight

        # Hollow Knight focal eyes — bright green with inner glow
        for ex in [cx-4, cx+4]:
            pygame.draw.circle(s, GR0,  (ex, 9), 3)   # Outer dark
            pygame.draw.circle(s, (0, 240, 90), (ex, 9), 3)  # Bright neon ring
            pygame.draw.circle(s, (180,255,210), (ex, 9), 1)  # Inner specular

        # ── DAGGERS (3-tone metallic — Hades sharp transition) ──
        for dx_off, flip in [(-16, 1), (10, -1)]:
            # Hilt
            pygame.draw.rect(s, BT0, (cx+dx_off, 18, 4, 8), border_radius=1)
            pygame.draw.rect(s, BT1, (cx+dx_off, 18, 4, 4))
            # Blade (3-tone sharp)
            bx = cx + dx_off + (0 if flip > 0 else 2)
            pygame.draw.polygon(s, DG0, [(bx, 5),(bx+3, 5),(bx+2, 18),(bx, 18)])   # Shadow
            pygame.draw.polygon(s, DG1, [(bx, 5),(bx+2, 5),(bx+1, 18),(bx, 18)])   # Midtone
            pygame.draw.line(s,   DGS, (bx, 6), (bx, 16), 1)                       # Specular edge

        if is_dying:
            s.set_alpha(alpha)
            self.move_angle -= 15 if getattr(self, 'flip', False) else -15
            rotated = pygame.transform.rotate(s, self.move_angle)
        else:
            rotated = pygame.transform.flip(s, True, False) if getattr(self, 'flip', False) else s

        # Scale down for 32px paths
        scale_f = 0.65
        final_size = (int(rotated.get_width() * scale_f), int(rotated.get_height() * scale_f))
        scaled = pygame.transform.smoothscale(rotated, final_size)

        cx_r, cy_r = int(self.x), int(self.y + y_off)
        if not is_dying:
            draw_with_outline(screen, scaled, cx_r, cy_r, (0,0,0), 2)
        else:
            screen.blit(scaled, scaled.get_rect(center=(cx_r, cy_r)).topleft)
        if not is_dying:
            self._draw_health_bar(screen, bar_width=18, bar_height=4, icon='fast')


# ── i. Lớp con TankEnemy────────
class TankEnemy(Enemy):
    """
    Kẻ địch BỌC THÉP — thân to, máu nhiều, màu cam/sắt nung.
    Ghi đè update() và draw() — đa hình với lớp cơ sở Enemy.
    """
    def __init__(self, path):
        super().__init__(path, "tank")      # Tra ENEMY_CONFIG["tank"]

    def update(self):
        """Ghi đè update — di chuyển nặng nề, bụi nâu đất."""
        self._move()
        self._emit_dust(interval=12, count=3, color=(160, 130, 80))
        # Signal rung mặt đất — được đọc từ main.py
        self.ground_shake = (self.walk_timer % 20 == 0)

    def draw(self, screen, is_dying=False):
        """Iron Golem 3-tone — Hades lava-crack glow, Stardew hue-shift rust shadows."""
        # Palette: Rust iron (cool red shadows, warm orange highlights)
        IR0 = ( 90,  28,   5)  # Shadow deep burnt (hue-shift cool-red)
        IR1 = (175,  78,  18)  # Midtone rust orange
        IR2 = (235, 120,  40)  # Highlight warm orange
        IRS = (255, 200, 100)  # Specular glint (warm yellow)
        IRT = (255,  75,   0)  # Terminator (Hades hot orange edge)
        # Lava cracks (multi-layer Hades glow)
        LV0 = (255,  80,   0)  # Outer lava
        LV1 = (255, 200,  30)  # Inner bright
        LV2 = (255, 255, 200)  # Core white-hot
        # Gold
        GD0 = (140,  90,   8); GD1 = (215, 165,  22); GD2 = (255, 225,  85)
        # Axe metal
        AX0 = ( 70,  78, 105)  # Cool steel shadow
        AX1 = (180, 188, 205)  # Steel midtone
        AX2 = (235, 242, 255)  # Steel highlight
        AXS = (255, 255, 240)  # Specular
        # Crest
        CS0 = (165,  40,   5); CS1 = (235,  65,  18); CS2 = (255, 135,  55)

        if is_dying:
            alpha = int(255 * (self.death_timer / 15))
            self.move_angle += 5
            y_off = (15 - self.death_timer) * 0.5
        else:
            alpha = 255
            y_off = math.sin(self.walk_timer * 0.12) * 1.5

        self._draw_dust(screen)

        shadow_a = int(90 * (self.death_timer / 15)) if is_dying else 90
        shd = pygame.Surface((58, 20), pygame.SRCALPHA)
        pygame.draw.ellipse(shd, (0, 0, 0, shadow_a), (0, 0, 58, 20))
        screen.blit(shd, (int(self.x) - 29, int(self.y) + 11))

        sw, sh = 66, 74
        s = pygame.Surface((sw, sh), pygame.SRCALPHA)
        cx = 33

        if not is_dying:
            leg_y1 = int(math.sin(self.walk_timer * 0.15) * 3)
            leg_y2 = int(math.sin(self.walk_timer * 0.15 + math.pi) * 3)
        else:
            leg_y1 = leg_y2 = 0

        # ── HEAVY GREAVES (3-tone) ──
        for lx, lo in [(cx-16, leg_y1), (cx+2, leg_y2)]:
            pygame.draw.rect(s, IR0, (lx, 46+lo, 13, 20), border_radius=4)  # Shadow
            pygame.draw.rect(s, IR1, (lx, 46+lo, 13, 13), border_radius=3)  # Midtone
            pygame.draw.rect(s, IR2, (lx, 46+lo,  8,  6), border_radius=3)  # Highlight
            pygame.draw.line(s, IRT, (lx, 59+lo), (lx+13, 59+lo), 1)        # Terminator
            pygame.draw.circle(s, IRS, (lx+4, 48+lo), 2)                    # Specular
            # Sabatons
            pygame.draw.rect(s, IR0, (lx-1, 63+lo, 15, 7), border_radius=3)
            pygame.draw.rect(s, IR1, (lx-1, 63+lo, 15, 4), border_radius=2)

        # ── BODY ARMOR (3-tone big breastplate) ──
        pygame.draw.rect(s, IR0, (cx-20, 24, 40, 26), border_radius=6)  # Shadow
        pygame.draw.rect(s, IR1, (cx-20, 24, 40, 16), border_radius=6)  # Midtone
        pygame.draw.rect(s, IR2, (cx-20, 24, 24,  8), border_radius=5)  # Highlight
        pygame.draw.line(s, IRT, (cx-20, 40), (cx+20, 40), 1)           # Terminator
        pygame.draw.line(s, IR0, (cx,    24), (cx,    50), 2)            # Center seam
        pygame.draw.circle(s, IRS, (cx-7, 27), 3)  # Specular
        pygame.draw.circle(s, IRS, (cx+8, 28), 2)

        # ── LAVA CRACKS (Hades multi-layer glow technique) ──
        cracks = [((cx-14,30),(cx-5,40)), ((cx+6,32),(cx+14,42)), ((cx-5,44),(cx+5,36))]
        for c in cracks:
            pygame.draw.line(s, LV0, c[0], c[1], 4)  # Outer glow
            pygame.draw.line(s, LV1, c[0], c[1], 2)  # Inner
            pygame.draw.line(s, LV2, c[0], c[1], 1)  # Core white

        # ── MASSIVE PAULDRONS (3-tone) ──
        for px, phx in [( 0, 5), (cx+7, cx+13)]:
            pygame.draw.ellipse(s, IR0, (px, 20, 26, 20))           # Shadow
            pygame.draw.ellipse(s, IR1, (px, 20, 26, 14))           # Midtone
            pygame.draw.ellipse(s, IR2, (px+2, 20, 14,  7))         # Highlight
            pygame.draw.circle(s, IRS, (px+6, 22), 2)               # Specular
        # Shoulder spikes
        pygame.draw.polygon(s, IR0, [(0,18),(6,18),(2, 8)])
        pygame.draw.polygon(s, IR1, [(1,18),(5,18),(2,10)])
        pygame.draw.polygon(s, IR0, [(sw-6,18),(sw,18),(sw-2, 8)])
        pygame.draw.polygon(s, IR1, [(sw-5,18),(sw-1,18),(sw-2,10)])

        # ── HELMET (large chibi dome, 3-tone) ──
        pygame.draw.rect(s, IR0, (cx-18, 4, 36, 22), border_radius=10)  # Shadow
        pygame.draw.rect(s, IR1, (cx-18, 4, 36, 14), border_radius=8)   # Midtone
        pygame.draw.rect(s, IR2, (cx-18, 4, 22,  7), border_radius=6)   # Highlight
        pygame.draw.rect(s, IR0, (cx-18, 4, 36, 22), border_radius=10, width=2)  # Rim
        # T-visor
        pygame.draw.rect(s, (18,  8,  2), (cx-11,  9, 22,  7))
        pygame.draw.rect(s, (18,  8,  2), (cx- 4,  9,  8, 15))
        # Specular on helm
        pygame.draw.circle(s, IRS, (cx-8, 6), 3)
        pygame.draw.circle(s, IRS, (cx-5, 7), 1)

        # ── FIERY EYES (Hollow Knight / Hades focal point) ──
        for ex in [cx-8, cx+8]:
            pygame.draw.circle(s, IR0,  (ex, 13), 5)  # Dark ring
            pygame.draw.circle(s, LV0,  (ex, 13), 5)  # Lava outer
            pygame.draw.circle(s, LV1,  (ex, 13), 3)  # Inner bright
            pygame.draw.circle(s, LV2,  (ex, 13), 1)  # Core white

        # ── HELMET CREST (3-tone) ──
        pygame.draw.polygon(s, CS0, [(cx-8,4),(cx+8,4),(cx,-6)])
        pygame.draw.polygon(s, CS1, [(cx-6,4),(cx+6,4),(cx,-2)])
        pygame.draw.polygon(s, CS2, [(cx-3,3),(cx+3,3),(cx, 0)])
        pygame.draw.line(s, IRS, (cx, -4), (cx, 2), 1)  # Crest specular

        # ── SHIELD left (3-tone) ──
        sh_f = [(-2,26),(12,26),(12,44),(5,52),(-2,44)]
        sh_m = [(-2,26),(12,26),(12,40),(5,47),(-2,40)]
        sh_h = [(-2,26),(12,26),(12,32),(-2,32)]
        pygame.draw.polygon(s, IR0, sh_f)
        pygame.draw.polygon(s, IR1, sh_m)
        pygame.draw.polygon(s, IR2, sh_h)
        pygame.draw.line(s, LV0, (-2,26), (-2,44), 2)   # Lava crack on shield edge
        pygame.draw.circle(s, GD1, (5, 38), 5)          # Shield emblem
        pygame.draw.circle(s, GD2, (4, 37), 2)
        pygame.draw.polygon(s, IR0, sh_f, 1)

        # ── BATTLE AXE right (3-tone metallic) ──
        pygame.draw.rect(s, IR1, (sw-11, 28, 8, 20), border_radius=2)   # Handle
        pygame.draw.rect(s, IR2, (sw-11, 28, 8, 10), border_radius=2)   # Handle highlight
        pygame.draw.line(s, AX1, (sw-7,  29), (sw-7,  46), 2)           # Handle shine
        # Axe head (3-tone steel)
        pygame.draw.polygon(s, AX0, [(sw-21,  8),(sw+2,  8),(sw+4, 26),(sw-23, 26)])
        pygame.draw.polygon(s, AX1, [(sw-21,  8),(sw+2,  8),(sw+4, 26),(sw-23, 26)])
        pygame.draw.polygon(s, AX2, [(sw-20,  8),(sw+1,  8),(sw-1, 16),(sw-20, 16)])  # Upper highlight
        pygame.draw.line(s,   AXS, (sw-19, 9), (sw, 9), 2)              # Blade edge specular
        pygame.draw.polygon(s, AX0, [(sw-21,8),(sw+2,8),(sw+4,26),(sw-23,26)], 1)

        if is_dying:
            s.set_alpha(alpha)
            self.move_angle -= 5 if getattr(self, 'flip', False) else -5
            rotated = pygame.transform.rotate(s, self.move_angle)
        else:
            rotated = pygame.transform.flip(s, True, False) if getattr(self, 'flip', False) else s

        # Scale down for 32px paths
        scale_f = 0.75
        final_size = (int(rotated.get_width() * scale_f), int(rotated.get_height() * scale_f))
        scaled = pygame.transform.smoothscale(rotated, final_size)

        cx_r, cy_r = int(self.x), int(self.y + y_off)
        if not is_dying:
            draw_with_outline(screen, scaled, cx_r, cy_r, (140, 40, 0), 2)  # Orange-red outline
        else:
            screen.blit(scaled, scaled.get_rect(center=(cx_r, cy_r)).topleft)
        if not is_dying:
            self._draw_health_bar(screen, bar_width=32, bar_height=6, icon='tank')

# ── WaveManager — sử dụng ENEMY_CONFIG để sinh kẻ địch ──────────────────────
class WaveManager:
    """Quản lý làn sóng kẻ địch. Tra ENEMY_CONFIG để tạo đúng loại theo wave."""
    def __init__(self, paths):
        # Chấp nhận list đường (đa nhánh) hoặc một đường đơn (tương thích cũ)
        self.paths = paths if isinstance(paths[0], (list, tuple)) and isinstance(paths[0][0], (list,tuple)) else paths
        # Đảm bảo luôn là list of paths
        if paths and not isinstance(paths[0][0], (list, tuple)):
            self.paths = [paths]   # wrap single path
        self.enemies = []
        self.dying_enemies = []
        self.wave = 1
        self.spawn_timer = 0
        self.spawn_delay = 55
        self.enemies_to_spawn = 5
        self.hp_multiplier = 1.0
        self.game_won = False
        
        # Spatial Hash cho tối ưu hoá quét đạn AoE
        self.spatial_hash = {}
        self.cell_size = 40

    def _get_spawn_type(self):
        """
        Tra ENEMY_CONFIG theo wave để quyết định loại kẻ địch cần sinh.
        Không hard-code chỉ số — chỉ chọn khoá trong ENEMY_CONFIG.
        """
        if self.wave == 1:
            return random.choices(["normal", "fast", "tank"], weights=[50, 30, 20])[0]
        elif self.wave == 2:
            return random.choices(["normal", "fast", "tank"], weights=[40, 35, 25])[0]
        else:
            return random.choices(["normal", "fast", "tank"], weights=[30, 40, 30])[0]

    def _create_enemy(self, enemy_type):
        """Factory: chọn ngẫu nhiên một nhánh đường rồi tạo kẻ địch đúng loại."""
        chosen_path = random.choice(self.paths)  # Mỗi địch đi ngẫu nhiên một nhánh
        if enemy_type == "fast":
            return FastEnemy(chosen_path)
        elif enemy_type == "tank":
            return TankEnemy(chosen_path)
        return Enemy(chosen_path, "normal")

    def update(self):
        if self.game_won:
            return 0, 0

        if self.enemies_to_spawn > 0:
            self.spawn_timer += 1
            if self.spawn_timer >= self.spawn_delay:
                enemy_type = self._get_spawn_type()     # Tra bảng
                self.enemies.append(self._create_enemy(enemy_type))
                self.enemies_to_spawn -= 1
                self.spawn_timer = 0

        gold_earned   = 0
        escaped_count = 0
        newly_dead    = []
        self.spatial_hash.clear()
        
        for enemy in self.enemies:
            was_alive = enemy.alive
            enemy.update()                  # ĐA HÌNH: gọi update() không if-else
            if enemy.hp <= 0 and was_alive:
                enemy.alive = False
                gold_earned += enemy.reward     # Lấy reward từ config
                enemy.death_timer = 15          # Thêm vào hàng đợi chết
                self.dying_enemies.append(enemy)
                newly_dead.append(enemy)
                play_sound("enemy_die")
            elif not enemy.alive and enemy.hp > 0 and was_alive:
                escaped_count += 1
                
            if enemy.alive:
                # Cập nhật kẻ địch vào Spatial Hash theo toạ độ lưới cell_size
                cx, cy = int(enemy.x // self.cell_size), int(enemy.y // self.cell_size)
                self.spatial_hash.setdefault((cx, cy), []).append(enemy)

        self.enemies = [e for e in self.enemies if e.alive]
        
        # Cập nhật enemy đang chết
        for d in self.dying_enemies:
            d.death_timer -= 1
        self.dying_enemies = [d for d in self.dying_enemies if d.death_timer > 0]
        
        return gold_earned, escaped_count, newly_dead

    def draw(self, screen):
        # Vẽ xác đang tan biến trước để không đè lên kẻ địch sống
        for d in self.dying_enemies:
            d.draw(screen, is_dying=True)
        # Vẽ kẻ địch còn sống
        for e in self.enemies:
            e.draw(screen)
