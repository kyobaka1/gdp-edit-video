// GDP Image Studio — chạy trong trang dựng ảnh: co chữ cho vừa khung, vẽ đường chỉ, trả số đo cho bộ kiểm.
window.IMS = (() => {
  const stage = () => document.getElementById('stage');
  const U = () => stage().getBoundingClientRect().width / 1000;

  // số dòng thật của 1 phần tử chữ (đếm theo các hộp dòng)
  function lineCount(el) {
    const r = document.createRange(); r.selectNodeContents(el);
    const sm = el.querySelector('small'); if (sm) r.setEndBefore(sm);          // dòng phụ `note` không tính vào số dòng tiêu đề
    const tops = new Set(); for (const b of r.getClientRects()) if (b.width > 1) tops.add(Math.round(b.top / 3));
    return tops.size;
  }

  // Co cỡ chữ cho tới khi vừa số dòng tối đa và không tràn bề ngang. Không co quá 60% cỡ xin.
  function fit() {
    const out = {};
    for (const b of document.querySelectorAll('.b[data-fs]')) {
      const want = parseFloat(b.dataset.fs), maxLines = parseInt(b.dataset.lines || '0', 10);
      let fs = want;
      const tx = b.querySelector('.tx') || b;
      const over = () => {
        const sw = stage().getBoundingClientRect(), r = b.getBoundingClientRect();
        if (maxLines && !b.classList.contains('pills') && lineCount(tx) > maxLines) return true;
        if (b.scrollWidth > b.clientWidth + 1) return true;
        return (b.dataset.nowrap !== undefined || b.classList.contains('pills')) && r.width > sw.width * 0.96;
      };
      b.style.setProperty('--fs', fs);
      while (over() && fs > want * 0.6) { fs = Math.round(fs * 0.97 * 10) / 10; b.style.setProperty('--fs', fs); }
      out[b.id] = fs;
    }
    return out;
  }

  // Đường chỉ (callout) và đường kích thước (dim) — vẽ sau khi đã biết khung chữ
  function drawLines() {
    const svg = document.getElementById('lines'); svg.innerHTML = '';
    const S = stage().getBoundingClientRect(), u = U();
    const P = (xy) => [xy[0] / 100 * S.width, xy[1] / 100 * S.height];
    const add = (tag, attrs) => { const e = document.createElementNS('http://www.w3.org/2000/svg', tag);
      for (const k in attrs) e.setAttribute(k, attrs[k]); svg.appendChild(e); return e; };
    for (const b of document.querySelectorAll('.callout[data-to]')) {
      const [tx, ty] = P(JSON.parse(b.dataset.to)), r = (b.querySelector('.tx') || b).getBoundingClientRect();
      const col = getComputedStyle(b).color, pad = 7 * u;
      // điểm xuất phát: giữa cạnh của khung chữ nằm gần điểm chỉ nhất
      const c = [[r.left - pad, (r.top + r.bottom) / 2], [r.right + pad, (r.top + r.bottom) / 2],
                 [(r.left + r.right) / 2, r.top - pad], [(r.left + r.right) / 2, r.bottom + pad]]
        .sort((a, z) => Math.hypot(a[0] - tx, a[1] - ty) - Math.hypot(z[0] - tx, z[1] - ty))[0];
      const w = parseFloat(b.dataset.lw || '2.4') * u;
      add('line', { x1: c[0], y1: c[1], x2: tx, y2: ty, stroke: 'rgba(0,0,0,.22)', 'stroke-width': w * 2.2, 'stroke-linecap': 'round' });
      add('line', { x1: c[0], y1: c[1], x2: tx, y2: ty, stroke: col, 'stroke-width': w, 'stroke-linecap': 'round' });
      add('circle', { cx: tx, cy: ty, r: 6.5 * u, fill: col, stroke: 'rgba(0,0,0,.22)', 'stroke-width': u });
      add('circle', { cx: tx, cy: ty, r: 13 * u, fill: 'none', stroke: col, 'stroke-width': 1.6 * u, opacity: .55 });
    }
    for (const b of document.querySelectorAll('.dim[data-from]')) {
      const a = P(JSON.parse(b.dataset.from)), z = P(JSON.parse(b.dataset.to));
      const col = getComputedStyle(b).color, w = 2.2 * u, t = 9 * u;
      const ang = Math.atan2(z[1] - a[1], z[0] - a[0]), nx = -Math.sin(ang) * t, ny = Math.cos(ang) * t;
      const r = (b.querySelector('.tx') || b).getBoundingClientRect();
      const gap = (Math.abs(Math.cos(ang)) * r.width + Math.abs(Math.sin(ang)) * r.height) / 2 + 6 * u;
      const mx = (a[0] + z[0]) / 2, my = (a[1] + z[1]) / 2, dx = Math.cos(ang) * gap, dy = Math.sin(ang) * gap;
      const seg = (x1, y1, x2, y2) => add('line', { x1, y1, x2, y2, stroke: col, 'stroke-width': w, 'stroke-linecap': 'round' });
      seg(a[0], a[1], mx - dx, my - dy); seg(mx + dx, my + dy, z[0], z[1]);     // chừa chỗ cho con số ở giữa
      seg(a[0] - nx, a[1] - ny, a[0] + nx, a[1] + ny); seg(z[0] - nx, z[1] - ny, z[0] + nx, z[1] + ny);
    }
  }

  // Số đo từng khối: khung khối + khung TỪNG DÒNG chữ thật + màu + cỡ chữ → bộ kiểm (qa.py)
  function measure() {
    const S = stage().getBoundingClientRect(), out = [];
    const box = (r) => [r.left - S.left, r.top - S.top, r.width, r.height];
    for (const b of document.querySelectorAll('.b, .logo, .wm')) {
      const item = { id: b.id, type: b.dataset.type, rect: box(b.getBoundingClientRect()), texts: [] };
      for (const tx of b.querySelectorAll('.tx, .k, .v, .title, .hl, small')) {
        const cs = getComputedStyle(tx), r = document.createRange(); r.selectNodeContents(tx);
        const rows = [...r.getClientRects()].filter((q) => q.width > 1 && q.height > 1).map(box);
        if (!rows.length) continue;
        item.texts.push({ text: tx.innerText, rows, color: tx.dataset.color || cs.color, px: parseFloat(cs.fontSize),
          gradColor: (b.classList.contains('grad') && b.classList.contains('tone-dark') && tx.dataset.colorDark) || null,
          weight: parseInt(cs.fontWeight, 10), lines: lineCount(tx), boxed: !!tx.closest('.pill, .st-plate'),
          font: tx.closest('.headline, .pill, .title, .disp') ? b.dataset.fd : b.dataset.fb, part: tx.classList.contains('hl') ? 'hl' : (tx.tagName === 'SMALL' ? 'note' : null),
          outlined: !!tx.closest('.st-outline') || (b.classList.contains('headline') && !b.classList.contains('st-plate')
            && parseFloat(getComputedStyle(b).getPropertyValue('--edge')) >= 0.08),
          edged: b.classList.contains('headline') && !b.classList.contains('st-plate')
            && parseFloat(getComputedStyle(b).getPropertyValue('--edge')) >= 0.03 });
      }
      if (b.dataset.fs) { item.want = parseFloat(b.dataset.fs); item.got = parseFloat(getComputedStyle(b).getPropertyValue('--fs')); }
      if (b.dataset.lines) item.maxLines = parseInt(b.dataset.lines, 10);
      out.push(item);
    }
    return out;
  }

  // Đặt tông sáng/đậm sau khi đo nền thật dưới khối (khối để tone = auto)
  function setTone(id, tone) {
    const b = document.getElementById(id); if (!b) return;
    b.classList.remove('tone-light', 'tone-dark'); b.classList.add('tone-' + tone);
    for (const p of b.querySelectorAll('.pill.glass')) p.classList.toggle('on-light', tone === 'dark');
  }
  function setSrc(id, src, cls) { const e = document.getElementById(id); if (!e) return; if (src) e.src = src; if (cls) e.classList.add(cls); }

  return { fit, drawLines, measure, setTone, setSrc };
})();
