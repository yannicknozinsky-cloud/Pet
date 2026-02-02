from TTS.api import TTS
import os

print("Current working dir:", os.getcwd())

# Offline-englisches Modell
tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False, gpu=False)

# Ausgabedatei
output_file = "output.wav"
tts.tts_to_file(text="Hello! This is offline English TTS.", file_path=output_file)

print("File created at:", os.path.abspath(output_file))
