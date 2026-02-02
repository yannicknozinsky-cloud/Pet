# wakeword.py
import sounddevice as sd
import vosk
import queue
import json
import os
import threading

class WakeWordDetector:
    def __init__(self, model_path, keywords=["hey taro", "taro"], samplerate=16000, blocksize=4000, partial_len=2):
        self.model_path = model_path
        self.keywords = keywords
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.partial_len = partial_len
        self.q = queue.Queue()
        self.recognizer = vosk.KaldiRecognizer(vosk.Model(self.model_path), self.samplerate)
        self.callback_func = None
        self.running = False
        self.thread = None

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        self.q.put(bytes(indata))

    def _listen(self):
        with sd.RawInputStream(samplerate=self.samplerate, blocksize=self.blocksize,
                               dtype="int16", channels=1, callback=self.audio_callback):
            while self.running:
                try:
                    data = self.q.get(timeout=0.1)
                except queue.Empty:
                    continue
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").lower()
                    for kw in self.keywords:
                        if kw in text:
                            self.callback_func()
                else:
                    partial = json.loads(self.recognizer.PartialResult())
                    partial_text = partial.get("partial", "").lower()
                    for kw in self.keywords:
                        if kw[:self.partial_len] in partial_text:
                            self.callback_func()

    def start(self, on_wakeword):
        """Start listening in a background thread."""
        if self.running:
            return
        self.callback_func = on_wakeword
        self.running = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop background listening."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
