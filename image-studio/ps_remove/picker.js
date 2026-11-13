// Mở ảnh trên máy vào Photoshop web mà không cần hộp chọn file hệ thống (Claude không bấm được hộp đó).
// Chạy qua javascript_tool của Claude in Chrome trên tab photoshop.adobe.com (trang chủ):
//   B1. dán ĐOẠN 1 → find "claude upload slot" → file_upload(ref, paths=[ảnh]) nạp ảnh vào ô tạm.
//   B2. dán ĐOẠN 2 → bấm nút "Upload" (ô "Drag and drop…") → "Upload from computer" → Photoshop mở ảnh.
// Trang tải lại thì phải dán lại cả hai đoạn.

// ĐOẠN 1 — ô tải tạm
document.querySelectorAll('#claude-file-input').forEach(e => e.remove());
const inp = document.createElement('input');
inp.type = 'file'; inp.id = 'claude-file-input'; inp.accept = 'image/*';
inp.setAttribute('aria-label', 'claude upload slot');
inp.style.cssText = 'position:fixed;left:4px;bottom:4px;z-index:999999;background:#fff';
document.body.appendChild(inp);

// ĐOẠN 2 — thay hộp chọn file bằng handle giả trả đúng file vừa nạp
window.showOpenFilePicker = async function () {
  const file = document.getElementById('claude-file-input').files[0];
  const h = { kind: 'file', name: file.name, getFile: async () => file, isSameEntry: async o => o === h,
              queryPermission: async () => 'granted', requestPermission: async () => 'granted' };
  document.getElementById('claude-file-input').style.display = 'none';
  return [h];
};
