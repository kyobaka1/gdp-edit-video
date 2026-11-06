// Theme Number Impact (Claude viết 06/11/2026) — cùng 3 theme Scene Library. Màu/font theo shop.json:
// GDP UTM Avo (#c01818 / #f1c40f) · PHALEDO Averta (#161616 / #b89a6a / #f2e9e3).
window.SCENE_THEMES = {
  gdp_red: {
    label: "GDP — Red Paper Lab", engine: "paper", brand: "GIADUNGPLUS",
    fonts: { num: "GdpBold", small: "GdpReg", title: "GdpBold" },
    color: { top: "#ffffff", bottom: "rgba(255,255,255,.5)", hiTop: "#ffd84a", hiBottom: "rgba(241,196,15,.55)", shadow: "rgba(24,6,4,.62)",
             small: "#fff4e6", arrow: "#f1c40f", up: "#1f8a3a", down: "#c01818",
             barA: "#efe3cc", barB: "#f1c40f", chartNum: "#2b1b12", chartSmall: "#3b2a1c", title: "#f4efe6" },
    bg: { default: "giay-kraft-nau-toi", red: "giay-do-gach" },
    px: { big: 210, from: 130, small: 46, chart: 92, title: 50 }, y: 0.27,
    motion: "số đếm lên rồi khựng (snap), mũi tên vàng vẽ tay từ số cũ sang số mới; full: 2 cột giấy mọc lên, tem đỏ ghi mức tăng"
  },
  phaledo_dark: {
    label: "PHALEDO — Dark Glass Editorial", engine: "glass", brand: "PHALEDO",
    fonts: { num: "PhLight", small: "PhReg", title: "PhReg" },
    color: { top: "#f2e9e3", bottom: "rgba(242,233,227,.5)", hiTop: "#e8d6b0", hiBottom: "rgba(184,154,106,.55)", shadow: "rgba(0,0,0,.6)",
             small: "#d2b98c", arrow: "#b89a6a", up: "#d2b98c", down: "#a8706a",
             barA: "rgba(242,233,227,.18)", barB: "rgba(184,154,106,.75)", chartNum: "#f2e9e3", chartSmall: "#c0b7a6", title: "#d2b98c", line: "#b89a6a" },
    bg: { default: "den-giay-my-thuat" }, light: "anh-sang-khuc-xa",
    px: { big: 200, from: 120, small: 34, chart: 96, title: 32 }, y: 0.28,
    motion: "số mảnh lớn đếm lên mượt, nét kẻ champagne; mũi tên mảnh; full: cột kính mảnh mọc lên, số nét mảnh"
  },
  phaledo_warm: {
    label: "PHALEDO — Warm Kitchen Journal", engine: "journal", brand: "PHALEDO",
    fonts: { num: "PhBold", small: "PhLight", title: "PhBold" },
    color: { top: "#fbf3e6", bottom: "rgba(251,243,230,.6)", hiTop: "#f3cf98", hiBottom: "rgba(224,178,122,.6)", shadow: "rgba(50,28,12,.58)",
             small: "#fbf3e6", arrow: "#c0703f", up: "#6f7f4f", down: "#a0522d",
             barA: "rgba(160,120,90,.35)", barB: "rgba(192,112,63,.75)", chartNum: "#3e2c20", chartSmall: "#6b5646", title: "#3e2c20" },
    bg: { default: "giay-be-am" }, page: "trang-so-tay-trong",
    px: { big: 190, from: 116, small: 40, chart: 84, title: 46 }, y: 0.27,
    motion: "số kem ấm trượt lên + đếm, mũi tên cong bút chì; full: cột tô bút màu trên trang sổ, khoanh mức tăng"
  }
};
