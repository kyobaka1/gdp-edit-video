// Theme Problem → Solution (Claude viết 06/11/2026) — cùng 3 theme Scene Library. Màu/font theo shop.json:
// GDP UTM Avo (#c01818 / #f1c40f) · PHALEDO Averta (#161616 / #b89a6a / #f2e9e3), nhãn PHALEDO IN HOA.
window.SCENE_THEMES = {
  gdp_red: {
    label: "GDP — Red Paper Lab", engine: "paper", brand: "GIADUNGPLUS",
    fonts: { label: "GdpBold", note: "GdpReg", stamp: "GdpBold" },
    color: { pLabel: "#fff4e6", sLabel: "#2b1b12", pNote: "#ffe3c4", sNote: "#3b2a1c", bad: "#ffd2c4", badStamp: "#fff1e0",
             good: "#1f7a3a", print: "#fbfaf6", cross: "#ffe9d6" },
    bg: { problem: "giay-do-gach", solution: "giay-kraft-nau-toi" },
    px: { label: 92, note: 40, stamp: 62, micro: 42 },
    motion: "tờ giấy đỏ (vấn đề, dấu SAI) bị XÉ ĐÔI bay ra 2 phía lộ giấy kraft + mảng vàng (giải pháp, dấu ĐÚNG đập xuống); stop-motion 12 hình/giây"
  },
  phaledo_dark: {
    label: "PHALEDO — Dark Glass Editorial", engine: "glass", brand: "PHALEDO",
    fonts: { label: "PhBold", note: "PhLight", stamp: "PhReg" },
    color: { pLabel: "#8f8a84", sLabel: "#f2e9e3", pNote: "#7a756f", sNote: "#c0b7a6", bad: "#a8706a", good: "#d2b98c",
             line: "#b89a6a", shine: "rgba(255,247,234,.95)", pill: "rgba(16,16,16,.58)", cross: "#a8706a" },
    bg: { problem: "den-giay-my-thuat", solution: "den-giay-my-thuat" }, light: "anh-sang-khuc-xa",
    px: { label: 86, note: 36, stamp: 34, micro: 38 },
    motion: "vấn đề xám, nét gạch mảnh; vệt sáng champagne quét ngang mở ra giải pháp sáng, dấu ✓ mảnh"
  },
  phaledo_warm: {
    label: "PHALEDO — Warm Kitchen Journal", engine: "journal", brand: "PHALEDO",
    fonts: { label: "PhBold", note: "PhLight", stamp: "PhBold" },
    color: { pLabel: "#5a4636", sLabel: "#3e2c20", pNote: "#7a6656", sNote: "#6b5646", bad: "#a0522d", good: "#6f7f4f",
             tag: "#fbf3e6", print: "#fbf8f2", cross: "#a0522d" },
    bg: { problem: "giay-be-am", solution: "giay-be-am" }, page: "trang-so-tay-trong",
    px: { label: 80, note: 34, stamp: 42, micro: 38 },
    motion: "trang sổ 'vấn đề' bị gạch chéo bút chì rồi LẬT đi, lộ trang 'giải pháp' được khoanh + tick vẽ tay"
  }
};
