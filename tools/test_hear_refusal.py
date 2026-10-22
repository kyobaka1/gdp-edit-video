r"""Mẫu nhận diện "gpt-audio-mini từ chối nghe" (voice._REFUSAL): bắt đủ mọi câu từ chối đã gặp 22/10, không bắt nhầm
câu thuyết minh thật (bắt nhầm = mảnh đúng bị coi là chưa kiểm). Chạy: .venv\Scripts\python.exe tools\test_hear_refusal.py"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import config  # noqa: E402
from studio.voice import _REFUSAL  # noqa: E402

REFUSALS = [
    "Chắc chắn, xin vui lòng cung cấp audio để tôi có thể bắt đầu chép lại nội dung.",
    "Xin lỗi, tôi không thể xác định âm thanh từ yêu cầu của bạn. Vui lòng cung cấp r",
    "Chắc chắn, vui lòng cung cấp audio để tôi có thể bắt đầu chép lời.",
    "Tôi xin lỗi, nhưng tôi cần bạn cung cấp nội dung hoặc đoạn văn bản mà bạn muốn tôi chép lại.",
    "Chào bạn, xin hãy cung cấp nội dung âm thanh để tôi có thể chép lại nguyên văn lời nói.",
    "Xin vui lòng cung cấp tệp âm thanh để tôi có thể chép lại.",
    "Xin lỗi, tôi không thể nghe được audio.",
    "Chắc chắn rồi, vui lòng phát audio để tôi có thể chép lại nội dung.",
    "Vui lòng bật audio để tôi có thể chép lại nội dung.",
    "Được, vui lòng cung cấp audio để tôi có thể chép lại.",
    "Tất nhiên, vui lòng cung cấp đoạn audio mà bạn muốn chép lại.",
    "Tôi xin lỗi, tôi không nghe được danh sách chi tiết trong câu hỏi của bạn.",
    "Tôi xin lỗi, nhưng tôi hiện không thể nghe hoặc xử lý âm thanh.",
    "Rất tiếc, tôi không thể nghe được nội dung từ yêu cầu này. Bạn có thể thử tải lại",
    "Tôi xin lỗi, tôi không thể giúp với yêu cầu đó.",
    "Chắc chắn, vui lòng cho tôi biết bạn muốn chép nội dung từ đoạn audio nào.",
]
miss = [r for r in REFUSALS if not _REFUSAL.search(r)]
# mọi câu thuyết minh thật trong các job (kịch bản edl.narration) — không được khớp
real = []
for f in config.JOBS.glob("*/edl.json"):
    try:
        real += [p["text"] for p in (json.loads(f.read_text(encoding="utf-8")).get("narration") or {}).get("paragraphs", [])]
    except Exception:
        pass
false = [t for t in real if _REFUSAL.search(t)]
print(f"bắt {len(REFUSALS) - len(miss)}/{len(REFUSALS)} câu từ chối · bắt nhầm {len(false)}/{len(real)} câu thuyết minh thật")
for r in miss:
    print("  SÓT:", r)
for t in false[:10]:
    print("  NHẦM:", t)
sys.exit(1 if miss or false else 0)
