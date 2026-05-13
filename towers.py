"""
Mô-đun quản lý Tháp Phòng Thủ (Tower) của trò chơi Kingdom Guardians.

Mô-đun này triển khai hệ thống tháp theo hướng đối tượng với kế thừa và đa hình,
cho phép vòng lặp chính xử lý mọi loại tháp thống nhất qua cùng một giao diện.

Điểm nhấn thuật toán & đồ họa:
    - Target Mode (First/Nearest/Strongest/Weakest) dùng Priority Queue (heapq) độ phức tạp O(log n).
    - Tháp Gỗ (Archer) được vẽ 3D với cột cờ, mái che bạt đỏ/xanh, kiến trúc vững chãi.
    - Tháp Pha Lê (Magic) là khối Obelisk hắc ám với pha lê lơ lửng, quỹ đạo quay tinh tế.
    - Cả hai đều có Muzzle Flash (chớp lửa) mỗi khi khai hỏa.

Lớp:
    Tower      : Lớp cơ sở — Tháp Cung Thủ bắn đạn tên mục tiêu đơn.
        Cung cấp _find_target() (dùng heapq) và giao diện update() / draw() / upgrade().
    MagicTower : Kế thừa Tower — Tháp Ma Thuật bắn đạn AoE gây sát thương diện rộng.
        Ghi đè update() để bắn Bullet loại "aoe", truyền thêm wave_manager.
        Ghi đè draw() để vẽ đài tinh thể lơ lửng, nâng cấp tăng thêm aoe_radius.
"""
import pygame
import math
import heapq
from settings import *
from bullets import Bullet
from audio import play_sound


