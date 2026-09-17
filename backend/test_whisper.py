import base64
import tempfile
import os
from faster_whisper import WhisperModel

print("Loading model...")
model = WhisperModel("tiny", device="cpu", compute_type="int8")
print("Model loaded.")
