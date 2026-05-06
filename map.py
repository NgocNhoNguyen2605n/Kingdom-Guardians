"""
Mô-đun quản lý Bản Đồ (Map) của trò chơi Kingdom Guardians.

Mô-đun này định nghĩa cấu trúc dữ liệu lưới (grid) cho ba bản đồ chơi khác
nhau, thuật toán tìm đường đi (path-finding) và logic vẽ bản đồ lên màn hình.

Hằng số:
    ALL_LEVELS : Danh sách 3 lưới bản đồ (LEVEL_1, LEVEL_2, LEVEL_3).
    MAP_NAMES  : Tên hiển thị tương ứng của từng bản đồ.
    MAP_THEMES : Bảng màu cỏ/đất riêng cho từng bản đồ.

Lớp:
    Map: Đại diện cho một bản đồ đang hoạt động. Chịu trách nhiệm:
        - Chuyển lưới ô (tile grid) thành danh sách toạ độ pixel (path).
        - Sinh ngẫu nhiên các vật trang trí (cây bụi) trên ô cỏ.
        - Vẽ nền, đường đi, lưới chiến thuật và trang trí mỗi frame.
        - Kiểm tra ô có thể đặt tháp hay không (is_placeable).
"""
import pygame
import random
import math
from settings import *

# ── Định nghĩa 3 bản đồ ──────────────────────────────────────────────────────
# Ký hiệu: 0 = đường đi, 1 = cỏ đặt tháp, 2 = điểm xuất phát, 3 = điểm đích

LEVEL_1 = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [2, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 3, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
]

# Bản đồ 2: Đường chữ Z — buộc đặt tháp ở 3 góc ngoặt
LEVEL_2 = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1],
    [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
    [1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 1, 1],
]

# Bản đồ 3: Hai nhánh bầu dục — lính rẽ lên HOẶC xuống, cả hai đều đến đích
# Nhánh A (trên): hàng 2, cols 4-15
# Nhánh B (dưới): hàng 12, cols 4-15
# Cột 4 = ngã rẽ xuất phát | Cột 15 = ngã rẽ nhập lại
LEVEL_3 = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],  # row 0
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],  # row 1
    [1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1],  # row 2  nhánh A
    [1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1],  # row 3
    [1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1],  # row 4
    [1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1],  # row 5
    [1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1],  # row 6
    [2, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 3],  # row 7  trục chính
    [1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1],  # row 8
    [1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1],  # row 9
    [1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1],  # row 10
    [1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1],  # row 11
    [1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1],  # row 12 nhánh B
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],  # row 13
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],  # row 14
]

ALL_LEVELS = [LEVEL_1, LEVEL_2, LEVEL_3]
MAP_NAMES  = ["Grasslands", "Serpent Pass", "Spiral Keep"]
# Màu sắc chủ đạo cho từng map (cỏ sáng, cỏ tối, đất)
MAP_THEMES = [
    {"grass_l": (145,190,60), "grass_d": (130,175,45), "dirt": (220,195,135), "dirt_b": (195,165,100)},
    {"grass_l": (100,160,80), "grass_d": ( 80,140,60), "dirt": (200,170,110), "dirt_b": (170,140, 80)},
    {"grass_l": ( 80,140,160),"grass_d": ( 60,120,140),"dirt": (180,160,140), "dirt_b": (150,130,110)},
]


