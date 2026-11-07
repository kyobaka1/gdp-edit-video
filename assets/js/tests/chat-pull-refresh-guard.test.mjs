import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const chatJsPath = resolve(__dirname, '..', 'chat.js');

async function loadChatExports() {
  const source = await readFile(chatJsPath, 'utf8');
  const context = {
    window: {},
    document: {
      addEventListener() {},
      getElementById() { return null; },
      querySelector() { return null; },
      createElement() {
        return {
          _text: '',
          set textContent(value) { this._text = String(value); },
          get innerHTML() {
            return this._text
              .replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;')
              .replace(/'/g, '&#39;');
          },
        };
      },
    },
    console,
    setTimeout,
    clearTimeout,
  };
  context.globalThis = context.window;
  vm.createContext(context);
  vm.runInContext(source, context, { filename: chatJsPath });
  return context.window;
}

async function loadGuard() {
  const exports = await loadChatExports();
  return exports.GDPChatPullRefreshGuard;
}

function box({ scrollTop, clientHeight = 320, scrollHeight = 1000 }) {
  return { scrollTop, clientHeight, scrollHeight };
}

test('chat pull refresh guard blocks dragging past the top edge', async () => {
  const guard = await loadGuard();

  assert.equal(guard.shouldPreventBoundaryScroll(box({ scrollTop: 0 }), 120, 152), true);
});

test('chat pull refresh guard blocks dragging past the bottom edge', async () => {
  const guard = await loadGuard();

  assert.equal(guard.shouldPreventBoundaryScroll(box({ scrollTop: 680 }), 152, 120), true);
});

test('chat pull refresh guard allows normal in-list scrolling', async () => {
  const guard = await loadGuard();

  assert.equal(guard.shouldPreventBoundaryScroll(box({ scrollTop: 180 }), 152, 120), false);
  assert.equal(guard.shouldPreventBoundaryScroll(box({ scrollTop: 180 }), 120, 152), false);
});

test('chat sticker picker placement stays inside the mobile thread bounds', async () => {
  const exports = await loadChatExports();
  const placement = exports.GDPChatStickerPickerPlacement;
  const anchorRect = { left: 118, right: 154, width: 36 };
  const boundsRect = { left: 56, right: 390, width: 334 };

  const styles = placement.compute(anchorRect, boundsRect, 314, 8);
  const placedLeft = anchorRect.left + styles.left;
  const placedRight = placedLeft + styles.width;

  assert.equal(styles.width, 314);
  assert.ok(styles.left < 0);
  assert.ok(placedLeft >= boundsRect.left + 8);
  assert.ok(placedRight <= boundsRect.right - 8);
});

test('ticket event card renders escaped multiline content and ticket CTA', async () => {
  const exports = await loadChatExports();
  const html = exports.GDPChatTicketEventCard.render({
    actor_name: 'Yến Nhi <script>',
    event_content: 'Gửi bù 2 cốc\nLý do giao thiếu',
    warehouse_label: 'Kho SG',
    ticket_number: 'TK3242',
    ticket_url: '/cskh/tickets/3317/',
  });

  assert.match(html, /Yến Nhi &lt;script&gt; vừa thêm 1 event/);
  assert.match(html, /whitespace-pre-wrap/);
  assert.match(html, /Gửi bù 2 cốc\nLý do giao thiếu/);
  assert.match(html, /Kho SG/);
  assert.match(html, /href="\/cskh\/tickets\/3317\/"/);
  assert.match(html, />Xem ngay</);
});
