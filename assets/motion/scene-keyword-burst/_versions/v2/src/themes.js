// Theme Keyword Burst (Claude viết 05/11/2026) — cùng 3 theme của Scene Library, token riêng cho chữ đè footage.
// Màu/font theo assets/shops/<shop>/shop.json: GDP UTM Avo (#c01818/#f1c40f) · PHALEDO Averta (#161616/#b89a6a/#f2e9e3).
window.SCENE_THEMES = {
  gdp_red: {
    label: "GDP — Red Paper Lab", engine: "paper", brand: "GIADUNGPLUS",
    fonts: { word: "GdpBold", lead: "GdpBold" },
    color: { top: "#ffffff", bottom: "rgba(255,255,255,.48)", accentTop: "#ffd84a", accentBottom: "rgba(241,196,15,.52)",
             shadow: "rgba(24,6,4,.62)", ghost: "rgba(255,255,255,.24)", lead: "#f4efe6" },
    tape: "bang-giay-den-trong", y: 0.25, px: { micro: 190, standard: 220, full: 240 }, min1: 130, track: "0em",
    motion: "snap: từng chữ trượt ngang từ phía nó đứng, vượt nhẹ rồi khựng; băng giấy đen nhịp stop-motion 12 hình/giây"
  },
  phaledo_dark: {
    label: "PHALEDO — Dark Glass Editorial", engine: "glass", brand: "PHALEDO",
    fonts: { word: "PhBold", lead: "PhReg" },
    color: { top: "#f2e9e3", bottom: "rgba(242,233,227,.46)", accentTop: "#e2c99a", accentBottom: "rgba(184,154,106,.52)",
             shine: "rgba(255,247,234,.95)", shadow: "rgba(0,0,0,.6)", ghost: "rgba(226,201,154,.20)", lead: "#d2b98c", line: "#b89a6a" },
    y: 0.27, px: { micro: 168, standard: 188, full: 200 }, min1: 118, track: ".05em",
    motion: "chữ trồi lên trong mặt nạ theo từng từ, chậm và mượt, ánh sáng quét qua, nét mảnh champagne"
  },
  phaledo_warm: {
    label: "PHALEDO — Warm Kitchen Journal", engine: "journal", brand: "PHALEDO",
    fonts: { word: "PhBold", lead: "PhReg" },
    color: { top: "#fbf3e6", bottom: "rgba(251,243,230,.55)", accentTop: "#f3cf98", accentBottom: "rgba(224,178,122,.55)",
             shadow: "rgba(50,28,12,.58)", lead: "#4a3424", underline: "#f0d2a0" },
    tape: "bang-washi-be", y: 0.26, px: { micro: 180, standard: 200, full: 220 }, min1: 124, track: ".01em",
    motion: "chữ trượt lên nhẹ + nghiêng về thẳng như dán vào sổ, băng washi, nét gạch chân tự vẽ"
  }
};
