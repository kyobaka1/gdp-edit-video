r"""Kiểm chuỗi TTS dự phòng (studio/voice.py TTS_CHAIN).
  sim  : giả lập vclip hết tiền (402) → phải rơi xuống tokenrouter, câu sau KHÔNG gọi lại vclip (0 ký tự).
  live : gọi thật từng model dự phòng với giọng từng shop, nghe lại → điểm khớp (cổng 0,9). Ghi jobs/_probe/chain/.
Chạy: .venv\Scripts\python.exe tools\probe_tts_chain.py sim|live"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from google.genai import errors  # noqa: E402

from studio import config, voice  # noqa: E402
from studio.narration import _hear  # noqa: E402
from studio.templates import shop_voice  # noqa: E402

SHOPS = ["giadungplus_official", "lteng_vn", "lteng_hcm", "phaledo_official"]
TEXT = voice.spoken("Đồ dùng phòng tắm bừa bộn? Đã có kệ treo tường PHALEDO, lắp không cần khoan, "
                    "thành chắn cao giữ đồ không rơi. Chờ keo khô 48 đến 72 giờ là dùng được.")
out = config.JOBS / "_probe" / "chain"
out.mkdir(parents=True, exist_ok=True)

if sys.argv[1:] == ["sim"]:
    import requests
    calls, waits = [], []
    voice.time.sleep = lambda secs: waits.append(secs)  # không đợi thật

    def http_err(code, text):
        r = requests.Response()
        r.status_code, r._content = code, text.encode()
        return requests.HTTPError(f"{code} Client Error", response=r)

    def fake_vclip(model, text, v):  # hết tiền / key sai → bỏ vclip cả lượt chạy
        calls.append(model)
        raise http_err(402, "insufficient credit")

    script = {"openai/gpt-audio-mini": [http_err(429, "Maximum 5 requests within 1 minutes"), None, None]}

    def fake_router(model, text, v):  # mini: lần đầu dính giới hạn phút rồi chạy · gpt-audio: không tới lượt
        calls.append(model)
        step = script[model].pop(0)
        if step is not None:
            raise step
        return open(out.parent / "tokenrouter" / "gpt-audio-mini.wav", "rb").read(), "audio/wav"

    voice._vclip_tts, voice._tokenrouter_tts = fake_vclip, fake_router
    used1 = voice.synthesize("câu 1", {"vclip": "x", "name": "Kore", "gender": "nữ"}, out / "sim1.wav")
    first = list(calls)
    used2 = voice.synthesize("câu 2", {"vclip": "x", "name": "Kore", "gender": "nữ"}, out / "sim2.wav")
    second = calls[len(first):]
    print("lượt 1 gọi:", first, "đợi", waits, "→", used1, f"{voice._wav_duration(out / 'sim1.wav'):.2f}s")
    print("lượt 2 gọi:", second, "→", used2)
    ok1 = used1 == used2 == "openai/gpt-audio-mini" and second == ["openai/gpt-audio-mini"] and waits == [61]
    ok1 &= first == ["vclip", "openai/gpt-audio-mini", "openai/gpt-audio-mini"]

    # 402 (hết tiền) cả vclip lẫn gpt-audio-mini → bỏ cả lượt chạy; hết sạch chuỗi → lỗi có lý do từng model
    voice._exhausted.clear()
    calls.clear()
    script["openai/gpt-audio-mini"] = [http_err(402, "insufficient credit")]
    try:
        voice.synthesize("câu 3", {"vclip": "x", "name": "Kore", "gender": "nữ"}, out / "sim3.wav")
        ok2, msg = False, "không báo lỗi"
    except RuntimeError as exc:
        msg = str(exc)
        ok2 = all(m in msg for m in ("vclip: DEAD", "gpt-audio-mini: DEAD"))
    print("hết sạch chuỗi:", msg.replace(chr(10), " | ")[:400])
    print("ĐẠT" if ok1 and ok2 else "TRƯỢT", ok1, ok2)
    sys.exit(0 if ok1 and ok2 else 1)

models = list(voice.TTS_CHAIN) if len(sys.argv) < 3 else [p for p in voice.TTS_CHAIN if p[1] == sys.argv[2]]
for provider, model in models:
    for shop in SHOPS if provider in ("tokenrouter", "vclip") else SHOPS[:1]:
        v = shop_voice(shop)
        f = out / f"{model.replace('/', '_')}_{shop}.wav"
        try:
            voice.synthesize(TEXT, v, f, chain=[(provider, model)])
            heard = _hear(f)
            s = voice._match(TEXT, heard)
            gv = v.get("vclip_name", "")[-6:] if provider == "vclip" else v["name"] if provider == "gemini" else (v.get("openai") or voice.OPENAI_VOICE_BY_GENDER[v["gender"]])
            print(f"{model:28} {shop:22} {gv:8} {voice._wav_duration(f):5.1f}s khớp {s:.2f} {'ĐẠT' if s >= 0.9 else 'TRƯỢT'}"
                  f" | {heard.strip()[:90]}")
        except Exception as exc:
            print(f"{model:28} {shop:22} LỖI {str(exc)[:200]}")
