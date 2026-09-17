import base64
import tempfile
import os
from faster_whisper import WhisperModel

print("Loading model...")
model = WhisperModel("small", device="cpu", compute_type="int8")
print("Model loaded.")

# create a dummy valid wav using ffmpeg
os.system("ffmpeg -f lavfi -i sine=frequency=1000:duration=1 -acodec pcm_s16le -y dummy.wav")

segments, info = model.transcribe("dummy.wav", beam_size=5)
text = "".join([s.text for s in segments])
print("Transcribed:", text)
