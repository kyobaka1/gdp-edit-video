// Mở ảnh trên máy vào Photoshop web mà không cần hộp chọn file hệ thống (Claude không bấm được hộp đó).
// Chạy qua javascript_tool trên tab photoshop.adobe.com (trang chủ). Trang tải lại / đổi route thì chạy lại.
//   1. Dán đoạn dưới → find "claude upload slot" → file_upload(ref, paths=[lasso.js, i01.jpg, i01.json, i02.jpg, …])
//      (nạp CẢ LÔ một lần; nạp lại = ghi đè danh sách file)
//   2. window.__openName = 'i01.jpg' (ảnh đầu của nhóm) → bấm "Upload" → "Upload from computer" → Photoshop mở ảnh.
document.querySelectorAll('#claude-file-input').forEach(e => e.remove());
const inp = document.createElement('input');
inp.type = 'file'; inp.id = 'claude-file-input'; inp.multiple = true;
inp.setAttribute('aria-label', 'claude upload slot');
inp.style.cssText = 'position:fixed;left:4px;bottom:4px;z-index:999999;background:#fff;width:90px';
document.body.appendChild(inp);
window.showOpenFilePicker = async function () {
  const files = [...document.getElementById('claude-file-input').files];
  const file = files.find(f => window.__openName ? f.name === window.__openName : f.type.startsWith('image/'));
  const h = { kind: 'file', name: file.name, getFile: async () => file, isSameEntry: async o => o === h,
              queryPermission: async () => 'granted', requestPermission: async () => 'granted' };
  document.getElementById('claude-file-input').style.display = 'none';
  return [h];
};
'picker ready';
