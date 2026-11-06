// Theme Detail Spotlight (Claude viết 06/11/2026) — cùng 3 theme Scene Library. Màu/font theo shop.json:
// GDP UTM Avo (#c01818 / #f1c40f) · PHALEDO Averta (#161616 / #b89a6a / #f2e9e3).
window.SCENE_THEMES = {
  gdp_red: {
    label: "GDP — Red Paper Lab", engine: "paper", brand: "GIADUNGPLUS",
    fonts: { label: "GdpBold", note: "GdpReg" },
    color: { ring: "#e0241b", arrow: "#e0241b", label: "#f4efe6", note: "#2b1b12", loupe: "#fbfaf6" },
    dim: 0.22, px: { label: 46, note: 32 },
    motion: "khoanh bút dạ đỏ 2 vòng + mũi tên vẽ tay; nhãn băng giấy đen + ghi chú giấy xé (stop-motion 12 hình/giây); kính lúp viền giấy trắng"
  },
  phaledo_dark: {
    label: "PHALEDO — Dark Glass Editorial", engine: "glass", brand: "PHALEDO",
    fonts: { label: "PhReg", note: "PhLight" },
    color: { ring: "#d2b98c", arrow: "#d2b98c", label: "#e8d6b0", note: "#f2e9e3", loupe: "#b89a6a", pill: "rgba(16,16,16,.58)" },
    dim: 0.45, px: { label: 34, note: 31 },
    motion: "vùng sáng (ngoài tối dần), vòng mảnh champagne + vòng lan, đường chỉ dẫn mảnh gấp khúc tới nhãn chữ giãn; kính lúp viền champagne"
  },
  phaledo_warm: {
    label: "PHALEDO — Warm Kitchen Journal", engine: "journal", brand: "PHALEDO",
    fonts: { label: "PhBold", note: "PhLight" },
    color: { ring: "#c0703f", arrow: "#c0703f", label: "#3e2c20", note: "#6b5646", tag: "#fbf3e6", loupe: "#fbf8f2" },
    dim: 0.18, px: { label: 42, note: 30 },
    motion: "khoanh bút chì nâu cam 2 nét + mũi tên cong vẽ tay, nhãn thẻ giấy kem có washi; kính lúp viền giấy kem"
  }
};