class Map:
    """Quản lý bản đồ: lưới tile, path pixel, trang trí và vẽ."""

    def __init__(self, level_index=0):
        self.level_index = level_index
        self.grid        = ALL_LEVELS[level_index]
        self.theme       = MAP_THEMES[level_index]
        self.paths       = self._find_all_paths()   # Danh sách MỌI đường đến đích
        self.path        = self.paths[0] if self.paths else []  # Giữ tương thích cũ
        self.decorations = self.generate_decorations()
        
        # Biến cho hiệu ứng sinh động (lá rơi, cỏ rung)
        self.time_ticker = 0
        self.particles = []
        for _ in range(35):
            self.particles.append([random.randint(0, WIDTH), random.randint(-10, HEIGHT),
                                   random.uniform(0.5, 1.5), random.uniform(-0.5, 0.5),
                                   random.choice([(100,200,80), (150,220,100), (200,250,150)])])

    @staticmethod
    def from_index(idx):
        return Map(idx)

    # ── Tìm TẤT CẢ đường đi bằng DFS ────────────────────────────────────────
    def _find_all_paths(self):
        """
        DFS đệ quy tìm mọi đường đơn giản từ ô xuất phát (2) đến ô đích (3).
        Mỗi đường trả về là danh sách toạ độ pixel.
        Độ phức tạp: O(V + E) với V = số ô đường đi, E = số cạnh kề.
        """
        start = None
        for r in range(ROWS):
            for c in range(COLS):
                if self.grid[r][c] == 2:
                    start = (c, r)
                    break
            if start:
                break
        if start is None:
            return []

        all_paths = []

        def dfs(cur, visited, path):
            cx, cy = cur
            for nx, ny in [(cx+1,cy),(cx-1,cy),(cx,cy+1),(cx,cy-1)]:
                if 0 <= nx < COLS and 0 <= ny < ROWS and (nx,ny) not in visited:
                    tile = self.grid[ny][nx]
                    if tile == 3:                          # Đến đích → lưu đường
                        all_paths.append(path + [(nx,ny)])
                    elif tile == 0:                        # Ô đường → tiếp tục DFS
                        dfs((nx,ny), visited|{(nx,ny)}, path+[(nx,ny)])

        dfs(start, {start}, [start])

        # Chuyển toạ độ lưới → pixel
        return [
            [(x*TILE_SIZE+TILE_SIZE//2, y*TILE_SIZE+TILE_SIZE//2) for x,y in p]
            for p in all_paths
        ]

    # Alias giữ tương thích với code cũ
    def find_path(self):
        return self.path

    # ── Trang trí ngẫu nhiên ────────────────────────────────────────────────
    def generate_decorations(self):
        decorations = []
        for _ in range(35):
            c = random.randint(0, COLS-1)
            r = random.randint(1, ROWS-1)
            if self.grid[r][c] == 1:
                x = c * TILE_SIZE + random.randint(5, TILE_SIZE-5)
                y = r * TILE_SIZE + random.randint(5, TILE_SIZE-5)
                size = random.randint(8, 20)
                decorations.append((x, y, size))
        return decorations

    # ── Vẽ bản đồ ───────────────────────────────────────────────────────────
    def draw(self, screen):
        self.time_ticker += 1
        th = self.theme
        screen.fill(th["grass_l"])

        # Lưới chiến thuật mờ
        for r in range(ROWS):
            pygame.draw.line(screen, (0,0,0), (0, r*TILE_SIZE), (WIDTH, r*TILE_SIZE))
        for c in range(COLS):
            pygame.draw.line(screen, (0,0,0), (c*TILE_SIZE, 0), (c*TILE_SIZE, HEIGHT))
        grid_alpha = pygame.Surface((WIDTH, HEIGHT))
        grid_alpha.set_alpha(12)
        grid_alpha.fill(WHITE)
        screen.blit(grid_alpha, (0,0))

        for r in range(ROWS):
            for c in range(COLS):
                tile = self.grid[r][c]
                rect = pygame.Rect(c*TILE_SIZE, r*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                if tile == 1:
                    if (r + c) % 2 == 0:
                        pygame.draw.rect(screen, th["grass_d"], rect)
                elif tile in (0, 2, 3):
                    pygame.draw.rect(screen, th["dirt"], rect)
                    pygame.draw.line(screen, th["dirt_b"], rect.topleft,    rect.topright,    2)
                    pygame.draw.line(screen, th["dirt_b"], rect.bottomleft, rect.bottomright, 2)
                    # Cuội sỏi trên đường đất (seeded random)
                    px = (c*17 + r*7)  % (TILE_SIZE-12) + 6
                    py = (r*13 + c*11) % (TILE_SIZE-12) + 6
                    pebble_col = tuple(min(255, v+20) for v in th["dirt"])
                    pygame.draw.circle(screen, pebble_col, (c*TILE_SIZE+px, r*TILE_SIZE+py), 2)
                    px2 = (c*23 + r*19) % (TILE_SIZE-12) + 6
                    py2 = (r*7  + c*17) % (TILE_SIZE-12) + 6
                    pygame.draw.circle(screen, th["dirt_b"], (c*TILE_SIZE+px2, r*TILE_SIZE+py2), 1)

        # Gợi ý vị trí đặt tháp
        for r in range(ROWS):
            for c in range(COLS):
                if self.grid[r][c] == 1 and r > 0 and c % 2 == 1 and r % 2 == 1:
                    cx = c * TILE_SIZE + TILE_SIZE//2
                    cy = r * TILE_SIZE + TILE_SIZE//2
                    pygame.draw.circle(screen, th["grass_d"], (cx, cy), 12, 3)

        # Cây trang trí — thân gỗ + 3 tầng lá + hiệu ứng rung / bóng đổ
        for i, (x, y, size) in enumerate(self.decorations):
            # Hiệu ứng rung nhẹ
            sway = math.sin(self.time_ticker * 0.04 + i) * 1.5
            
            # Bóng đổ
            shd = pygame.Surface((size*2+4, size//2+2), pygame.SRCALPHA)
            pygame.draw.ellipse(shd, (0,0,0,40), (0, 0, size*2+4, size//2+2))
            screen.blit(shd, (x-size-2 + sway*0.3, y+size//2-1))
            
            # Thân cây nâu
            trunk_w = max(3, size//4)
            pygame.draw.rect(screen, (90,58,25),
                             (x - trunk_w//2, y, trunk_w, size//2+2), border_radius=1)
            pygame.draw.line(screen, (130,85,40),
                             (x - trunk_w//2+1, y), (x - trunk_w//2+1, y+size//2), 1)
                             
            # Tầng lá 3 lớp (dưới → trên, to → nhỏ)
            pygame.draw.circle(screen, (40,75,15),  (x+2 + sway*0.5, y+2),     size)
            pygame.draw.circle(screen, BUSH_COLOR,  (x + sway,       y),       size)
            pygame.draw.circle(screen, (70,115,30), (x-size//4 + sway*1.2, y-size//4), int(size*0.65))
            pygame.draw.circle(screen, (100,150,45),(x-size//3 + sway*1.6, y-size//3), int(size*0.35))
            
            # Highlight lá sáng
            pygame.draw.circle(screen, th["grass_l"], (x-size//3 + sway*1.6, y-size//3), max(1, size//5))

        # Hiệu ứng hạt (lá rơi bay lượn)
        for p in self.particles:
            # Di chuyển hạt x và y
            p[0] += p[3] + math.sin(self.time_ticker * 0.03 + p[1]*0.1) * 0.6
            p[1] += p[2]
            # Nếu rơi quá màn hình thì vòng lại
            if p[1] > HEIGHT:
                p[1] = -10
                p[0] = random.randint(0, WIDTH)
            pygame.draw.rect(screen, p[4], (p[0], p[1], 4, 3), border_radius=1)

        # Marker điểm xuất phát (cổng xanh)
        if self.path:
            sx, sy = self.path[0]
            pygame.draw.rect(screen, (40,80,180),  (sx-14, sy-18, 28, 32), border_radius=4)
            pygame.draw.rect(screen, (80,140,255), (sx-14, sy-18, 28, 32), 2, border_radius=4)
            pygame.draw.rect(screen, (20,40,100),  (sx-8,  sy-4,  16, 18), border_radius=3)
            pygame.draw.rect(screen, (100,180,255),(sx-6,  sy-16,  5, 10), border_radius=2)
            pygame.draw.rect(screen, (100,180,255),(sx+1,  sy-16,  5, 10), border_radius=2)
            s_txt = pygame.Surface((28, 8), pygame.SRCALPHA)
            pygame.draw.rect(s_txt, (140,200,255,180), (0,0,28,8), border_radius=2)
            screen.blit(s_txt, (sx-14, sy-24))

        # Marker điểm đích (pháo đài đỏ)
        if self.path:
            ex, ey = self.path[-1]
            pygame.draw.rect(screen, (140,45,45), (ex-16, ey-22, 32, 36), border_radius=4)
            pygame.draw.rect(screen, (200,70,70), (ex-16, ey-22, 32, 36), 2, border_radius=4)
            for i in range(4):                                      # Merlons (lỗ châu mai)
                mx = ex-14 + i*9
                pygame.draw.rect(screen, (160,55,55), (mx, ey-28, 7, 8), border_radius=1)
            pygame.draw.rect(screen, (80,20,20),  (ex-8, ey, 16, 14), border_radius=2)
            pygame.draw.rect(screen, (200,60,60), (ex-8, ey, 16, 14), 1, border_radius=2)
            pygame.draw.line(screen, (220,80,80), (ex-2, ey-20),(ex-2, ey-12), 2)
            pygame.draw.polygon(screen,(220,40,40),[(ex-2,ey-28),(ex-2,ey-20),(ex+6,ey-24)])

    # ── Kiểm tra có thể đặt tháp ────────────────────────────────────────────
    def is_placeable(self, x, y):
        if y < 40:
            return False
        c, r = x // TILE_SIZE, y // TILE_SIZE
        if 0 <= c < COLS and 0 <= r < ROWS:
            return self.grid[r][c] == 1
        return False
