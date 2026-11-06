// Theme Count & Reveal (Claude viết 05/11/2026) — cùng 3 theme Scene Library. Màu/font theo shop.json:
// GDP UTM Avo (#c01818 / #f1c40f) · PHALEDO Averta (#161616 / #b89a6a / #f2e9e3), tiêu đề PHALEDO IN HOA.
window.SCENE_THEMES = {
  gdp_red: {
    label: "GDP — Red Paper Lab", engine: "paper", brand: "GIADUNGPLUS",
    fonts: { title: "GdpBold", eyebrow: "GdpBold", term: "GdpBold", note: "GdpReg", num: "GdpBold" },
    color: { title: "#2b1b12", eyebrow: "#f4efe6", term: "#2b1b12", note: "#5a4636", num: "#b3121a", mark: "241,196,15" },
    bg: { default: "giay-do-gach", kraft: "giay-kraft-nau-toi" },
    px: { title: 96, count: 150, term: 64, note: 38, micro: 40 },
    motion: "checklist giấy: từng tờ giấy đập vào từ hai phía (stop-motion 12 hình/giây) kèm tem đỏ đánh số, tờ mới nhất tô bút dạ vàng"
  },
  phaledo_dark: {
    label: "PHALEDO — Dark Glass Editorial", engine: "glass", brand: "PHALEDO",
    fonts: { title: "PhBold", eyebrow: "PhReg", term: "PhBold", note: "PhLight", num: "PhLight" },
    color: { title: "#f2e9e3", shine: "rgba(255,247,234,.95)", eyebrow: "#d2b98c", line: "#b89a6a", term: "#f2e9e3",
             note: "#c0b7a6", num: "#b89a6a", pill: "rgba(16,16,16,.58)" },
    bg: { default: "den-giay-my-thuat" }, light: "anh-sang-khuc-xa",
    px: { title: 90, count: 420, term: 64, note: 38, micro: 38 },
    motion: "ba mục editorial: số mảnh champagne + dòng trồi lên trong mặt nạ, nét kẻ mảnh tự vẽ giữa các mục, ánh sáng quét"
  },
  phaledo_warm: {
    label: "PHALEDO — Warm Kitchen Journal", engine: "journal", brand: "PHALEDO",
    fonts: { title: "PhBold", eyebrow: "PhReg", term: "PhBold", note: "PhLight", num: "PhReg" },
    color: { title: "#3e2c20", eyebrow: "#8a6a4a", term: "#3e2c20", note: "#6b5646", num: "#8a6a4a", box: "#8a6a4a",
             check: "#6f7f4f", tag: "#fbf3e6" },
    bg: { default: "giay-be-am" }, page: "trang-so-tay-trong", washi: "bang-washi-be",
    px: { title: 84, count: 140, term: 58, note: 36, micro: 38 },
    motion: "trang sổ tay trượt lên, mỗi mục được tick bằng nét vẽ tay rồi hiện chữ, lá khô + hạt cà phê trên mép trang"
  }
};
