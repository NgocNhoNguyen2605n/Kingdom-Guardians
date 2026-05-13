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

def parse_map(map_str):
    return [[int(char) for char in line.strip()] for line in map_str.strip().split('\n')]

LEVEL_1_STR = """
1111111111111111111111111111111111111111
1111111111111111111111111111111111111111
2000000000000000000000000000000000001111
1111111111111111111111111111111111101111
1111111111111111111111111111111111101111
1111100000000000000000000000000000001111
1111101111111111111111111111111111111111
1111101111111111111111111111111111111111
1111100000000000000000000000000000001111
1111111111111111111111111111111111101111
1111111111111111111111111111111111101111
1111100000000000000000000000000000001111
1111101111111111111111111111111111111111
1111101111111111111111111111111111111111
1111100000000000000000000000000000001111
1111111111111111111111111111111111101111
1111111111111111111111111111111111101111
1111100000000000000000000000000000001111
1111101111111111111111111111111111111111
1111100000000000000000000000000000000003
1111111111111111111111111111111111111111
1111111111111111111111111111111111111111
"""

LEVEL_2_STR = """
1111111111111111111111111111111111111111
1111111111111111111111111111111111111111
2000000000000000000000000000000000001111
1111111111111111111111111111111111101111
1111111111111111111111111111111111101111
1111111111111111111111111111111111101111
1111100000000000000000000000001111101111
1111101111111111111111111111101111101111
1111101111111111111111111111101111101111
1111101111111111111111111111101111101111
1111101111100000000000001111101111101111
1111101111101111111111101111101111101111
1111101111101111111111301111101111101111
1111101111101111111111111111101111101111
1111101111101111111111111111101111101111
1111101111100000000000000000001111101111
1111101111111111111111111111111111101111
1111101111111111111111111111111111101111
1111101111111111111111111111111111101111
1111100000000000000000000000000000001111
1111111111111111111111111111111111111111
1111111111111111111111111111111111111111
"""

LEVEL_3_STR = """
1111111111111111111111111111111111111111
1111111111111111111111111111111111111111
1111111111111111111111111111111111111111
1111100000000000000000000000000111111111
1111101111111111111111111111110111111111
1111101111111111111111111111110111111111
1111101111111111111111111111110111111111
1111101111111111111111111111110111111111
1111101111111111111111111111110111111111
1111101111111111111111111111110111111111
2000001111111111111111111111110000000003
1111101111111111111111111111110111111111
1111101111111111111111111111110111111111
1111101111111111111111111111110111111111
1111101111111111111111111111110111111111
1111101111111111111111111111110111111111
1111101111111111111111111111110111111111
1111100000000000000000000000000111111111
1111111111111111111111111111111111111111
1111111111111111111111111111111111111111
1111111111111111111111111111111111111111
1111111111111111111111111111111111111111
"""

