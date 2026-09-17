import sys
import json
from faster_whisper import WhisperModel

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No file path provided"}))
        sys.exit(1)
        
    audio_path = sys.argv[1]
    try:
        model = WhisperModel("small", device="cpu", compute_type="int8")
        segments, info = model.transcribe(audio_path, beam_size=5)
        lines = []
        for segment in segments:
            t = segment.text.strip()
            if not t:
                continue
            # 若该语段末尾没有任何标点，默认追加句号或自然隔断，保证语意有呼吸停顿
            if not t[-1] in "，。！？,.!?；;…~”’\"'":
                t += "。"
            lines.append(t)
        text = "\n".join(lines).strip()
        print(json.dumps({"text": text}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    main()
