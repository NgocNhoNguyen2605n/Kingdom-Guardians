"""
Kho hằng số toàn cục (Global Constants) của trò chơi Kingdom Guardians.

Mô-đun này tập trung toàn bộ thông số cấu hình cố định của trò chơi vào một nơi
duy nhất, giúp dễ dàng điều chỉnh mà không cần sửa logic trong từng module.

Nhóm hằng số:
    Cửa sổ  : WIDTH, HEIGHT, FPS — kích thước màn hình và tốc độ khung hình.
    Lưới    : TILE_SIZE, ROWS, COLS — kích thước ô và số hàng/cột bản đồ.
    Gameplay: MAX_WAVES, AOE_RADIUS — số wave tối đa và bán kính nổ AoE.
    Màu sắc : WHITE, BLACK, RED, GREEN, BLUE, GOLD_COLOR, ... — bảng màu chung.
    Vật liệu: WOOD_COLOR, STONE_COLOR, GRASS_LIGHT, DIRT_PATH, ... — màu chủ đề.
"""
# Cấu hình cửa sổ game
WIDTH = 800
HEIGHT = 600
FPS = 60

# Cấu hình lưới bản đồ
TILE_SIZE = 40
ROWS = HEIGHT // TILE_SIZE
COLS = WIDTH // TILE_SIZE

# Mốc Giới Hạn Trận Game
MAX_WAVES = 5

# Màu sắc RGB (Bảng màu mới mô phỏng Kingdom Rush)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 20, 60)
GREEN = (0, 150, 0)
BLUE = (30, 100, 200)

GRASS_LIGHT = (145, 190, 60)
GRASS_DARK = (130, 175, 45)
BUSH_COLOR = (70, 120, 30)

DIRT_PATH = (220, 195, 135)
DIRT_BORDER = (195, 165, 100)

UI_PANEL_BG = (40, 35, 30)
UI_PANEL_BORDER = (20, 15, 10)
GOLD_COLOR = (255, 215, 0)

WOOD_COLOR = (139, 90, 43)
STONE_COLOR = (120, 120, 120)

# Bán kính nổ AoE mặc định của Tháp Ma Thuật
AOE_RADIUS = 80
