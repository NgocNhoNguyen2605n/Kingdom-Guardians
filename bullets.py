"""
Mô-đun quản lý Đạn Bắn (Bullet) của trò chơi Kingdom Guardians.

Mô-đun này định nghĩa lớp Bullet đảm nhiệm toàn bộ vòng đời của một viên đạn:
bay về phía mục tiêu, va chạm, gây sát thương và hiển thị hiệu ứng hình ảnh.

Điểm nhấn thuật toán & đồ họa:
    - Quét diện nổ (AoE) dùng Spatial Hashing (tra cứu từ WaveManager) siêu tốc O(1) trung bình.
    - Hiệu ứng đạn cung xoay góc theo ma trận, đạn phép có vòng hào quang (Halo), 
      và hiệu ứng nổ lan rộng dần khi chạm mục tiêu (Ripple effect).

Lớp:
    Bullet: Viên đạn bay từ tháp đến mục tiêu. Hỗ trợ ba loại:
        - "arrow" : Tên cung — vẽ thân tên và mũi thép xoay theo hướng bay.
        - "magic" : Phép thuật thường — quả cầu xanh/tím phát sáng (Glow).
        - "aoe"   : Nổ diện — Gọi sóng nổ, lọc quái trong bán kính qua Spatial Hash,
            trừ máu tất cả và bung hiệu ứng vòng tròn tử thần trong 18 frame.
"""
import pygame
import math
from settings import *
from audio import play_sound

