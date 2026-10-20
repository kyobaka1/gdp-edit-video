# GDP Video Studio — hướng dẫn cho Claude Code

Giao tiếp với Sếp bằng tiếng Việt. **Quy trình + luật đầy đủ: skill `gdp-video-localize`**
(`C:\Users\Admin\.claude\skills\gdp-video-localize\SKILL.md`, bản sao trong repo giadungplus `skills/gdp-video-localize/`).
Plan/trạng thái: repo giadungplus `docs/plans/2026-10-20-gdp-video-studio-viet-hoa-video.md`.

## Lệnh nhanh

```powershell
Set-Location C:\Users\Admin\gdp-video-studio; $env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe vs.py new inbox\<file>.mp4 --id <brand>-<slug>
.\.venv\Scripts\python.exe vs.py analyze <id>            # --regroup: không tốn token
#   → viết jobs\<id>\direct.py (mẫu: jobs\phaledo-ke-nha-tam-01\direct.py) → chạy nó ra edl.json
.\.venv\Scripts\python.exe vs.py music <id>              # nhạc Lyria không lời
.\.venv\Scripts\python.exe vs.py narrate <id>            # thuyết minh liền mạch, 1 lượt TTS
.\.venv\Scripts\python.exe vs.py render <id> [--final]
.\.venv\Scripts\python.exe vs.py qa <id> [--final]        # phải ĐẠT (sót 0); chưa → vs.py patch <id>
.\.venv\Scripts\python.exe vs.py audiocheck <id> [--final]
.\.venv\Scripts\python.exe vs.py templates <shop>        # xem mẫu chữ của shop
.\.venv\Scripts\python.exe vs.py shops                   # tình trạng tài nguyên từng shop (assets/shops/)
```

## 5 luật không được quên

1. Chữ trong cảnh (sản phẩm/nhãn/phụ kiện) giữ nguyên; chỉ đè chữ đồ hoạ, bằng MẪU có sẵn của SHOP
   (`assets/shops/<shop>/templates/`, `edl.shop`). Tài nguyên shop theo chuẩn `assets/shops/README.md`.
2. Dòng chữ xoay chéo → một ô xoay cùng góc.
3. Thuyết minh = một bài liền mạch bám cảnh, có chuyển ý — không đọc lại phụ đề; một lượt TTS (một giọng).
4. TTS gửi đúng văn bản, không chỉ dẫn giọng điệu; cổng kiểm ngược bắt buộc.
5. Nhạc nền luôn có, nhỏ nhưng nghe thấy (giọng −14 LUFS, nhạc −25 LUFS); không thêm tuyên bố sản phẩm chưa có trong nguồn.
