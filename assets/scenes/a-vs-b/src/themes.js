// Theme A vs B (Claude viết 06/11/2026) — cùng 3 theme Scene Library. Màu/font theo shop.json:
// GDP UTM Avo (#c01818 / #f1c40f) · PHALEDO Averta (#161616 / #b89a6a / #f2e9e3), nhãn PHALEDO IN HOA.
window.SCENE_THEMES = {
  gdp_red: {
    label: "GDP — Red Paper Lab", engine: "paper", brand: "GIADUNGPLUS",
    fonts: { title: "GdpBold", label: "GdpBold", point: "GdpBold", vs: "GdpBold" },
    color: { title: "#2b1b12", label: "#f4efe6", point: "#2b1b12", vs: "#b3121a", win: "#1f8a3a", lose: "#b3121a",
             card: "#efe3cc", mark: "241,196,15" },
    bg: { default: "giay-do-gach", kraft: "giay-kraft-nau-toi" },
    px: { title: 80, label: 46, point: 38, vs: 92, micro: 40 },
    motion: "hai phe giấy: ảnh in viền trắng dán băng keo đập vào từ hai phía (stop-motion 12 hình/giây), tem đỏ VS ở giữa, phe thắng đóng dấu ✓, phe thua xám + gạch chéo"
  },
  phaledo_dark: {
    label: "PHALEDO — Dark Glass Editorial", engine: "glass", brand: "PHALEDO",
    fonts: { title: "PhBold", label: "PhBold", point: "PhLight", vs: "PhLight" },
    color: { title: "#f2e9e3", shine: "rgba(255,247,234,.95)", label: "#f2e9e3", point: "#d9d0c2", line: "#b89a6a",
             vs: "#d2b98c", win: "#d2b98c", card: "rgba(18,18,18,.55)", pill: "rgba(16,16,16,.58)" },
    bg: { default: "den-giay-my-thuat" }, light: "anh-sang-khuc-xa",
    px: { title: 76, label: 44, point: 34, vs: 64, micro: 36 },
    motion: "so sánh tối giản: hai khung ảnh viền champagne mảnh mở dần (mặt nạ), chữ mảnh, 'vs' mảnh trong vòng tròn; phe thắng sáng viền, phe thua mờ xám"
  },
  phaledo_warm: {
    label: "PHALEDO — Warm Kitchen Journal", engine: "journal", brand: "PHALEDO",
    fonts: { title: "PhBold", label: "PhBold", point: "PhReg", vs: "PhBold" },
    color: { title: "#3e2c20", label: "#3e2c20", point: "#4a3424", vs: "#c0703f", win: "#6f7f4f", lose: "#a0522d",
             tag: "#fbf3e6", polaroid: "#fbf8f2" },
    bg: { default: "giay-be-am" }, washi: "bang-washi-be",
    px: { title: 72, label: 42, point: 34, vs: 70, micro: 36 },
    motion: "hai polaroid rơi nhẹ + washi, 'vs' khoanh tay; phe thắng được khoanh tròn + tick vẽ tay, phe thua mờ xám"
  }
};
