import threading
import queue
import asyncio
import edge_tts
import sounddevice as sd
import soundfile as sf
import io
import pyrubberband as pyrb  # stabile Pitch + TimeStretch Library

class OnlineTTS(threading.Thread):
    def __init__(self, voice="de-DE-ConradNeural"):
        super().__init__(daemon=True)
        self.voice = voice
        self.text_queue = queue.Queue()
        self.running = True
        self.start()

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        while self.running:
            try:
                # FIFO: erster Text, der reinkam
                text, rate, pitch = self.text_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            self.loop.run_until_complete(self._speak_async(text, rate, pitch))

    async def _speak_async(self, text, rate, pitch_steps):
        # Edge-TTS Audio streamen
        communicate = edge_tts.Communicate(text, self.voice)
        audio_bytes = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes.extend(chunk["data"])

        audio, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")

        # Pitch in Halbtonschritten (+/-)
        pitch_steps = float(pitch_steps)
        rate = float(rate)

        # Pyrubberband verändert Pitch + Geschwindigkeit stabil
        if pitch_steps != 0:
            audio = pyrb.pitch_shift(audio, sr, n_steps=pitch_steps)
        if rate != 1.0:
            audio = pyrb.time_stretch(audio, sr, rate)

        # Abspielen blockierend
        sd.play(audio, sr)
        sd.wait()

    def speak(self, text, rate=1.0, pitch=0):
        """
        text: Text der gesprochen werden soll
        rate: Geschwindigkeit, float, 1.0 = normal
        pitch: Halbtonschritte, float, +3 höher, -3 tiefer
        """
        # FIFO: nicht leeren, einfach hinten anstellen
        self.text_queue.put((text, float(rate), float(pitch)))

    def stop(self):
        self.running = False

