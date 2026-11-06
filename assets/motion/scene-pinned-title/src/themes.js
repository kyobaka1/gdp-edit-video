// Theme Pinned Title (Claude viết 05/11/2026) — cùng 3 theme Scene Library. Màu/font theo shop.json:
// GDP UTM Avo (#c01818 / #f1c40f) · PHALEDO Averta (#161616 / #b89a6a / #f2e9e3), tiêu đề PHALEDO IN HOA.
window.SCENE_THEMES = {
  gdp_red: {
    label: "GDP — Red Paper Lab", engine: "paper", brand: "GIADUNGPLUS",
    fonts: { title: "GdpBold", eyebrow: "GdpBold", term: "GdpBold", note: "GdpReg" },
    color: { title: "#2b1b12", eyebrow: "#f4efe6", term: "#2b1b12", note: "#5a4636", num: "#b3121a", mark: "#f1c40f" },
    card: "nhan-tieu-de-trong", clip: "kep-giay", tape: "bang-giay-den-trong", strip: "bang-keo-giay", stamp: "tem-do-trong",
    y: 0.195, px: { title: 118, micro: 44, term: 46, note: 31 },
    motion: "thẻ giấy đập xuống + kẹp giấy ghim (nhịp stop-motion 12 hình/giây); nhãn con là băng giấy đập vào từ phía nó đứng, mục đang nói tô vàng"
  },
  phaledo_dark: {
    label: "PHALEDO — Dark Glass Editorial", engine: "glass", brand: "PHALEDO",
    fonts: { title: "PhBold", eyebrow: "PhReg", term: "PhReg", note: "PhLight" },
    color: { title: "#f2e9e3", bottom: "rgba(242,233,227,.62)", shine: "rgba(255,247,234,.95)", shadow: "rgba(0,0,0,.6)",
             eyebrow: "#d2b98c", line: "#b89a6a", term: "#f2e9e3", note: "#c0b7a6", num: "#d2b98c",
             pill: "rgba(16,16,16,.58)", edge: "rgba(184,154,106,.38)", edgeOn: "#b89a6a" },
    y: 0.18, px: { title: 120, micro: 38, term: 42, note: 30 },
    motion: "tiêu đề trồi lên trong mặt nạ + ánh sáng quét; nhãn con là viên kính tối viền champagne hiện mờ dần, mục đang nói sáng viền"
  },
  phaledo_warm: {
    label: "PHALEDO — Warm Kitchen Journal", engine: "journal", brand: "PHALEDO",
    fonts: { title: "PhBold", eyebrow: "PhReg", term: "PhBold", note: "PhLight" },
    color: { title: "#3e2c20", eyebrow: "#8a6a4a", term: "#3e2c20", note: "#6b5646", num: "#8a6a4a",
             tag: "#fbf3e6", ink: "#c0703f", check: "#6f7f4f" },
    page: "trang-so-tay-trong", washi: "bang-washi-be",
    y: 0.18, px: { title: 104, micro: 40, term: 42, note: 30 },
    motion: "mẩu trang sổ tay trượt lên + washi; nhãn con là thẻ giấy kem rơi nhẹ, mục đang nói gạch chân tự vẽ, mục đã qua được tick"
  }
};
