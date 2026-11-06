// Theme Quote / Insight (Claude viết 06/11/2026) — cùng 3 theme Scene Library. Màu/font theo shop.json:
// GDP UTM Avo (#c01818 / #f1c40f) · PHALEDO Averta (#161616 / #b89a6a / #f2e9e3). Ngoặc kép PHALEDO = Georgia (font máy Windows,
// kiểu tạp chí) — Averta vẽ dấu “ như 2 vạch xiên '//'.
window.SCENE_THEMES = {
  gdp_red: {
    label: "GDP — Red Paper Lab", engine: "paper", brand: "GIADUNGPLUS",
    fonts: { quote: "GdpBold", key: "GdpBold", mark: "GdpBold", by: "GdpBold", eyebrow: "GdpBold" },
    color: { quote: "#2b1b12", key: "#b3121a", mark: "#c01818", under: "#e0241b", by: "#f4efe6", eyebrow: "#f4efe6", eyebrowBg: "#c01818" },
    bg: { default: "giay-kraft-nau-toi", red: "giay-do-gach" },
    card: "giay-note-vang-trong", tape: "bang-keo-giay", byTape: "bang-giay-den-trong",
    px: { quote: 84, micro: 46, by: 32, eyebrow: 28, mark: 250, markMicro: 120 },
    motion: "giấy note vàng rơi xuống kraft (12 hình/giây) + băng keo dán; ngoặc kép đỏ to; chữ hiện từng từ, cụm khoá đỏ + vạch bút dạ đỏ quét dưới; người nói trên băng giấy đen"
  },
  phaledo_dark: {
    label: "PHALEDO — Dark Glass Editorial", engine: "glass", brand: "PHALEDO",
    fonts: { quote: "PhLight", key: "PhBold", mark: "Georgia", by: "PhReg", eyebrow: "PhReg" },
    color: { quote: "#f2e9e3", key: "#d2b98c", mark: "#b89a6a", under: "#b89a6a", by: "#d2b98c", eyebrow: "#d2b98c", line: "#b89a6a",
             panel: "rgba(14,14,14,.74)" },
    bg: { default: "den-giay-my-thuat" }, light: "anh-sang-khuc-xa",
    px: { quote: 68, micro: 42, by: 26, eyebrow: 24, mark: 240, markMicro: 120 },
    motion: "chữ mảnh hiện từng từ (mờ → nét, trồi nhẹ) trên nền đen ánh sáng khúc xạ; cụm khoá đậm champagne + gạch mảnh; dòng kẻ champagne mở ra trước tên người nói IN HOA giãn chữ"
  },
  phaledo_warm: {
    label: "PHALEDO — Warm Kitchen Journal", engine: "journal", brand: "PHALEDO",
    fonts: { quote: "PhReg", key: "PhBold", mark: "Georgia", by: "PhLight", eyebrow: "PhBold" },
    color: { quote: "#3e2c20", key: "#9a4a26", mark: "#c0703f", by: "#7a5a3c", eyebrow: "#6f7f4f", panel: "#fbf3e6" },
    bg: { default: "giay-be-am" }, page: "trang-so-tay-trong", washi: "bang-washi-be", under: "net-gach-chan-nau", branch: "nhanh-la-kho",
    px: { quote: 68, micro: 40, by: 30, eyebrow: 28, mark: 220, markMicro: 110 },
    motion: "trang sổ tay trượt lên + băng washi; chữ hiện từng từ, cụm khoá đậm nâu đỏ + nét bút gạch chân tự vẽ; nhành lá khô góc trang"
  }
};
