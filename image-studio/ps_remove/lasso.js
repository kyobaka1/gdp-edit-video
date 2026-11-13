// Vẽ lasso trong Photoshop web bằng chuỗi pointer event (chạy qua javascript_tool của Claude in Chrome).
// 1) Tools -> Select -> Lasso, bấm "Select more" (sau Ctrl+D chế độ tự về "Create new selection").
// 2) Gán window.__POLYS = <nội dung polys.json của text_polys.py>, dán đoạn dưới, gọi:
//      await window.__drawAll()              // vẽ hết
//      await window.__drawAll(['nhan-1'])    // chỉ vẽ cụm có tên này
// 3) Soát bằng ảnh chụp phóng to, rồi bấm Remove ở thanh nổi dưới ảnh.
//    Sếp 13/11: chọn HẾT mọi cụm chữ rồi Remove MỘT lần (không Remove từng cụm). Chỗ còn sót mới lasso nhỏ + Remove tiếp.
window.__lassoCss = async function (P) {
  function deepAt(x, y) {
    let el = document.elementFromPoint(x, y);
    while (el && el.shadowRoot) {
      const inner = el.shadowRoot.elementFromPoint(x, y);
      if (!inner || inner === el) break;
      el = inner;
    }
    return el;
  }
  const tgt = deepAt(P[0][0], P[0][1]);
  const base = { bubbles: true, cancelable: true, composed: true, pointerId: 1, pointerType: 'mouse', isPrimary: true, view: window };
  const ev = (type, x, y, btns) => {
    const o = { ...base, clientX: x, clientY: y, screenX: x, screenY: y, button: type === 'pointermove' ? -1 : 0, buttons: btns };
    tgt.dispatchEvent(new PointerEvent(type, o));
    tgt.dispatchEvent(new MouseEvent(type.replace('pointer', 'mouse'), { ...o, button: 0 }));
  };
  ev('pointerdown', P[0][0], P[0][1], 1);
  for (let i = 1; i <= P.length; i++) {
    const a = P[i - 1], b = P[i % P.length];
    const n = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / 1.5));
    for (let j = 1; j <= n; j++) {
      ev('pointermove', a[0] + (b[0] - a[0]) * j / n, a[1] + (b[1] - a[1]) * j / n, 1);
      await new Promise(r => setTimeout(r, 2));
    }
  }
  ev('pointerup', P[0][0], P[0][1], 0);
};
window.__drawAll = async function (names) {
  let c = 0;
  for (const [n, P] of window.__POLYS) {
    if (names && !names.includes(n)) continue;
    await window.__lassoCss(P);
    c++;
    await new Promise(r => setTimeout(r, 350));
  }
  return c;
};
