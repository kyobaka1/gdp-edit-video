// Theme Timeline / Process (Claude viết 06/11/2026) — cùng 3 theme Scene Library. Màu/font theo shop.json:
// GDP UTM Avo (#c01818 / #f1c40f) · PHALEDO Averta (#161616 / #b89a6a / #f2e9e3).
window.SCENE_THEMES = {
  gdp_red: {
    label: "GDP — Red Paper Lab", engine: "paper", brand: "GIADUNGPLUS",
    fonts: { label: "GdpBold", note: "GdpBold", num: "GdpBold", title: "GdpBold" },
    color: { line: "#e0241b", label: "#2b1b12", note: "#f4efe6", num: "#b3121a", title: "#f4efe6", done: "#1f7a3a",
             mark: "241,196,15", bar: "rgba(20,12,8,.55)", chip: "#f4efe6", chipText: "#2b1b12" },
    bg: { default: "giay-kraft-nau-toi", red: "giay-do-gach" },
    px: { label: 72, note: 36, title: 62, micro: 34 },
    motion: "đường bút dạ đỏ chạy từ mốc này sang mốc kia, tem đỏ đánh số đập xuống, nhãn giấy xé + băng đen ghi mốc thời gian; mốc đang nói tô vàng"
  },
  phaledo_dark: {
    label: "PHALEDO — Dark Glass Editorial", engine: "glass", brand: "PHALEDO",
    fonts: { label: "PhBold", note: "PhReg", num: "PhLight", title: "PhReg" },
    color: { line: "#b89a6a", label: "#f2e9e3", note: "#d2b98c", num: "#d2b98c", title: "#d2b98c", done: "#d2b98c",
             dim: "rgba(242,233,227,.45)", bar: "rgba(16,16,16,.6)", chip: "rgba(16,16,16,.6)", chipText: "#f2e9e3" },
    bg: { default: "den-giay-my-thuat" }, light: "anh-sang-khuc-xa",
    px: { label: 66, note: 30, title: 38, micro: 30 },
    motion: "nét mảnh champagne chạy dọc nối các nút tròn mảnh, nút đang nói có vòng lan, nút đã qua tô đặc"
  },
  phaledo_warm: {
    label: "PHALEDO — Warm Kitchen Journal", engine: "journal", brand: "PHALEDO",
    fonts: { label: "PhBold", note: "PhReg", num: "PhBold", title: "PhBold" },
    color: { line: "#c0703f", label: "#3e2c20", note: "#7a5a3c", num: "#3e2c20", title: "#3e2c20", done: "#6f7f4f",
             bar: "rgba(251,243,230,.9)", chip: "#fbf3e6", chipText: "#3e2c20" },
    bg: { default: "giay-be-am" }, page: "trang-so-tay-trong",
    px: { label: 62, note: 32, title: 56, micro: 30 },
    motion: "nét chấm bút chì nối các vòng tròn vẽ tay trên trang sổ, mốc đã qua được tick xanh rêu"
  }
};
