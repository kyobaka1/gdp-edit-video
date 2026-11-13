// Công cụ trong trang Photoshop web (chạy qua javascript_tool của Claude in Chrome). Sếp 13/11/2026.
// Nạp file KHÔNG qua tool call (đỡ token): ô tải tạm #claude-file-input (picker.js, `multiple`) +
// file_upload(ref, paths=[lasso.js, i01.jpg, i01.json, …]) → nạp script này bằng:
//   eval(await [...document.getElementById('claude-file-input').files].find(f => f.name === 'lasso.js').text())
//
//   __cal(x0, y0, scale)         // hiệu chỉnh: góc trên-trái ảnh (CSS px) + CSS px / px ảnh. Đo 1 lần mỗi nhóm kích thước
//   await __loadPolys('i01.json')// polygon toạ độ ảnh (batch.py / text_polys.py) → window.__POLYS
//   await __drawAll()            // vẽ mọi cụm; cụm 2 trở đi giữ Shift (= cộng vùng chọn) — khỏi bấm "Select more"
//   await __drawAll(['nhan-1'])  // chỉ vẽ cụm có tên này
//   await __toClipboard('i02.jpg') // chép ảnh vào CLIPBOARD THẬT (PNG) → rồi computer key "ctrl+v" (công cụ Move) = layer mới
// Sếp 13/11: chọn HẾT mọi cụm chữ rồi Remove MỘT lần. Chỗ còn sót mới lasso nhỏ + Remove tiếp.
// ⚠ Không dispatch sự kiện 'paste' giả: Photoshop đọc clipboard thật → dán nhầm chữ đang có trong clipboard.
window.__file = name => [...document.getElementById('claude-file-input').files].find(f => f.name === name);
window.__CAL = window.__CAL || null;
window.__cal = (x0, y0, s) => (window.__CAL = { x0, y0, s });
window.__loadPolys = async name => {
  if (!window.__CAL) throw new Error('chưa __cal(x0, y0, scale)');
  const { x0, y0, s } = window.__CAL;
  window.__POLYS = JSON.parse(await window.__file(name).text()).map(([n, P]) => [n, P.map(([x, y]) => [x0 + x * s, y0 + y * s])]);
  return window.__POLYS.length;
};
window.__lassoCss = async function (P, add) {
  function deepAt(x, y) {
    let el = document.elementFromPoint(x, y);
    while (el && el.shadowRoot) { const inner = el.shadowRoot.elementFromPoint(x, y); if (!inner || inner === el) break; el = inner; }
    return el;
  }
  const tgt = deepAt(P[0][0], P[0][1]);
  const base = { bubbles: true, cancelable: true, composed: true, pointerId: 1, pointerType: 'mouse', isPrimary: true, view: window, shiftKey: !!add };
  const ev = (type, x, y, btns) => {
    const o = { ...base, clientX: x, clientY: y, screenX: x, screenY: y, button: type === 'pointermove' ? -1 : 0, buttons: btns };
    tgt.dispatchEvent(new PointerEvent(type, o));
    tgt.dispatchEvent(new MouseEvent(type.replace('pointer', 'mouse'), { ...o, button: 0 }));
  };
  if (add) document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Shift', code: 'ShiftLeft', shiftKey: true, bubbles: true }));
  ev('pointerdown', P[0][0], P[0][1], 1);
  for (let i = 1; i <= P.length; i++) {
    const a = P[i - 1], b = P[i % P.length];
    const n = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / 1.5));
    for (let j = 1; j <= n; j++) { ev('pointermove', a[0] + (b[0] - a[0]) * j / n, a[1] + (b[1] - a[1]) * j / n, 1); await new Promise(r => setTimeout(r, 2)); }
  }
  ev('pointerup', P[0][0], P[0][1], 0);
  if (add) document.dispatchEvent(new KeyboardEvent('keyup', { key: 'Shift', code: 'ShiftLeft', bubbles: true }));
};
window.__drawAll = async function (names, addFirst) {
  let c = 0;
  for (const [n, P] of window.__POLYS) {
    if (names && !names.includes(n)) continue;
    await window.__lassoCss(P, addFirst || c > 0);
    c++;
    await new Promise(r => setTimeout(r, 350));
  }
  return c;
};
window.__toClipboard = async function (name) {
  const bmp = await createImageBitmap(window.__file(name));
  const c = new OffscreenCanvas(bmp.width, bmp.height);
  c.getContext('2d').drawImage(bmp, 0, 0);
  await navigator.clipboard.write([new ClipboardItem({ 'image/png': await c.convertToBlob({ type: 'image/png' }) })]);
  return bmp.width + 'x' + bmp.height;
};
'ps_remove lasso.js loaded';
