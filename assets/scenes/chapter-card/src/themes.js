// Theme của Scene Library (Claude viết 05/11/2026) — màu/font theo assets/shops/<shop>/shop.json, asset theo
// assets/library/kits/<bộ>.json. Thêm theme = thêm 1 khoá ở đây + asset trong assets.js (library.export_web).
window.SCENE_THEMES = {
  gdp_red: {
    label: "GDP — Red Paper Lab", engine: "paper", brand: "GIADUNGPLUS",
    fonts: { title: "GdpBold", sub: "GdpReg", eyebrow: "GdpBold" },          // UTM Avo (shop.json GDP)
    color: { title: "#2b1b12", sub: "#f4efe6", eyebrow: "#2b1b12" },
    bg: { default: "giay-do-gach", kraft: "giay-kraft-nau-toi" },
    photo: "anh-in-bep-den-trang",
    motion: "pop / snap, giấy bay nhịp stop-motion 12 hình/giây"
  },
  phaledo_dark: {
    label: "PHALEDO — Dark Glass Editorial", engine: "glass", brand: "PHALEDO",
    fonts: { title: "PhBold", sub: "PhLight", eyebrow: "PhReg" },             // Averta (shop.json PHALEDO)
    color: { title: "#f2e9e3", shine: "#fff7ea", sub: "#c0b7a6", eyebrow: "#b89a6a", line: "#b89a6a", frame: "rgba(184,154,106,.55)" },
    bg: { default: "den-giay-my-thuat" }, light: "anh-sang-khuc-xa",
    photo: "none",
    motion: "fade / reveal theo dòng / ánh sáng quét qua chữ, chậm và mượt"
  },
  phaledo_warm: {
    label: "PHALEDO — Warm Kitchen Journal", engine: "journal", brand: "PHALEDO",
    fonts: { title: "PhBold", sub: "PhLight", eyebrow: "PhReg" },
    color: { title: "#3e2c20", sub: "#6b5646", eyebrow: "#8a6a4a" },
    bg: { default: "giay-be-am" }, page: "trang-so-tay-trong",
    photo: "anh-nguyen-lieu-am",
    motion: "trang sổ tay trượt vào như lật trang, polaroid rơi nhẹ, nét gạch chân tự vẽ"
  }
};
