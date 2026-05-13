import pygame
import os

SOUNDS = {}

def init_audio():
    try:
        pygame.mixer.init()
        # Đảm bảo thư mục tồn tại
        sound_dir = "assets/sounds"
        if os.path.exists(sound_dir):
            files = ["shoot_arrow.wav", "shoot_magic.wav", "hit.wav", "build.wav", "click.wav", "enemy_die.wav"]
            for f in files:
                path = os.path.join(sound_dir, f)
                if os.path.exists(path):
                    key = f.replace(".wav", "")
                    SOUNDS[key] = pygame.mixer.Sound(path)
                    if key in ["shoot_arrow", "shoot_magic", "hit", "enemy_die"]:
                        SOUNDS[key].set_volume(0.3)
                    else:
                        SOUNDS[key].set_volume(0.6)
    except Exception as e:
        print("Lỗi khởi tạo âm thanh:", e)

def play_sound(name):
    if name in SOUNDS:
        SOUNDS[name].play()
