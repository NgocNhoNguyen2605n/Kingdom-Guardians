"""
Mô-đun quản lý Tháp Phòng Thủ (Tower) của trò chơi Kingdom Guardians.

Mô-đun này triển khai hệ thống tháp theo hướng đối tượng với kế thừa và đa hình,
cho phép vòng lặp chính xử lý mọi loại tháp thống nhất qua cùng một giao diện.

Lớp:
    Tower      : Lớp cơ sở — Tháp Cung Thủ bắn đạn tên/phép đơn mục tiêu.
        Cung cấp _find_target() dùng chung và giao diện update() / draw() / upgrade().
    MagicTower : Kế thừa Tower — Tháp Ma Thuật bắn đạn AoE gây sát thương diện rộng.
        Ghi đè update() để bắn Bullet loại "aoe" kèm danh sách kẻ địch (enemies_ref),
        ghi đè draw() để vẽ tháp tím huyền bí với tinh thể phát sáng,
        ghi đè upgrade() để tăng thêm aoe_radius cùng damage và range.
"""
import pygame
import math
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
        """Tìm kẻ địch theo chế độ ưu tiên (First, Strongest, Weakest)."""
        valid = [e for e in enemies if math.hypot(e.x - self.x, e.y - self.y) <= self.range]
        if not valid:
            return None
            
        if self.target_mode == "Strongest":
            return max(valid, key=lambda e: e.hp)
        elif self.target_mode == "Weakest":
            return min(valid, key=lambda e: e.hp)
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
        """Tháp đá gach với chọi gác, lỗ châu mai và nhân vật chi tiết."""
        x, y = self.x, self.y
        
        # Vẽ bóng đổ dưới tháp (Ellipse đen, alpha thấp)
        pygame.draw.ellipse(screen, (0, 0, 0, 60), (x - 24, y + 5, 48, 20))
        
        # Đế tròn (đá xám sẫn)
        pygame.draw.circle(screen, (70,70,75),   (x, y+5), 20)
        pygame.draw.circle(screen, (105,105,115),(x, y),   20)
        pygame.draw.circle(screen, (50,50,55),   (x, y),   20, 2)
        # Đường rãnh thân đá
        pygame.draw.arc(screen, (85,85,95), (x-18,y-18,36,36), 0.3, 2.8, 3)
        # Thân tháp gạch
        pygame.draw.rect(screen, (115,105,95), (x-13, y-28, 26, 28), border_radius=2)
        # Gạch tường (2 hàng xen kẻ)
        for row, offset in [(0,0),(1,6)]:
            ry = y - 28 + row * 10
            for col in range(3):
                bx = x - 12 + offset + col * 13
                pygame.draw.rect(screen, (95,85,78),  (bx, ry, 12, 9), border_radius=1)
                pygame.draw.rect(screen, (140,125,110),(bx, ry, 12, 4), border_radius=1)
        # Lỗ châu mai (3 đầu)
        for i in range(3):
            mx = x - 10 + i * 10
            pygame.draw.rect(screen, (55,45,38), (mx, y-36, 6, 10), border_radius=2)
        pygame.draw.rect(screen, (75,65,55), (x-13, y-30, 26, 4))
        # Cửa tháp
        pygame.draw.rect(screen, (40,30,20), (x-5, y-12, 10, 12), border_radius=4)
        pygame.draw.rect(screen, (80,65,50), (x-5, y-12, 10, 12), 1, border_radius=4)
        if self.level == 1:
            # Cung thủ chi tiết
            cs = pygame.Surface((22,26), pygame.SRCALPHA)
            # Thân (giáp da xanh)
            pygame.draw.rect(cs, (30,100,50), (7,10,8,10), border_radius=2)
            pygame.draw.rect(cs, (50,130,70), (7,10,8, 5), border_radius=2)
            # Đầu + mũ
            pygame.draw.circle(cs, (220,175,120),(11, 7), 5)
            pygame.draw.rect(cs, (50,80,30), (7, 3,8, 5), border_radius=2)
            # Cung
            pygame.draw.arc(cs, (130,90,40), (1,1,10,16), 0, math.pi, 2)
            pygame.draw.line(cs, (180,140,80), (6,1),(6,17), 1)
            # Cung
            pygame.draw.line(cs, (210,215,220),(14,8),(14, 2), 2)
            rotated = pygame.transform.rotate(cs, self.angle)
            rect = rotated.get_rect(center=(x, y-32))
            screen.blit(rotated, rect.topleft)
        else:
            # Phù thủy cấp 2
            cs = pygame.Surface((24,28), pygame.SRCALPHA)
            pygame.draw.circle(cs, (45,0,130), (12,14), 7)
            pygame.draw.circle(cs, (70,0,170), (12,14), 7, 2)
            pygame.draw.circle(cs, (230,185,135),(12,14), 5)
            pygame.draw.polygon(cs, (30,0,100), [(7,12),(17,12),(12,1)])
            pygame.draw.polygon(cs, (140,0,220), [(7,12),(17,12),(12,1)], 1)
            pygame.draw.line(cs, (160,110,50), (16,14),(21,4), 2)
            pygame.draw.circle(cs, (0,230,255),(21,4), 4)
            pygame.draw.circle(cs, (180,255,255),(21,4), 2)
            rotated = pygame.transform.rotate(cs, self.angle)
            rect = rotated.get_rect(center=(x, y-34))
            screen.blit(rotated, rect.topleft)
        # Chấm level
        for i in range(self.level):
            pygame.draw.circle(screen, (0,210,255), (x-8+i*8, y+16), 3)
            pygame.draw.circle(screen, (150,240,255),(x-8+i*8, y+16), 1)

        # Muzzle Flash (Chớp lửa khi bắn)
        if self.shoot_timer > 0:
            import random
            flash_radius = 6 + (self.shoot_timer * 2)
            # Tính toán vị trí nòng súng theo góc
            fx = x + math.cos(math.radians(-self.angle + 90)) * 20
            fy = (y - 32) - math.sin(math.radians(-self.angle + 90)) * 20
            
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
        """Tháp Pha Lê: thân cẩm thạch tím, tinh thể nhiều lớp, đại phù thủy."""
        x, y = self.x, self.y
        
        # Vẽ bóng đổ dưới tháp
        pygame.draw.ellipse(screen, (0, 0, 0, 60), (x - 24, y + 5, 48, 20))
        
        # Đế phun sương tím
        glow = pygame.Surface((50,50), pygame.SRCALPHA)
        pygame.draw.circle(glow, (100,0,180,40), (25,25), 24)
        screen.blit(glow, (x-25, y-21))
        pygame.draw.circle(screen, (45,25,75), (x,y+5), 22)
        pygame.draw.circle(screen, (65,40,105),(x,y),   22)
        pygame.draw.circle(screen, (30,15,55), (x,y),   22, 2)
        # Đường đá cẩm thạch
        pygame.draw.arc(screen,(80,50,120),(x-20,y-20,40,40),0.4,2.6,3)
        # Thân tháp tím cẩm thạch
        pygame.draw.rect(screen, (55,35,90),  (x-14,y-30,28,30), border_radius=3)
        pygame.draw.rect(screen, (75,50,115), (x-14,y-30,28,14), border_radius=3)
        pygame.draw.rect(screen, (30,15,55),  (x-14,y-30,28,30), 2, border_radius=3)
        # Rune phát sáng trên tường
        for rx, ry in [(x-8,y-25),(x+4,y-20),(x-4,y-12)]:
            pygame.draw.circle(screen, (180,80,255), (rx,ry), 2)
            pygame.draw.circle(screen, (220,150,255),(rx,ry), 1)
        # Cửa vòm huyền bí
        pygame.draw.rect(screen, (15,5,40), (x-5,y-13,10,13), border_radius=5)
        pygame.draw.rect(screen, (100,50,180),(x-5,y-13,10,13), 1, border_radius=5)
        # Ban công pha lê
        pygame.draw.rect(screen, (80,55,125),(x-16,y-32,32, 5), border_radius=2)
        for i in range(4):
            pygame.draw.rect(screen,(100,70,150),(x-14+i*9,y-37,6,7),border_radius=2)
        # Tinh thể nóc tím 3 tầng
        pygame.draw.circle(screen, (160,60,220),(x,y-36),  8)
        pygame.draw.circle(screen, (200,120,255),(x,y-36), 5)
        pygame.draw.circle(screen, (230,190,255),(x,y-36), 2)
        pygame.draw.circle(screen, WHITE,        (x,y-36), 1)
        # Vệnh tinh thể nhỏ 2 bên
        pygame.draw.circle(screen, (180,80,240),(x-9,y-30), 4)
        pygame.draw.circle(screen, (220,160,255),(x-9,y-30),2)
        pygame.draw.circle(screen, (180,80,240),(x+9,y-30), 4)
        pygame.draw.circle(screen, (220,160,255),(x+9,y-30),2)
        # Đại phù thủy
        cs = pygame.Surface((28,30), pygame.SRCALPHA)
        pygame.draw.circle(cs, (18,0,55),  (14,15), 9)
        pygame.draw.circle(cs, (90,0,170), (14,15), 9, 2)
        pygame.draw.circle(cs, (225,182,138),(14,15),6)
        pygame.draw.polygon(cs, (12,0,45), [(7,13),(21,13),(14,0)])
        pygame.draw.polygon(cs, (150,0,210),[(7,13),(21,13),(14,0)], 1)
        pygame.draw.line(cs, (160,110,50),(18,15),(24,3), 2)
        pygame.draw.circle(cs, (255,80,255),(24,3), 5)
        pygame.draw.circle(cs, (255,200,255),(24,3),2)
        pygame.draw.circle(cs, WHITE,(24,3), 1)
        rotated = pygame.transform.rotate(cs, self.angle)
        rect = rotated.get_rect(center=(x,y-42))
        screen.blit(rotated, rect.topleft)
        # Chấm level màu tím xếc
        for i in range(self.level):
            pygame.draw.circle(screen,(200,80,255),(x-8+i*9,y+18),4)
            pygame.draw.circle(screen,(230,160,255),(x-8+i*9,y+18),2)
            
        # Hiệu ứng nạp phép (tinh thể sáng dần)
        charge_ratio = 1.0 - (max(0, self.cooldown_timer) / self.cooldown)
        if charge_ratio > 0.3:
            glow_radius = int(25 + 15 * charge_ratio)
            glow_surf = pygame.Surface((glow_radius*2, glow_radius*2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (150, 50, 255, int(60 * charge_ratio)), (glow_radius, glow_radius), glow_radius)
            screen.blit(glow_surf, (x - glow_radius, y - 36 - glow_radius))

        # Vẽ Muzzle Flash khi bắn
        if self.shoot_timer > 0:
            import random
            flash_radius = 8 + (self.shoot_timer * 3)
            fx = x + math.cos(math.radians(-self.angle + 90)) * 20
            fy = (y - 42) - math.sin(math.radians(-self.angle + 90)) * 20
            
            s = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(s, (200, 100, 255, 200), (20, 20), flash_radius)
            pygame.draw.circle(s, (255, 200, 255, 255), (20, 20), flash_radius // 2)
            screen.blit(s, (fx - 20, fy - 20))

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