LEVEL_1 = parse_map(LEVEL_1_STR)
LEVEL_2 = parse_map(LEVEL_2_STR)
LEVEL_3 = parse_map(LEVEL_3_STR)

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
        base_grid = ALL_LEVELS[level_index]
        self.theme       = MAP_THEMES[level_index]
        
        # Center the base_grid inside the dynamic ROWS x COLS
        self.grid = []
        base_r = len(base_grid)
        base_c = len(base_grid[0])
        
        start_r = max(0, (ROWS - base_r) // 2)
        start_c = max(0, (COLS - base_c) // 2)
        
        for r in range(ROWS):
            row = []
            for c in range(COLS):
                if start_r <= r < start_r + base_r and start_c <= c < start_c + base_c:
                    row.append(base_grid[r - start_r][c - start_c])
                else:
                    row.append(1) # Cỏ (có thể xây dựng)
            self.grid.append(row)
            
        self.paths       = self._find_all_paths()   # Danh sách MỌI đường đến đích
        self.path        = self.paths[0] if self.paths else []  # Giữ tương thích cũ
        self.decorations = self.generate_decorations()
        
        # Biến cho hiệu ứng sinh động (lá rơi, cỏ rung)
        self.time_ticker = 0
        self.particles = []
        num_particles = int(35 * (WIDTH * HEIGHT) / (800 * 600))
        for _ in range(num_particles):
            self.particles.append([random.randint(0, WIDTH), random.randint(-10, HEIGHT),
                                   random.uniform(0.5, 1.5), random.uniform(-0.5, 0.5),
                                   random.choice([(100,200,80), (150,220,100), (200,250,150)])])
        
        # Pre-generate grass blades near paths (cỏ rung gió)
        self.grass_blades = []
        random.seed(self.level_index * 77 + 1)
        for p in self.paths:
            for pt in p[::3]:  # Mỗi 3 điểm lấy 1
                for _ in range(5):
                    ox = random.randint(-TILE_SIZE, TILE_SIZE)
                    oy = random.randint(-TILE_SIZE, TILE_SIZE)
                    bx, by = pt[0] + ox, pt[1] + oy
                    # Kiểm tra không nằm trên đường
                    on_path = False
                    for pp in p:
                        if math.hypot(bx - pp[0], by - pp[1]) < TILE_SIZE // 2 + 4:
                            on_path = True; break
                    if not on_path and 0 < bx < WIDTH and 0 < by < HEIGHT:
                        length = random.randint(5, 10)
                        tilt   = random.uniform(-0.3, 0.3)
                        col    = random.choice([
                            (80, 160, 60), (100, 180, 70), (120, 200, 80), (70, 145, 50)])
                        self.grass_blades.append((bx, by, length, tilt, col))


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
        random.seed(self.level_index)
        
        # Biome settings
        if self.level_index == 0:
            types = ['pine', 'pine', 'oak', 'rock', 'flower']
        elif self.level_index == 1:
            types = ['cactus', 'cactus', 'dead_tree', 'rock', 'bones']
        else:
            types = ['dead_pine', 'crystal', 'crystal', 'rock', 'dark_flower']
            
        num_decorations = int(45 * (ROWS * COLS) / 300)
        for _ in range(num_decorations):
            c = random.randint(0, COLS-1)
            r = random.randint(0, ROWS-1)
            if self.grid[r][c] == 1:
                x = c * TILE_SIZE + random.randint(5, TILE_SIZE-5)
                y = r * TILE_SIZE + random.randint(5, TILE_SIZE-5)
                size = random.randint(10, 18)
                dtype = random.choice(types)
                
                # Cây cối không được đè lên đường
                valid = True
                for p in self.paths:
                    for px, py in p:
                        if math.hypot(x - px, y - py) < TILE_SIZE * 0.8:
                            valid = False; break
                    if not valid: break
                if valid:
                    decorations.append((x, y, size, dtype))
        return decorations

    def _init_biome_data(self):
        """Khởi tạo dữ liệu biome theo từng map"""
        import os
        if hasattr(self, '_biome_ready'):
            return
        self._biome_ready = True
        random.seed(self.level_index * 999)
        
        # Tạo texture nền cỏ (pre-baked)
        self._grass_surf = pygame.Surface((WIDTH, HEIGHT))
        th = self.theme
        self._grass_surf.fill(th["grass_l"])
        for _ in range(400):
            gx = random.randint(0, WIDTH)
            gy = random.randint(0, HEIGHT)
            r  = random.randint(8, 28)
            c  = (max(0,th["grass_d"][0]-10), max(0,th["grass_d"][1]-10), max(0,th["grass_d"][2]))
            pygame.draw.circle(self._grass_surf, c, (gx, gy), r)
        # Patch sáng hơn
        for _ in range(200):
            gx = random.randint(0, WIDTH)
            gy = random.randint(0, HEIGHT)
            r  = random.randint(4, 16)
            c  = (min(255,th["grass_l"][0]+15), min(255,th["grass_l"][1]+15), min(255,th["grass_l"][2]))
            pygame.draw.circle(self._grass_surf, c, (gx, gy), r)

        # Hồ nước (map 0)
        self._ponds = []
        if self.level_index == 0:
            for _ in range(3):
                px = random.randint(60, WIDTH-60)
                py = random.randint(100, HEIGHT-100)
                # Kiểm tra không đè lên đường
                on_path = any(
                    math.hypot(px-ex, py-ey) < 60
                    for path in self.paths for ex, ey in path
                )
                if not on_path:
                    # Kiểm tra ô cỏ
                    c_ = px // TILE_SIZE
                    r_ = py // TILE_SIZE
                    if 0 <= c_ < COLS and 0 <= r_ < ROWS and self.grid[r_][c_] == 1:
                        self._ponds.append((px, py, random.randint(22, 38), random.randint(14, 24)))

        # Bụi cát (map 1)
        self._dust = []
        if self.level_index == 1:
            for _ in range(60):
                self._dust.append([
                    random.randint(0, WIDTH),
                    random.uniform(0, HEIGHT),
                    random.uniform(0.5, 2.5),
                    random.uniform(0.3, 1.0),
                ])

        # Bào tử ma thuật (map 2)
        self._spores = []
        if self.level_index == 2:
            for _ in range(50):
                self._spores.append([
                    random.uniform(0, WIDTH),
                    random.uniform(0, HEIGHT),
                    random.uniform(-0.3, 0.3),
                    random.uniform(-0.4, -0.1),
                    random.choice([(80,200,255),(180,80,255),(100,255,200)]),
                ])

    def draw(self, screen):
        self.time_ticker += 1
        th = self.theme
        t  = self.time_ticker
        self._init_biome_data()

        # ── Vẽ nền theo biome ──
        if self.level_index == 2:
            # Map 3: Rừng đêm tối - nền xanh thẫm
            screen.blit(self._grass_surf, (0, 0))
            dark = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            dark.fill((0, 0, 40, 90))
            screen.blit(dark, (0, 0))
        else:
            screen.blit(self._grass_surf, (0, 0))

        # ── Hồ nước (Map 0) ──
        if self.level_index == 0 and self._ponds:
            for (px, py, rw, rh) in self._ponds:
                ripple = math.sin(t * 0.05) * 2
                pond_s = pygame.Surface((rw*2+10, rh*2+10), pygame.SRCALPHA)
                pygame.draw.ellipse(pond_s, (80, 150, 210, 160), (0,0,rw*2,rh*2))
                pygame.draw.ellipse(pond_s, (120, 190, 240, 100), (4,4,rw*2-8,rh*2-8))
                # Highlight nước
                pygame.draw.ellipse(pond_s, (200,235,255, 120), (6, 4, rw-4, rh//2))
                screen.blit(pond_s, (px - rw, py - rh))
                # Gợn sóng
                for ri in range(1, 3):
                    phase = (t*0.03 + ri*1.2) % (math.pi*2)
                    rr = int(rw * (0.6 + ri*0.3) + math.sin(phase)*3)
                    rrh = int(rh * (0.6 + ri*0.25) + math.sin(phase)*2)
                    rsurf = pygame.Surface((rr*2+4, rrh*2+4), pygame.SRCALPHA)
                    al = max(0, int(80*(1 - ri*0.35)))
                    pygame.draw.ellipse(rsurf, (140,210,255,al), (0,0,rr*2,rrh*2), 2)
                    screen.blit(rsurf, (px-rr, py-rrh))

        # ── Bụi cát bay (Map 1) ──
        if self.level_index == 1:
            for p in self._dust:
                p[0] += p[2]
                p[1] += math.sin(t*0.02 + p[0]*0.01) * 0.3
                if p[0] > WIDTH: p[0] = 0
                al = int(60 * p[3])
                ds = pygame.Surface((int(p[2]*8)+4, 3), pygame.SRCALPHA)
                pygame.draw.ellipse(ds, (220,190,120, al), (0,0,ds.get_width(),3))
                screen.blit(ds, (int(p[0]), int(p[1])))

        # ── Bào tử ma thuật (Map 2) ──
        if self.level_index == 2:
            for p in self._spores:
                p[0] += p[2] + math.sin(t*0.02+p[1]*0.05)*0.4
                p[1] += p[3]
                if p[1] < -10: p[1] = HEIGHT
                if p[0] < 0: p[0] = WIDTH
                if p[0] > WIDTH: p[0] = 0
                al = int(130 + 80*math.sin(t*0.04+p[0]*0.03))
                al = max(30, min(255, al))
                ss = pygame.Surface((8,8), pygame.SRCALPHA)
                pygame.draw.circle(ss, (*p[4], al), (4,4), 3)
                screen.blit(ss, (int(p[0])-4, int(p[1])-4))
                # Glow nhỏ
                gs = pygame.Surface((16,16), pygame.SRCALPHA)
                pygame.draw.circle(gs, (*p[4], al//4), (8,8), 7)
                screen.blit(gs, (int(p[0])-8, int(p[1])-8))

        # 2. Ô cỏ có thể xây - cụm cỏ nhỏ
        random.seed(self.level_index * 150)
        for r in range(ROWS):
            for c in range(COLS):
                if self.grid[r][c] == 1:
                    cx = c * TILE_SIZE + TILE_SIZE//2
                    cy = r * TILE_SIZE + TILE_SIZE//2
                    # Chỉ vẽ vài nhánh cỏ mờ ở trung tâm tile để người chơi biết có thể xây
                    if random.random() < 0.6:
                        pygame.draw.arc(screen, th["grass_d"], (cx-4, cy-4, 8, 8), 0, math.pi/2, 2)
                        pygame.draw.arc(screen, th["grass_d"], (cx, cy, 6, 6), math.pi, math.pi*1.5, 1)

        # 3. Lòng Đường + Bóng Đổ Cạnh Đường (chiều sâu 3D)
        path_color   = th["dirt"]
        border_color = th["dirt_b"]
        shadow_col   = (0, 0, 0)
        path_width   = int(TILE_SIZE * 0.85)
        shadow_width = path_width + 8

        for p in self.paths:
            if len(p) > 1:
                # --- Bóng đổ ---
                shd_s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                pygame.draw.lines(shd_s, (*shadow_col, 45), False, p, shadow_width)
                for pt in p:
                    pygame.draw.circle(shd_s, (*shadow_col, 45), pt, shadow_width // 2)
                screen.blit(shd_s, (0, 0))
                # --- Viền sậm và Lòng đường hữu cơ (Organic jagged edges) ---
                # Thay vì dùng line thẳng đuột, ta vẽ các vòng tròn gồ ghề dọc theo đường
                pygame.draw.lines(screen, border_color, False, p, path_width + 4)
                for pt in p: pygame.draw.circle(screen, border_color, pt, (path_width + 4)//2)
                pygame.draw.lines(screen, path_color, False, p, path_width - 2)
                for pt in p: pygame.draw.circle(screen, path_color, pt, (path_width - 2)//2)

                # Vẽ chi tiết lởm chởm rìa đường (Jagged edges)
                random.seed(self.level_index * 888)
                for i in range(len(p) - 1):
                    p1, p2 = p[i], p[i+1]
                    dist = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
                    steps = int(dist // 8)
                    for step in range(steps):
                        t = step / steps
                        cx = p1[0] + (p2[0] - p1[0]) * t
                        cy = p1[1] + (p2[1] - p1[1]) * t
                        # Rìa trái và phải
                        ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0]) + math.pi/2
                        ox = math.cos(ang) * (path_width//2)
                        oy = math.sin(ang) * (path_width//2)
                        
                        if random.random() < 0.6:
                            # Cục đất viền
                            r_size = random.randint(4, 9)
                            pygame.draw.circle(screen, border_color, (int(cx+ox), int(cy+oy)), r_size)
                            pygame.draw.circle(screen, path_color, (int(cx+ox - ox*0.2), int(cy+oy - oy*0.2)), r_size-2)
                            pygame.draw.circle(screen, border_color, (int(cx-ox), int(cy-oy)), r_size)
                            pygame.draw.circle(screen, path_color, (int(cx-ox + ox*0.2), int(cy-oy + oy*0.2)), r_size-2)

                # --- Vết xe kéo / Dấu chân giữa đường (Wagon Tracks) ---
                track_col = tuple(max(0, c - 15) for c in path_color)
                for i in range(len(p) - 1):
                    p1, p2 = p[i], p[i+1]
                    ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0]) + math.pi/2
                    ox = math.cos(ang) * (path_width//4)
                    oy = math.sin(ang) * (path_width//4)
                    # Vẽ 2 vệt bánh xe song song
                    for side in [1, -1]:
                        pygame.draw.line(screen, track_col, 
                            (p1[0] + ox*side, p1[1] + oy*side), 
                            (p2[0] + ox*side, p2[1] + oy*side), 2)
                        # Highlight mờ cạnh vết bánh xe
                        pygame.draw.line(screen, tuple(min(255, c + 15) for c in path_color), 
                            (p1[0] + ox*side + 1, p1[1] + oy*side + 1), 
                            (p2[0] + ox*side + 1, p2[1] + oy*side + 1), 1)
                # --- Sỏi ---
                random.seed(self.level_index * 200)
                for pt in p:
                    if random.random() < 0.3:
                        rx = pt[0] + random.randint(-path_width//2, path_width//2)
                        ry = pt[1] + random.randint(-path_width//2, path_width//2)
                        pygame.draw.circle(screen, border_color, (rx, ry), 1)

                # --- Stone tile pattern (Kingdom Rush style — đường lát đá) ---
                random.seed(self.level_index * 333)
                stone_light = tuple(min(255, c + 25) for c in path_color)
                stone_dark  = tuple(max(0,   c - 20) for c in path_color)
                for idx in range(0, len(p) - 1, 5):
                    pt = p[idx]
                    if random.random() < 0.55:
                        sw = random.randint(10, 18)
                        sh = random.randint(7, 12)
                        ox = random.randint(-path_width//3, path_width//3)
                        oy = random.randint(-5, 5)
                        rx, ry = pt[0] + ox - sw//2, pt[1] + oy - sh//2
                        stone_c = random.choice([stone_light, stone_dark, path_color])
                        pygame.draw.rect(screen, stone_c, (rx, ry, sw, sh), border_radius=2)
                        # Highlight trên viên đá
                        pygame.draw.line(screen, stone_light, (rx+1, ry+1), (rx+sw-2, ry+1), 1)
                        # Viền tối
                        pygame.draw.rect(screen, border_color, (rx, ry, sw, sh), 1, border_radius=2)

        # 3b. Cỏ Rung Gió (Animated Grass Blades) dọc hai bên đường
        t_blade = self.time_ticker * 0.04
        for (bx, by, length, tilt, col) in self.grass_blades:
            sway = math.sin(t_blade + bx * 0.05) * 3 + tilt * 4
            tip_x = bx + sway
            tip_y = by - length
            # Bóng cỏ
            pygame.draw.line(screen, (0, 0, 0, 30), (bx, by), (tip_x + 1, tip_y + 2), 1)
            # Thân cỏ
            pygame.draw.line(screen, col, (bx, by), (tip_x, tip_y), 2)
            # Đầu cỏ sáng hơn
            bright = tuple(min(255, c + 50) for c in col)
            pygame.draw.circle(screen, bright, (int(tip_x), int(tip_y)), 1)

        # 4. Y-sorted Decorations (Stardew Valley / Kingdom Rush Style)
        sorted_trees = sorted(self.decorations, key=lambda d: d[1])

        # Color Palettes
        PINE_SHD, PINE_MID, PINE_HLT, PINE_TRM = (20,55,28), (38,90,45), (75,140,62), (110,185,75)
        DPINE_SHD, DPINE_MID, DPINE_HLT, DPINE_TRM = (30,25,35), (55,50,65), (80,75,95), (110,105,125)
        OAK_SHD, OAK_MID, OAK_HLT = (40,75,20), (65,115,35), (105,165,50)
        WD_SHD, WD_MID, WD_HLT = (40,20,12), (75,45,25), (110,70,35)
        DWD_SHD, DWD_MID, DWD_HLT = (30,30,30), (50,50,55), (80,80,85)
        CAC_SHD, CAC_MID, CAC_HLT = (45,60,20), (80,110,35), (130,170,60)
        CRY_SHD, CRY_MID, CRY_HLT = (10,50,70), (30,100,150), (80,200,255)
        RCK_SHD, RCK_MID, RCK_HLT = (60,60,65), (100,100,105), (150,150,160)

        for x, y, size, dtype in sorted_trees:
            # ── 1. Drop Shadow ──
            if dtype in ['flower', 'dark_flower', 'bones', 'rock']:
                shd_w, shd_h = int(size*1.5), int(size*0.8)
            else:
                shd_w, shd_h = int(size*3), int(size*1.5)
            
            shd = pygame.Surface((shd_w, shd_h), pygame.SRCALPHA)
            pygame.draw.ellipse(shd, (0,0,0, 70), (0, 0, shd_w, shd_h))
            screen.blit(shd, (int(x - shd_w//2), int(y - shd_h//4)))

            # ── 2. Vẽ từng loại trang trí ──
            if dtype in ['pine', 'dead_pine']:
                is_dead = (dtype == 'dead_pine')
                c_shd = DPINE_SHD if is_dead else PINE_SHD
                c_mid = DPINE_MID if is_dead else PINE_MID
                c_hlt = DPINE_HLT if is_dead else PINE_HLT
                c_trm = DPINE_TRM if is_dead else PINE_TRM
                
                # Trunk
                tw = max(4, size // 3)
                th = int(size * 1.5)
                pygame.draw.rect(screen, DWD_SHD if is_dead else WD_SHD, (x - tw//2, y, tw, th), border_radius=2)
                pygame.draw.rect(screen, DWD_MID if is_dead else WD_MID, (x - tw//2 + 1, y, tw - 1, th), border_radius=2)
                pygame.draw.polygon(screen, DWD_SHD if is_dead else WD_SHD, [(x - tw//2, y + th - 2), (x - tw, y + th + 3), (x, y + th)])
                pygame.draw.polygon(screen, DWD_MID if is_dead else WD_MID, [(x + tw//2, y + th - 2), (x + tw, y + th + 3), (x, y + th)])

                # Layers (ANIMATED: cây đung đưa theo gió)
                sway_ang = math.sin(t * 0.015 + x * 0.02) * 2.5  # pixel
                for layer in range(4):
                    ly = y - size * (0.3 + layer * 0.7)
                    lw = size * (1.8 - layer * 0.25)
                    lh = size * (1.2 + layer * 0.15)
                    sw = sway_ang * (layer + 1) * 0.3  # đầu cây lung lay hơn
                    pygame.draw.polygon(screen, c_shd, [(x+sw, ly - lh), (x - lw+sw, ly + lh*0.5), (x + lw+sw, ly + lh*0.5)])
                    pygame.draw.polygon(screen, c_mid, [(x+sw, ly - lh + 2), (x - lw*0.8+sw, ly + lh*0.45), (x + lw*0.8+sw, ly + lh*0.45)])
                    pygame.draw.polygon(screen, c_hlt, [(x+sw, ly - lh + 2), (x - lw*0.8+sw, ly + lh*0.45), (x+sw, ly + lh*0.45)])
                    pygame.draw.line(screen, c_trm, (x - lw*0.8+sw, ly + lh*0.45), (x+sw, ly - lh + 2), 1)
                    if layer < 3 and not is_dead:
                        for j in range(-int(lw*0.6), int(lw*0.6), int(size*0.4)):
                            pygame.draw.polygon(screen, c_shd, [(x+j, ly+lh*0.4), (x+j-size*0.2, ly+lh*0.65), (x+j+size*0.3, ly+lh*0.4)])
                            pygame.draw.polygon(screen, c_mid, [(x+j+1, ly+lh*0.4), (x+j-size*0.1, ly+lh*0.6), (x+j+size*0.2, ly+lh*0.4)])

            elif dtype == 'oak':
                # Trunk
                tw = max(4, size // 2); th2 = int(size * 1.2)
                pygame.draw.rect(screen, WD_SHD, (x - tw//2, y-4, tw, th2), border_radius=2)
                pygame.draw.rect(screen, WD_MID, (x - tw//2 + 1, y-4, tw - 1, th2), border_radius=2)
                # Fluffy leaves (3 circles, animated sway)
                sw = math.sin(t * 0.018 + x * 0.02) * 3
                for oy2, ox2, rad, shd, mid, hlt in [
                    (-size*1.5, 0,        size*1.5, OAK_SHD, OAK_MID, OAK_HLT),
                    (-size*1.0, -size*0.8, size*1.2, OAK_SHD, OAK_MID, OAK_HLT),
                    (-size*1.0,  size*0.8, size*1.2, OAK_SHD, OAK_MID, OAK_HLT),
                ]:
                    pygame.draw.circle(screen, shd, (int(x+ox2+sw), int(y+oy2)), int(rad))
                    pygame.draw.circle(screen, mid, (int(x+ox2+sw), int(y+oy2-2)), int(rad*0.9))
                    pygame.draw.circle(screen, hlt, (int(x+ox2-rad*0.2+sw), int(y+oy2-rad*0.2)), int(rad*0.5))

            elif dtype == 'cactus':
                tw = max(4, size // 2); th = int(size * 1.8)
                pygame.draw.rect(screen, CAC_SHD, (x - tw//2, y - th, tw, th), border_radius=tw//2)
                pygame.draw.rect(screen, CAC_MID, (x - tw//2 + 1, y - th, tw - 1, th), border_radius=tw//2)
                pygame.draw.line(screen, CAC_HLT, (x - tw//4, y - th + 2), (x - tw//4, y - 2), 1)
                # Branches
                pygame.draw.rect(screen, CAC_MID, (x + tw//2, y - th//2, size//1.5, tw), border_radius=2)
                pygame.draw.rect(screen, CAC_MID, (x + tw//2 + size//1.5 - tw, y - th//1.5, tw, th//3), border_radius=2)
                # Spikes
                for sy in range(y - th + 4, y, 6):
                    pygame.draw.line(screen, (200,200,150), (x - tw//2 - 2, sy), (x - tw//2, sy + 2), 1)

            elif dtype == 'dead_tree':
                tw = max(3, size // 3); th = int(size * 1.5)
                pygame.draw.polygon(screen, DWD_SHD, [(x-tw, y), (x+tw, y), (x+tw//2, y-th), (x-tw//2, y-th)])
                pygame.draw.polygon(screen, DWD_MID, [(x-tw//2, y), (x+tw//2, y), (x+tw//4, y-th), (x-tw//4, y-th)])
                # Crooked branches
                pygame.draw.line(screen, DWD_MID, (x, y - th//2), (x - size, y - th), max(2, tw//2))
                pygame.draw.line(screen, DWD_MID, (x, y - th//1.5), (x + size*0.8, y - th*1.2), max(2, tw//2))

            elif dtype == 'crystal':
                h = size * 1.5; w = size * 0.8
                # Removed Pulse glow per user request
                
                pygame.draw.polygon(screen, CRY_SHD, [(x, y - h), (x - w, y), (x, y + h//4), (x + w, y)])
                pygame.draw.polygon(screen, CRY_MID, [(x, y - h), (x - w*0.5, y), (x, y + h//4), (x + w*0.5, y)])
                pygame.draw.polygon(screen, CRY_HLT, [(x, y - h + 2), (x - w*0.2, y), (x, y + h//5)])

            elif dtype == 'rock':
                pygame.draw.circle(screen, RCK_SHD, (x, y), size//2)
                pygame.draw.circle(screen, RCK_MID, (x-1, y-1), size//2 - 1)
                pygame.draw.circle(screen, RCK_HLT, (x-2, y-2), size//4)

            elif dtype == 'bones':
                pygame.draw.arc(screen, (220,220,200), (x-size//2, y-size//2, size, size), 0, math.pi, 2)
                pygame.draw.arc(screen, (220,220,200), (x-size//3, y-size//3, size//1.5, size//1.5), 0, math.pi, 2)

            elif dtype in ['flower', 'dark_flower']:
                c1 = (255,255,255) if dtype == 'flower' else (150,50,200)
                c2 = (255,200,50)  if dtype == 'flower' else (255,100,255)
                for ox, oy in [(0,-3), (-3,0), (3,0), (0,3)]:
                    pygame.draw.circle(screen, c1, (x+ox, y+oy), 2)
                pygame.draw.circle(screen, c2, (x, y), 2)

        # 5. Marker Điểm Xuất Phát — Cột đá 2 bên
        if self.path:
            sx, sy = self.path[0]
            # Removed ripple effect per user request
            # Cột đá 2 bên
            pygame.draw.rect(screen, (80, 80, 90),  (sx-25, sy-30, 10, 35), border_radius=2)
            pygame.draw.rect(screen, (120,120,130), (sx-25, sy-30,  5, 35), border_radius=2)
            pygame.draw.rect(screen, (80, 80, 90),  (sx+15, sy-30, 10, 35), border_radius=2)
            pygame.draw.rect(screen, (120,120,130), (sx+15, sy-30,  5, 35), border_radius=2)
            # Khí xoáy xanh
            pygame.draw.ellipse(screen, (100, 200, 255, 150), (sx-15, sy-25, 30, 25))
            pygame.draw.ellipse(screen, (200, 240, 255, 200), (sx-8,  sy-20, 16, 15))

        # 6. Marker Điểm Đích — Cờ phất phới
        if self.path:
            ex, ey = self.path[-1]
            pygame.draw.ellipse(screen, (0, 0, 0, 80), (ex-35, ey-15, 70, 30))
            # Đế pháo đài
            pygame.draw.rect(screen, (100,100,110), (ex-30, ey-30, 60, 30), border_radius=4)
            pygame.draw.rect(screen, (140,140,150), (ex-30, ey-30, 60, 10), border_radius=4)
            for i in range(5):
                pygame.draw.rect(screen, (80,80,90), (ex-28+i*12, ey-35, 8, 10), border_radius=2)
            # Cổng vòm đỏ
            pygame.draw.rect(screen, (40,10,10),   (ex-12, ey-15, 24, 25), border_radius=10)
            pygame.draw.rect(screen, (180,40,40),  (ex-12, ey-15, 24, 25), 3, border_radius=10)
            # Cờ phất phới (wave animation)
            flag_t = self.time_ticker * 0.08
            for pole_x, dir_x in [(-20, 1), (20, -1)]:
                px, py = ex + pole_x, ey - 35
                pygame.draw.line(screen, (200,180,50), (px, py), (px, py - 20), 2)
                pts = []
                for seg in range(6):
                    fx = px + dir_x * seg * 2
                    fy = py - 20 + seg * 2 + int(math.sin(flag_t + seg * 0.8) * 3)
                    pts.append((fx, fy))
                if len(pts) >= 2:
                    pygame.draw.lines(screen, (40,100,220), False, pts, 2)
                # Thân cờ fill
                if len(pts) >= 3:
                    fill_pts = pts + [(pts[-1][0], pts[0][1])]
                    try:
                        pygame.draw.polygon(screen, (40,100,220), fill_pts)
                    except:
                        pass

        # 7. Hiệu ứng Lá Rơi
        for p in self.particles:
            p[0] += p[3] + math.sin(self.time_ticker * 0.03 + p[1]*0.1) * 0.6
            p[1] += p[2]
            if p[1] > HEIGHT:
                p[1] = -10
                p[0] = random.randint(0, WIDTH)
            pygame.draw.rect(screen, p[4], (int(p[0]), int(p[1]), 4, 3), border_radius=1)


    # ── Kiểm tra có thể đặt tháp ────────────────────────────────────────────
    def is_placeable(self, x, y):
        if y < 40:
            return False
        c, r = x // TILE_SIZE, y // TILE_SIZE
        if 0 <= c < COLS and 0 <= r < ROWS:
            return self.grid[r][c] == 1
        return False
