"""
Mô-đun quản lý Bản Đồ (Map) của trò chơi Kingdom Guardians.

Mô-đun này định nghĩa cấu trúc dữ liệu lưới (grid) cho ba bản đồ chơi khác
nhau, thuật toán tìm đường đi (path-finding) và logic vẽ bản đồ lên màn hình.

Điểm nhấn đồ họa (Đã được đại tu):
    - Render nền cỏ hữu cơ bằng hàng trăm lớp màu (Procedural Generation).
    - Đường đi uốn lượn tự nhiên không bị giới hạn bởi khối ô vuông.
    - Cây cỏ đổ bóng 3D, với các hiệu ứng hạt (lá rơi) bay lượn sinh động.

Hằng số:
    ALL_LEVELS : Danh sách 3 lưới bản đồ (LEVEL_1, LEVEL_2, LEVEL_3).
    MAP_NAMES  : Tên hiển thị tương ứng của từng bản đồ.
    MAP_THEMES : Bảng màu cỏ/đất riêng cho từng bản đồ.

Lớp:
    Map: Đại diện cho một bản đồ đang hoạt động. Chịu trách nhiệm:
        - Chuyển lưới ô (tile grid) thành danh sách toạ độ pixel (path).
        - Sinh ngẫu nhiên các vật trang trí (cây bụi, rừng thông) trên ô cỏ.
        - Vẽ nền cảnh quan đẹp mắt, marker xuất phát/đích và lưới phòng thủ.
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
        random.seed(self.level_index) # Để cây và trang trí cố định mỗi lần chơi
        for _ in range(25): # Giảm số cây để đỡ rối mắt
            c = random.randint(0, COLS-1)
            r = random.randint(0, ROWS-1)
            if self.grid[r][c] == 1:
                x = c * TILE_SIZE + random.randint(5, TILE_SIZE-5)
                y = r * TILE_SIZE + random.randint(5, TILE_SIZE-5)
                size = random.randint(10, 18) # Giảm kích thước cây
                # Đảm bảo không đè quá nhiều lên đường
                valid = True
                for p in self.paths:
                    for px, py in p:
                        if math.hypot(x - px, y - py) < TILE_SIZE:
                            valid = False; break
                    if not valid: break
                if valid:
                    decorations.append((x, y, size))
        return decorations

    def draw(self, screen):
        self.time_ticker += 1
        th = self.theme
        screen.fill(th["grass_l"])

        # 1. Nền Cỏ Bề Mặt (Procedural Grass Texture) - Rất nhẹ nhàng
        random.seed(self.level_index * 100)
        s_grass = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for _ in range(300): # Giảm mạnh số lượng để đơn giản hóa
            gx = random.randint(0, WIDTH)
            gy = random.randint(0, HEIGHT)
            r_val = random.randint(10, 30)
            col = (th["grass_d"][0], th["grass_d"][1], th["grass_d"][2], 40) # Rất mờ
            pygame.draw.circle(s_grass, col, (gx, gy), r_val)
        screen.blit(s_grass, (0, 0))

        # 2. Điểm Đặt Tháp (Chỉ đánh dấu bằng một chút cỏ sẫm màu)
        for r in range(ROWS):
            for c in range(COLS):
                if self.grid[r][c] == 1:
                    cx = c * TILE_SIZE + TILE_SIZE//2
                    cy = r * TILE_SIZE + TILE_SIZE//2
                    pygame.draw.circle(screen, th["grass_d"], (cx, cy), 14)
                    pygame.draw.circle(screen, th["grass_l"], (cx, cy), 11)

        # 3. Lòng Đường Hữu Cơ (Organic Curved Path)
        path_color = th["dirt"]
        border_color = th["dirt_b"]
        path_width = int(TILE_SIZE * 0.85)

        for p in self.paths:
            if len(p) > 1:
                # Viền sậm
                pygame.draw.lines(screen, border_color, False, p, path_width + 4)
                for pt in p: pygame.draw.circle(screen, border_color, pt, (path_width + 4)//2)
                
                # Lòng đường
                pygame.draw.lines(screen, path_color, False, p, path_width - 2)
                for pt in p: pygame.draw.circle(screen, path_color, pt, (path_width - 2)//2)
                
                # Một ít sỏi nhỏ li ti dọc viền
                random.seed(self.level_index * 200)
                for pt in p:
                    if random.random() < 0.3:
                        rx = pt[0] + random.randint(-path_width//2, path_width//2)
                        ry = pt[1] + random.randint(-path_width//2, path_width//2)
                        pygame.draw.circle(screen, border_color, (rx, ry), 1)

        # 4. Rừng Cây (Pine Trees)
        # Sắp xếp cây theo trục Y để vẽ từ trên xuống dưới (tránh đè ngược)
        sorted_trees = sorted(self.decorations, key=lambda d: d[1])
        for x, y, size in sorted_trees:
            # Bóng đổ
            shd = pygame.Surface((size*3, size*1.5), pygame.SRCALPHA)
            pygame.draw.ellipse(shd, (0,0,0, 60), (0, 0, size*3, size*1.5))
            screen.blit(shd, (x - size*1.5, y + size*0.5))
            
            # Thân cây
            pygame.draw.rect(screen, (60, 35, 15), (x - size//4, y, size//2, size*1.2), border_radius=2)
            pygame.draw.line(screen, (40, 20, 10), (x + size//4 - 1, y), (x + size//4 - 1, y + size*1.2), 2)

            # Tán thông (3 tầng)
            t_col_dark = (30, 80, 40)
            t_col_mid  = (40, 100, 50)
            t_col_lit  = (55, 130, 65)
            
            for layer in range(3):
                ly = y - size*(0.5 + layer)
                lw = size * (1.8 - layer*0.3)
                lh = size * (1.2 + layer*0.1)
                
                # Nền tối
                pygame.draw.polygon(screen, t_col_dark, [(x, ly - lh), (x - lw, ly + lh*0.5), (x + lw, ly + lh*0.5)])
                # Tán chính
                pygame.draw.polygon(screen, t_col_mid,  [(x, ly - lh), (x - lw*0.8, ly + lh*0.4), (x + lw*0.8, ly + lh*0.4)])
                # Tán sáng (Highlight)
                pygame.draw.polygon(screen, t_col_lit,  [(x, ly - lh), (x - lw*0.3, ly + lh*0.3), (x + lw*0.7, ly + lh*0.3)])

        # 5. Marker Điểm Xuất Phát (Cổng Không Gian)
        if self.path:
            sx, sy = self.path[0]
            # Vòng tròn ma thuật
            pygame.draw.ellipse(screen, (0, 0, 0, 80), (sx-25, sy-10, 50, 20))
            for i in range(3, 0, -1):
                pygame.draw.ellipse(screen, (50, 100, 255), (sx-20*i, sy-8*i, 40*i, 16*i), max(1, 4-i))
            # Cột đá 2 bên
            pygame.draw.rect(screen, (80, 80, 90), (sx-25, sy-30, 10, 35), border_radius=2)
            pygame.draw.rect(screen, (120, 120, 130), (sx-25, sy-30, 5, 35), border_radius=2)
            pygame.draw.rect(screen, (80, 80, 90), (sx+15, sy-30, 10, 35), border_radius=2)
            pygame.draw.rect(screen, (120, 120, 130), (sx+15, sy-30, 5, 35), border_radius=2)
            # Khí xoáy xanh
            pygame.draw.ellipse(screen, (100, 200, 255, 150), (sx-15, sy-25, 30, 25))
            pygame.draw.ellipse(screen, (200, 240, 255, 200), (sx-8, sy-20, 16, 15))

        # 6. Marker Điểm Đích (Pháo Đài Vương Quốc)
        if self.path:
            ex, ey = self.path[-1]
            pygame.draw.ellipse(screen, (0, 0, 0, 80), (ex-35, ey-15, 70, 30))
            # Đế pháo đài đá
            pygame.draw.rect(screen, (100, 100, 110), (ex-30, ey-30, 60, 30), border_radius=4)
            pygame.draw.rect(screen, (140, 140, 150), (ex-30, ey-30, 60, 10), border_radius=4)
            for i in range(5):
                pygame.draw.rect(screen, (80, 80, 90), (ex-28 + i*12, ey-35, 8, 10), border_radius=2)
            # Cổng vòm đỏ
            pygame.draw.rect(screen, (40, 10, 10), (ex-12, ey-15, 24, 25), border_radius=10)
            pygame.draw.rect(screen, (180, 40, 40), (ex-12, ey-15, 24, 25), 3, border_radius=10)
            # Cờ xanh vương quốc
            pygame.draw.line(screen, (200, 180, 50), (ex-20, ey-35), (ex-20, ey-55), 2)
            pygame.draw.line(screen, (200, 180, 50), (ex+20, ey-35), (ex+20, ey-55), 2)
            pygame.draw.polygon(screen, (40, 100, 220), [(ex-20, ey-55), (ex-5, ey-50), (ex-20, ey-45)])
            pygame.draw.polygon(screen, (40, 100, 220), [(ex+20, ey-55), (ex+35, ey-50), (ex+20, ey-45)])

        # Hiệu ứng hạt rơi (leaves)
        for p in self.particles:
            p[0] += p[3] + math.sin(self.time_ticker * 0.03 + p[1]*0.1) * 0.6
            p[1] += p[2]
            if p[1] > HEIGHT:
                p[1] = -10
                p[0] = random.randint(0, WIDTH)
            pygame.draw.rect(screen, p[4], (p[0], p[1], 4, 3), border_radius=1)

    # ── Kiểm tra có thể đặt tháp ────────────────────────────────────────────
    def is_placeable(self, x, y):
        if y < 40:
            return False
        c, r = x // TILE_SIZE, y // TILE_SIZE
        if 0 <= c < COLS and 0 <= r < ROWS:
            return self.grid[r][c] == 1
        return False
