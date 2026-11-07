import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const plusorJsPath = resolve(__dirname, '..', 'plusor.js');

async function loadRenderer() {
  const source = await readFile(plusorJsPath, 'utf8');
  const context = {
    window: {},
    document: {
      addEventListener() {},
      getElementById() { return null; },
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
    localStorage: {
      getItem() { return null; },
      setItem() {},
      removeItem() {},
    },
    setTimeout,
    clearTimeout,
  };
  context.globalThis = context.window;
  vm.createContext(context);
  vm.runInContext(source, context, { filename: plusorJsPath });
  return context.window.PluSorProductDrawerRenderer;
}

test('compact drawer renders variant identity, totals, and concise warehouse cells', async () => {
  const renderer = await loadRenderer();
  const html = renderer.render({
    image_url: 'https://example.test/product.jpg',
    total_available: 7,
    total_on_hand: 9,
    variants: [{
      variant_id: 9101,
      image_url: 'https://example.test/variant.jpg',
      sku: 'HOP-TRANG',
      name: 'Hop dung do - Trang',
      options: ['Trang'],
      available: 7,
      on_hand: 9,
      warehouses: [
        { location_id: 548744, available: 0, on_hand: 0 },
        { location_id: 241737, available: 4, on_hand: 6 },
        { location_id: 783623, available: 3, on_hand: 3 },
      ],
    }],
  });

  assert.match(html, /https:\/\/example\.test\/variant\.jpg/);
  assert.match(html, /HOP-TRANG/);
  assert.match(html, />Trang</);
  assert.doesNotMatch(html, /Hop dung do - Trang/);
  assert.match(html, /Tổng có thể bán: 7/);
  assert.match(html, /Tổng thực tế: 9/);
  assert.match(html, /data-warehouse-code="HN"/);
  assert.match(html, /data-warehouse-code="SG"[\s\S]*?>0</);
  assert.match(html, /data-warehouse-code="SR"/);
  assert.ok(html.indexOf('data-warehouse-code="HN"') < html.indexOf('data-warehouse-code="SG"'));
  assert.ok(html.indexOf('data-warehouse-code="SG"') < html.indexOf('data-warehouse-code="SR"'));
  assert.doesNotMatch(html, /class="sku-row"/);
});

test('compact drawer falls back to product image, placeholder, and escapes values', async () => {
  const renderer = await loadRenderer();
  const html = renderer.render({
    image_url: 'https://example.test/product.jpg',
    total_available: 0,
    total_on_hand: 0,
    variants: [
      {
        variant_id: 9102,
        image_url: '',
        sku: '<script>alert(1)</script>',
        name: 'Xanh',
        options: [],
        available: 0,
        on_hand: 0,
        warehouses: [],
      },
      {
        variant_id: 9103,
        image_url: '',
        sku: 'NO-IMAGE',
        name: 'Không ảnh',
        options: ['Không ảnh'],
        available: 0,
        on_hand: 0,
        warehouses: [],
      },
    ],
  });

  assert.equal((html.match(/https:\/\/example\.test\/product\.jpg/g) || []).length, 3);
  assert.match(html, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
  assert.doesNotMatch(html, /<script>alert\(1\)<\/script>/);

  const placeholderHtml = renderer.render({
    image_url: '',
    total_available: 0,
    total_on_hand: 0,
    variants: [{ sku: 'NONE', name: 'Không ảnh', options: [], warehouses: [] }],
  });
  assert.match(placeholderHtml, /plusor-ph-img/);
});
