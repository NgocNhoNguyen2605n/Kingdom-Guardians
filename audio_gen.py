import numpy as np
import wave
import os

def save_wav(filename, audio_data, sample_rate=44100):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with wave.open(filename, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        # Chuyển đổi [-1.0, 1.0] sang int16
        audio_data = np.clip(audio_data, -1.0, 1.0)
        audio_data = (audio_data * 32767).astype(np.int16)
        f.writeframes(audio_data.tobytes())

def generate_arrow(sample_rate=44100):
    duration = 0.15
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    # Sweep từ 1500Hz xuống 500Hz
    freqs = np.linspace(1500, 500, len(t))
    audio = np.sin(2 * np.pi * freqs * t)
    # Envelope: decay nhanh
    envelope = np.exp(-t * 20)
    return audio * envelope * 0.3

def generate_magic(sample_rate=44100):
    duration = 0.3
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    # Sweep từ 800Hz xuống 200Hz
    freqs = np.linspace(800, 200, len(t))
    audio = np.sin(2 * np.pi * freqs * t)
    # Thêm harmonics để nghe giống ma thuật hơn
    audio += 0.5 * np.sin(2 * np.pi * freqs * 2 * t)
    envelope = np.exp(-t * 10)
    return audio * envelope * 0.4

def generate_hit(sample_rate=44100):
    duration = 0.1
    audio = np.random.uniform(-1, 1, int(sample_rate * duration))
    # Lowpass filter đơn giản bằng cách dùng rolling mean (chống nhiễu quá chói)
    window_size = 5
    audio = np.convolve(audio, np.ones(window_size)/window_size, mode='same')
    envelope = np.exp(-np.linspace(0, duration, len(audio)) * 30)
    return audio * envelope * 0.5

def generate_build(sample_rate=44100):
    duration = 0.15
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    # Âm trầm vuông (wood thud)
    audio = np.sign(np.sin(2 * np.pi * 150 * t))
    envelope = np.exp(-t * 25)
    return audio * envelope * 0.6

def generate_click(sample_rate=44100):
    duration = 0.05
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio = np.sin(2 * np.pi * 1000 * t)
    envelope = np.exp(-t * 50)
    return audio * envelope * 0.3

def generate_die(sample_rate=44100):
    duration = 0.25
    audio = np.random.uniform(-1, 1, int(sample_rate * duration))
    # Âm vỡ vụn, giảm tần số
    t = np.linspace(0, duration, len(audio))
    freq_mod = np.sin(2 * np.pi * 50 * t)
    audio = audio * freq_mod
    envelope = np.exp(-t * 15)
    return audio * envelope * 0.4

if __name__ == "__main__":
    print("Đang tạo file âm thanh tổng hợp (Procedural Audio)...")
    save_wav("assets/sounds/shoot_arrow.wav", generate_arrow())
    save_wav("assets/sounds/shoot_magic.wav", generate_magic())
    save_wav("assets/sounds/hit.wav", generate_hit())
    save_wav("assets/sounds/build.wav", generate_build())
    save_wav("assets/sounds/click.wav", generate_click())
    save_wav("assets/sounds/enemy_die.wav", generate_die())
    print("Hoàn tất!")
