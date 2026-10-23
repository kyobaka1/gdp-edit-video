# GDP Video Studio — hướng dẫn cho Codex

Giống hệt `CLAUDE.md` (đọc file đó trước). Giao tiếp với Sếp bằng tiếng Việt.

Skill (đã cài vào `~\.codex\skills` bằng `tools\sync_skill.py install`; nguồn ở `.claude\skills\` trong studio):

- `gdp-video-localize` — Việt hoá video tiếng Trung (quy trình + luật đầy đủ).
- `gdp-video-motion` — animation thương hiệu (Claude Design → alpha → chèn vào job; logo động thay logo tĩnh,
  watermark động thay chữ). Hợp đồng: `assets/motion/README.md`.

Model xịn đang lái phiên → KHÔNG tự mở ảnh / nghe audio bằng model đó: xem ảnh `vs.py look`, nghe `vs.py hear`
(luật chi phí trong skill gdp-video-localize).