# ── i. Lớp cơ sở Tower ───────────────────────────────────────────────────────
class Tower:
    """
    Lớp CƠ SỞ cho mọi tháp phòng thủ.
    Định nghĩa giao diện chung update() và draw() — vòng lặp chính
    xử lý đồng nhất qua đa hình, không cần if-else theo loại tháp.
    """
    def __init__(self, x, y):
        self.x = (x // TILE_SIZE) * TILE_SIZE + TILE_SIZE // 2
        self.y = (y // TILE_SIZE) * TILE_SIZE + TILE_SIZE // 2
        self.range        = 100
        self.damage       = 30
        self.cooldown     = 40
        self.cooldown_timer = 0
        self.level        = 1
        self.upgrade_cost = 80
        self.total_gold_spent = 65
        self.angle        = 0
        self.shoot_timer  = 0
        self.flash_duration = 5
        self.lean_angle   = 0.0
        self.lean_target  = 0.0
        self.target_mode  = "First"  # First, Strongest, Weakest

    def _find_target(self, enemies):
        """Tìm kẻ địch theo chế độ ưu tiên (First, Nearest, Strongest, Weakest)."""
        valid = [e for e in enemies if math.hypot(e.x - self.x, e.y - self.y) <= self.range]
        if not valid:
            return None
            
        if self.target_mode == "Strongest":
            heap = [(-e.hp, id(e), e) for e in valid]
            heapq.heapify(heap)
            return heap[0][2]
        elif self.target_mode == "Weakest":
            heap = [(e.hp, id(e), e) for e in valid]
            heapq.heapify(heap)
            return heap[0][2]
        elif self.target_mode == "Nearest":
            return min(valid, key=lambda e: math.hypot(e.x - self.x, e.y - self.y))
        else: # "First" (đi xa nhất)
            # path_index lớn hơn tức là xa hơn. Nếu cùng path_index, dùng khoảng cách đến waypoint tiếp theo.
            return max(valid, key=lambda e: e.path_index)

    def update(self, wave_manager, bullets):
        """Ghi đè trong lớp con — vòng lặp chính gọi thống nhất không if-else."""
        if self.shoot_timer > 0:
            self.shoot_timer -= 1
            
        if self.cooldown_timer > 0:
            self.cooldown_timer -= 1
            
        target = self._find_target(wave_manager.enemies)
        if target:
            dx, dy = target.x - self.x, target.y - self.y
            self.angle = math.degrees(math.atan2(-dy, dx)) - 90
            self.lean_target = 8.0   # Ngả về phía trước khi có địch
            if self.cooldown_timer <= 0:
                b_type = "arrow" if self.level == 1 else "magic"
                spd    = 8      if self.level == 1 else 6
                bullets.append(Bullet(self.x, self.y, target, self.damage, spd, b_type))
                self.cooldown_timer = self.cooldown
                self.shoot_timer = self.flash_duration
                play_sound("shoot_arrow")
        else:
            self.lean_target = 0.0   # Đứng thẳng khi rảnh
        # Smooth lean lerp
        self.lean_angle += (self.lean_target - self.lean_angle) * 0.15

    def draw(self, screen):
        """Tháp Cung Thủ — Stardew Valley 3-tone wood grain + Hades metallic specular."""
        x, y = self.x, self.y
        import random as _rng

        # Palettes
        # Stone base: cool blue-grey (hue-shifted shadow — Stardew)
        ST0 = ( 62,  68,  85)   # Shadow cool stone
        ST1 = (112, 118, 132)   # Midtone grey
        ST2 = (168, 174, 190)   # Highlight warm-white
        STS = (220, 225, 235)   # Specular glint
        # Moss (warm green — Stardew warm ambient)
        MS0 = ( 40,  72,  28)   # Moss shadow
        MS1 = ( 70, 108,  48)   # Moss mid
        MS2 = (105, 155,  72)   # Moss highlight
        # Wood: warm brown (hue-shift shadow = purple-brown, highlight = tan-yellow)
        WD0 = ( 48,  22,  10)   # Shadow dark oak (cool purple-brown)
        WD1 = ( 95,  55,  22)   # Midtone
        WD2 = (155,  95,  42)   # Highlight warm oak
        WDS = (200, 145,  78)   # Specular warm grain
        # Roof
        rf_c = (195, 48, 48) if self.level == 1 else (45, 70, 198)
        rf_h = (235, 88, 88) if self.level == 1 else (88, 118, 238)
        rf_d = (130, 18, 18) if self.level == 1 else (18, 30, 135)
        rf_t = (255,155,155) if self.level == 1 else (155,185,255)  # Terminator edge

        # ── SHADOW ──
        shd_s = pygame.Surface((60, 22), pygame.SRCALPHA)
        pygame.draw.ellipse(shd_s, (0, 0, 0, 65), (0, 0, 60, 22))
        screen.blit(shd_s, (x-30, y+2))

        # ── STONE BASE (3-tone ellipse — Stardew isometric) ──
        pygame.draw.ellipse(screen, ST0, (x-25, y-6,  50, 22))   # Shadow
        pygame.draw.ellipse(screen, ST1, (x-25, y-13, 50, 22))   # Midtone
        pygame.draw.ellipse(screen, ST2, (x-25, y-13, 30, 10))   # Highlight (light from top-left)
        pygame.draw.circle(screen, STS, (x-12, y-14), 2)          # Specular on stone top
        # Stone crack details (Stardew texture)
        pygame.draw.line(screen, ST0, (x-10, y-10), (x-5, y-6), 1)
        pygame.draw.line(screen, ST0, (x+5,  y-12), (x+10,y-8), 1)
        # Moss patch (3-tone — warm ambient fill)
        pygame.draw.ellipse(screen, MS0, (x-20, y-10, 18, 9))
        pygame.draw.ellipse(screen, MS1, (x-20, y-10, 18, 6))
        pygame.draw.ellipse(screen, MS2, (x-18, y-10,  8, 4))

        # ── BACK POSTS (3-tone wood grain) ──
        for px in [x-16, x+12]:
            pygame.draw.rect(screen, WD0, (px,   y-36, 6, 28), border_radius=1)  # Shadow side
            pygame.draw.rect(screen, WD1, (px+1, y-36, 4, 28), border_radius=1)  # Midtone
            pygame.draw.rect(screen, WD2, (px+1, y-36, 2, 28))                   # Highlight
            # Grain lines (Stardew texture detail)
            for gy in range(y-33, y-9, 5):
                pygame.draw.line(screen, WDS, (px+1, gy), (px+4, gy+1), 1)

        # ── FLOOR PLATFORM (3-tone wood ellipse) ──
        pygame.draw.ellipse(screen, WD0, (x-28, y-38, 56, 16))   # Shadow
        pygame.draw.ellipse(screen, WD1, (x-28, y-44, 56, 16))   # Midtone
        pygame.draw.ellipse(screen, WD2, (x-28, y-44, 32, 8))    # Highlight
        # Wood plank lines
        for i in range(-14, 20, 7):
            pygame.draw.line(screen, WD0, (x+i, y-43), (x+i, y-31), 1)
        # Plank highlight
        pygame.draw.line(screen, WDS, (x-26, y-44), (x+26, y-44), 1)

        # ── FRONT POSTS (3-tone) ──
        for px, edge in [(x-22, -1), (x+14, 1)]:
            pygame.draw.rect(screen, WD0, (px,   y-36, 8, 30), border_radius=1)
            pygame.draw.rect(screen, WD1, (px+1, y-36, 6, 30), border_radius=1)
            pygame.draw.rect(screen, WD2, (px+1, y-36, 3, 30))
            # Grain
            for gy in range(y-34, y-7, 6):
                pygame.draw.line(screen, WDS, (px+1, gy), (px+5, gy+1), 1)

        # ── TORCH (animated fire — Hades focal glow) ──
        tx, ty = x - 22, y - 22
        pygame.draw.rect(screen, WD0, (tx-2, ty, 5, 7), border_radius=1)
        pygame.draw.rect(screen, WD1, (tx-2, ty, 5, 4))
        # Multi-layer glow (Hades technique)
        _rng.seed(self.shoot_timer)  # Deterministic flicker
        for radius, col in [(5,(255,120,0,60)),(3,(255,180,30,100)),(2,(255,230,150,180))]:
            glow = pygame.Surface((radius*2+2, radius*2+2), pygame.SRCALPHA)
            pygame.draw.circle(glow, col, (radius+1, radius+1), radius)
            screen.blit(glow, (tx-radius+1, ty-radius-2))
        for _ in range(3):
            fx = tx + 1 + _rng.uniform(-1.5, 1.5)
            fy = ty - _rng.uniform(2, 7)
            pygame.draw.circle(screen, _rng.choice([(255,100,0),(255,200,30),(255,50,0)]), (int(fx), int(fy)), _rng.randint(1,2))

        # ── CROSSBEAMS (3-tone diagonal) ──
        pygame.draw.line(screen, WD0, (x-16, y-10), (x+12, y-30), 3)
        pygame.draw.line(screen, WD1, (x-16, y-10), (x+12, y-30), 2)
        pygame.draw.line(screen, WD0, (x-16, y-30), (x+12, y-10), 3)
        pygame.draw.line(screen, WD1, (x-16, y-30), (x+12, y-10), 2)

        # ── ARCHER SPRITE (3-tone Stardew-style) ──
        if self.level == 1:
            cs = pygame.Surface((30, 34), pygame.SRCALPHA)
            SK1 = (228, 182, 142); SK2 = (255, 218, 178); SK0 = (190, 120, 80)
            LD1 = (155, 128,  88); LD2 = (200, 168, 115)  # Leather
            # Body (3-tone leather)
            pygame.draw.rect(cs, LD1, (10,14, 9,12), border_radius=2)
            pygame.draw.rect(cs, LD2, (10,14, 6, 6), border_radius=2)
            # Head (3-tone skin)
            pygame.draw.circle(cs, SK0, (14, 8), 6)
            pygame.draw.circle(cs, SK1, (13, 7), 5)
            pygame.draw.circle(cs, SK2, (12, 6), 3)
            # Robin Hood hat (3-tone green)
            pygame.draw.polygon(cs, (28, 90, 40), [(8,7),(20,7),(14,-1)])
            pygame.draw.polygon(cs, (50,130, 62), [(10,7),(18,7),(14, 1)])
            # Bow (3-tone wood)
            pygame.draw.arc(cs, WD0, (1, 2,14,22), 0, math.pi, 3)
            pygame.draw.arc(cs, WD1, (1, 2,14,22), 0, math.pi, 2)
            pygame.draw.line(cs, (195,195,210), (8,2),(8,24), 1)  # String
            pygame.draw.line(cs, (220,220,220),(18,13),(8,13), 2)  # Arrow
            # Lean then rotate
            cs_leaned = pygame.transform.rotate(cs, self.lean_angle)
            rotated = pygame.transform.rotate(cs_leaned, self.angle)
            rect = rotated.get_rect(center=(x, y-50))
            screen.blit(rotated, rect.topleft)
        else:
            # Elite archer — steel armor 3-tone
            cs = pygame.Surface((30, 36), pygame.SRCALPHA)
            STA = (100,108,128); STB = (165,172,188); STC = (215,222,238); SS=(252,252,232)
            SK1 = (228, 182, 142); SK2 = (255, 218, 178)
            # Body armor
            pygame.draw.rect(cs, STA, (10,14, 9,14), border_radius=2)
            pygame.draw.rect(cs, STB, (10,14, 9, 8), border_radius=2)
            pygame.draw.rect(cs, STC, (10,14, 6, 4), border_radius=2)
            # Head
            pygame.draw.circle(cs, SK1, (14, 8), 6)
            pygame.draw.circle(cs, SK2, (13, 7), 3)
            # Steel helmet (3-tone)
            pygame.draw.polygon(cs, STA, [(8,8),(20,8),(14, 1)])
            pygame.draw.polygon(cs, STB, [(10,8),(18,8),(14, 2)])
            pygame.draw.circle(cs, SS,  (11, 3), 1)  # Helm specular
            # Crossbow (3-tone)
            pygame.draw.rect(cs, WD1, (12,10, 4,20))
            pygame.draw.polygon(cs, STA, [(3,16),(25,16),(14,10)])
            pygame.draw.polygon(cs, STB, [(4,16),(24,16),(14,11)])
            pygame.draw.line(cs,   STC, (3,16),(14,26), 1)
            pygame.draw.line(cs,   STC, (25,16),(14,26), 1)
            pygame.draw.circle(cs, SS, (5, 17), 1)  # Bow arm specular
            rotated = pygame.transform.rotate(cs, self.angle)
            rect = rotated.get_rect(center=(x, y-52))
            screen.blit(rotated, rect.topleft)

        # ── TENT ROOF (3-tone — Stardew warm light from top) ──
        # Shadow back face
        pygame.draw.polygon(screen, rf_d, [(x-28,y-46),(x+28,y-46),(x,y-66)])
        # Main front face (2 sides)
        pygame.draw.polygon(screen, rf_c, [(x-30,y-42),(x,y-78),(x+30,y-42),(x,y-52)])
        # Highlight left side (light from top-left)
        pygame.draw.polygon(screen, rf_h, [(x-30,y-42),(x,y-78),(x,y-52)])
        # Terminator line at ridge (Hades style)
        pygame.draw.line(screen, rf_t, (x-30,y-42),(x,y-78), 1)
        # Flag pole + flag (3-tone)
        pygame.draw.line(screen, WD0, (x, y-78),(x, y-94), 2)
        pygame.draw.line(screen, WD2, (x+1, y-78),(x+1, y-94), 1)
        flag_c2 = (255,210,60) if self.level == 1 else (60,255,120)
        flag_h2 = (255,245,180) if self.level == 1 else (180,255,210)
        pygame.draw.polygon(screen, flag_c2, [(x,y-94),(x+14,y-90),(x,y-84)])
        pygame.draw.polygon(screen, flag_h2, [(x,y-94),(x+14,y-90),(x,y-89)])  # Flag highlight

        # ── MUZZLE FLASH (Hades multi-layer glow) ──
        if self.shoot_timer > 0:
            flash_r = 5 + self.shoot_timer * 2
            fx = x + math.cos(math.radians(-self.angle+90)) * 26
            fy = (y-50) - math.sin(math.radians(-self.angle+90)) * 26
            for r, col in [(flash_r+4,(255,180,50,60)),(flash_r,(255,220,100,130)),(flash_r//2,(255,255,220,220))]:
                gf = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
                pygame.draw.circle(gf, col, (r+2, r+2), r)
                screen.blit(gf, (int(fx)-r-2, int(fy)-r-2))



    def upgrade(self):
        if self.level >= 2:
            return
        self.total_gold_spent += self.upgrade_cost
        self.level        += 1
        self.damage       += 25
        self.range        += 40 if self.level == 2 else 15
        self.upgrade_cost  = int(self.upgrade_cost * 1.5)


# ── i. Lớp con MagicTower — kế thừa Tower ────────────────────────────────────
class MagicTower(Tower):
    """
    Tháp MA THUẬT — bắn đạn AoE gây sát thương diện rộng.
    Ghi đè update() và draw() — đa hình với lớp cơ sở Tower.
    """
    def __init__(self, x, y):
        super().__init__(x, y)
        self.range        = 130
        self.damage       = 45
        self.cooldown     = 70
        self.upgrade_cost = 130
        self.total_gold_spent = 110
        self.aoe_radius   = AOE_RADIUS   # Bán kính nổ từ settings.py

    def update(self, wave_manager, bullets):
        """
        Ghi đè update — bắn đạn AoE thay vì đạn đơn.
        Truyền wave_manager vào Bullet để kích hoạt quét diện Spatial Hashing.
        """
        if self.shoot_timer > 0:
            self.shoot_timer -= 1
            
        if self.cooldown_timer > 0:
            self.cooldown_timer -= 1
            
        target = self._find_target(wave_manager.enemies)
        if target:
            dx, dy = target.x - self.x, target.y - self.y
            self.angle = math.degrees(math.atan2(-dy, dx)) - 90
            if self.cooldown_timer <= 0:
                bullets.append(Bullet(
                    self.x, self.y, target, self.damage, 5, "aoe",
                    wave_manager=wave_manager,  # Truyền wave_manager thay vì enemies list
                    aoe_radius=self.aoe_radius  # Bán kính nổ
                ))
                self.cooldown_timer = self.cooldown
                self.shoot_timer = self.flash_duration
                play_sound("shoot_magic")

    def draw(self, screen):
        """Tháp Pha Lê: Khối Obelisk đá đen bí ẩn, pha lê bay lơ lửng."""
        x, y = self.x, self.y
        
        # Bóng đổ
        pygame.draw.ellipse(screen, (0, 0, 0, 70), (x - 30, y + 2, 60, 24))
        
        # Sương mù phép thuật dưới đáy
        glow = pygame.Surface((60,40), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (140, 40, 255, 60), (0,0, 60,40))
        screen.blit(glow, (x-30, y-15))
        
        # Đế đá Obelisk (Đen/Tím than)
        pygame.draw.ellipse(screen, (30, 25, 40), (x-26, y-5, 52, 22))
        pygame.draw.ellipse(screen, (50, 45, 65), (x-26, y-12, 52, 22))
        
        # Thân tháp Obelisk nhọn, nhiều mặt
        pygame.draw.polygon(screen, (20, 15, 30), [(x-18, y-5), (x+18, y-5), (x+10, y-50), (x-10, y-50)])
        pygame.draw.polygon(screen, (40, 35, 55), [(x-18, y-5), (x, y-2), (x, y-50), (x-10, y-50)])
        pygame.draw.polygon(screen, (60, 50, 80), [(x, y-2), (x+18, y-5), (x+10, y-50), (x, y-50)])
        
        # Rune phát sáng nhịp nhàng
        pulse = math.sin(pygame.time.get_ticks() * 0.004) * 0.5 + 0.5
        rune_c = (int(150 + 105*pulse), int(50 + 100*pulse), 255)
        pygame.draw.polygon(screen, rune_c, [(x-5, y-20), (x, y-15), (x+5, y-20), (x, y-30)], 2)
        pygame.draw.circle(screen, rune_c, (x, y-38), 3)

        # Pha lê lớn lơ lửng (Floating Crystal)
        c_y = y - 65 + math.sin(pygame.time.get_ticks() * 0.003) * 6
        
        # Lớp sáng Halo
        halo_r = int(18 + 5*pulse)
        halo = pygame.Surface((halo_r*2, halo_r*2), pygame.SRCALPHA)
        pygame.draw.circle(halo, (180, 50, 255, 40), (halo_r, halo_r), halo_r)
        screen.blit(halo, (x - halo_r, c_y - halo_r))
        
        # Vòng sáng ma thuật (Pulse Rings)
        t = pygame.time.get_ticks() * 0.001
        for i in range(2):
            phase = (t + i * 0.5) % 1.0
            r = int(10 + phase * 35)
            alpha = int(150 * (1.0 - phase))
            ring = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.circle(ring, (200, 100, 255, alpha), (r, r), r, max(1, int(3 * (1.0 - phase))))
            screen.blit(ring, (x - r, c_y - r))

        # Lõi pha lê (Crystal Core)
        col_drk = (120, 20, 200) if self.level == 1 else (200, 20, 120)
        col_mid = (180, 60, 255) if self.level == 1 else (255, 60, 180)
        col_lit = (220, 140, 255) if self.level == 1 else (255, 140, 220)
        
        c_w, c_h = 12, 22
        if self.level == 2: c_w, c_h = 16, 28
        
        pygame.draw.polygon(screen, col_drk, [(x, c_y - c_h), (x + c_w, c_y), (x, c_y + c_h), (x - c_w, c_y)])
        pygame.draw.polygon(screen, col_mid, [(x, c_y - c_h), (x, c_y + c_h), (x - c_w, c_y)])
        pygame.draw.polygon(screen, col_lit, [(x, c_y - c_h), (x, c_y + c_h*0.8), (x - c_w*0.5, c_y)])
        
        # Các mảnh vỡ bay quanh (Orbiting shards)
        for i in range(3):
            ang = pygame.time.get_ticks() * 0.002 + i * (math.pi * 2 / 3)
            ox = math.cos(ang) * 25
            oy = math.sin(ang) * 8
            pygame.draw.polygon(screen, col_mid, [(x+ox, c_y+oy-4), (x+ox+3, c_y+oy), (x+ox, c_y+oy+4), (x+ox-3, c_y+oy)])
            pygame.draw.polygon(screen, col_lit, [(x+ox, c_y+oy-4), (x+ox, c_y+oy+4), (x+ox-3, c_y+oy)])

        # Hiệu ứng nạp phép / chớp lửa (Muzzle flash)
        if self.shoot_timer > 0:
            flash_r = 15 + (self.shoot_timer * 4)
            fx = x + math.cos(math.radians(-self.angle + 90)) * 20
            fy = c_y - math.sin(math.radians(-self.angle + 90)) * 20
            s = pygame.Surface((60, 60), pygame.SRCALPHA)
            pygame.draw.circle(s, (200, 100, 255, 180), (30, 30), flash_r)
            pygame.draw.circle(s, (255, 200, 255, 255), (30, 30), flash_r // 2)
            screen.blit(s, (fx - 30, fy - 30))

    def upgrade(self):
        """Nâng cấp: tăng damage, range và aoe_radius."""
        if self.level >= 2:
            return
        self.total_gold_spent += self.upgrade_cost
        self.level        += 1
        self.damage       += 20
        self.aoe_radius   += 15
        self.range        += 20
        self.upgrade_cost  = int(self.upgrade_cost * 1.6)
