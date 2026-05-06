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

# ── iii. Bảng tra cứu (Dictionary / HashMap) cấu hình kẻ địch ────────────────
# Mọi tham số HP, tốc độ, phần thưởng được lưu tập trung theo khoá tên loại.
# WaveManager tra bảng này khi sinh kẻ địch — thêm loại mới chỉ cần 1 dòng.
ENEMY_CONFIG = {
    "normal": {"hp": 100, "speed": 1.3, "reward": 15},
    "fast":   {"hp":  60, "speed": 2.8, "reward": 20},
    "tank":   {"hp": 280, "speed": 0.7, "reward": 35},
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

    def _move(self):
        """Logic di chuyển dọc path — dùng chung cho mọi lớp con."""
        self.walk_timer += 1
        if self.path_index < len(self.path) - 1:
            target_x, target_y = self.path[self.path_index + 1]
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy)
            self.move_angle = math.degrees(math.atan2(-dy, dx)) - 90
            if dist < self.speed:
                self.path_index += 1
            else:
                self.x += (dx / dist) * self.speed
                self.y += (dy / dist) * self.speed
        else:
            self.alive = False

    def update(self):
        """
        Giao diện đa hình — vòng lặp chính gọi enemy.update() không phân biệt loại.
        Lớp con ghi đè để thêm hành vi riêng.
        """
        self._move()

    def _draw_health_bar(self, screen, bar_width=24, bar_height=5, y_offset=-22):
        """Thanh máu chi tiết với viền đen bo góc và gradient chuyển màu."""
        hp_perc = max(0, self.hp / self.max_hp)
        bx = int(self.x - bar_width // 2)
        by = int(self.y + y_offset)
        
        # Viền đen dày dặn hơn
        pygame.draw.rect(screen, (10,10,10), (bx-2, by-2, bar_width+4, bar_height+4), border_radius=4)
        pygame.draw.rect(screen, (40,40,40), (bx, by, bar_width, bar_height), border_radius=2)
        
        fill_w = int(bar_width * hp_perc)
        if fill_w > 0:
            # Nội suy màu từ Đỏ -> Vàng -> Xanh lá
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
            # Highlight sáng phía trên cho có khối
            light = tuple(min(255, c + 80) for c in color)
            pygame.draw.rect(screen, light, (bx, by, fill_w, max(1, bar_height//2)), border_radius=2)

    def draw(self, screen, is_dying=False):
        """Hiệp sĩ bọc giáp đầy đủ: mũ giáp có mào, khiên xanh, kiếm bạc."""
        if is_dying:
            alpha = int(255 * (self.death_timer / 15))
            self.move_angle += 12 # Xoay ngã xuống
            y_off = (15 - self.death_timer) # Chìm dần
            pygame.draw.ellipse(screen, (0,0,0, int(60*self.death_timer/15)), (self.x-14, self.y+8, 28, 9))
        else:
            alpha = 255
            y_off = math.sin(self.walk_timer * 0.3) * 2
            pygame.draw.ellipse(screen, (0,0,0,60), (self.x-14, self.y+8, 28, 9))

        s = pygame.Surface((38, 42), pygame.SRCALPHA)
        # Chân (có animation bước đi nếu còn sống)
        if not is_dying:
            leg_y1 = math.sin(self.walk_timer * 0.4) * 4
            leg_y2 = math.sin(self.walk_timer * 0.4 + math.pi) * 4
        else:
            leg_y1 = leg_y2 = 0

        pygame.draw.rect(s, (110,110,120), (11,28+leg_y1, 6,11), border_radius=2)
        pygame.draw.rect(s, (100,100,110), (21,28+leg_y2, 6,11), border_radius=2)
        pygame.draw.rect(s, (140,140,150), (11,35+leg_y1, 6, 4), border_radius=1)
        pygame.draw.rect(s, (130,130,140), (21,35+leg_y2, 6, 4), border_radius=1)
        # Thân giáp
        pygame.draw.rect(s, (130,130,145), (9,14,20,16), border_radius=3)
        pygame.draw.ellipse(s, (155,155,170), (12,16,14,10))
        pygame.draw.line(s, (170,170,185), (19,15),(19,28), 1)
        # Đai lưng
        pygame.draw.rect(s, (80,45,10), (9,29,20, 3))
        pygame.draw.rect(s, (160,130,20),(17,28, 6, 5))
        # Vai (pauldrons)
        pygame.draw.ellipse(s, (140,140,155), (3,12,12, 8))
        pygame.draw.ellipse(s, (140,140,155), (23,12,12, 8))
        pygame.draw.ellipse(s, (165,165,180), (3,11,12, 5))
        pygame.draw.ellipse(s, (165,165,180), (23,11,12, 5))
        # Mũ giáp
        pygame.draw.circle(s, (160,160,175), (19,10), 9)
        pygame.draw.circle(s, (140,140,155), (19,10), 9, 2)
        # Kính che mặt
        pygame.draw.rect(s, (35,35,45), (13, 8,12, 5), border_radius=2)
        pygame.draw.line(s, (70,70,80), (13,10),(25,10), 1)
        # Mào đỏ
        pygame.draw.polygon(s, (190,20,20), [(16,1),(22,1),(19,-5)])
        pygame.draw.polygon(s, (220,40,40), [(15,6),(23,6),(19,0)])
        # Khiên (trái)
        pygame.draw.polygon(s, (25,60,155), [(2,13),(9,13),(9,23),(5,27),(2,23)])
        pygame.draw.polygon(s, (180,200,220), [(2,13),(9,13),(9,23),(5,27),(2,23)], 1)
        pygame.draw.circle(s, (200,180,20), (5,19), 2)
        # Kiếm (phải)
        pygame.draw.rect(s, (110,75,25), (27,20, 4, 8), border_radius=1)
        pygame.draw.rect(s, (150,130,50), (25,17, 8, 2))
        pygame.draw.polygon(s, (210,215,225), [(28,4),(30,4),(29,17)])
        pygame.draw.line(s, (240,245,255), (29,5),(29,16), 1)
        if is_dying:
            s.set_alpha(alpha)
        rotated = pygame.transform.rotate(s, self.move_angle)
        rect = rotated.get_rect(center=(self.x, self.y + y_off))
        screen.blit(rotated, rect.topleft)
        if not is_dying:
            self._draw_health_bar(screen, bar_width=24, bar_height=5)


# ── i. Lớp con FastEnemy — kế thừa Enemy ────────────────────────────────────
class FastEnemy(Enemy):
    """
    Kẻ địch TỐC ĐỘ — thân gọn, màu xanh lá neon, di chuyển rất nhanh.
    Ghi đè update() và draw() — đa hình với lớp cơ sở Enemy.
    """
    def __init__(self, path):
        super().__init__(path, "fast")      # Tra ENEMY_CONFIG["fast"]

    def update(self):
        """Ghi đè update — hiện tại thêm bước nhảy nhanh nhịp hơn."""
        self._move()

    def draw(self, screen, is_dying=False):
        """Sát thủ áo choàng tối: mắt xanh phát quang, dao găm bạc, khói chân."""
        if is_dying:
            alpha = int(255 * (self.death_timer / 15))
            self.move_angle += 15 # Xoay ngã xuống nhanh
            y_off = (15 - self.death_timer)
            pygame.draw.ellipse(screen, (0,0,0, int(50*self.death_timer/15)), (self.x-9, self.y+7, 18, 7))
        else:
            alpha = 255
            y_off = math.sin(self.walk_timer * 0.6) * 3
            pygame.draw.ellipse(screen, (0,0,0,50), (self.x-9, self.y+7, 18, 7))
            
        s = pygame.Surface((30, 36), pygame.SRCALPHA)
        # Chân gọn (bước siêu nhanh)
        if not is_dying:
            leg_y1 = math.sin(self.walk_timer * 0.7) * 4
            leg_y2 = math.sin(self.walk_timer * 0.7 + math.pi) * 4
        else:
            leg_y1 = leg_y2 = 0
            
        pygame.draw.rect(s, (25,55,28), ( 9,25+leg_y1, 5, 9), border_radius=1)
        pygame.draw.rect(s, (20,50,23), (16,25+leg_y2, 5, 9), border_radius=1)
        pygame.draw.rect(s, (35,70,35), ( 9,30+leg_y1, 5, 4), border_radius=1)
        pygame.draw.rect(s, (30,65,30), (16,30+leg_y2, 5, 4), border_radius=1)
        # Áo choàng (cloak) tối
        pygame.draw.polygon(s, (20,55,28), [(4,12),(26,12),(28,25),(15,32),(2,25)])
        pygame.draw.polygon(s, (35,80,40), [(4,12),(26,12),(28,25),(15,32),(2,25)], 1)
        # Đai và túi đạn
        pygame.draw.rect(s, (110,75,25), (5,20,20, 2))
        pygame.draw.circle(s, (160,130,30), (15,21), 2)
        pygame.draw.rect(s, (80,50,15), (20,21, 4, 5), border_radius=1)
        # Đầu / Mũ trùm
        pygame.draw.circle(s, (18,50,22), (15, 9), 8)
        pygame.draw.polygon(s, (12,38,16), [(9,9),(21,9),(15,-1)])
        # Mặt trong bóng tối
        pygame.draw.circle(s, (190,145,100), (15, 9), 5)
        shd = pygame.Surface((12,5), pygame.SRCALPHA)
        pygame.draw.ellipse(shd, (10,30,12,160), (0,0,12,5))
        s.blit(shd, (9,7))
        # Mắt xanh neon
        pygame.draw.circle(s, (0,230,90), (12, 9), 2)
        pygame.draw.circle(s, (0,230,90), (18, 9), 2)
        pygame.draw.circle(s, (180,255,200),(12, 9), 1)
        pygame.draw.circle(s, (180,255,200),(18, 9), 1)
        # Dao găm trái
        pygame.draw.rect(s, (90,60,20), (2,13, 3, 7), border_radius=1)
        pygame.draw.polygon(s, (205,215,225), [(2,3),(5,3),(4,13),(2,13)])
        pygame.draw.line(s, (240,245,255), (3,4),(3,12), 1)
        # Dao găm phải
        pygame.draw.rect(s, (90,60,20), (25,13, 3, 7), border_radius=1)
        pygame.draw.polygon(s, (205,215,225), [(25,3),(28,3),(27,13),(25,13)])
        pygame.draw.line(s, (240,245,255), (26,4),(26,12), 1)
        if is_dying:
            s.set_alpha(alpha)
        rotated = pygame.transform.rotate(s, self.move_angle)
        rect = rotated.get_rect(center=(self.x, self.y + y_off))
        screen.blit(rotated, rect.topleft)
        if not is_dying:
            self._draw_health_bar(screen, bar_width=20, bar_height=4)


# ── i. Lớp con TankEnemy — kế thừa Enemy ────────────────────────────────────
class TankEnemy(Enemy):
    """
    Kẻ địch BỌC THÉP — thân to, máu nhiều, màu cam/sắt nung.
    Ghi đè update() và draw() — đa hình với lớp cơ sở Enemy.
    """
    def __init__(self, path):
        super().__init__(path, "tank")      # Tra ENEMY_CONFIG["tank"]

    def update(self):
        """Ghi đè update — di chuyển cơ bản, thân nặng nề."""
        self._move()

    def draw(self, screen, is_dying=False):
        """Iron Golem khổng lồ: mắt cam rực, vết nứt giáp, rìu chiến hai đầu."""
        if is_dying:
            alpha = int(255 * (self.death_timer / 15))
            self.move_angle += 5 # Xoay chậm
            y_off = (15 - self.death_timer) * 0.5
            pygame.draw.ellipse(screen, (0,0,0, int(70*self.death_timer/15)), (self.x-19, self.y+10, 38, 13))
        else:
            alpha = 255
            y_off = math.sin(self.walk_timer * 0.12) * 1
            pygame.draw.ellipse(screen, (0,0,0,70), (self.x-19, self.y+10, 38, 13))
            
        s = pygame.Surface((48, 52), pygame.SRCALPHA)
        # Chân to (bước chậm nịch)
        if not is_dying:
            leg_y1 = math.sin(self.walk_timer * 0.15) * 3
            leg_y2 = math.sin(self.walk_timer * 0.15 + math.pi) * 3
        else:
            leg_y1 = leg_y2 = 0
            
        pygame.draw.rect(s, (120,55,10), (10,34+leg_y1,11,15), border_radius=3)
        pygame.draw.rect(s, (110,50, 8), (27,34+leg_y2,11,15), border_radius=3)
        pygame.draw.rect(s, (150,75,18), (10,44+leg_y1,11, 6), border_radius=2)
        pygame.draw.rect(s, (140,65,12), (27,44+leg_y2,11, 6), border_radius=2)
        # Thân giáp khổng lồ
        pygame.draw.rect(s, (140,60,12), (7,16,34,20), border_radius=5)
        pygame.draw.rect(s, (165,80,20), (7,16,34,10), border_radius=3)
        pygame.draw.line(s, (100,40, 5), (24,16),(24,35), 2)
        # Vết nứt phát sáng cam
        pygame.draw.line(s, (255,140, 0), (10,20),(17,28), 2)
        pygame.draw.line(s, (255,170,20), (31,22),(38,30), 2)
        pygame.draw.line(s, (255,110, 0), (16,32),(22,25), 2)
        # Vai khổng lồ
        pygame.draw.ellipse(s, (125,52, 8), ( 0,12,18,14))
        pygame.draw.ellipse(s, (125,52, 8), (30,12,18,14))
        pygame.draw.ellipse(s, (165,85,22), ( 0,11,18, 7))
        pygame.draw.ellipse(s, (165,85,22), (30,11,18, 7))
        pygame.draw.polygon(s, (90,38, 5), [( 0,12),( 5,12),( 2, 5)])
        pygame.draw.polygon(s, (90,38, 5), [(43,12),(48,12),(45, 5)])
        # Mũ giáp khổng lồ
        pygame.draw.rect(s, (115,48, 8), (10, 3,28,16), border_radius=6)
        pygame.draw.rect(s, (95,38, 5), (10, 3,28,16), border_radius=6, width=2)
        # Kính chữ T
        pygame.draw.rect(s, (35,18, 3), (13, 7,22, 5))
        pygame.draw.rect(s, (35,18, 3), (21, 7, 6,11))
        # Mắt cam rực lửa
        pygame.draw.circle(s, (255,120, 0), (17,10), 4)
        pygame.draw.circle(s, (255,210,50), (17,10), 2)
        pygame.draw.circle(s, (255,120, 0), (31,10), 4)
        pygame.draw.circle(s, (255,210,50), (31,10), 2)
        # Mào mũ
        pygame.draw.rect(s, (95,38, 5), (18, 0,12, 5))
        pygame.draw.polygon(s, (190,65,15), [(18,0),(30,0),(24,-6)])
        # Tay trái: khiên nhỏ
        pygame.draw.rect(s, (95,38, 5), (-1,18, 7,15), border_radius=2)
        pygame.draw.polygon(s, (85,32, 5), [(-2,18),(7,18),(7,29),(2,34),(-2,29)])
        pygame.draw.polygon(s, (200,175,20), [(-2,18),(7,18),(7,29),(2,34),(-2,29)], 1)
        pygame.draw.circle(s, (200,150,10), (2,25), 3)
        # Tay phải: rìu chiến hai đầu
        pygame.draw.rect(s, (90,60,20), (40,20, 5,15), border_radius=2)
        pygame.draw.line(s, (180,180,180),(42,21),(42,33), 2)
        pygame.draw.polygon(s, (175,178,188), [(35,5),(47,5),(49,17),(33,17)])
        pygame.draw.polygon(s, (205,208,218), [(35,5),(47,5),(49,17),(33,17)], 2)
        pygame.draw.line(s, (230,232,240), (36,6),(46,6), 2)
        if is_dying:
            s.set_alpha(alpha)
        rotated = pygame.transform.rotate(s, self.move_angle)
        rect = rotated.get_rect(center=(self.x, self.y + y_off))
        screen.blit(rotated, rect.topleft)
        if not is_dying:
            self._draw_health_bar(screen, bar_width=36, bar_height=6, y_offset=-30)


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
        if self.wave <= 2:
            return "normal"
        elif self.wave == 3:
            return random.choices(["normal", "fast"], weights=[70, 30])[0]
        elif self.wave == 4:
            return random.choices(["normal", "fast", "tank"], weights=[50, 30, 20])[0]
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
        self.spatial_hash.clear()
        
        for enemy in self.enemies:
            was_alive = enemy.alive
            enemy.update()                  # ĐA HÌNH: gọi update() không if-else
            if enemy.hp <= 0 and was_alive:
                enemy.alive = False
                gold_earned += enemy.reward     # Lấy reward từ config
                enemy.death_timer = 15          # Thêm vào hàng đợi chết
                self.dying_enemies.append(enemy)
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
        
        return gold_earned, escaped_count

    def draw(self, screen):
        # Vẽ xác đang tan biến trước để không đè lên kẻ địch sống
        for d in self.dying_enemies:
            d.draw(screen, is_dying=True)
        # Vẽ kẻ địch còn sống
        for e in self.enemies:
            e.draw(screen)
