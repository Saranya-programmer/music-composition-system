# backend/music_generator.py
import os
import time
import torch
import numpy as np
from scipy.io.wavfile import write
from pydub import AudioSegment
from backend.model_manager import ModelManager

class MusicGenerator:
    def __init__(self, default_model="backend/musicgen-small", samplerate=32000, output_dir="generated"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.sr = samplerate
        self.output_dir = output_dir
        self.model_manager = ModelManager(self.device)

        print(f"[MusicGenerator] Device: {self.device}")
        self.model_manager.load_model(default_model)

    def duration_to_tokens(self, seconds):
        return max(50, int(seconds * 50))

    def map_energy(self, energy):
        if energy >= 8:
            return 1.2, 4.0
        elif energy >= 5:
            return 1.0, 3.0
        return 0.8, 2.0

    def post_process(self, wav_path):
        audio = AudioSegment.from_wav(wav_path)
        audio = audio.normalize().fade_in(300).fade_out(300)
        mp3_path = wav_path.replace(".wav", ".mp3")
        audio.export(mp3_path, format="mp3")
        return mp3_path

    def generate(self, prompt, duration=10, energy=5, model_name=None):
        if model_name:
            self.model_manager.load_model(model_name)

        model, processor = self.model_manager.get()
        os.makedirs(self.output_dir, exist_ok=True)

        print(f"[MusicGenerator] Generating ({self.model_manager.current_name}) → {duration}s")

        temperature, cfg = self.map_energy(energy)
        max_new_tokens = self.duration_to_tokens(duration)

        inputs = processor(text=[prompt], return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        start = time.time()
        audio_values = model.generate(
            **inputs,
            do_sample=True,
            temperature=temperature,
            guidance_scale=cfg,
            max_new_tokens=max_new_tokens
        )

        audio = audio_values[0].cpu().numpy().squeeze()
        audio = np.clip(audio, -1, 1)

        expected = int(duration * self.sr)
        if len(audio) < expected:
            audio = np.pad(audio, (0, expected - len(audio)))

        wav_path = os.path.join(self.output_dir, f"music_{int(time.time())}.wav")
        write(wav_path, self.sr, (audio * 32767).astype(np.int16))

        mp3_path = self.post_process(wav_path)

        return {
            "wav": wav_path,
            "mp3": mp3_path,
            "duration": duration,
            "model": self.model_manager.current_name,
            "elapsed_s": round(time.time() - start, 2)
        }
