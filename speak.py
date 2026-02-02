# speak.py
from TTS.api import TTS
import sounddevice as sd
import threading
import queue
import torch

# TTS laden
tts = TTS(model_name="tts_models/de/thorsten/vits", progress_bar=False)
tts.to("cuda" if torch.cuda.is_available() else "cpu")

class SpeechWorker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.text_queue = queue.Queue()
        self.running = True
        self.start()

    def run(self):
        while self.running:
            try:
                text = self.text_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                wav = tts.tts(text, speed=2.0, pitch=6.0) 
                sd.play(wav, samplerate=tts.synthesizer.output_sample_rate)
                sd.wait()
            except Exception as e:
                print(f"TTS-Fehler: {e}")

    def speak(self, text):
        self.text_queue.put(text)

    def stop(self):
        self.running = False

worker = SpeechWorker()

def readtext(text):
    worker.speak(text)
