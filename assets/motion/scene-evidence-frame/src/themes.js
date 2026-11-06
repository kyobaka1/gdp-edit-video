// Theme Evidence Frame (Claude viết 06/11/2026) — cùng 3 theme Scene Library. Màu/font theo shop.json:
// GDP UTM Avo (#c01818 / #f1c40f) · PHALEDO Averta (#161616 / #b89a6a / #f2e9e3).
window.SCENE_THEMES = {
  gdp_red: {
    label: "GDP — Red Paper Lab", engine: "paper", brand: "GIADUNGPLUS",
    fonts: { title: "GdpBold", figure: "GdpBold", small: "GdpReg" },
    color: { title: "#f4efe6", figure: "#b3121a", figlab: "#2b1b12", caption: "#2b1b12", print: "#fbfaf6", stamp: "#c01818" },
    bg: { default: "giay-kraft-nau-toi", red: "giay-do-gach" },
    px: { title: 46, figure: 96, figlab: 30, caption: 28 },
    motion: "ảnh điều tra: tấm ảnh in viền trắng đập lên bảng giấy kraft, băng keo 2 góc, tem đỏ 'THẬT'; số liệu trên giấy note vàng; stop-motion 12 hình/giây"
  },
  phaledo_dark: {
    label: "PHALEDO — Dark Glass Editorial", engine: "glass", brand: "PHALEDO",
    fonts: { title: "PhReg", figure: "PhLight", small: "PhLight" },
    color: { title: "#e8d6b0", figure: "#f2e9e3", figlab: "#c0b7a6", caption: "#a89f90", line: "#b89a6a", pill: "rgba(16,16,16,.6)" },
    bg: { default: "den-giay-my-thuat" }, light: "anh-sang-khuc-xa",
    px: { title: 32, figure: 104, figlab: 30, caption: 26 },
    motion: "ảnh và số liệu tinh gọn: khung mảnh champagne + dấu cắt góc, ảnh mở dần (mặt nạ), số lớn nét mảnh hiện dần dưới nét kẻ"
  },
  phaledo_warm: {
    label: "PHALEDO — Warm Kitchen Journal", engine: "journal", brand: "PHALEDO",
    fonts: { title: "PhBold", figure: "PhBold", small: "PhLight" },
    color: { title: "#3e2c20", figure: "#3e2c20", figlab: "#6b5646", caption: "#6b5646", corner: "#8a6a4a", tag: "#fbf3e6", print: "#fbf8f2" },
    bg: { default: "giay-be-am" }, washi: "bang-washi-be",
    px: { title: 44, figure: 88, figlab: 28, caption: 26 },
    motion: "ảnh dán sổ: ảnh có 4 góc giấy giữ ảnh + washi, rơi nhẹ; số liệu trên thẻ giấy kem, ghi nguồn chữ mảnh"
  }
};
