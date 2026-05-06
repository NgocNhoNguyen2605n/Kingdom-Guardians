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
        self.upgrade_cost = 60
        self.total_gold_spent = 50
        self.angle        = 0
        self.shoot_timer  = 0
        self.flash_duration = 5
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
            if self.cooldown_timer <= 0:
                b_type = "arrow" if self.level == 1 else "magic"
                spd    = 8      if self.level == 1 else 6
                bullets.append(Bullet(self.x, self.y, target, self.damage, spd, b_type))
                self.cooldown_timer = self.cooldown
                self.shoot_timer = self.flash_duration

    def draw(self, screen):
        """Tháp Gỗ: Nền đá, cột gỗ, chòi canh bạt bọc thép."""
        x, y = self.x, self.y
        
        # Bóng đổ lớn
        pygame.draw.ellipse(screen, (0, 0, 0, 70), (x - 28, y + 2, 56, 24))
        
        # Đế đá thô
        pygame.draw.ellipse(screen, (90, 95, 100), (x - 24, y - 5, 48, 20))
        pygame.draw.ellipse(screen, (130, 135, 140), (x - 24, y - 12, 48, 20))
        pygame.draw.ellipse(screen, (100, 105, 110), (x - 24, y - 12, 48, 20), 2)
        # Rêu trên đá
        pygame.draw.ellipse(screen, (60, 90, 40), (x - 22, y - 8, 20, 10))
        
        # Cột gỗ phía sau
        pygame.draw.rect(screen, (50, 30, 15), (x - 18, y - 35, 6, 28), border_radius=1)
        pygame.draw.rect(screen, (50, 30, 15), (x + 12, y - 35, 6, 28), border_radius=1)
        
        # Sàn gỗ chòi canh
        pygame.draw.ellipse(screen, (70, 40, 20), (x - 26, y - 40, 52, 16))
        pygame.draw.ellipse(screen, (110, 70, 30), (x - 26, y - 44, 52, 16))
        pygame.draw.ellipse(screen, (80, 50, 20), (x - 26, y - 44, 52, 16), 2)
        # Tấm ván gỗ (wood planks)
        for i in range(-16, 20, 8):
            pygame.draw.line(screen, (90, 55, 25), (x + i, y - 42), (x + i, y - 30), 1)

        # Cột gỗ phía trước (đè lên sàn gỗ một chút)
        pygame.draw.rect(screen, (80, 50, 25), (x - 22, y - 35, 8, 30), border_radius=1)
        pygame.draw.rect(screen, (80, 50, 25), (x + 14, y - 35, 8, 30), border_radius=1)
        pygame.draw.line(screen, (50, 30, 15), (x - 22, y - 35), (x - 22, y - 5), 1)
        pygame.draw.line(screen, (50, 30, 15), (x + 14, y - 35), (x + 14, y - 5), 1)
        
        # Thanh chéo gia cố (Crossbeams)
        pygame.draw.line(screen, (60, 35, 18), (x - 18, y - 10), (x + 14, y - 30), 3)
        pygame.draw.line(screen, (70, 45, 22), (x - 18, y - 30), (x + 14, y - 10), 3)

        # Cung thủ
        if self.level == 1:
            cs = pygame.Surface((26,30), pygame.SRCALPHA)
            # Thân (giáp da lính)
            pygame.draw.rect(cs, (160, 140, 100), (9,12,8,10), border_radius=2)
            pygame.draw.rect(cs, (120, 100, 70), (9,12,8, 5), border_radius=2)
            # Đầu + mũ nón lá nhỏ (Robin Hood style)
            pygame.draw.circle(cs, (240, 200, 160),(13, 8), 5)
            pygame.draw.polygon(cs, (40, 120, 60), [(8,6), (18,6), (13, 0)])
            # Cung gỗ
            pygame.draw.arc(cs, (100, 60, 20), (2,2,12,20), 0, math.pi, 3)
            pygame.draw.line(cs, (200, 200, 200), (8,2), (8,22), 1)
            # Tên đang giương
            pygame.draw.line(cs, (220, 220, 220),(16,12),(8, 12), 2)
            rotated = pygame.transform.rotate(cs, self.angle)
            rect = rotated.get_rect(center=(x, y-48))
            screen.blit(rotated, rect.topleft)
        else:
            # Cung thủ cấp 2 (Elite Crossbow / Sniper)
            cs = pygame.Surface((28,32), pygame.SRCALPHA)
            pygame.draw.rect(cs, (40, 40, 50), (10,14,8,12), border_radius=2)
            pygame.draw.rect(cs, (80, 80, 90), (10,14,8, 6), border_radius=2)
            pygame.draw.circle(cs, (240, 200, 160),(14, 9), 5)
            # Mũ sắt thép
            pygame.draw.polygon(cs, (160, 170, 180), [(9,8), (19,8), (14, 2)])
            pygame.draw.polygon(cs, (200, 210, 220), [(11,8), (17,8), (14, 2)])
            # Nỏ (Crossbow) bằng kim loại
            pygame.draw.rect(cs, (100, 80, 50), (12, 10, 4, 18))
            pygame.draw.polygon(cs, (180, 190, 200), [(4,15), (24,15), (14, 10)])
            pygame.draw.line(cs, (250, 250, 250), (4,15), (14,24), 1)
            pygame.draw.line(cs, (250, 250, 250), (24,15), (14,24), 1)
            rotated = pygame.transform.rotate(cs, self.angle)
            rect = rotated.get_rect(center=(x, y-50))
            screen.blit(rotated, rect.topleft)

        # Mái bạt (Tent Roof)
        roof_c = (200, 60, 60) if self.level == 1 else (60, 80, 200)
        roof_l = (240, 90, 90) if self.level == 1 else (90, 120, 240)
        roof_d = (140, 30, 30) if self.level == 1 else (30, 40, 140)
        
        # Vải bạt sau
        pygame.draw.polygon(screen, roof_d, [(x - 26, y - 46), (x + 26, y - 46), (x, y - 65)])
        # Vải bạt trước
        pygame.draw.polygon(screen, roof_c, [(x - 28, y - 42), (x, y - 75), (x + 28, y - 42), (x, y - 50)])
        pygame.draw.polygon(screen, roof_l, [(x - 28, y - 42), (x, y - 75), (x, y - 50)]) # Sáng 1 bên
        # Cột cờ trên đỉnh
        pygame.draw.line(screen, (50, 30, 15), (x, y - 75), (x, y - 90), 2)
        flag_c = (255, 200, 50) if self.level == 1 else (50, 255, 100)
        pygame.draw.polygon(screen, flag_c, [(x, y - 90), (x + 12, y - 86), (x, y - 82)])

        # Muzzle Flash (Chớp lửa)
        if self.shoot_timer > 0:
            import random
            flash_radius = 6 + (self.shoot_timer * 2)
            fx = x + math.cos(math.radians(-self.angle + 90)) * 24
            fy = (y - 48) - math.sin(math.radians(-self.angle + 90)) * 24
            s = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 200, 50, 150), (15, 15), flash_radius)
            pygame.draw.circle(s, (255, 255, 200, 255), (15, 15), flash_radius // 2)
            screen.blit(s, (fx - 15, fy - 15))

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
        self.upgrade_cost = 90
        self.total_gold_spent = 80
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