class Bullet:
    """
    Đạn bay từ tháp đến mục tiêu.
    Hỗ trợ 3 loại: 'arrow' (cung), 'magic' (phép), 'aoe' (nổ diện).
    """
    def __init__(self, x, y, target, damage, speed, b_type="arrow",
                 wave_manager=None, aoe_radius=0):
        self.x = x
        self.y = y
        self.target = target
        self.damage = damage
        self.speed = speed
        self.alive = True
        self.b_type = b_type
        self.angle = 0
        # ── Dữ liệu AoE ──────────────────────────────────────────────────────
        self.wave_manager = wave_manager # Tham chiếu quản lý wave chứa spatial_hash
        self.aoe_radius  = aoe_radius    # Bán kính nổ
        self.exploding   = False         # Đang trong pha nổ?
        self.explode_timer = 0           # Đếm ngược frame hiệu ứng nổ
        self.explode_x = 0              # Toạ độ tâm nổ
        self.explode_y = 0
        self.trail = []   # Vết đuôi (trail) của mũi tên

    def update(self):
        # Nếu đang trong pha nổ, đếm ngược rồi huỷ đạn
        if self.exploding:
            self.explode_timer -= 1
            if self.explode_timer <= 0:
                self.alive = False
            return

        dx = self.target.x - self.x
        dy = self.target.y - self.y
        dist = math.hypot(dx, dy)
        self.angle = math.degrees(math.atan2(-dy, dx))

        if dist < self.speed:
            if self.b_type == "aoe" and self.wave_manager is not None:
                # ── ii. Giải thuật quét diện AoE với Spatial Hashing ─────────
                self.explode_x = self.target.x
                self.explode_y = self.target.y
                
                # Lấy kẻ địch từ spatial hash xung quanh tâm nổ
                cell_size = self.wave_manager.cell_size
                cx = int(self.explode_x // cell_size)
                cy = int(self.explode_y // cell_size)
                cells_radius = int(math.ceil(self.aoe_radius / cell_size))
                
                for nx in range(cx - cells_radius, cx + cells_radius + 1):
                    for ny in range(cy - cells_radius, cy + cells_radius + 1):
                        for enemy in self.wave_manager.spatial_hash.get((nx, ny), []):
                            d = math.hypot(enemy.x - self.explode_x, enemy.y - self.explode_y)
                            if d <= self.aoe_radius:
                                enemy.hp -= self.damage
                                
                self.exploding = True
                self.explode_timer = 18
                play_sound("hit")
            else:
                # Đạn thường: chỉ trừ máu mục tiêu
                self.target.hp -= self.damage
                self.alive = False
                play_sound("hit")
        else:
            # Lưu trail cho mũi tên / magic (giữ tối đa 6 điểm)
            self.trail.append((self.x, self.y))
            if len(self.trail) > 6:
                self.trail.pop(0)
            self.x += (dx / dist) * self.speed
            self.y += (dy / dist) * self.speed

    def draw(self, screen):
        if self.exploding:
            progress = 1.0 - (self.explode_timer / 18)
            t_frac   = self.explode_timer / 18   # 1.0 → 0.0
            # Ring 1: Trắng rực lõi (nhỏ, fade nhanh)
            r1 = max(1, int(self.aoe_radius * 0.35 * progress))
            a1 = max(0, int(255 * t_frac))
            if r1 > 0:
                s1 = pygame.Surface((r1*2+2, r1*2+2), pygame.SRCALPHA)
                pygame.draw.circle(s1, (255, 255, 255, a1), (r1+1, r1+1), r1)
                screen.blit(s1, (int(self.explode_x)-r1-1, int(self.explode_y)-r1-1))
            # Ring 2: Cam nắng (giữa)
            r2 = max(1, int(self.aoe_radius * 0.65 * progress))
            a2 = max(0, int(220 * t_frac * 0.85))
            if r2 > 0:
                s2 = pygame.Surface((r2*2+2, r2*2+2), pygame.SRCALPHA)
                pygame.draw.circle(s2, (255, 140, 30, a2), (r2+1, r2+1), r2, max(1, r2//4))
                screen.blit(s2, (int(self.explode_x)-r2-1, int(self.explode_y)-r2-1))
            # Ring 3: Đỏ/Tím ngoài (viền lan rộng)
            radius = max(1, int(self.aoe_radius * progress))
            alpha  = max(0, int(180 * t_frac))
            if radius > 0:
                s3 = pygame.Surface((radius*2+10, radius*2+10), pygame.SRCALPHA)
                cx, cy = radius+5, radius+5
                pygame.draw.circle(s3, (200, 60, 255, alpha//4), (cx,cy), radius)
                pygame.draw.circle(s3, (200, 60, 255, alpha),    (cx,cy), radius, max(2, radius//6))
                screen.blit(s3, (int(self.explode_x)-radius-5, int(self.explode_y)-radius-5))
            return

        if self.b_type == "arrow":
            # Vẽ trail trước
            for i, (tx, ty) in enumerate(self.trail):
                trail_alpha = int(120 * (i / max(1, len(self.trail))))
                trail_r = max(1, i // 2)
                ts = pygame.Surface((trail_r*2+2, trail_r*2+2), pygame.SRCALPHA)
                pygame.draw.circle(ts, (200, 160, 80, trail_alpha), (trail_r+1, trail_r+1), trail_r)
                screen.blit(ts, (int(tx)-trail_r-1, int(ty)-trail_r-1))
            length = 12
            rad = math.radians(-self.angle)
            cos_a, sin_a = math.cos(rad), math.sin(rad)
            tip_x  = self.x + cos_a * length
            tip_y  = self.y + sin_a * length
            tail_x = self.x - cos_a * length
            tail_y = self.y - sin_a * length
            # Thân tẫn gỗ
            pygame.draw.line(screen, (120,70,20), (tail_x,tail_y), (tip_x,tip_y), 2)
            pygame.draw.line(screen, (160,110,50),(tail_x,tail_y),(self.x,self.y), 1)
            # Lông vũ (fletching) cượng tại đuôi
            perp_x, perp_y = -sin_a * 4, cos_a * 4
            pygame.draw.line(screen, (200,180,160),
                             (tail_x+perp_x, tail_y+perp_y),
                             (tail_x+cos_a*6, tail_y+sin_a*6), 1)
            pygame.draw.line(screen, (200,180,160),
                             (tail_x-perp_x, tail_y-perp_y),
                             (tail_x+cos_a*6, tail_y+sin_a*6), 1)
            # Mũi thép tam giác
            a_s = pygame.Surface((12,12), pygame.SRCALPHA)
            pygame.draw.polygon(a_s, (210,215,225), [(0,2),(0,10),(10,6)])
            pygame.draw.polygon(a_s, (240,245,255), [(0,2),(0,10),(10,6)], 1)
            r_a = pygame.transform.rotate(a_s, self.angle)
            screen.blit(r_a, r_a.get_rect(center=(tip_x,tip_y)).topleft)

        elif self.b_type == "magic":
            # Quả cầu phép 3 lớp glow
            gx, gy = int(self.x), int(self.y)
            g = pygame.Surface((22,22), pygame.SRCALPHA)
            pygame.draw.circle(g, (80,0,200,100), (11,11), 10)
            screen.blit(g, (gx-11, gy-11))
            pygame.draw.circle(screen, (0,180,255), (gx,gy), 6)
            pygame.draw.circle(screen, (100,220,255),(gx,gy), 4)
            pygame.draw.circle(screen, WHITE,        (gx,gy), 2)

        else:  # aoe
            gx, gy = int(self.x), int(self.y)
            # Hào quang ngoài
            g = pygame.Surface((28,28), pygame.SRCALPHA)
            pygame.draw.circle(g, (180,0,255,80),  (14,14), 13)
            screen.blit(g, (gx-14,gy-14))
            # Lớp giữa
            pygame.draw.circle(screen, (140,0,220), (gx,gy), 9)
            pygame.draw.circle(screen, (190,60,255),(gx,gy), 6)
            pygame.draw.circle(screen, (220,140,255),(gx,gy),3)
            pygame.draw.circle(screen, WHITE,       (gx,gy), 1)
            # Vòng năng lượng xoay quanh
            for i in range(4):
                ang = math.radians(self.walk_timer * 8 + i * 90) if hasattr(self,'walk_timer') else math.radians(i*90)
                ox = int(math.cos(ang) * 11)
                oy = int(math.sin(ang) * 11)
                pygame.draw.circle(screen, (255,100,255),(gx+ox,gy+oy), 2)
