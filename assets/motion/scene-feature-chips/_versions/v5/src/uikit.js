// UI Kit chung cho Scene "giao diện" C13+ (Claude viết 07/11/2026, học từ mẫu m2 / s1 / Blue 1 — example/_phan-tich).
// BẢN GỐC ở assets/scenes/_uikit/uikit.js — mỗi family giữ một bản sao trong src/ (Motion Engine chép src/ khi import);
// sửa bản gốc rồi chạy `tools/ui_scenes_sync.py` để chép lại cho mọi family có "uikit": true.
//
// Khác 3 theme thương hiệu cũ (giấy đỏ / kính đen / sổ tay): đây là "đạo cụ giao diện" hiện đại — thẻ bo góc, chip,
// công tắc, hộp nhấn — dùng chung mọi shop; FONT + MÀU NHẤN theo thương hiệu (query brand / accent do cutlib điền):
// GDP & LTENG = UTM Avo · PHALEDO = Averta (không serif).  Theme: ui_dark (thẻ tối trên footage) · ui_light (thẻ sáng).
window.UIKIT = (function () {
  const Q = new URLSearchParams(location.search);
  const W = 1080, H = 1920, FPS = 30;
  const BRAND = (Q.get("brand") || "GIADUNGPLUS").toUpperCase();
  const DEF_ACC = { GIADUNGPLUS: "#f1c40f", PHALEDO: "#b89a6a", LTENG: "#2a8fd6" };
  const ACC = /^#[0-9a-f]{6}$/i.test(Q.get("accent") || "") ? Q.get("accent") : (DEF_ACC[BRAND] || "#f1c40f");
  const F = BRAND === "PHALEDO" ? { bold: "PhBold", reg: "PhReg", light: "PhLight" }
                                : { bold: "GdpBold", reg: "GdpReg", light: "GdpReg" };
  const THEME_ID = Q.get("theme") === "ui_light" ? "ui_light" : "ui_dark";
  const lum = hex => { const n = parseInt(hex.slice(1), 16); return (0.2126 * (n >> 16 & 255) + 0.7152 * (n >> 8 & 255) + 0.0722 * (n & 255)) / 255; };
  const rgba = (hex, a) => { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16 & 255},${n >> 8 & 255},${n & 255},${a})`; };
  const onAcc = lum(ACC) > 0.45 ? "#141414" : "#ffffff";
  const THEMES = {
    ui_dark: { label: "UI Dark — thẻ tối kính", card: "rgba(20,20,22,.80)", card2: "rgba(38,38,42,.86)", line: "rgba(255,255,255,.13)",
               text: "#ffffff", sub: "rgba(255,255,255,.64)", faint: "rgba(255,255,255,.28)", scrim: "rgba(0,0,0,.48)",
               shadow: "0 18px 40px rgba(0,0,0,.45)", off: "rgba(255,255,255,.18)" },
    ui_light: { label: "UI Light — thẻ sáng", card: "rgba(250,250,252,.93)", card2: "rgba(240,241,245,.95)", line: "rgba(20,24,35,.08)",
                text: "#15171c", sub: "#5d6272", faint: "rgba(20,24,35,.25)", scrim: "rgba(12,14,22,.30)",
                shadow: "0 18px 40px rgba(10,12,20,.28)", off: "rgba(20,24,35,.14)" },
  };
  const T = THEMES[THEME_ID];
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, k) => a + (b - a) * k;
  const prog = (t, a, b) => b <= a ? (t >= b ? 1 : 0) : clamp((t - a) / (b - a));
  const outCubic = x => 1 - Math.pow(1 - x, 3);
  const inCubic = x => x * x * x;
  const outBack = (x, s = 1.6) => 1 + (s + 1) * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2);
  const inOut = x => x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
  function rng(n) { let a = ((parseInt(Q.get("seed") || "1", 10) || 1) * 7919 + n * 104729) >>> 0;
    return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  const root = document.getElementById("root");
  // chữ luôn vẽ khử răng cưa XÁM: thẻ phủ khung nền đặc Chrome tự chuyển LCD (viền màu) lúc chữ đứng yên, xám lúc đang
  // có hiệu ứng → vẽ lại cùng thời điểm lệch (đo 07/11 feature-chips full: 187 mức). Lớp filter trên #stage chặn LCD.
  document.getElementById("stage").style.filter = "contrast(1)";
  const imgs = [];
  function node(tag, css, parent, text) { const e = document.createElement(tag); e.className = "abs";
    if (css) Object.assign(e.style, css); if (text != null) e.textContent = text; (parent || root).appendChild(e); return e; }
  function place(el, x, y) { el.style.left = Math.round(x) + "px"; el.style.top = Math.round(y) + "px"; }
  function fitFont(el, px, maxW, minK = 0.55) { let k = 1; el.style.fontSize = px + "px";
    while (el.offsetWidth > maxW && k > minK) { k -= 0.03; el.style.fontSize = Math.round(px * k) + "px"; } return el.offsetWidth <= maxW + 1; }
  function items(key = "items") { try { const a = JSON.parse(Q.get(key) || "[]"); return Array.isArray(a) ? a : []; } catch (e) { return []; } }
  function img(src) { const im = new Image(); im.src = src; imgs.push(im); return im; }

  // ── icon nét đơn (24×24, stroke) — chip / bước / CTA. "nhãn|icon" trong items ép icon; không ép thì đoán theo chữ ──
  const ICONS = {
    check: "M5 12.5l4.2 4.2L19 7", x: "M6 6l12 12M18 6L6 18", star: "M12 3.5l2.6 5.4 5.9.8-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.8z",
    bolt: "M13 3L5 13.5h6L10 21l8-10.5h-6z", drop: "M12 3.5c3.6 4.4 5.5 7.6 5.5 10.2a5.5 5.5 0 01-11 0c0-2.6 1.9-5.8 5.5-10.2z",
    shield: "M12 3l7 3v5.5c0 4.4-3 7.9-7 9.5-4-1.6-7-5.1-7-9.5V6z", leaf: "M5 19c0-8 5-13 14-14 0 9-5 14-13 14M5 19l7-7",
    clock: "M12 21a9 9 0 100-18 9 9 0 000 18zM12 7v5l3.2 2", box: "M3.5 7.5L12 3l8.5 4.5v9L12 21l-8.5-4.5zM3.5 7.5L12 12l8.5-4.5M12 12v9",
    home: "M4 11l8-7 8 7v9H4zM9.5 20v-5.5h5V20", ruler: "M3 15.5L15.5 3 21 8.5 8.5 21zM7 11.5l2 2M10 8.5l2 2M13 5.5l2 2",
    sparkle: "M12 3l1.8 5.4L19 10l-5.2 1.6L12 17l-1.8-5.4L5 10l5.2-1.6zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z",
    hand: "M8 13V6.5a1.5 1.5 0 013 0V12M11 11V5a1.5 1.5 0 013 0v6M14 11V6.5a1.5 1.5 0 013 0V14c0 4-2.5 7-6.5 7-3 0-4.5-1.5-6-4l-1.5-3a1.5 1.5 0 012.6-1.5L8 14",
    heart: "M12 20s-7.5-4.6-7.5-10A4.3 4.3 0 0112 7.4 4.3 4.3 0 0119.5 10c0 5.4-7.5 10-7.5 10z", cart: "M3 4h2.5l2.2 11h10.6L21 7.5H6.3M9.5 20a1 1 0 100-2 1 1 0 000 2zM17.5 20a1 1 0 100-2 1 1 0 000 2z",
    chat: "M4 5h16v11H9l-5 4z", fire: "M12 21c-4 0-6.5-2.6-6.5-6 0-3.4 2.6-5 3.4-8.5 2.2 1.4 3.1 3.2 3.1 5 1-.8 1.6-2.1 1.7-3.5 2.4 1.9 4.8 4.4 4.8 7 0 3.4-2.5 6-6.5 6z",
    tag: "M3.5 12.5V4h8.5L21 13l-8.5 8.5zM8 8.5h.01", money: "M3 6.5h18v11H3zM12 15a3 3 0 100-6 3 3 0 000 6zM6 9.5v5M18 9.5v5",
    sun: "M12 16.5a4.5 4.5 0 100-9 4.5 4.5 0 000 9zM12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4",
    layers: "M12 3l9 5-9 5-9-5zM3 13l9 5 9-5", chef: "M7 13.5V20h10v-6.5M7 13.5A4 4 0 017.6 6a4.5 4.5 0 018.8 0A4 4 0 0117 13.5z",
    wrench: "M14.5 6.5a4 4 0 015 5L11 20a2.1 2.1 0 01-3-3l8.5-8.5M14.5 6.5L12 4l-1.5 3 3 3 3-1.5",
  };
  const GUESS = [   // từ khoá tiếng Việt → icon (không ép bằng "|icon")
    [/chống nước|chống thấm|nước|rửa|ẩm|mốc/i, "drop"], [/inox|bền|chắc|chịu lực|an toàn|bảo hành|khoá|chống gỉ/i, "shield"],
    [/nhanh|phút|giây|giờ|tiết kiệm thời gian/i, "clock"], [/điện|sạc|pin|w\b|công suất/i, "bolt"], [/tự nhiên|tre|gỗ|xanh|sạch|eco/i, "leaf"],
    [/gọn|xếp|ngăn|tầng|kệ|hộp|đựng/i, "layers"], [/dán|lắp|khoan|vít|đinh/i, "wrench"], [/bếp|nấu|ăn|thực phẩm/i, "chef"],
    [/nhà|phòng|tường/i, "home"], [/kích thước|cm|mm|dài|rộng/i, "ruler"], [/giá|rẻ|tiết kiệm|đồng|tr\b|triệu|k\b/i, "money"],
    [/đẹp|sang|cao cấp|bóng/i, "sparkle"], [/tay|cầm|dễ dùng/i, "hand"], [/tặng|quà|ưu đãi|giảm/i, "tag"], [/nắng|mặt trời|ánh sáng/i, "sun"],
  ];
  function splitIcon(label) { const m = String(label).split("|"); return { text: m[0].trim(), icon: (m[1] || "").trim() }; }
  function iconFor(label, fallback = "check") { const s = splitIcon(label); if (s.icon && ICONS[s.icon]) return s.icon;
    for (const [re, ic] of GUESS) if (re.test(s.text)) return ic; return fallback; }
  function icon(name, color, size, sw = 2) { const d = ICONS[name] || ICONS.check;
    return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" style="position:static;display:block"><path d="${d}" fill="none" stroke="${color}" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round"/></svg>`; }

  // thẻ bo góc (thân thẻ giao diện) — nền theo theme, viền mảnh
  function card(css, parent) { return node("div", Object.assign({ background: T.card, borderRadius: "30px", border: `1.5px solid ${T.line}`,
    boxShadow: T.shadow }, css || {}), parent); }
  function scrim(alpha) { return node("div", { width: W + "px", height: H + "px",
    background: `radial-gradient(ellipse at 50% 45%, rgba(0,0,0,${(alpha * 0.55).toFixed(3)}) 0%, rgba(0,0,0,${alpha.toFixed(3)}) 75%)` }); }
  // nhãn nhỏ (eyebrow) + tiêu đề — mẫu: dòng nhỏ trắng + dòng to màu nhấn
  function heading(eyebrow, title, opt = {}) {
    const o = Object.assign({ x: W / 2, y: 0.17 * H, align: "center", maxW: 0.78 * W, ePx: 40, tPx: 86 }, opt);
    const wrap = node("div", { width: o.maxW + "px", textAlign: o.align });
    const e = eyebrow ? node("div", { position: "relative", fontFamily: F.reg, fontSize: o.ePx + "px", color: o.eColor || T.sub,
      whiteSpace: "nowrap", display: "inline-block" }, wrap, eyebrow) : null;
    const t = title ? node("div", { position: "relative", fontFamily: F.bold, fontSize: o.tPx + "px", color: o.tColor || ACC,
      lineHeight: "1.08", whiteSpace: "nowrap", display: "block", marginTop: "6px",
      textShadow: THEME_ID === "ui_dark" ? "0 3px 18px rgba(0,0,0,.55)" : "none" }, wrap, title) : null;
    if (e) { e.style.display = "block"; fitFont(e, o.ePx, o.maxW, 0.6); }
    if (t) fitFont(t, o.tPx, o.maxW, 0.5);
    const x0 = o.align === "center" ? o.x - o.maxW / 2 : o.align === "right" ? o.x - o.maxW : o.x;
    place(wrap, x0, o.y);
    return { wrap, e, t, h: wrap.offsetHeight };
  }
  function show(el, k, dy = 24, scale = 0) {   // hiện dần: mờ → rõ + trượt lên (+ phóng nhẹ)
    if (!el) return; el.style.opacity = k.toFixed(4);
    // dịch theo PIXEL NGUYÊN: lẻ px thì Chrome lúc vẽ lớp riêng lúc không → vẽ lại cùng thời điểm lệch chữ (Motion Engine báo)
    el.style.transform = `translateY(${Math.round((1 - k) * dy)}px)` + (scale ? ` scale(${(1 - scale + scale * k).toFixed(4)})` : "");
  }
  function exitAll(t, D, EX) {   // ra: mờ + nhoè về trong suốt (khung cuối trong suốt — Motion Engine kiểm)
    const DE = D - 1 / FPS, kx = inCubic(prog(t, DE - EX, DE));
    root.style.opacity = (t >= DE - 1e-6 ? 0 : 1 - kx).toFixed(4);
    root.style.filter = kx > 0.001 ? `blur(${(8 * kx).toFixed(2)}px)` : "none";
    return kx;
  }
  function ready(texts, after) {
    const fams = [...new Set(Object.values(F))];
    return Promise.all([
      ...fams.map(f => document.fonts.load(`40px "${f}"`, (texts || "") + "ỢẤỂỖ0123456789%")),
      ...imgs.map(im => im.decode().catch(() => { throw new Error("thiếu ảnh " + im.src); })),
    ]).then(after);
  }
  return { Q, W, H, FPS, BRAND, ACC, onAcc, F, T, THEME_ID, lum, rgba, clamp, lerp, prog, outCubic, inCubic, outBack, inOut, rng,
           root, node, place, fitFont, items, img, imgs, ICONS, icon, iconFor, splitIcon, card, scrim, heading, show, exitAll, ready };
})();
