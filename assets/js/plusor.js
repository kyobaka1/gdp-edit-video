/**
 * PluSor — chat thống nhất (plusor_v2 messages[]) + Action System v2.
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'gdp_plusor_panel_open';
  var SESSION_KEY = 'gdp_plusor_session_id';
  /** Chỉ render tối đa N tin gần nhất; tin cũ tải khi kéo lên đầu vùng chat. */
  var PLUSOR_VISIBLE_BATCH = 30;
  var PLUSOR_ASSISTANT_ICON = '/static/sticker/sticker-PLUSOR/plusor.png';
  /** Insight titles từ pipeline tối ưu container — dùng khi merge payload SSE. */
  var PLUSOR_CONTAINER_INSIGHT_TITLES = {
    'Phân tích dữ liệu': true,
    'Rủi ro & lưu ý': true,
    'Knapsack / CBM': true,
    'SKU signals (HIGH_ATTENTION)': true,
    'Phân tích sâu từng SKU': true,
    'Thách thức giả định': true,
  };
  var PLUSOR_JSON_KV_MAX_DEPTH = 10;

  function esc(s) {
    if (s == null) return '';
    var d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
  }

  function escAttr(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
      .replace(/</g, '&lt;');
  }

  /**
   * Markdown → HTML đã sanitize (marked + DOMPurify). Fallback esc + br nếu thiếu lib.
   */
  function plusorMarkdownToSafeHtml(raw) {
    var text = String(raw == null ? '' : raw);
    if (!text.trim()) return '';
    var w = typeof window !== 'undefined' ? window : {};
    var mk = w.marked;
    var pur = w.DOMPurify;
    if (!mk || typeof mk.parse !== 'function' || !pur || typeof pur.sanitize !== 'function') {
      return esc(text).replace(/\n/g, '<br>');
    }
    try {
      var html = mk.parse(text, { async: false, breaks: true, gfm: true });
      return pur.sanitize(html, { USE_PROFILES: { html: true } });
    } catch (e) {
      return esc(text).replace(/\n/g, '<br>');
    }
  }

  function progressPayloadToLabel(p) {
    if (!p || typeof p !== 'object') return 'PluSor đang xử lý…';
    if (p.stage === 'image_prepare') return 'PluSor đang chuẩn bị ảnh…';
    if (p.stage === 'vision') return 'PluSor đang đọc ảnh và chữ…';
    if (p.stage === 'retrieve') return 'PluSor đang tìm sản phẩm tương tự…';
    if (p.stage === 'rerank') return 'PluSor đang xếp hạng kết quả…';
    if (p.stage === 'inventory') return 'PluSor đang kiểm tra tồn kho…';
    var k = p.kind;
    if (k === 'planner') {
      if (p.route === 'agentic_tools') return 'PluSor đang chuẩn bị gọi công cụ…';
      if (p.route === 'rag') return 'PluSor đang chuẩn bị tra cứu tài liệu…';
      return 'PluSor đang chuẩn bị trả lời…';
    }
    if (k === 'rag') return 'PluSor đang tìm tài liệu nội bộ…';
    if (k === 'llm') {
      if (p.stage === 'summary') return 'PluSor đang tổng hợp câu trả lời…';
      var r = p.round != null ? ' (vòng ' + p.round + ')' : '';
      return 'PluSor đang chờ phản hồi từ AI' + r + '…';
    }
    if (k === 'tool') {
      var nm = p.name || 'công cụ';
      return 'PluSor đang dùng ' + nm + '…';
    }
    if (k === 'agentic' && p.stage === 'start') return 'PluSor đang khởi chạy tác tử công cụ…';
    if (k === 'thinking_chunk') return 'PluSor đang suy nghĩ…';
    return 'PluSor đang xử lý…';
  }

  function getCsrfToken() {
    var m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  /**
   * Gộp ngữ cảnh trang tĩnh (__PLUSOR_CONTEXT__) với URL/title trình duyệt hiện tại.
   * Server vẫn có thể bổ sung/fallback (HTTP Referer) nếu thiếu.
   */
  function buildPlusorPageContext() {
    var base = window.__PLUSOR_CONTEXT__ || {};
    var o = {};
    for (var k in base) {
      if (Object.prototype.hasOwnProperty.call(base, k)) o[k] = base[k];
    }
    try {
      o.page_url = window.location.href;
      o.page_path = window.location.pathname || '';
      o.page_title = document.title || '';
    } catch (e) {
      o.page_url = o.page_url || '';
      o.page_path = o.page_path || '';
      o.page_title = o.page_title || '';
    }
    return o;
  }

  function normalizeClientPayload(p) {
    if (!p || typeof p !== 'object') {
      return { schema_version: 'plusor_v2', messages: [], trace: {} };
    }
    if (
      (p.schema_version === 'plusor_v2' || p.schema_version === 'plusi_v2') &&
      Array.isArray(p.messages)
    ) {
      return {
        schema_version: 'plusor_v2',
        messages: p.messages.slice(),
        trace: p.trace || {},
      };
    }
    var msgs = [];
    (p.insights || []).forEach(function (i) {
      msgs.push({
        role: 'assistant',
        type: 'insight',
        title: i.title || '—',
        content: i.description || '',
        severity: i.severity || 'medium',
        insight_type: i.type || 'info',
        sku: i.sku,
      });
    });
    var cs = String(p.chat_summary || '').trim();
    if (cs) {
      msgs.push({ role: 'assistant', type: 'text', content: cs });
    }
    (p.actions || []).forEach(function (a) {
      if (!a || !a.id) return;
      msgs.push({
        role: 'assistant',
        type: 'action',
        action_id: a.id,
        id: a.id,
        label: a.label || a.id,
        payload: a.payload || {},
        confidence: a.confidence,
        risk: a.risk,
        impact_estimate: a.impact_estimate,
        action_type: a.type || 'api_call',
      });
    });
    return { schema_version: 'plusor_v2', messages: msgs, trace: p.trace || {} };
  }

  function readJsonScript(id) {
    var el = document.getElementById(id);
    if (!el || !el.textContent) return '';
    try {
      var v = JSON.parse(el.textContent.trim());
      return typeof v === 'string' ? v : '';
    } catch (e) {
      return '';
    }
  }

  function userAvatarMarkup() {
    var url = readJsonScript('plusor-panel-user-avatar-url').trim();
    var name = readJsonScript('plusor-panel-user-name').trim();
    var initials = (name || 'U').slice(0, 2).toUpperCase();
    if (url) {
      return (
        '<div class="plusor-msg-avatar plusor-msg-avatar--photo">' +
        '<img src="' +
        escAttr(url) +
        '" alt="" loading="lazy" onerror="this.style.display=\'none\'">' +
        '<span style="display:none;align-items:center;justify-content:center;width:100%;height:100%;font-size:10px">' +
        esc(initials) +
        '</span></div>'
      );
    }
    return '<div class="plusor-msg-avatar">' + esc(initials) + '</div>';
  }

  function assistantAvatarHtml() {
    return (
      '<div class="plusor-msg-avatar plusor-msg-avatar--assistant" aria-hidden="true">' +
      '<img src="' +
      escAttr(PLUSOR_ASSISTANT_ICON) +
      '" alt="" width="28" height="28" loading="lazy" decoding="async" />' +
      '</div>'
    );
  }

  function severityCardClass(sev) {
    var s = (sev || 'medium').toLowerCase();
    if (s === 'high') return 'plusor-card--high';
    if (s === 'low') return 'plusor-card--low';
    return 'plusor-card--medium';
  }

  function formatMsgTime(ts) {
    if (ts == null || ts === '') return '';
    var d = new Date(typeof ts === 'number' ? ts : Number(ts));
    if (isNaN(d.getTime())) return '';
    var h = d.getHours().toString().padStart(2, '0');
    var m = d.getMinutes().toString().padStart(2, '0');
    return h + ':' + m;
  }

  /**
   * Chuẩn hoá văn bản tiếng Anh từ LLM → tiếng Việt (PluSor container / rủi ro).
   * Không dịch máy đầy đủ — map cụm thường gặp để UX đọc được.
   */
  function translateVi(s) {
    if (s == null || s === '') return s;
    var t = String(s);
    var pairs = [
      [/Identified as risk SKU but still included in plan with (\d+) pcs\. Potential stockout or quality issues\./gi,
        'Được đánh dấu SKU rủi ro nhưng vẫn nằm trong kế hoạch ($1 pcs). Nguy cơ hết hàng hoặc chất lượng.'],
      [/High volume of risky inventory\./gi, 'Khối lượng tồn rủi ro lớn.'],
      [/Potential stockout or quality issues/gi, 'Nguy cơ hết hàng hoặc vấn đề chất lượng'],
      [/Suggested quantity only (\d+) pieces \(minimum threshold\)[^.]*\./gi,
        'Chỉ đề xuất $1 pcs (ngưỡng tối thiểu).'],
      [/Likely included just to fill space but adds operational complexity\./gi,
        'Có thể chỉ để lấp chỗ nhưng làm phức tạp vận hành.'],
      [/Remove entirely; replace with higher-volume SKU or accept slightly lower fill rate\./gi,
        'Loại hoàn toàn; thay bằng SKU khối lượng lớn hơn hoặc chấp nhận fill thấp hơn một chút.'],
      [/Exclude; use space for more substantial quantities of other SKUs\./gi,
        'Loại trừ; dùng chỗ cho SKU khác với số lượng đáng kể hơn.'],
      [/High risk:/gi, 'Rủi ro cao:'],
      [/High risk\s*:/gi, 'Rủi ro cao:'],
      [/Fill rate/gi, 'Tỷ lệ lấp đầy'],
      [/below target/gi, 'dưới mục tiêu'],
      [/despite optimization/gi, 'dù đã tối ưu'],
      [/despite optimization attempt/gi, 'dù đã thử tối ưu'],
      [/Container fill rate/gi, 'Tỷ lệ lấp đầy container'],
      [/Multiple SKUs with very low suggested quantities/gi, 'Nhiều SKU có số lượng đề xuất rất thấp'],
      [/excluded due to low suggested quantity/gi, 'bị loại do số lượng đề xuất thấp'],
      [/Three risk SKUs included/gi, 'Ba SKU rủi ro vẫn được đưa vào'],
      [/Expected profit value abnormally high/gi, 'Giá trị lợi nhuận dự kiến bất thường cao'],
      [/Data lacks inventory context/gi, 'Thiếu ngữ cảnh tồn kho trong dữ liệu'],
      [/Missing historical sales data/gi, 'Thiếu dữ liệu bán lịch sử'],
      [/No inventory levels provided/gi, 'Không có mức tồn kho'],
      [/Unclear scoring methodology/gi, 'Phương pháp chấm điểm chưa rõ'],
      [/Inconsistent unit precision/gi, 'Độ chính xác đơn vị không nhất quán'],
      [/Low fill rate/gi, 'Tỷ lệ lấp đầy thấp'],
      [/High number of excluded SKUs/gi, 'Số SKU bị loại cao'],
      [/Discrepancy between min_fill_cbm and achieved total_cbm/gi, 'Chênh lệch giữa min_fill_cbm và tổng CBM đạt được'],
      [/Risks identified but still included in plan/gi, 'Đã xác định rủi ro nhưng vẫn trong kế hoạch'],
      [/Extremely high expected profit value/gi, 'Lợi nhuận dự kiến cực cao'],
      [/profit in integer vs float/gi, 'lợi nhuận kiểu số nguyên vs số thực'],
      [/Suggested quantity/gi, 'Số lượng đề xuất'],
      [/minimum threshold/gi, 'ngưỡng tối thiểu'],
      [/operational complexity/gi, 'độ phức tạp vận hành'],
      [/negligible volume/gi, 'khối lượng không đáng kể'],
      [/handling complexity/gi, 'độ phức tạp xử lý'],
      [/extremely low volume contribution/gi, 'đóng góp CBM rất thấp'],
      [/At minimum inclusion threshold/gi, 'Ở ngưỡng tối thiểu để đưa vào'],
      [/contributes negligible volume/gi, 'đóng góp CBM không đáng kể'],
    ];
    for (var i = 0; i < pairs.length; i++) {
      t = t.replace(pairs[i][0], pairs[i][1]);
    }
    return t;
  }

  function translateFlagSnake(s) {
    var m = {
      low_fill_rate: 'Fill thấp',
      high_exclusion_rate: 'Loại nhiều SKU',
      risk_skus_included: 'SKU rủi ro vẫn trong plan',
      data_quality_issues: 'Chất lượng dữ liệu',
      profit_anomaly: 'Bất thường lợi nhuận',
      low_fill_rate_despite_optimization: 'Fill thấp dù đã tối ưu',
      high_exclusion_rate_alt: 'Tỷ lệ loại cao',
      sku_suggestion_quantity_discrepancy: 'Lệch số lượng đề xuất',
      profit_value_anomaly: 'Giá trị lợi nhuận bất thường',
      missing_sku_volume_data: 'Thiếu CBM SKU',
      inconsistent_profit_formatting: 'Định dạng lợi nhuận không nhất quán',
      unclear_exclusion_criteria: 'Tiêu chí loại chưa rõ',
    };
    var k = String(s || '').trim();
    if (m[k]) return m[k];
    return translateVi(k.replace(/_/g, ' '));
  }

  function parseCardContent(content) {
    var raw = String(content == null ? '' : content);
    var s = raw.trim();
    s = s.replace(/<br\s*\/?>/gi, '\n');
    s = s.replace(/&lt;br\s*\/?&gt;/gi, '\n');
    s = s.replace(/&nbsp;/g, ' ');
    s = s.replace(/\u00a0/g, ' ');
    s = s.replace(/^```(?:json)?\s*/i, '');
    s = s.replace(/\s*```\s*$/i, '');
    s = s.trim();
    try {
      var parsed = JSON.parse(s);
      if (parsed && typeof parsed === 'object') return { isJson: true, parsed: parsed, rawText: raw };
    } catch (e) {}
    var first = s.indexOf('{');
    var last = s.lastIndexOf('}');
    if (first >= 0 && last > first) {
      try {
        var sub = s.slice(first, last + 1);
        var parsed2 = JSON.parse(sub);
        if (parsed2 && typeof parsed2 === 'object') return { isJson: true, parsed: parsed2, rawText: raw };
      } catch (e2) {}
    }
    return { isJson: false, parsed: null, rawText: raw };
  }

  function normalizeKnapsackParsed(p) {
    if (!p || typeof p !== 'object') return p;
    var out = {};
    var k;
    for (k in p) {
      if (Object.prototype.hasOwnProperty.call(p, k)) out[k] = p[k];
    }
    var sfl = p.summary_for_llm;
    if (sfl && typeof sfl === 'object') {
      if (out.fill_rate == null && sfl.fill_rate != null) out.fill_rate = sfl.fill_rate;
      if (out.total_cbm == null && sfl.total_cbm != null) out.total_cbm = sfl.total_cbm;
      if (out.capacity == null && sfl.capacity != null) out.capacity = sfl.capacity;
      if (out.capacity_cbm == null && sfl.capacity != null) out.capacity_cbm = sfl.capacity;
      if ((!out.warnings || !out.warnings.length) && Array.isArray(sfl.warnings)) out.warnings = sfl.warnings;
      if ((!out.excluded_top3 || !out.excluded_top3.length) && Array.isArray(sfl.excluded_top3))
        out.excluded_top3 = sfl.excluded_top3;
      if (!out.summary && (sfl.container || sfl.total_cbm != null)) {
        out.summary =
          (sfl.container ? 'Container ' + sfl.container + '. ' : '') +
          (sfl.total_cbm != null && sfl.capacity != null
            ? 'CBM: ' + Number(sfl.total_cbm).toFixed(2) + ' / ' + sfl.capacity + ' (' + (sfl.fill_rate != null ? sfl.fill_rate : '') + '%). '
            : '') +
          (Array.isArray(sfl.warnings) && sfl.warnings[0] ? translateVi(String(sfl.warnings[0])).slice(0, 280) : '');
      }
    }
    return out;
  }

  function pctBar(p) {
    var n = Number(p);
    if (isNaN(n)) n = 0;
    n = Math.max(0, Math.min(100, n <= 1 ? n * 100 : n));
    return (
      '<div class="pcard-progress"><div class="pcard-progress-fill" style="width:' +
      n +
      '%"></div></div>'
    );
  }

  function renderAnalysisCard(parsed, msg) {
    var it = msg.insight_type || 'info';
    var patterns = Array.isArray(parsed.patterns) ? parsed.patterns : [];
    var issues = Array.isArray(parsed.data_quality_issues) ? parsed.data_quality_issues : [];
    var pen = parsed.confidence_penalty;
    var penNum =
      typeof pen === 'number' ? (pen <= 1 ? pen * 100 : pen) : pen != null ? Number(pen) : null;
    var head =
      '<div class="flex justify-between gap-1 mb-1"><span class="font-semibold text-heading text-xs">' +
      esc(msg.title || '') +
      '</span><span class="plusor-meta">' +
      esc(it) +
      '</span></div>';
    var quote = parsed.summary
      ? '<div class="pcard-quote mt-1">' + esc(translateVi(String(parsed.summary))) + '</div>'
      : '';
    var patHtml = '';
    if (patterns.length) {
      patHtml =
        '<div class="mt-1 flex flex-wrap gap-1">' +
        patterns
          .slice(0, 12)
          .map(function (p) {
            return '<span class="pcard-badge plusor-badge plusor-badge--cyan">' + esc(translateVi(String(p))) + '</span>';
          })
          .join('') +
        '</div>';
    }
    var issHtml = '';
    if (issues.length) {
      issHtml =
        '<div class="mt-1 flex flex-wrap gap-1">' +
        issues
          .slice(0, 12)
          .map(function (x) {
            return '<span class="pcard-badge plusor-badge plusor-badge--amber">' + esc(translateVi(String(x))) + '</span>';
          })
          .join('') +
        '</div>';
    }
    var bar = '';
    if (penNum != null && !isNaN(penNum)) {
      bar =
        '<div class="mt-2 text-[10px] plusor-txt-muted">Độ phạt tin cậy ' +
        Math.round(penNum) +
        '%</div>' +
        pctBar(penNum);
    }
    return (
      '<div class="plusor-card ' +
      severityCardClass(msg.severity) +
      '">' +
      head +
      quote +
      patHtml +
      issHtml +
      bar +
      '</div>'
    );
  }

  function renderRiskCard(parsed, msg) {
    var it = msg.insight_type || 'risk';
    var lvl = String(parsed.risk_level || 'medium').toLowerCase();
    var badgeCls =
      lvl === 'high' || lvl === 'critical' ? 'plusor-badge plusor-badge--red' : 'plusor-badge plusor-badge--amber';
    var head =
      '<div class="flex justify-between gap-1 mb-1 flex-wrap"><span class="font-semibold text-heading text-xs">' +
      esc(msg.title || '') +
      '</span><span class="pcard-badge ' +
      badgeCls +
      '">' +
      esc(lvl === 'high' ? 'cao' : lvl === 'critical' ? 'nghiêm trọng' : lvl === 'low' ? 'thấp' : 'trung bình') +
      '</span><span class="plusor-meta">' +
      esc(it) +
      '</span></div>';
    var sumQ =
      parsed.summary != null && String(parsed.summary).trim()
        ? '<div class="pcard-quote mt-1 text-[11px]">' + esc(translateVi(String(parsed.summary))) + '</div>'
        : '';
    var cbm =
      parsed.cbm_at_risk != null
        ? '<div class="text-[11px] mt-1 plusor-txt-warn">CBM rủi ro: <strong>' +
          esc(String(parsed.cbm_at_risk)) +
          '</strong></div>'
        : '';
    var flags = Array.isArray(parsed.flags) ? parsed.flags : [];
    var flagHtml =
      flags.length > 0
        ? '<div class="mt-1 flex flex-wrap gap-1">' +
          flags
            .slice(0, 16)
            .map(function (f) {
              return '<span class="pcard-badge plusor-badge plusor-badge--neutral">' + esc(translateFlagSnake(String(f))) + '</span>';
            })
            .join('') +
          '</div>'
        : '';
    var crit = Array.isArray(parsed.critical_skus) ? parsed.critical_skus : [];
    var rows = '';
    crit.slice(0, 8).forEach(function (row) {
      var sku = row && row.sku != null ? String(row.sku) : '';
      var reason = row && row.reason != null ? String(row.reason) : '';
      rows +=
        '<div class="pcard-sku-row"><span class="font-mono text-[10px] plusor-txt-cyan">' +
        esc(sku) +
        '</span><span class="text-[10px] plusor-txt-body flex-1">' +
        esc(translateVi(reason)) +
        '</span></div>';
    });
    return (
      '<div class="plusor-card ' +
      severityCardClass(msg.severity) +
      '">' +
      head +
      sumQ +
      cbm +
      flagHtml +
      (rows ? '<div class="mt-1">' + rows + '</div>' : '') +
      '</div>'
    );
  }

  function renderKnapsackCard(parsed, msg) {
    parsed = normalizeKnapsackParsed(parsed);
    var it = msg.insight_type || 'info';
    var head =
      '<div class="flex justify-between gap-1 mb-1"><span class="font-semibold text-heading text-xs">' +
      esc(msg.title || '') +
      '</span><span class="plusor-meta">' +
      esc(it) +
      '</span></div>';
    var sumQ =
      parsed.summary != null && String(parsed.summary).trim()
        ? '<div class="pcard-quote mt-1 text-[11px]">' + esc(translateVi(String(parsed.summary))) + '</div>'
        : '';
    var fr = parsed.fill_rate;
    var frNum = fr != null ? Number(fr) : null;
    var bar = '';
    if (frNum != null && !isNaN(frNum)) {
      var pct = frNum <= 1 ? frNum * 100 : frNum;
      bar = '<div class="text-[10px] plusor-txt-muted mt-1">Tỷ lệ lấp đầy</div>' + pctBar(pct);
    }
    var cap = '';
    if (parsed.total_cbm != null || parsed.capacity != null || parsed.capacity_cbm != null) {
      cap =
        '<div class="text-[11px] mt-1 plusor-txt-body">Tổng CBM: <strong>' +
        esc(String(parsed.total_cbm != null ? Number(parsed.total_cbm).toFixed(2) : '—')) +
        '</strong> / dung tích <strong>' +
        esc(String(parsed.capacity != null ? parsed.capacity : parsed.capacity_cbm != null ? parsed.capacity_cbm : '—')) +
        '</strong></div>';
    }
    var warns = Array.isArray(parsed.warnings) ? parsed.warnings : [];
    var whtml = '';
    warns.slice(0, 6).forEach(function (w) {
      whtml += '<div class="plusor-warn-line">' + esc(translateVi(String(w))) + '</div>';
    });
    var ex = Array.isArray(parsed.excluded_top3) ? parsed.excluded_top3 : [];
    var exBlock = '';
    if (ex.length) {
      var inner = ex
        .slice(0, 6)
        .map(function (x) {
          if (x && typeof x === 'object') {
            var line =
              (x.sku ? String(x.sku) : '') +
              (x.reason ? ' — ' + translateVi(String(x.reason)) : '') +
              (x.score != null ? ' (score ' + x.score + ')' : '');
            return '<div class="text-[10px] py-0.5 pcard-sku-row">' + esc(line) + '</div>';
          }
          return '<div class="text-[10px] py-0.5">' + esc(String(x)) + '</div>';
        })
        .join('');
      exBlock =
        '<details class="mt-2"><summary class="pcard-collapse-toggle">SKU loại trừ (top)</summary><div class="mt-1 opacity-90">' +
        inner +
        '</div></details>';
    }
    return (
      '<div class="plusor-card ' +
      severityCardClass(msg.severity) +
      '">' +
      head +
      sumQ +
      bar +
      cap +
      whtml +
      exBlock +
      '</div>'
    );
  }

  function renderChallengerCard(parsed, msg) {
    var it = msg.insight_type || 'recommendation';
    var head =
      '<div class="flex justify-between gap-1 mb-1"><span class="font-semibold text-heading text-xs">' +
      esc(msg.title || '') +
      '</span><span class="plusor-meta">' +
      esc(it) +
      '</span></div>';
    var items = Array.isArray(parsed.challenges) ? parsed.challenges : Array.isArray(parsed.items) ? parsed.items : [];
    if (!items.length && parsed.challenge) items = [parsed];
    var blocks = '';
    items.slice(0, 8).forEach(function (ch, idx) {
      var sku = ch && ch.sku != null ? String(ch.sku) : '';
      var issue = ch && ch.issue != null ? String(ch.issue) : '';
      var sug = ch && ch.suggestion != null ? String(ch.suggestion) : '';
      blocks +=
        '<details class="plusor-detail-box mt-1" ' +
        (idx === 0 ? 'open' : '') +
        '><summary class="cursor-pointer text-[11px] font-mono plusor-txt-cyan">' +
        esc(sku || '—') +
        '</summary><div class="text-[10px] plusor-txt-body mt-1">' +
        (issue ? '<div>' + esc(translateVi(issue)) + '</div>' : '') +
        (sug ? '<div class="mt-1 plusor-txt-green">→ ' + esc(translateVi(sug)) + '</div>' : '') +
        '</div></details>';
    });
    if (!blocks) {
      return renderStructuredJsonCard(parsed, msg);
    }
    return '<div class="plusor-card ' + severityCardClass(msg.severity) + '">' + head + blocks + '</div>';
  }

  function renderSkuSignalsCard(parsed, msg) {
    var it = msg.insight_type || 'info';
    var head =
      '<div class="flex justify-between gap-1 mb-1 flex-wrap"><span class="font-semibold text-heading text-xs">' +
      esc(msg.title || 'SKU signals') +
      '</span><span class="plusor-meta">' +
      esc(it) +
      '</span></div>';
    var rows = Array.isArray(parsed.sku_details) ? parsed.sku_details : [];
    if (!rows.length) {
      return renderStructuredJsonCard(parsed, msg);
    }
    var table =
      '<div class="mt-1 overflow-x-auto"><table class="w-full text-[10px] border-collapse">' +
      '<thead><tr class="plusor-txt-muted text-left border-b border-[color:var(--border-color)]">' +
      '<th class="py-1 pr-1">SKU</th>' +
      '<th class="py-1 pr-1" title="Số lượng gợi ý">SL <span class="opacity-70">(?)</span></th>' +
      '<th class="py-1 pr-1" title="Thể tích ước tính (mét khối)">CBM <span class="opacity-70">(?)</span></th>' +
      '<th class="py-1 pr-1">Chú ý</th>' +
      '<th class="py-1">Signal</th>' +
      '</tr></thead><tbody>';
    rows.slice(0, 24).forEach(function (row) {
      if (!row || typeof row !== 'object') return;
      var sku = row.sku != null ? String(row.sku) : '—';
      var pcs = row.suggested_pcs != null ? String(row.suggested_pcs) : '—';
      var cbm = row.suggested_cbm != null ? String(row.suggested_cbm) : '—';
      var att = row.attention_level != null ? String(row.attention_level) : '';
      var sig = row.signal && typeof row.signal === 'object' ? row.signal.type || '' : '';
      table +=
        '<tr class="border-b border-[color:var(--border-color)]/40">' +
        '<td class="py-1 pr-1 font-mono plusor-txt-cyan">' +
        esc(sku) +
        '</td>' +
        '<td class="py-1 pr-1">' +
        esc(pcs) +
        '</td>' +
        '<td class="py-1 pr-1">' +
        esc(cbm) +
        '</td>' +
        '<td class="py-1 pr-1 text-[9px]">' +
        esc(att) +
        '</td>' +
        '<td class="py-1 text-[9px]">' +
        esc(sig) +
        '</td>' +
        '</tr>';
    });
    table += '</tbody></table></div>';
    if (rows.length > 24) {
      table +=
        '<div class="text-[10px] plusor-txt-muted mt-1">+ ' +
        (rows.length - 24) +
        ' SKU…</div>';
    }
    return '<div class="plusor-card ' + severityCardClass(msg.severity) + '">' + head + table + '</div>';
  }

  function renderSkuDeepReviewsCard(parsed, msg) {
    var it = msg.insight_type || 'recommendation';
    var head =
      '<div class="flex justify-between gap-1 mb-1 flex-wrap"><span class="font-semibold text-heading text-xs">' +
      esc(msg.title || 'Phân tích sâu') +
      '</span><span class="plusor-meta">' +
      esc(it) +
      '</span></div>';
    var reviews = Array.isArray(parsed.sku_reviews) ? parsed.sku_reviews : [];
    if (!reviews.length) {
      return renderStructuredJsonCard(parsed, msg);
    }
    var blocks = '';
    reviews.slice(0, 32).forEach(function (r, idx) {
      if (!r || typeof r !== 'object') return;
      var sku = r.sku != null ? String(r.sku) : '—';
      var action = r.action != null ? String(r.action) : '';
      var delta = r.delta_pcs != null ? String(r.delta_pcs) : '';
      var newPcs = r.new_recommended_pcs != null ? String(r.new_recommended_pcs) : '';
      var conf = r.confidence != null ? String(r.confidence) : '';
      var steps = Array.isArray(r.reasoning_steps) ? r.reasoning_steps : [];
      var stepsHtml = '';
      steps.forEach(function (st) {
        stepsHtml += '<li class="text-[10px] leading-snug">' + esc(translateVi(String(st))) + '</li>';
      });
      var badgeCls =
        action === 'INCREASE'
          ? 'plusor-badge--cyan'
          : action === 'DECREASE'
            ? 'plusor-badge--amber'
            : 'plusor-badge--neutral';
      blocks +=
        '<details class="plusor-detail-box mt-1" ' +
        (idx === 0 ? 'open' : '') +
        '><summary class="cursor-pointer flex flex-wrap gap-1 items-center text-[11px]">' +
        '<span class="font-mono plusor-txt-cyan">' +
        esc(sku) +
        '</span>' +
        (action
          ? '<span class="pcard-badge plusor-badge ' +
            badgeCls +
            ' text-[9px]">' +
            esc(action) +
            '</span>'
          : '') +
        (delta ? '<span class="text-[10px] plusor-txt-muted">Δ ' + esc(delta) + ' pcs</span>' : '') +
        (newPcs ? '<span class="text-[10px]">→ ' + esc(newPcs) + ' pcs</span>' : '') +
        (conf ? '<span class="text-[10px] plusor-txt-muted">conf ' + esc(conf) + '</span>' : '') +
        '</summary>' +
        (stepsHtml
          ? '<ol class="list-decimal pl-4 mt-1 space-y-0.5">' + stepsHtml + '</ol>'
          : '<div class="text-[10px] plusor-txt-muted mt-1">—</div>') +
        '</details>';
    });
    if (reviews.length > 32) {
      blocks +=
        '<div class="text-[10px] plusor-txt-muted mt-1">+ ' + (reviews.length - 32) + ' SKU…</div>';
    }
    return '<div class="plusor-card ' + severityCardClass(msg.severity) + '">' + head + blocks + '</div>';
  }

  /**
   * Nhãn hiển thị cho key JSON (fallback: snake_case → khoảng trắng).
   */
  function humanizeJsonKey(k) {
    var KEY_LABELS = {
      verdict: 'Kết luận',
      actions: 'Gợi ý hành động',
      confidence: 'Độ tin cậy',
      risks: 'Rủi ro',
      summary: 'Tóm tắt',
      patterns: 'Mẫu nhận diện',
      data_quality_issues: 'Vấn đề dữ liệu',
      critical_skus: 'SKU rủi ro',
      flags: 'Cờ cảnh báo',
      challenges: 'Thách thức',
      fill_rate: 'Tỷ lệ lấp đầy',
      total_cbm: 'Tổng CBM',
      capacity: 'Dung tích',
      cbm_at_risk: 'CBM rủi ro',
      risk_level: 'Mức rủi ro',
      excluded_top3: 'Loại trừ (top)',
      warnings: 'Cảnh báo',
      summary_for_llm: 'Tóm tắt (LLM)',
      expected_profit: 'Lợi nhuận dự kiến',
      sku_details: 'Chi tiết SKU',
      sku_reviews: 'Đánh giá từng SKU',
      reasoning_steps: 'Lý luận',
      suggested_pcs: 'SL gợi ý (pcs)',
      suggested_cbm: 'CBM gợi ý',
      attention_level: 'Mức chú ý',
      stock_status: 'Trạng thái tồn',
      new_recommended_pcs: 'SL đề xuất mới',
      delta_pcs: 'Chênh lệch SL',
    };
    return KEY_LABELS[k] || String(k).replace(/_/g, ' ');
  }

  function sortStructuredKeys(keys) {
    var order = [
      'verdict',
      'summary',
      'actions',
      'confidence',
      'risks',
      'patterns',
      'data_quality_issues',
      'flags',
      'critical_skus',
      'fill_rate',
      'total_cbm',
      'cbm_at_risk',
    ];
    return keys.slice().sort(function (a, b) {
      var ia = order.indexOf(a);
      var ib = order.indexOf(b);
      if (ia === -1 && ib === -1) return a.localeCompare(b);
      if (ia === -1) return 1;
      if (ib === -1) return -1;
      return ia - ib;
    });
  }

  function formatJsonValueHtml(v, keyHint, depth) {
    depth = depth || 0;
    if (v === null || v === undefined) return '<span class="plusor-txt-muted">—</span>';
    if (typeof v === 'string') {
      var long = v.length > 100 || v.indexOf('\n') >= 0;
      if (keyHint === 'verdict' || long) {
        return '<div class="pcard-quote text-[11px] leading-snug">' + esc(translateVi(v)) + '</div>';
      }
      return '<div class="text-[11px] plusor-txt-body">' + esc(translateVi(v)) + '</div>';
    }
    if (typeof v === 'number') {
      if (keyHint === 'confidence' || keyHint === 'confidence_penalty') {
        var n = v <= 1 && v >= 0 ? v * 100 : v;
        if (isNaN(n)) n = 0;
        return pctBar(n) + '<div class="text-[10px] mt-0.5 plusor-txt-muted">' + esc(String(Math.round(n))) + '%</div>';
      }
      return '<span class="text-[11px] font-mono plusor-txt-body">' + esc(String(v)) + '</span>';
    }
    if (typeof v === 'boolean') {
      return '<span class="text-[11px]">' + (v ? 'Có' : 'Không') + '</span>';
    }
    if (Array.isArray(v)) {
      if (v.length === 0) return '<span class="text-[10px] plusor-txt-muted">(trống)</span>';
      if (typeof v[0] === 'string') {
        return (
          '<ul class="pcard-kv-list">' +
          v
            .slice(0, 40)
            .map(function (x) {
              return '<li>' + esc(translateVi(String(x))) + '</li>';
            })
            .join('') +
          '</ul>'
        );
      }
      if (typeof v[0] === 'object' && v[0] !== null) {
        return (
          '<div class="pcard-nested-items">' +
          v
            .slice(0, 16)
            .map(function (row) {
              return (
                '<div class="pcard-nested-item">' +
                renderStructuredJsonBody(row, depth + 1) +
                '</div>'
              );
            })
            .join('') +
          '</div>'
        );
      }
      return '<div class="text-[10px]">' + esc(v.map(String).join(', ')) + '</div>';
    }
    if (typeof v === 'object') {
      return '<div class="pcard-nested">' + renderStructuredJsonBody(v, depth + 1) + '</div>';
    }
    return '<div>' + esc(String(v)) + '</div>';
  }

  function renderStructuredJsonBody(parsed, depth) {
    if (depth > PLUSOR_JSON_KV_MAX_DEPTH) {
      try {
        var s = JSON.stringify(parsed, null, 2);
        var lim = 48000;
        var truncated = s.length > lim;
        var show = truncated ? s.slice(0, lim) + '\n…' : s;
        return (
          '<details class="mt-1 plusor-json-deep" open>' +
          '<summary class="text-[10px] plusor-txt-muted cursor-pointer">Nội dung lồng sâu (' +
          s.length +
          ' ký tự)</summary>' +
          '<pre class="mt-1 p-2 rounded border border-[color:var(--border-color)]/40 text-[10px] plusor-txt-body whitespace-pre-wrap break-all max-h-64 overflow-auto">' +
          esc(show) +
          '</pre></details>'
        );
      } catch (e) {
        return '';
      }
    }
    if (parsed === null || parsed === undefined) return '';
    if (Array.isArray(parsed)) {
      return formatJsonValueHtml(parsed, 'array', depth);
    }
    if (typeof parsed !== 'object') {
      return formatJsonValueHtml(parsed, '', depth);
    }
    var keys = sortStructuredKeys(Object.keys(parsed));
    var html = '';
    for (var i = 0; i < keys.length; i++) {
      var k = keys[i];
      var v = parsed[k];
      if (v === undefined) continue;
      html +=
        '<div class="pcard-kv-block">' +
        '<div class="pcard-kv-label">' +
        esc(humanizeJsonKey(k)) +
        '</div>' +
        '<div class="pcard-kv-value">' +
        formatJsonValueHtml(v, k, depth) +
        '</div>' +
        '</div>';
    }
    return html;
  }

  /**
   * Card ngoại lệ: object JSON không khớp insight/action cụ thể — hiển thị key / value rõ ràng.
   */
  function renderStructuredJsonCard(parsed, msg) {
    var m = msg || {};
    var title = m.title != null && String(m.title).trim() ? String(m.title).trim() : 'Kết quả phân tích';
    var head =
      '<div class="flex justify-between gap-1 mb-2 items-start">' +
      '<span class="font-semibold text-heading text-xs">' +
      esc(title) +
      '</span>' +
      '<span class="pcard-badge plusor-badge plusor-badge--cyan text-[9px]">Có cấu trúc</span>' +
      '</div>';
    return (
      '<div class="plusor-card plusor-card--low pcard-structured">' +
      head +
      renderStructuredJsonBody(parsed, 0) +
      '</div>'
    );
  }

  function renderJsonSummaryCard(parsed, msg) {
    return renderStructuredJsonCard(parsed, msg);
  }

  function stripMarkdownFences(s) {
    return String(s == null ? '' : s)
      .replace(/^```(?:json)?\s*/i, '')
      .replace(/\s*```\s*$/i, '')
      .trim();
  }

  function insightContentFromMessage(msg) {
    if (msg && msg.structured != null && typeof msg.structured === 'object') {
      return { isJson: true, parsed: msg.structured, rawText: String(msg.content || '') };
    }
    return parseCardContent(String(msg.content == null ? '' : msg.content));
  }

  function renderInsightBrokenJsonBanner(msg, rawText) {
    var title = (msg.title || '').trim();
    if (!PLUSOR_CONTAINER_INSIGHT_TITLES[title]) return '';
    var raw = String(rawText || '');
    if (!raw.trim()) return '';
    var looksBroken = /^\s*\{/.test(raw) || /^\s*\[/.test(raw);
    if (!looksBroken) return '';
    return (
      '<div class="mb-1 rounded border border-amber-200/80 bg-amber-50/90 px-2 py-1 text-[10px] text-amber-900 dark:bg-amber-950/40 dark:text-amber-100 dark:border-amber-800">' +
      '<strong>Gợi ý:</strong> Không parse được JSON (có thể bị cắt giữa chừng từ server). ' +
      'Dùng bản có <code class="text-[9px]">structured</code> từ API hoặc chạy lại tối ưu.</div>'
    );
  }

  function renderInsightPlain(msg, rawText) {
    var it = msg.insight_type || 'info';
    var body = stripMarkdownFences(rawText);
    body = body.replace(/<br\s*\/?>/gi, '\n');
    var title = (msg.title || '').trim();
    if (
      title === 'Phân tích dữ liệu' ||
      title === 'Rủi ro & lưu ý' ||
      title === 'Knapsack / CBM' ||
      title === 'Thách thức giả định'
    ) {
      body = translateVi(body);
    }
    return (
      '<div class="plusor-card ' +
      severityCardClass(msg.severity) +
      '">' +
      '<div class="flex justify-between gap-1 mb-1"><span class="font-semibold text-heading text-xs">' +
      esc(msg.title || '') +
      '</span><span class="plusor-meta">' +
      esc(it) +
      '</span></div>' +
      '<div class="text-body leading-snug whitespace-pre-wrap">' +
      esc(body).replace(/\n/g, '<br>') +
      '</div>' +
      (msg.sku ? '<p class="mt-1 text-[10px] font-mono plusor-txt-muted">SKU: ' + esc(msg.sku) + '</p>' : '') +
      '</div>'
    );
  }

  function renderInsightByTitle(msg) {
    var title = (msg.title || '').trim();
    var pc = insightContentFromMessage(msg);
    if (!pc.isJson) {
      var norm = String(msg.content || '')
        .replace(/<br\s*\/?>/gi, '\n')
        .replace(/&lt;br\s*\/?&gt;/gi, '\n');
      var pc2 = parseCardContent(norm);
      if (pc2.isJson) pc = pc2;
    }
    if (pc.isJson) {
      var p = pc.parsed;
      if (title === 'Phân tích dữ liệu') return renderAnalysisCard(p, msg);
      if (title === 'Rủi ro & lưu ý') return renderRiskCard(p, msg);
      if (title === 'Knapsack / CBM') return renderKnapsackCard(p, msg);
      if (title === 'Thách thức giả định') return renderChallengerCard(p, msg);
      if (title === 'SKU signals (HIGH_ATTENTION)' || (p && !Array.isArray(p) && p.sku_details))
        return renderSkuSignalsCard(p, msg);
      if (title === 'Phân tích sâu từng SKU' || (p && !Array.isArray(p) && p.sku_reviews))
        return renderSkuDeepReviewsCard(p, msg);
      return renderJsonSummaryCard(p, msg);
    }
    return renderInsightBrokenJsonBanner(msg, pc.rawText) + renderInsightPlain(msg, pc.rawText);
  }

  function renderVerdictCard(parsed, msg) {
    var verdict = parsed.verdict != null ? translateVi(String(parsed.verdict)) : '';
    var actions = Array.isArray(parsed.actions) ? parsed.actions : [];
    var risks = Array.isArray(parsed.risks) ? parsed.risks : [];
    var conf = parsed.confidence;
    var confNum = typeof conf === 'number' ? (conf <= 1 ? conf * 100 : conf) : conf != null ? Number(conf) : null;
    var steps = '';
    actions.forEach(function (a, i) {
      steps += '<div class="text-[11px] mt-1"><strong>' + (i + 1) + '.</strong> ' + esc(translateVi(String(a))) + '</div>';
    });
    var riskBlock = '';
    if (risks.length) {
      riskBlock =
        '<div class="mt-2 text-[10px] plusor-txt-warn"><span class="font-semibold">Rủi ro:</span> ' +
        risks
          .slice(0, 5)
          .map(function (r) {
            return esc(translateVi(String(r)));
          })
          .join(' · ') +
        '</div>';
    }
    var bar =
      confNum != null && !isNaN(confNum)
        ? '<div class="mt-2 text-[10px] plusor-txt-muted">Độ tin cậy</div>' + pctBar(confNum)
        : '';
    return (
      '<div class="plusor-card plusor-card--low">' +
      '<div class="pcard-quote text-[12px] font-medium text-heading">' +
      esc(verdict) +
      '</div>' +
      steps +
      riskBlock +
      bar +
      '</div>'
    );
  }

  function renderChatPreviewCard(st) {
    st = st || {};
    var rec = st.recipient || {};
    var name = esc(rec.full_name || '');
    var pos = esc(String(rec.position_title || '').trim());
    var dept = esc(String(rec.department || '').trim());
    var badge = '';
    if (pos || dept) {
      badge =
        '<span class="plusor-comms-badge text-[10px] plusor-txt-muted ml-1">' +
        (pos ? pos + (dept ? ' · ' + dept : '') : dept) +
        '</span>';
    }
    var rawBody = String(st.full_message != null ? st.full_message : st.message_preview || '');
    var bodySafe = esc(rawBody).replace(/\n/g, '<br>');
    return (
      '<div class="plusor-card plusor-card--low plusor-comms-card plusor-card--chat-preview">' +
      '<div class="text-[10px] plusor-txt-muted uppercase tracking-wide mb-1">Xác nhận gửi tin</div>' +
      '<div class="flex flex-wrap items-baseline gap-1 mb-2">' +
      '<span class="font-semibold text-heading text-xs">' +
      name +
      '</span>' +
      badge +
      '</div>' +
      '<div class="plusor-comms-preview-scroll text-[12px] plusor-txt-body mb-3">' +
      bodySafe +
      '</div>' +
      '<div class="plusor-comms-actions">' +
      '<button type="button" class="plusor-exec-btn plusor-exec-btn--inline" data-plusor-send-prompt="gửi đi">Gửi ngay</button>' +
      '<button type="button" class="plusor-exec-btn plusor-exec-btn--inline plusor-comms-btn-secondary" data-plusor-focus-input="1">Chỉnh nội dung</button>' +
      '</div></div>'
    );
  }

  function renderChatSentCard(st) {
    st = st || {};
    var href = String(st.chat_url || '/chat/').trim() || '/chat/';
    var isDup = String(st.status || '') === 'already_sent';
    var label = isDup ? 'Tin đã gửi trước đó (không trùng)' : 'Đã gửi tin nhắn';
    var name = esc(String(st.target_name || '').trim());
    return (
      '<div class="plusor-card plusor-card--low plusor-comms-card plusor-card--chat-sent">' +
      '<div class="text-[10px] plusor-txt-muted mb-1">' +
      esc(label) +
      '</div>' +
      (name ? '<div class="text-xs font-semibold text-heading mb-2">' + name + '</div>' : '') +
      '<a class="plusor-exec-btn plusor-exec-btn--inline text-center no-underline !mt-0" href="' +
      escAttr(href) +
      '">Mở chat</a>' +
      '</div>'
    );
  }

  function renderUnreadSummaryCard(st) {
    st = st || {};
    var rooms = Array.isArray(st.rooms) ? st.rooms : [];
    var rows = '';
    rooms.forEach(function (r) {
      var un = r.unread != null ? r.unread : 0;
      var href = r.chat_url || '/chat/?room_id=' + encodeURIComponent(String(r.room_id || ''));
      rows +=
        '<li class="plusor-comms-unread-row plusor-unread__item list-none">' +
        '<a href="' +
        escAttr(href) +
        '" class="plusor-unread__room-link" target="_blank" rel="noopener noreferrer">' +
        '<span class="plusor-unread__name font-medium text-heading text-[11px]">' +
        esc(r.name || '') +
        '</span>' +
        '<span class="plusor-unread__count text-[11px] plusor-txt-warn shrink-0">(' +
        un +
        ')</span>' +
        '</a>' +
        (r.last_msg
          ? '<div class="text-[10px] plusor-txt-muted truncate mt-0.5 pl-0">' +
            esc(r.last_msg) +
            '</div>'
          : '') +
        '</li>';
    });
    var total = st.total_unread_rooms != null ? st.total_unread_rooms : rooms.length;
    var fullSummary = (st.full_summary || st.summary || '').trim();
    var summaryBlock = fullSummary
      ? '<div class="plusor-unread-summary-body text-[11px] plusor-txt-body whitespace-pre-wrap mt-2 leading-relaxed">' +
        esc(fullSummary) +
        '</div>'
      : '';
    var listBlock = '';
    if (rows) {
      listBlock =
        '<ul class="plusor-unread-room-list list-none m-0 mt-2 p-0 space-y-0.5">' + rows + '</ul>';
    } else if (!fullSummary) {
      listBlock = '<div class="text-[11px] plusor-txt-muted">Không có tin chưa đọc.</div>';
    }
    return (
      '<div class="plusor-card plusor-card--low plusor-comms-card plusor-card--unread-summary">' +
      '<div class="text-[10px] font-semibold text-heading mb-2">Tin chưa đọc — ' +
      total +
      ' phòng</div>' +
      summaryBlock +
      listBlock +
      '</div>'
    );
  }

  function renderCoworkerListCard(st) {
    st = st || {};
    var cands = Array.isArray(st.candidates) ? st.candidates : [];
    var rows = '';
    cands.forEach(function (c, i) {
      var nm = String(c.full_name || '').trim();
      var hint = nm || 'Người ' + (i + 1);
      var prompt = 'Nhắn tin cho ' + hint;
      var sub = [c.position_title, c.department].filter(Boolean).join(' · ');
      rows +=
        '<div class="plusor-comms-cow-row">' +
        '<div class="min-w-0 flex-1">' +
        '<div class="text-xs font-medium text-heading">' +
        esc(nm) +
        '</div>' +
        (sub
          ? '<div class="text-[10px] plusor-txt-muted">' + esc(sub) + '</div>'
          : '') +
        '</div>' +
        '<button type="button" class="plusor-comms-pick-btn" data-plusor-send-prompt="' +
        escAttr(prompt) +
        '">Chọn</button>' +
        '</div>';
    });
    return (
      '<div class="plusor-card plusor-card--medium plusor-comms-card plusor-card--coworker-list">' +
      '<div class="text-[10px] font-semibold text-heading mb-2">Chọn người nhận</div>' +
      rows +
      '</div>'
    );
  }

  function renderThinkingBlock(msg, meta) {
    var thMeta = meta || msg.meta || {};
    var thRaw = msg.content || '';
    var isStreaming = thMeta.streaming !== false;
    var thLabel = esc(String(thMeta.label || 'Quá trình suy luận'));
    var budgetTokens = thMeta.budget_tokens || 0;
    var badgeHtml = budgetTokens > 0 ? '<span class="plusor-thinking-badge">' + esc(String(budgetTokens) + ' tok') + '</span>' : '';
    var streamingClass = isStreaming ? ' plusor-thinking-block--streaming' : '';
    var thContent = esc(String(thRaw || ''));
    return (
      '<div class="plusor-thinking-block' + streamingClass + '" onclick="this.classList.toggle(\'plusor-thinking-block--open\')">' +
      '<div class="plusor-thinking-header">' +
      '<span class="plusor-thinking-icon">' +
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M6 4l4 4-4 4"/></svg>' +
      '</span>' +
      '<span>' + thLabel + '</span>' +
      '<span class="plusor-thinking-pulse"></span>' +
      badgeHtml +
      '</div>' +
      '<div class="plusor-thinking-body">' +
      '<div class="plusor-thinking-content">' + thContent + '</div>' +
      '</div>' +
      '</div>'
    );
  }

  function renderTableMessage(msg) {
    var st = msg.structured || {};
    var cols = Array.isArray(st.columns) ? st.columns : [];
    var rows = Array.isArray(st.rows) ? st.rows : [];
    var caption = st.caption || '';
    if (!cols.length && !rows.length) return '<div class="plusor-msg-bubble">(Bảng trống)</div>';
    var theadHtml = '';
    if (cols.length) {
      theadHtml += '<thead><tr>';
      for (var ci = 0; ci < cols.length; ci++) {
        var col = cols[ci];
        var alignCls = col.align === 'right' ? ' col--right' : col.align === 'center' ? ' col--center' : '';
        theadHtml += '<th class="' + alignCls + '">' + esc(col.label || col.key || '') + '</th>';
      }
      theadHtml += '</tr></thead>';
    }
    var tbodyHtml = '<tbody>';
    for (var ri = 0; ri < rows.length; ri++) {
      var row = rows[ri];
      tbodyHtml += '<tr>';
      if (cols.length) {
        for (var cj = 0; cj < cols.length; cj++) {
          var key = cols[cj].key;
          var val = row[key] != null ? String(row[key]) : '';
          var tdAlign = cols[cj].align === 'right' ? ' col--right' : cols[cj].align === 'center' ? ' col--center' : '';
          tbodyHtml += '<td class="' + tdAlign + '">' + esc(val) + '</td>';
        }
      }
      tbodyHtml += '</tr>';
    }
    tbodyHtml += '</tbody>';
    var capHtml = caption ? '<div class="plusor-table-caption">' + esc(caption) + '</div>' : '';
    var titleHtml = (msg.title) ? '<div class="plusor-table-title">' + esc(msg.title) + '</div>' : '';
    return (
      '<div class="plusor-msg-bubble">' +
      titleHtml +
      '<div class="plusor-table-wrapper">' +
      '<table>' + theadHtml + tbodyHtml + '</table>' +
      capHtml +
      '</div></div>'
    );
  }

  function renderCardGroupMessage(msg) {
    var st = msg.structured || {};
    var cards = Array.isArray(st.cards) ? st.cards : [];
    var layout = st.layout || 'grid';
    var cols = st.columns || 2;
    if (!cards.length) return '<div class="plusor-msg-bubble">(Không có dữ liệu)</div>';
    var titleHtml = (msg.title) ? '<div class="plusor-card-group-title">' + esc(msg.title) + '</div>' : '';
    var gridStyle = layout === 'row' ? ' plusor-card-group--row' : '';
    gridStyle += ' plusor-card-group--cols-' + Math.max(1, Math.min(cols, 4));
    var cardsHtml = '';
    for (var i = 0; i < cards.length; i++) {
      var card = cards[i];
      var trendHtml = '';
      if (card.trend) {
        var trendDir = card.trend === 'down' ? 'down' : 'up';
        var trendArrow = card.trend === 'down' ? '↓' : '↑';
        trendHtml = '<span class="plusor-stat-card__trend plusor-stat-card__trend--' + trendDir + '">' + trendArrow + ' ' + esc(String(card.trend_value || '')) + '</span>';
      }
      cardsHtml += (
        '<div class="plusor-stat-card">' +
        '<span class="plusor-stat-card__label">' + esc(card.label || '') + '</span>' +
        '<span class="plusor-stat-card__value">' + esc(String(card.value != null ? card.value : '')) + '</span>' +
        trendHtml +
        '</div>'
      );
    }
    return (
      '<div class="plusor-msg-bubble">' +
      titleHtml +
      '<div class="plusor-card-group' + gridStyle + '">' + cardsHtml + '</div>' +
      '</div>'
    );
  }

  function renderKVListMessage(msg) {
    var st = msg.structured || {};
    var pairs = Array.isArray(st.pairs) ? st.pairs : [];
    if (!pairs.length) return '<div class="plusor-msg-bubble">(Không có dữ liệu)</div>';
    var titleHtml = (msg.title) ? '<div class="plusor-kv-list-title">' + esc(msg.title) + '</div>' : '';
    var rowsHtml = '';
    for (var i = 0; i < pairs.length; i++) {
      var pair = pairs[i];
      var emphasisCls = pair.emphasis === 'high' ? ' plusor-kv-row__value--high' : pair.emphasis === 'low' ? ' plusor-kv-row__value--low' : '';
      rowsHtml += (
        '<div class="plusor-kv-row">' +
        '<span class="plusor-kv-row__key">' + esc(pair.key || '') + '</span>' +
        '<span class="plusor-kv-row__value' + emphasisCls + '">' + esc(String(pair.value != null ? pair.value : '')) + '</span>' +
        '</div>'
      );
    }
    return (
      '<div class="plusor-msg-bubble">' +
      titleHtml +
      '<div class="plusor-kv-list">' + rowsHtml + '</div>' +
      '</div>'
    );
  }

  function renderProductCardMessage(msg) {
    var img = msg.image
      ? '<img src="' +
        escAttr(msg.image) +
        '" alt="" loading="lazy" onerror="this.style.display=\'none\'">'
      : '<div class="plusor-ph-img" role="presentation"></div>';
    var meta = msg.meta || {};
    var metaStr = '';
    try {
      if (meta && typeof meta === 'object') {
        metaStr = Object.keys(meta)
          .slice(0, 4)
          .map(function (k) {
            return k + ': ' + meta[k];
          })
          .join(' · ');
      }
    } catch (e) {}
    return (
      '<div class="plusor-card plusor-card--low plusor-product-card">' +
      img +
      '<div class="min-w-0 flex-1">' +
      '<div class="font-mono text-[11px] font-semibold text-heading">' +
      esc(msg.sku || '') +
      '</div>' +
      (msg.name
        ? '<div class="text-[10px] plusor-txt-body truncate">' + esc(msg.name) + '</div>'
        : '') +
      (metaStr
        ? '<div class="text-[10px] plusor-txt-muted mt-0.5">' + esc(metaStr) + '</div>'
        : '') +
      '</div></div>'
    );
  }

  function renderProductMatchGroup(msg) {
    var structured = msg.structured || {};
    var products = Array.isArray(structured.products) ? structured.products : [];
    if (!products.length) {
      return '<div class="plusor-msg-bubble">Chưa tìm thấy sản phẩm đủ phù hợp. Vui lòng thử ảnh rõ hơn.</div>';
    }
    var cards = products.map(function (product, index) {
      var status = product.status || 'out_of_stock';
      var badgeClass = status === 'in_stock' ? 'badge-green' : status === 'inactive' ? 'badge-red' : 'badge-amber';
      var statusText = status === 'in_stock' ? 'Còn hàng' : status === 'inactive' ? 'Ngừng bán' : 'Hết hàng';
      var confidence = Math.round(Number(product.confidence || product.score || 0) * 100);
      var image = product.image_url
        ? '<img src="' + escAttr(product.image_url) + '" alt="" class="w-16 h-16 rounded-lg object-cover shrink-0" loading="lazy">'
        : '<div class="plusor-ph-img w-16 h-16 shrink-0"></div>';
      return (
        '<button type="button" class="card card-hover w-full text-left mb-2" data-plusor-product-run="' +
        escAttr(structured.run_id || '') + '" data-plusor-product-id="' + escAttr(product.product_id) + '">' +
        '<div class="flex gap-3 items-start">' + image +
        '<div class="min-w-0 flex-1"><div class="flex justify-between gap-2">' +
        '<strong class="text-xs text-heading">' + esc((index + 1) + '. ' + (product.product_name || 'Sản phẩm')) + '</strong>' +
        '<span class="badge ' + badgeClass + '">' + esc(statusText) + '</span></div>' +
        '<div class="text-[11px] plusor-txt-muted mt-1">' +
        esc((product.skus || []).join(', ') || 'Xem SKU') + '</div>' +
        '<div class="flex gap-2 mt-2"><span class="badge badge-cyan">Khớp ' + confidence + '%</span>' +
        '<span class="badge badge-cont">Có thể bán: ' + esc(product.available || 0) + '</span></div>' +
        '</div></div></button>'
      );
    }).join('');
    var warning = structured.partial
      ? '<div class="badge badge-amber mb-2">Một nguồn AI tạm lỗi, kết quả dùng dữ liệu còn lại</div>'
      : '';
    if (structured.ambiguous) {
      warning += '<div class="badge badge-amber mb-2">Hai kết quả đầu khá sát nhau, nên kiểm tra SKU</div>';
    }
    return '<div class="plusor-msg-bubble"><div class="text-xs font-semibold text-heading mb-2">' +
      esc(msg.content || 'Sản phẩm phù hợp nhất') + '</div>' + warning + cards + '</div>';
  }

  function renderImageMessage(msg) {
    var image = msg.image || {};
    var url = typeof image === 'string' ? image : image.url;
    return '<div class="plusor-msg-bubble">' +
      (url ? '<img src="' + escAttr(url) + '" alt="Ảnh khách gửi" class="max-w-[220px] rounded-lg mb-2" loading="lazy">' : '') +
      (msg.content ? '<span class="whitespace-pre-wrap">' + esc(msg.content) + '</span>' : '') +
      '</div>';
  }

  function renderActionCardMessage(msg) {
    var conf =
      typeof msg.confidence === 'number'
        ? '<span class="text-[10px] opacity-80">' + Math.round(msg.confidence * 100) + '%</span>'
        : '';
    var risk = msg.risk
      ? '<span class="text-[10px] ' +
        (String(msg.risk).toLowerCase() === 'high'
          ? 'plusor-txt-danger'
          : String(msg.risk).toLowerCase() === 'low'
            ? 'plusor-txt-green'
            : 'plusor-txt-warn') +
        '">' +
        esc(msg.risk) +
        '</span>'
      : '';
    var imp = msg.impact_estimate
      ? '<div class="text-[10px] plusor-txt-muted mt-0.5">' + esc(msg.impact_estimate) + '</div>'
      : '';
    return (
      '<div class="plusor-card plusor-card--medium">' +
      '<div class="flex justify-between gap-1 flex-wrap items-center">' +
      '<span class="font-semibold text-heading text-xs">' +
      esc(msg.label || msg.action_id || '') +
      '</span>' +
      conf +
      ' ' +
      risk +
      '</div>' +
      imp +
      '<button type="button" class="plusor-exec-btn plusor-exec-btn--inline" data-plusor-action-id="' +
      escAttr(msg.action_id || msg.id || '') +
      '">Thực hiện</button>' +
      '</div>'
    );
  }

  function renderErrorCardMessage(msg) {
    var raw = msg.raw != null ? String(msg.raw) : '';
    return (
      '<div class="plusor-card plusor-card--high">' +
      '<span class="plusor-txt-danger font-medium text-xs">⚠ ' +
      esc(msg.message || 'Lỗi') +
      '</span>' +
      (raw
        ? '<div class="plusor-error-raw" title="' +
          escAttr(raw) +
          '">' +
          esc(raw.length > 120 ? raw.slice(0, 120) + '…' : raw) +
          '</div>'
        : '') +
      '</div>'
    );
  }

  function renderToolCallMessage(msg) {
    return (
      '<div class="plusor-card plusor-card--thinking text-[11px] whitespace-pre-wrap">' +
      esc(msg.content || msg.result || JSON.stringify(msg)) +
      '</div>'
    );
  }

  function renderSourceChips(msg) {
    var sources = msg && msg.meta && Array.isArray(msg.meta.sources) ? msg.meta.sources : [];
    if (!sources.length) return '';
    var chips = sources.slice(0, 4).map(function (source) {
      var title = source.title || 'Nguồn Knowledge';
      var method = source.method ? ' · ' + source.method : '';
      var score = source.score ? ' · ' + Math.round(Number(source.score) * 100) + '%' : '';
      var label = esc(title + method + score);
      if (source.url) {
        return (
          '<a class="plusor-source-chip" href="' + escAttr(source.url) + '" target="_blank" rel="noopener noreferrer">' +
          label +
          '</a>'
        );
      }
      return '<span class="plusor-source-chip">' + label + '</span>';
    }).join('');
    return '<div class="plusor-source-chips" aria-label="Nguồn tham chiếu">' + chips + '</div>';
  }

  function renderTextMessage(msg) {
    if (msg.structured != null && typeof msg.structured === 'object') {
      var st = msg.structured;
      if (!Array.isArray(st) && st.verdict != null && String(st.verdict).replace(/\s/g, '').length > 0) {
        return renderVerdictCard(st, msg);
      }
      if (!Array.isArray(st)) {
        return renderStructuredJsonCard(st, msg);
      }
      return (
        '<div class="plusor-msg-bubble"><div class="plusor-card plusor-card--low pcard-structured">' +
        renderStructuredJsonBody(st, 0) +
        '</div></div>'
      );
    }

    var rawContent = String(msg.content || '').replace(/<br\s*\/?>/gi, '\n');
    var pcText = parseCardContent(rawContent);
    if (!pcText.isJson && rawContent.indexOf('verdict') >= 0) {
      pcText = parseCardContent(stripMarkdownFences(rawContent));
    }
    if (pcText.isJson && pcText.parsed != null && typeof pcText.parsed === 'object') {
      var p = pcText.parsed;
      var hasVerdict =
        !Array.isArray(p) &&
        p.verdict != null &&
        String(p.verdict).replace(/\s/g, '').length > 0;
      if (hasVerdict) {
        return renderVerdictCard(p, msg);
      }
      if (!Array.isArray(p)) {
        return renderStructuredJsonCard(p, msg);
      }
      return (
        '<div class="plusor-msg-bubble"><div class="plusor-card plusor-card--low pcard-structured">' +
        renderStructuredJsonBody(p, 0) +
        '</div></div>'
      );
    }
    var plain = stripMarkdownFences(pcText.rawText || rawContent);
    return (
      '<div class="plusor-msg-bubble"><div class="plusor-md">' +
      plusorMarkdownToSafeHtml(plain) +
      '</div>' +
      renderSourceChips(msg) +
      '</div>'
    );
  }

  var MESSAGE_RENDERERS = {
    insight: renderInsightByTitle,
    chat_preview: function (msg) { return renderChatPreviewCard(msg.structured); },
    chat_sent: function (msg) { return renderChatSentCard(msg.structured); },
    unread_summary: function (msg) { return renderUnreadSummaryCard(msg.structured); },
    coworker_list: function (msg) { return renderCoworkerListCard(msg.structured); },
    product_card: renderProductCardMessage,
    product_match_group: renderProductMatchGroup,
    action: renderActionCardMessage,
    error: renderErrorCardMessage,
    thinking: function (msg) { return renderThinkingBlock(msg, msg.meta); },
    table: renderTableMessage,
    card_group: renderCardGroupMessage,
    kv_list: renderKVListMessage,
    tool_call: renderToolCallMessage,
    text: renderTextMessage
  };

  function renderMessageInner(msg) {
    var role = (msg.role || 'assistant').toLowerCase();
    if (role === 'user') {
      if ((msg.type || '') === 'image') return renderImageMessage(msg);
      return (
        '<div class="plusor-msg-bubble"><span class="whitespace-pre-wrap">' +
        esc(msg.content || '') +
        '</span></div>'
      );
    }
    var t = msg.type || 'text';
    var renderer = MESSAGE_RENDERERS[t];
    if (renderer) return renderer(msg);
    return renderTextMessage(msg);
  }

  function messageRowHtml(msg) {
    var ts = formatMsgTime(msg._ts);
    var tsHtml = ts ? '<span class="plusor-msg-ts">' + esc(ts) + '</span>' : '';
    var role = (msg.role || 'assistant').toLowerCase();
    if (role === 'user') {
      return (
        '<div class="plusor-msg-row plusor-msg-row--user">' +
        userAvatarMarkup() +
        '<div class="min-w-0 flex-1 flex flex-col items-end">' +
        renderMessageInner(msg) +
        tsHtml +
        '</div></div>'
      );
    }
    var copyBtnHtml = '<div class="plusor-msg-actions">' +
      '<button type="button" class="plusor-msg-action-btn plusor-msg-copy-btn" title="Sao chép" aria-label="Sao chép">' +
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>' +
      '</button></div>';
    return (
      '<div class="plusor-msg-row">' +
        assistantAvatarHtml() +
        '<div class="min-w-0 flex-1">' +
        renderMessageInner(msg) +
        copyBtnHtml +
        tsHtml +
        '</div></div>'
    );
  }

  function extractNodeResultText(result) {
    if (result == null) return '';
    if (typeof result === 'string') return result;
    if (typeof result === 'object') {
      if (result.text != null) return String(result.text);
      if (result.compressed_text != null) return String(result.compressed_text);
      if (result.error != null) return String(result.error);
    }
    try {
      return JSON.stringify(result);
    } catch (e) {
      return String(result);
    }
  }

  function buildNodeProgressMessage(nodeId, nodeLabel, result, parsedJson) {
    var content = '';
    if (parsedJson != null && typeof parsedJson === 'object') {
      try {
        content = JSON.stringify(parsedJson);
      } catch (e) {
        content = '';
      }
    }
    if (!content) content = extractNodeResultText(result).trim();
    if (!content) return null;
    var titles = {
      data_analyst: 'Phân tích dữ liệu',
      risk_scanner: 'Rủi ro & lưu ý',
      knapsack_solver: 'Knapsack / CBM',
      challenger: 'Thách thức giả định',
      plusor_synthesis: 'Tổng hợp PluSor',
    };
    var title = titles[nodeId] || nodeLabel || nodeId;
    if (nodeId === 'plusor_synthesis') {
      return { role: 'assistant', type: 'text', content: content, _ts: Date.now(), _node_id: nodeId };
    }
    var sev = 'medium';
    var it = 'info';
    if (nodeId === 'data_analyst' || nodeId === 'knapsack_solver') sev = 'low';
    if (nodeId === 'risk_scanner') {
      sev = 'medium';
      it = 'risk';
    }
    if (nodeId === 'challenger') it = 'recommendation';
    return {
      role: 'assistant',
      type: 'insight',
      title: title,
      content: content,
      severity: sev,
      insight_type: it,
      _ts: Date.now(),
      _node_id: nodeId,
    };
  }

  function compressProductImage(file) {
    return new Promise(function (resolve, reject) {
      if (!file || !/^image\/(jpeg|png|webp)$/i.test(file.type || '')) {
        reject(new Error('Chỉ hỗ trợ ảnh JPG, PNG hoặc WebP.'));
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        reject(new Error('Ảnh không được vượt quá 10MB.'));
        return;
      }
      var url = URL.createObjectURL(file);
      var image = new Image();
      image.onload = function () {
        var scale = Math.min(1, 1600 / Math.max(image.naturalWidth, image.naturalHeight));
        var canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
        canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
        var context = canvas.getContext('2d');
        context.fillStyle = 'white';
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.drawImage(image, 0, 0, canvas.width, canvas.height);
        URL.revokeObjectURL(url);
        canvas.toBlob(function (blob) {
          if (!blob) {
            reject(new Error('Không thể nén ảnh.'));
            return;
          }
          resolve(blob.size < file.size ? blob : file);
        }, 'image/jpeg', 0.82);
      };
      image.onerror = function () {
        URL.revokeObjectURL(url);
        reject(new Error('Không đọc được ảnh.'));
      };
      image.src = url;
    });
  }

  function uploadProductImage(file) {
    return compressProductImage(file).then(function (blob) {
      var form = new FormData();
      form.append('image', blob, 'customer-product.jpg');
      return fetch('/ai-hub/api/plusor/images/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': getCsrfToken() },
        body: form,
      });
    }).then(function (response) {
      return response.json().then(function (body) {
        if (!response.ok || !body.success) {
          throw new Error((body.errors && body.errors[0] && body.errors[0].message) || 'Không tải được ảnh.');
        }
        return body.data;
      });
    });
  }

  function closeProductDrawer() {
    var drawer = document.getElementById('plusor-product-drawer');
    var overlay = document.getElementById('plusor-product-overlay');
    if (drawer) {
      drawer.classList.remove('is-open');
      drawer.setAttribute('aria-hidden', 'true');
    }
    if (overlay) overlay.classList.remove('is-open');
  }

  function productDrawerWarehouseCode(warehouse) {
    var locationId = String((warehouse && warehouse.location_id) || '');
    var codesById = {
      '241737': 'HN',
      '548744': 'SG',
      '783623': 'SR',
    };
    if (codesById[locationId]) return codesById[locationId];

    var locationName = String((warehouse && warehouse.location_name) || '').trim();
    var normalized = locationName
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase();
    if (/(^|\s)(hn|ha noi)(\s|$)/.test(normalized)) return 'HN';
    if (/(^|\s)(sg|sai gon|ho chi minh|hcm)(\s|$)/.test(normalized)) return 'SG';
    if (/(^|\s)(sr|showroom)(\s|$)/.test(normalized)) return 'SR';

    var initials = normalized
      .split(/\s+/)
      .filter(function (part) { return part && part !== 'kho'; })
      .map(function (part) { return part.charAt(0); })
      .join('')
      .slice(0, 3)
      .toUpperCase();
    return initials || 'Kho';
  }

  function productDrawerImage(imageUrl, sizeClass) {
    var image = imageUrl
      ? '<img src="' + escAttr(imageUrl) +
        '" alt="" class="w-full h-full object-cover" loading="lazy" onerror="this.style.display=\'none\'">'
      : '';
    return '<div class="plusor-ph-img ' + sizeClass +
      ' rounded-lg shrink-0 overflow-hidden border border-line">' + image + '</div>';
  }

  function productDrawerValue(value) {
    return value == null || value === '' ? 0 : value;
  }

  function productDrawerVariantName(variant) {
    var options = Array.isArray(variant.options)
      ? variant.options.filter(function (value) { return String(value || '').trim(); })
      : [];
    return options.length ? options.join(' / ') : (variant.name || 'Phân loại');
  }

  var productDrawerRenderer = {
    warehouseCode: productDrawerWarehouseCode,

    render: function (data) {
      data = data || {};
      var productImage = data.image_url || '';
      var warehouseOrder = { HN: 0, SG: 1, SR: 2 };
      var variants = (data.variants || []).map(function (variant) {
        var variantImage = variant.image_url || productImage;
        var warehouses = (variant.warehouses || []).slice().sort(function (left, right) {
          var leftCode = productDrawerWarehouseCode(left);
          var rightCode = productDrawerWarehouseCode(right);
          var leftRank = warehouseOrder[leftCode] == null ? 99 : warehouseOrder[leftCode];
          var rightRank = warehouseOrder[rightCode] == null ? 99 : warehouseOrder[rightCode];
          return leftRank - rightRank || leftCode.localeCompare(rightCode);
        }).map(function (warehouse) {
          var code = productDrawerWarehouseCode(warehouse);
          return '<div class="rounded-lg border border-line px-3 py-2 text-center" data-warehouse-code="' +
            escAttr(code) + '">' +
            '<div class="text-[10px] font-semibold text-subtle">' + esc(code) + '</div>' +
            '<div class="mt-1 text-xs text-heading"><strong>' +
            esc(productDrawerValue(warehouse.available)) + '</strong> có thể bán</div>' +
            '<div class="text-[10px] text-subtle">Thực tế ' +
            esc(productDrawerValue(warehouse.on_hand)) + '</div></div>';
        }).join('');
        var warehouseGrid = warehouses
          ? '<div class="grid grid-cols-3 gap-2 mt-3">' + warehouses + '</div>'
          : '<div class="text-[11px] text-subtle mt-3">Chưa có dữ liệu theo kho.</div>';

        return '<section class="card mb-2" data-plusor-variant-id="' +
          escAttr(variant.variant_id || '') + '"><div class="flex gap-3 items-start">' +
          productDrawerImage(variantImage, 'w-16 h-16') +
          '<div class="min-w-0 flex-1"><div class="flex flex-wrap items-start justify-between gap-2">' +
          '<div class="min-w-0"><div class="font-mono text-[11px] font-semibold text-heading">' +
          esc(variant.sku || 'Chưa có SKU') + '</div>' +
          '<div class="text-xs font-semibold text-heading mt-0.5">' +
          esc(productDrawerVariantName(variant)) + '</div></div>' +
          '<div class="shrink-0 text-right text-[10px]">' +
          '<div class="font-semibold text-heading">Tổng ' +
          esc(productDrawerValue(variant.available)) + ' có thể bán</div>' +
          '<div class="text-subtle">Thực tế ' +
          esc(productDrawerValue(variant.on_hand)) + '</div></div></div>' +
          warehouseGrid + '</div></div></section>';
      }).join('');

      return '<div class="card mb-3"><div class="flex items-center gap-3">' +
        productDrawerImage(productImage, 'w-12 h-12') +
        '<div class="min-w-0 flex-1"><div class="text-xs font-semibold text-heading">Tồn kho sản phẩm</div>' +
        '<div class="flex flex-wrap gap-2 mt-1">' +
        '<span class="badge badge-green">Tổng có thể bán: ' +
        esc(productDrawerValue(data.total_available)) + '</span>' +
        '<span class="badge badge-cont">Tổng thực tế: ' +
        esc(productDrawerValue(data.total_on_hand)) + '</span></div></div></div></div>' +
        (variants || '<p class="text-sm text-subtle">Chưa có SKU.</p>');
    },
  };

  window.PluSorProductDrawerRenderer = productDrawerRenderer;

  function openProductDrawer(runId, productId) {
    var drawer = document.getElementById('plusor-product-drawer');
    var overlay = document.getElementById('plusor-product-overlay');
    var body = document.getElementById('plusor-product-drawer-body');
    var title = document.getElementById('plusor-product-drawer-title');
    if (!drawer || !body) return;
    body.innerHTML = '<div class="text-sm text-subtle">Đang tải SKU và tồn kho…</div>';
    drawer.classList.add('is-open');
    drawer.setAttribute('aria-hidden', 'false');
    if (overlay) overlay.classList.add('is-open');
    fetch('/ai-hub/api/plusor/product-image-results/' + encodeURIComponent(runId) +
      '/products/' + encodeURIComponent(productId) + '/', { credentials: 'same-origin' })
      .then(function (response) { return response.json(); })
      .then(function (result) {
        if (!result.success) throw new Error('Không thể tải tồn kho.');
        var data = result.data || {};
        if (title) title.textContent = data.product_name || 'Chi tiết sản phẩm';
        body.innerHTML = productDrawerRenderer.render(data);
      })
      .catch(function (error) {
        body.innerHTML = '<div class="badge badge-red">' + esc(error.message || 'Không thể tải tồn kho.') + '</div>';
      });
  }

  window.PluSor = window.PluSor || {
    _state: null,
    /** Meta từ API chat (run_id, route, execution_trace, ...) — không còn dùng payload.trace */
    _plusorMeta: null,
    _actions: [],
    _messages: [],
    /** Index tin đầu tiên đang hiển thị (virtual window); 0 = từ đầu lịch sử. */
    _msgWindowStart: 0,
    _loadingOlderBatch: false,
    _scrollOlderTimer: null,
    _open: false,
    /** Số tin giữ lại phía trên khi merge payload tối ưu container (user + intro). */
    _optimizerKeepPrefixCount: null,
    _welcomeChips: [],
    _pendingImage: null,

    _getEls: function () {
      return {
        root: document.getElementById('plusor-root'),
        panel: document.getElementById('plusor-panel'),
        toggle: document.getElementById('plusor-nav-btn'),
        close: document.getElementById('plusor-close'),
        messages: document.getElementById('plusor-messages'),
        input: document.getElementById('plusor-input-box'),
        sendBtn: document.getElementById('plusor-send-btn'),
        activity: document.getElementById('plusor-activity'),
        activityLabel: document.getElementById('plusor-activity-label'),
      };
    },

    /** Hiện/ẩn vùng activity (không ghi vào lịch sử tin nhắn). */
    setPlusorActivity: function (visible, text) {
      var els = this._getEls();
      var wrap = els.activity;
      var lab = els.activityLabel;
      if (!wrap) return;
      if (visible) {
        wrap.style.display = 'flex';
        if (lab != null && text != null) lab.textContent = text;
      } else {
        wrap.style.display = 'none';
        if (lab) lab.textContent = '';
      }
    },

    progressPayloadToLabel: function (p) {
      return progressPayloadToLabel(p);
    },

    /**
     * POST stream PluSor chat. opts: { message, page_context, session_id, onProgress, signal }
     * @returns {Promise<object>} envelope { type:'done', success, data, meta, errors }
     */
    sendChatStream: function (opts) {
      var self = this;
      opts = opts || {};
      var onProgress = opts.onProgress;
      var sid = opts.session_id;
      var signal = opts.signal || null;
      var bodyObj = {
        session_id: sid || null,
        message: opts.message || '',
        page_context: opts.page_context || {},
      };
      if (opts.image_id) bodyObj.image_id = opts.image_id;
      var pm = (opts.preferred_model && String(opts.preferred_model).trim()) || '';
      if (pm) bodyObj.preferred_model = pm;
      return fetch('/ai-hub/api/plusor/chat/stream/', {
        method: 'POST',
        credentials: 'same-origin',
        signal: signal,
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(bodyObj),
      }).then(function (r) {
        if (!r.ok) {
          return r.text().then(function (t) {
            throw new Error(t || 'HTTP ' + r.status);
          });
        }
        return self._consumePlusorSse(r, onProgress, signal);
      });
    },

    _consumePlusorSse: function (response, onProgress, signal) {
      var reader = response.body && response.body.getReader();
      if (!reader) {
        return Promise.reject(new Error('Không đọc được luồng phản hồi'));
      }
      function abortErr() {
        try {
          return new DOMException('Aborted', 'AbortError');
        } catch (e) {
          var x = new Error('Aborted');
          x.name = 'AbortError';
          return x;
        }
      }
      if (signal) {
        if (signal.aborted) {
          try {
            reader.cancel();
          } catch (e) {}
          return Promise.reject(abortErr());
        }
        signal.addEventListener(
          'abort',
          function () {
            try {
              reader.cancel();
            } catch (e) {}
          },
          { once: true }
        );
      }
      var dec = new TextDecoder();
      var buf = '';
      var finalBody = null;
      function pump() {
        if (signal && signal.aborted) {
          return Promise.reject(abortErr());
        }
        return reader
          .read()
          .then(function (res) {
            if (res.done) {
              if (signal && signal.aborted) {
                return Promise.reject(abortErr());
              }
              if (!finalBody) throw new Error('Luồng kết thúc không có kết quả');
              return finalBody;
            }
            buf += dec.decode(res.value, { stream: true });
            var parts = buf.split('\n\n');
            buf = parts.pop() || '';
            for (var pi = 0; pi < parts.length; pi++) {
              var lines = parts[pi].split('\n');
              for (var li = 0; li < lines.length; li++) {
                var line = lines[li].trim();
                if (line.indexOf('data:') !== 0) continue;
                var raw = line.slice(5).replace(/^\s/, '').replace(/\r/g, '');
                if (!raw) continue;
                var o;
                try {
                  o = JSON.parse(raw);
                } catch (e) {
                  continue;
                }
                if (o.type === 'progress' && onProgress) onProgress(o.payload);
                if (o.type === 'done') finalBody = o;
              }
            }
            return pump();
          })
          .catch(function (e) {
            if (signal && signal.aborted) {
              return Promise.reject(abortErr());
            }
            throw e;
          });
      }
      return pump();
    },

    _scrollMessagesToBottom: function () {
      var els = this._getEls();
      if (!els.messages) return;
      var el = els.messages;
      el.scrollTop = el.scrollHeight;
    },

    _injectStreamingThinking: function (text) {
      var els = this._getEls();
      if (!els.messages) return;
      var el = els.messages;
      // Remove previous streaming thinking element
      if (this._streamingThinkingEl && this._streamingThinkingEl.parentNode) {
        this._streamingThinkingEl.parentNode.removeChild(this._streamingThinkingEl);
      }
      var t = String(text || '').trim();
      if (!t) return;
      var thMsg = { role: 'assistant', type: 'thinking', content: t, meta: { streaming: true, label: 'Đang suy nghĩ...', collapsible: true } };
      var rowHtml = '<div class="plusor-msg-row">' +
        assistantAvatarHtml() +
        '<div class="min-w-0 flex-1">' +
        renderThinkingBlock(thMsg, thMsg.meta) +
        '</div></div>';
      var wrap = document.createElement('div');
      wrap.innerHTML = rowHtml;
      var node = wrap.firstElementChild;
      if (node) {
        el.appendChild(node);
        this._streamingThinkingEl = node;
        // Auto-open the thinking block during streaming
        node.querySelector('.plusor-thinking-block').classList.add('plusor-thinking-block--open');
      }
      this._scrollMessagesToBottom();
    },

    _showTypingIndicator: function () {
      this._hideTypingIndicator();
      var els = this._getEls();
      if (!els.messages) return;
      var el = els.messages;
      var row = document.createElement('div');
      row.className = 'plusor-typing-row';
      row.id = 'plusor-typing-indicator';
      row.innerHTML = assistantAvatarHtml() +
        '<div class="plusor-typing-dots">' +
        '<span class="plusor-typing-dot"></span>' +
        '<span class="plusor-typing-dot"></span>' +
        '<span class="plusor-typing-dot"></span>' +
        '</div>';
      el.appendChild(row);
      this._scrollMessagesToBottom();
    },

    _hideTypingIndicator: function () {
      var el = document.getElementById('plusor-typing-indicator');
      if (el && el.parentNode) el.parentNode.removeChild(el);
    },

    _setOpen: function (open) {
      var els = this._getEls();
      if (!els.panel) return;
      if (open && window.GDPChat && typeof window.GDPChat.closePanel === 'function') {
        var chatPanel = document.getElementById('chat-panel');
        if (chatPanel && chatPanel.classList.contains('gdp-chat-panel--open')) {
          window.GDPChat.closePanel();
        }
      }
      this._open = !!open;
      els.panel.classList.toggle('plusor-panel--open', this._open);
      if (els.root) els.root.classList.toggle('plusor-root--panel-open', this._open);
      if (els.toggle) {
        els.toggle.setAttribute('aria-expanded', this._open ? 'true' : 'false');
        els.toggle.classList.toggle('gdp-panel-trigger--open', this._open);
      }
      try {
        localStorage.setItem(STORAGE_KEY, this._open ? '1' : '0');
      } catch (e) {}
      if (this._open) {
        var self = this;
        requestAnimationFrame(function () {
          self._scrollMessagesToBottom();
        });
      }
    },

    /** Mở panel nổi (vd. trang optimize container khi chạy SSE). */
    openPanel: function () {
      this._setOpen(true);
    },

    /** Gọi trước khi thêm tin user/assistant lúc bắt đầu chạy optimize (để merge payload không xóa lịch sử cũ). */
    beginOptimizerSession: function () {},

    /** Gọi sau khi đã append user + assistant intro — giữ prefix tới hết intro. */
    endOptimizerSessionPrefix: function () {
      var n = (this._messages || []).length;
      this._optimizerKeepPrefixCount = n;
    },

    /**
     * Gộp plusor_payload từ SSE: giữ prefix (session + intro), thay phần insight pipeline bằng messages mới.
     */
    mergeOptimizerPayload: function (payload) {
      if (!payload || typeof payload !== 'object') return;
      var norm = normalizeClientPayload(payload);
      var incoming = norm.messages || [];
      var keep = this._optimizerKeepPrefixCount;
      if (keep == null || keep < 0) {
        return this.update(payload);
      }
      var head = (this._messages || []).slice(0, keep);
      this._messages = head.concat(incoming);
      this._optimizerKeepPrefixCount = null;
      this._state = norm;
      this._reindexActions();
      this._syncMsgWindowToTail();
      this._render(false);
      try {
        if (window.PluSorHistory) PluSorHistory.save(this._messages);
      } catch (e) {}
      try {
        document.dispatchEvent(new CustomEvent('plusor:update', { detail: norm }));
      } catch (e) {}
    },

    _reindexActions: function () {
      this._actions = [];
      var self = this;
      (this._messages || []).forEach(function (m) {
        if (m.type === 'action' && (m.action_id || m.id)) {
          self._actions.push({
            id: m.action_id || m.id,
            label: m.label || m.action_id,
            type: m.action_type || 'api_call',
            payload: m.payload || {},
            confidence: m.confidence,
            impact_estimate: m.impact_estimate,
            risk: m.risk,
          });
        }
      });
    },

    _actionById: function (id) {
      for (var i = 0; i < this._actions.length; i++) {
        if (this._actions[i].id === id) return this._actions[i];
      }
      return null;
    },

    _bind: function () {
      var self = this;
      var els = this._getEls();
      if (!els.toggle || els.toggle.dataset.plusorBound) return;
      els.toggle.dataset.plusorBound = '1';
      els.toggle.addEventListener('click', function () {
        self._setOpen(!els.panel.classList.contains('plusor-panel--open'));
      });
      if (els.close) {
        els.close.addEventListener('click', function () {
          self._setOpen(false);
        });
      }
      document.addEventListener('click', function (e) {
        var productBtn = e.target.closest('[data-plusor-product-run][data-plusor-product-id]');
        if (productBtn) {
          e.preventDefault();
          openProductDrawer(
            productBtn.getAttribute('data-plusor-product-run'),
            productBtn.getAttribute('data-plusor-product-id')
          );
          return;
        }
        if (e.target.closest('#plusor-product-drawer-close') || e.target.closest('#plusor-product-overlay')) {
          closeProductDrawer();
          return;
        }
        var sendPromptBtn = e.target.closest('[data-plusor-send-prompt]');
        if (sendPromptBtn && els.panel && els.panel.contains(sendPromptBtn)) {
          e.preventDefault();
          var pr = sendPromptBtn.getAttribute('data-plusor-send-prompt') || '';
          self.sendUserMessage(pr);
          return;
        }
        var focusInpBtn = e.target.closest('[data-plusor-focus-input]');
        if (focusInpBtn && els.panel && els.panel.contains(focusInpBtn)) {
          e.preventDefault();
          if (els.input) els.input.focus();
          return;
        }
        var copyBtn = e.target.closest('.plusor-msg-copy-btn');
        if (copyBtn && els.messages && els.messages.contains(copyBtn)) {
          e.preventDefault();
          var bubble = copyBtn.closest('.plusor-msg-row');
          var textContent = '';
          if (bubble) {
            var bubbleInner = bubble.querySelector('.plusor-msg-bubble');
            textContent = (bubbleInner ? bubbleInner.innerText : bubble.innerText) || '';
          }
          textContent = textContent.trim();
          if (textContent && navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(textContent).then(function () {
              copyBtn.classList.add('plusor-msg-action-btn--copied');
              setTimeout(function () { copyBtn.classList.remove('plusor-msg-action-btn--copied'); }, 1500);
            }, function () {});
          }
          return;
        }
        var btn = e.target.closest('.plusor-exec-btn');
        if (!btn || btn.disabled) return;
        var inPanel = els.messages && els.messages.contains(btn);
        var agentStream = document.getElementById('agent-stream');
        var inOptimizer = agentStream && agentStream.contains(btn);
        if (!inPanel && !inOptimizer) return;
        var aid = btn.getAttribute('data-plusor-action-id') || btn.getAttribute('data-action-index');
        var act = null;
        if (aid) act = self._actionById(aid);
        if (!act && btn.getAttribute('data-action-index') != null) {
          var idx = parseInt(btn.getAttribute('data-action-index'), 10);
          act = self._actions[idx];
        }
        if (!act) return;
        self.applyAction(act, btn, false);
      });
      function doSend() {
        self.sendMessage();
      }
      if (els.sendBtn) els.sendBtn.addEventListener('click', doSend);
      if (els.input) {
        els.input.addEventListener('keydown', function (e) {
          if (e.key === 'Enter') doSend();
        });
      }
      if (els.messages && !els.messages.dataset.plusorScrollBound) {
        els.messages.dataset.plusorScrollBound = '1';
        els.messages.addEventListener('scroll', function () {
          self._onMessagesScroll();
        });
      }
      try {
        if (localStorage.getItem(STORAGE_KEY) === '1') {
          self._setOpen(true);
        }
      } catch (e) {}
    },

    _syncMsgWindowToTail: function () {
      var n = (this._messages && this._messages.length) || 0;
      this._msgWindowStart = n > PLUSOR_VISIBLE_BATCH ? n - PLUSOR_VISIBLE_BATCH : 0;
    },

    _onMessagesScroll: function () {
      var self = this;
      if (this._scrollOlderTimer) clearTimeout(this._scrollOlderTimer);
      this._scrollOlderTimer = setTimeout(function () {
        self._scrollOlderTimer = null;
        var els = self._getEls();
        if (!els.messages || self._loadingOlderBatch) return;
        var el = els.messages;
        if (el.scrollTop > 72) return;
        if (self._msgWindowStart <= 0) return;
        self._loadOlderMessages();
      }, 120);
    },

    _loadOlderMessages: function () {
      if (this._msgWindowStart <= 0 || this._loadingOlderBatch) return;
      this._loadingOlderBatch = true;
      this._msgWindowStart = Math.max(0, this._msgWindowStart - PLUSOR_VISIBLE_BATCH);
      this._render(true);
      var self = this;
      requestAnimationFrame(function () {
        self._loadingOlderBatch = false;
      });
    },

    applyAction: function (action, btnEl, isBatch) {
      var self = this;
      var original = btnEl.innerHTML;
      btnEl.disabled = true;
      btnEl.dataset.originalHtml = original;
      btnEl.innerHTML = '<span class="inline-block animate-spin">&#x21BB;</span>';

      var ctx = buildPlusorPageContext();
      var idem =
        'plusor_' +
        (action.id || 'act') +
        '_' +
        Date.now() +
        '_' +
        Math.random().toString(36).slice(2, 8);
      var flowRun =
        (self._plusorMeta && self._plusorMeta.flow_run_id) ||
        (ctx.flow_run_id) ||
        (self._state && self._state.trace && self._state.trace.flow_run_id) ||
        '';

      var body = {
        action_id: action.id,
        payload: action.payload || {},
        context: ctx,
        flow_run_id: flowRun,
        idempotency_key: idem,
      };

      fetch('/ai-hub/api/actions/execute/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(body),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          var ok = data.success === true;
          var results = (data.data && data.data.results) || [];
          var first = results[0] || {};
          var innerOk = first.success !== false && (first.success === true || ok);
          if (ok && innerOk) {
            btnEl.innerHTML = '&#10003; ' + (isBatch ? 'OK' : 'Đã áp dụng');
            btnEl.classList.add('opacity-70');
            if (window.GDPToast && GDPToast.success) {
              GDPToast.success(first.message || 'Thành công');
            }
            self.appendLocalMessage({
              role: 'assistant',
              type: 'text',
              content: first.message || 'Đã thực hiện.',
            });
          } else {
            var msg =
              (data.errors && data.errors[0] && data.errors[0].message) ||
              first.message ||
              'Lỗi thực thi action';
            btnEl.disabled = false;
            btnEl.innerHTML = original;
            if (window.GDPToast && GDPToast.error) {
              GDPToast.error(msg);
            } else {
              window.alert(msg);
            }
            self.appendLocalMessage({
              role: 'assistant',
              type: 'error',
              message: msg,
              raw: JSON.stringify(first || data),
            });
          }
        })
        .catch(function () {
          btnEl.disabled = false;
          btnEl.innerHTML = original;
          if (window.GDPToast && GDPToast.error) {
            GDPToast.error('Không gọi được API action');
          }
        });
    },

    appendLocalMessage: function (msg) {
      msg._ts = msg._ts || Date.now();
      this._messages.push(msg);
      this._reindexActions();
      this._syncMsgWindowToTail();
      var els = this._getEls();
      if (!els.messages) return;
      this._render(false);
      try {
        if (window.PluSorHistory) PluSorHistory.save(this._messages);
      } catch (e) {}
    },

    sendMessage: function () {
      var self = this;
      var els = this._getEls();
      if (!els.input) return;
      var pendingImage = this._pendingImage;
      if (!els.input.value.trim() && !pendingImage) return;
      if (pendingImage && pendingImage.uploading) {
        if (window.GDPToast && GDPToast.info) GDPToast.info('Ảnh đang được tải lên.');
        return;
      }
      var text = els.input.value.trim();
      els.input.value = '';
      if (pendingImage) {
        this.appendLocalMessage({
          role: 'user',
          type: 'image',
          content: text,
          image: { url: pendingImage.thumbnailUrl || pendingImage.previewUrl },
        });
      } else {
        this.appendLocalMessage({ role: 'user', type: 'text', content: text });
      }

      var ctx = buildPlusorPageContext();
      var sid = null;
      try {
        sid = localStorage.getItem(SESSION_KEY);
      } catch (e) {}

      if (els.sendBtn) els.sendBtn.disabled = true;
      self.setPlusorActivity(true, 'PluSor đang kết nối…');
      self._showTypingIndicator();
      self
        .sendChatStream({
          message: text,
          page_context: ctx,
          session_id: sid || null,
          image_id: pendingImage && pendingImage.imageId,
          onProgress: function (p) {
            self._hideTypingIndicator();
            if (p && p.kind === 'thinking_chunk') {
              self._injectStreamingThinking(p.text);
              return;
            }
            self.setPlusorActivity(true, self.progressPayloadToLabel(p));
          },
        })
        .then(function (body) {
          self._hideTypingIndicator();
          if (els.sendBtn) els.sendBtn.disabled = false;
          self.setPlusorActivity(false);
          if (!body || !body.success) {
            var errMsg =
              (body && body.errors && body.errors[0] && body.errors[0].message) ||
              'Không gửi được tin nhắn PluSor.';
            self.appendLocalMessage({
              role: 'assistant',
              type: 'error',
              message: errMsg,
            });
            return;
          }
          var data = body.data || {};
          self._plusorMeta = body.meta || null;
          self._renderDebugPanel(body.meta || null);
          if (data.session_id) {
            try {
              localStorage.setItem(SESSION_KEY, data.session_id);
            } catch (e) {}
            self._refreshSessionListIfOpen();
          }
          var payload = data.payload || null;
          if (payload && payload.messages && payload.messages.length) {
            payload.messages.forEach(function (m) {
              self.appendLocalMessage(m);
            });
          } else if (payload) {
            self.update(payload);
          } else {
            self.appendLocalMessage({
              role: 'assistant',
              type: 'text',
              content: 'Không có phản hồi tin nhắn từ luồng AI.',
            });
          }
        })
        .catch(function () {
          self._hideTypingIndicator();
          if (els.sendBtn) els.sendBtn.disabled = false;
          self.setPlusorActivity(false);
          self.appendLocalMessage({
            role: 'assistant',
            type: 'error',
            message: 'Lỗi mạng hoặc server.',
          });
        });
      if (pendingImage) this._clearPendingImage();
    },

    sendUserMessage: function (text) {
      var t = String(text == null ? '' : text).trim();
      if (!t) return;
      var els = this._getEls();
      if (els.input) els.input.value = t;
      this.sendMessage();
    },

    /**
     * Render debug panel từ meta.execution_trace sau khi nhận done event.
     * Panel bị ẩn mặc định, hiện khi user click nút [i] trong header.
     */
    _renderDebugPanel: function (meta) {
      var panel = document.getElementById('plusor-debug-panel');
      var body = document.getElementById('plusor-debug-body');
      if (!panel || !body || !meta) return;
      var trace = meta.execution_trace || [];
      var rows = [];

      function row(label, value) {
        return (
          '<div class="plusor-debug-body-row">' +
          '<span class="plusor-debug-label">' + esc(label) + '</span>' +
          '<span class="plusor-debug-value">' + esc(String(value)) + '</span>' +
          '</div>'
        );
      }

      // Planner
      var planner = null;
      for (var i = 0; i < trace.length; i++) {
        if (trace[i].step === 'planner') { planner = trace[i]; break; }
      }
      if (planner) {
        rows.push(row('Route', planner.route || '—'));
        rows.push(row('Intent', planner.intent || '—'));
        rows.push(row('Confidence', planner.confidence != null ? (planner.confidence * 100).toFixed(0) + '%' : '—'));
        if (planner.reason) rows.push(row('Reason', planner.reason));
      }

      // RAG
      var ragStep = null;
      for (var i = 0; i < trace.length; i++) {
        if (trace[i].step === 'rag_retrieval') { ragStep = trace[i]; break; }
      }
      if (ragStep && ragStep.status === 'retrieved') {
        rows.push(row('RAG chunks', ragStep.chunks_count || 0));
        rows.push(row('RAG ms', ragStep.retrieve_ms || 0));
      }

      // Thinking
      var thinkStep = null;
      for (var i = 0; i < trace.length; i++) {
        if (trace[i].step === 'thinking') { thinkStep = trace[i]; break; }
      }
      if (thinkStep) {
        rows.push(row('Thinking', thinkStep.enabled ? 'enabled (' + thinkStep.budget_tokens + ' tok)' : 'off'));
      }

      // Tool calls
      var toolCalls = [];
      for (var i = 0; i < trace.length; i++) {
        if (trace[i].step === 'tool_call') toolCalls.push(trace[i]);
      }
      if (toolCalls.length) {
        var toolStr = toolCalls.map(function(t) { return (t.tool || '?') + ':' + (t.result_count != null ? t.result_count : t.status); }).join(', ');
        rows.push(row('Tools', toolStr));
      }

      // LLM summary
      rows.push(row('Model', meta.model || '—'));
      if (meta.tokens) rows.push(row('Tokens', meta.tokens));
      if (meta.cost_usd != null) rows.push(row('Cost', '$' + (parseFloat(meta.cost_usd) || 0).toFixed(5)));
      if (meta.latency_ms) rows.push(row('Latency', meta.latency_ms + 'ms'));

      body.innerHTML = rows.join('');
      panel.style.display = '';  // unhide the element
    },

    /** Init debug toggle button. Gọi sau khi panel DOM sẵn sàng. */
    _initDebugToggle: function () {
      var btn = document.getElementById('plusor-debug-toggle');
      var panel = document.getElementById('plusor-debug-panel');
      if (!btn || !panel) return;
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        var isOpen = panel.hasAttribute('open');
        if (isOpen) {
          panel.removeAttribute('open');
          btn.style.opacity = '0.5';
        } else {
          panel.setAttribute('open', '');
          btn.style.opacity = '1';
        }
      });
    },

    _initSessionToggle: function () {
      var self = this;
      var toggleBtn = document.getElementById('plusor-session-toggle');
      var drawer = document.getElementById('plusor-session-drawer');
      var newBtn = document.getElementById('plusor-session-new-btn');
      if (!toggleBtn || !drawer) return;
      toggleBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        if (drawer.style.display === 'none' || !drawer.style.display) {
          self._loadSessions();
          drawer.style.display = '';
          toggleBtn.style.opacity = '1';
        } else {
          drawer.style.display = 'none';
          toggleBtn.style.opacity = '0.5';
        }
      });
      if (newBtn) {
        newBtn.addEventListener('click', function () {
          self._newSession();
        });
      }
    },

    _loadSessions: function () {
      var self = this;
      return fetch('/ai-hub/api/plusor/sessions/', { credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (body) {
          if (!body || !body.success || !body.data) return;
          self._renderSessionDrawer(body.data.sessions || []);
        })
        .catch(function () {});
    },

    _renderSessionDrawer: function (sessions) {
      var list = document.getElementById('plusor-session-list');
      if (!list) return;
      list.innerHTML = '';
      var sid = null;
      try { sid = localStorage.getItem(SESSION_KEY); } catch (e) {}
      if (!sessions.length) {
        var empty = document.createElement('div');
        empty.className = 'plusor-session-item';
        empty.style.cursor = 'default';
        empty.style.opacity = '0.7';
        empty.textContent = 'Chưa có phiên nào';
        list.appendChild(empty);
        return;
      }
      var self = this;
      sessions.forEach(function (s) {
        var row = document.createElement('div');
        row.className = 'plusor-session-item';
        if (s.session_id === sid) row.classList.add('plusor-session-item--active');
        var title = (s.title && String(s.title).trim()) || 'Chat';
        var dateStr = '';
        if (s.last_active_at) {
          try {
            var d = new Date(s.last_active_at);
            dateStr = d.toLocaleDateString('vi-VN', { month: 'short', day: 'numeric' }) + ' ' +
              d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
          } catch (e) {}
        }
        row.innerHTML =
          '<span class="plusor-session-item__title" title="' + escAttr(title) + '">' +
          esc(title.length > 30 ? title.slice(0, 28) + '…' : title) +
          '</span>' +
          (dateStr ? '<span class="plusor-session-item__date">' + esc(dateStr) + '</span>' : '') +
          '<button type="button" class="plusor-session-item__del" aria-label="Xóa phiên">×</button>';
        row.querySelector('.plusor-session-item__title').addEventListener('click', function () {
          self._loadSession(s.session_id);
        });
        var delBtn = row.querySelector('.plusor-session-item__del');
        if (delBtn) {
          delBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            self._deleteSession(s.session_id);
          });
        }
        list.appendChild(row);
      });
    },

    _loadSession: function (sessionId) {
      var self = this;
      try { localStorage.setItem(SESSION_KEY, sessionId); } catch (e) {}
      fetch('/ai-hub/api/plusor/sessions/' + encodeURIComponent(sessionId) + '/messages/', {
        credentials: 'same-origin',
      })
        .then(function (r) { return r.json(); })
        .then(function (body) {
          if (!body || !body.success || !body.data) return;
          var msgs = body.data.messages || [];
          self._messages = msgs.map(function (m) {
            m._ts = m._ts || Date.now();
            return m;
          });
          self._reindexActions();
          self._syncMsgWindowToTail();
          self._render(false);
          self._loadSessions();
          var drawer = document.getElementById('plusor-session-drawer');
          if (drawer) drawer.style.display = 'none';
          var toggleBtn = document.getElementById('plusor-session-toggle');
          if (toggleBtn) toggleBtn.style.opacity = '0.5';
        })
        .catch(function () {});
    },

    _deleteSession: function (sessionId) {
      var self = this;
      fetch('/ai-hub/api/plusor/sessions/' + encodeURIComponent(sessionId) + '/', {
        method: 'DELETE',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': getCsrfToken() },
      })
        .then(function (r) { return r.json(); })
        .then(function (body) {
          if (!body || !body.success) return;
          var curSid = null;
          try { curSid = localStorage.getItem(SESSION_KEY); } catch (e) {}
          if (curSid === sessionId) {
            try { localStorage.removeItem(SESSION_KEY); } catch (e) {}
            self._messages = [];
            self._actions = [];
            self._plusorMeta = null;
            self._msgWindowTail = 0;
            self._render(false);
          }
          self._loadSessions();
        })
        .catch(function () {});
    },

    _newSession: function () {
      try { localStorage.removeItem(SESSION_KEY); } catch (e) {}
      this._messages = [];
      this._actions = [];
      this._plusorMeta = null;
      this._msgWindowTail = 0;
      this._render(false);
      var drawer = document.getElementById('plusor-session-drawer');
      if (drawer) drawer.style.display = 'none';
      var toggleBtn = document.getElementById('plusor-session-toggle');
      if (toggleBtn) toggleBtn.style.opacity = '0.5';
      this._loadSessions();
    },

    _refreshSessionListIfOpen: function () {
      var drawer = document.getElementById('plusor-session-drawer');
      if (drawer && drawer.style.display !== 'none') {
        this._loadSessions();
      }
    },

    /** Render một message (HTML) — dùng chung với trang container optimizer */
    renderMessageRowHtml: function (msg) {
      return messageRowHtml(msg);
    },

    /** Nội dung HTML bên trong hàng tin (assistant/user bubble/card) — dùng trang /ai-hub/chat/ */
    renderAssistantInner: function (msg) {
      return renderMessageInner(msg);
    },

    formatMsgTime: function (ts) {
      return formatMsgTime(ts);
    },

    buildNodeProgressMessage: function (nodeId, nodeLabel, result, parsedJson) {
      return buildNodeProgressMessage(nodeId, nodeLabel, result, parsedJson);
    },

    /** Chuẩn hoá payload v1/v2 */
    normalizePayload: function (p) {
      return normalizeClientPayload(p);
    },

    uploadProductImage: function (file) {
      return uploadProductImage(file);
    },

    openProductDrawer: function (runId, productId) {
      return openProductDrawer(runId, productId);
    },

    _clearPendingImage: function () {
      if (this._pendingImage && this._pendingImage.previewUrl) {
        URL.revokeObjectURL(this._pendingImage.previewUrl);
      }
      this._pendingImage = null;
      var preview = document.getElementById('plusor-image-preview');
      var input = document.getElementById('plusor-image-input');
      if (preview) preview.classList.add('hidden');
      if (input) input.value = '';
    },

    _selectProductImage: function (file) {
      var self = this;
      if (!file) return;
      this._clearPendingImage();
      var previewUrl = URL.createObjectURL(file);
      this._pendingImage = { previewUrl: previewUrl, uploading: true, imageId: null };
      var preview = document.getElementById('plusor-image-preview');
      var image = document.getElementById('plusor-image-preview-img');
      var name = document.getElementById('plusor-image-preview-name');
      if (preview) preview.classList.remove('hidden');
      if (image) image.src = previewUrl;
      if (name) name.textContent = 'Đang tải ' + (file.name || 'ảnh') + '…';
      uploadProductImage(file).then(function (data) {
        if (!self._pendingImage || self._pendingImage.previewUrl !== previewUrl) return;
        self._pendingImage.uploading = false;
        self._pendingImage.imageId = data.image_id;
        self._pendingImage.thumbnailUrl = data.thumbnail_url || previewUrl;
        if (name) name.textContent = file.name || 'Ảnh đã sẵn sàng';
      }).catch(function (error) {
        self._clearPendingImage();
        if (window.GDPToast && GDPToast.error) GDPToast.error(error.message || 'Không tải được ảnh.');
      });
    },

    _initImageInput: function () {
      var self = this;
      var button = document.getElementById('plusor-image-btn');
      var input = document.getElementById('plusor-image-input');
      var remove = document.getElementById('plusor-image-remove');
      var panel = document.getElementById('plusor-panel');
      if (!button || !input) return;
      button.addEventListener('click', function () { input.click(); });
      input.addEventListener('change', function () { self._selectProductImage(input.files && input.files[0]); });
      if (remove) remove.addEventListener('click', function () { self._clearPendingImage(); });
      if (panel) {
        panel.addEventListener('dragover', function (event) {
          if (event.dataTransfer && event.dataTransfer.types.indexOf('Files') >= 0) event.preventDefault();
        });
        panel.addEventListener('drop', function (event) {
          var file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
          if (!file) return;
          event.preventDefault();
          self._selectProductImage(file);
        });
        panel.addEventListener('paste', function (event) {
          var items = event.clipboardData && event.clipboardData.items;
          for (var i = 0; items && i < items.length; i++) {
            if (items[i].type.indexOf('image/') === 0) {
              self._selectProductImage(items[i].getAsFile());
              event.preventDefault();
              break;
            }
          }
        });
      }
    },

    update: function (payload, opts) {
      if (!payload || typeof payload !== 'object') return;
      if (opts && opts.merge === 'optimizer') {
        return this.mergeOptimizerPayload(payload);
      }
      var norm = normalizeClientPayload(payload);
      this._state = norm;
      this._messages = norm.messages ? norm.messages.slice() : [];
      this._reindexActions();
      this._syncMsgWindowToTail();
      this._render(false);
      try {
        if (window.PluSorHistory) PluSorHistory.save(this._messages);
      } catch (e) {}
      try {
        document.dispatchEvent(new CustomEvent('plusor:update', { detail: norm }));
      } catch (e) {}
    },

    /**
     * @param {boolean} preserveScroll — true khi prepend tin cũ (giữ vị trí scroll).
     */
    _render: function (preserveScroll) {
      var els = this._getEls();
      if (!els.messages) return;
      var el = els.messages;
      var msgs = this._messages || [];
      var n = msgs.length;
      if (!n) {
        el.innerHTML = '';
        var userName = readJsonScript('plusor-panel-user-name').trim() || 'bạn';
        var welcomeMsg = {
          role: 'assistant',
          type: 'text',
          content: 'Chào ' + userName + '! 👋\n\nHôm nay mình có thể giúp gì?',
          _ts: Date.now(),
        };
        var wrap = document.createElement('div');
        wrap.innerHTML = messageRowHtml(welcomeMsg);
        var node = wrap.firstElementChild;
        if (node) el.appendChild(node);

        var self = this;
        var chipsRow = document.createElement('div');
        chipsRow.className = 'plusor-welcome__chips';
        chipsRow.id = 'plusor-welcome-chips';
        el.appendChild(chipsRow);

        if (this._welcomeChips && this._welcomeChips.length) {
          this._renderChipsRow(chipsRow);
        } else {
          fetch('/ai-hub/api/plusor/welcome-chips/', { credentials: 'same-origin' })
            .then(function (r) { return r.json(); })
            .then(function (body) {
              if (body && body.success && body.data) {
                self._welcomeChips = body.data.welcome_chips || [];
              }
              if (chipsRow.parentNode) self._renderChipsRow(chipsRow);
            })
            .catch(function () {});
        }
        return;
      }
      if (this._msgWindowStart > n) this._msgWindowStart = 0;
      var start = this._msgWindowStart;
      var prevH = el.scrollHeight;
      var prevTop = el.scrollTop;
      var frag = document.createDocumentFragment();
      if (start > 0) {
        var loadHint = document.createElement('div');
        loadHint.className = 'plusor-load-older';
        loadHint.setAttribute('role', 'status');
        loadHint.textContent = '↑ ' + start + ' tin nhắn phía trên — kéo lên để tải thêm';
        frag.appendChild(loadHint);
      }
      for (var i = start; i < n; i++) {
        var wrap2 = document.createElement('div');
        wrap2.innerHTML = messageRowHtml(msgs[i]);
        var node2 = wrap2.firstElementChild;
        if (node2) frag.appendChild(node2);
      }
      el.innerHTML = '';
      el.appendChild(frag);
      if (preserveScroll) {
        el.scrollTop = el.scrollHeight - prevH + prevTop;
      } else {
        this._scrollMessagesToBottom();
      }
    },

    _renderChipsRow: function (container) {
      var chips = this._welcomeChips || [];
      if (!chips.length) {
        container.style.display = 'none';
        return;
      }
      container.style.display = '';
      var html = '';
      for (var i = 0; i < chips.length; i++) {
        var ch = chips[i] || {};
        var bid = String(ch.id != null ? ch.id : i);
        var lbl = esc(ch.label || '');
        var pr = String(ch.prompt || '');
        var bad = Number(ch.badge) || 0;
        var hasB = bad > 0 ? ' plusor-welcome-chip--has-badge' : '';
        var badgeHtml = bad > 0
          ? '<span class="plusor-welcome-chip__badge">' + esc(String(bad)) + '</span>'
          : '';
        if (ch.focus_input) {
          html +=
            '<button type="button" class="plusor-welcome-chip' + hasB +
            '" data-chip-id="' + escAttr(bid) +
            '" data-plusor-focus-input="1">' +
            '<span class="plusor-welcome-chip__label">' + lbl + '</span>' +
            badgeHtml + '</button>';
        } else {
          html +=
            '<button type="button" class="plusor-welcome-chip' + hasB +
            '" data-chip-id="' + escAttr(bid) +
            '" data-plusor-send-prompt="' + escAttr(pr) + '">' +
            '<span class="plusor-welcome-chip__label">' + lbl + '</span>' +
            badgeHtml + '</button>';
        }
      }
      container.innerHTML = html;
    },

    _init: function () {
      var self = this;
      this._bind();
      this._initSessionToggle();
      this._initImageInput();
      var sid = null;
      try {
        sid = localStorage.getItem(SESSION_KEY);
      } catch (e) {}
      if (sid) {
        fetch('/ai-hub/api/plusor/sessions/' + sid + '/messages/', {
          credentials: 'same-origin',
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (body) {
            var serverMsgs = (body && body.success && body.data && body.data.messages) || [];

            var localMsgs = [];
            try {
              if (window.PluSorHistory) {
                localMsgs = PluSorHistory.load() || [];
              }
            } catch (e) {}

            var merged = serverMsgs.length >= localMsgs.length ? serverMsgs : localMsgs;

            if (merged.length) {
              self._messages = merged.map(function (m) {
                m._ts = m._ts || Date.now();
                return m;
              });
              self._reindexActions();
              self._syncMsgWindowToTail();
              self._render(false);
            } else {
              self._render(false);
            }
          })
          .catch(function () {
            try {
              if (window.PluSorHistory) {
                var saved2 = PluSorHistory.load();
                if (saved2 && saved2.length) {
                  self._messages = saved2;
                  self._reindexActions();
                  self._syncMsgWindowToTail();
                  self._render(false);
                  return;
                }
              }
            } catch (e) {}
            self._render(false);
          });
        return;
      }
      try {
        if (window.PluSorHistory) {
          var saved = PluSorHistory.load();
          if (saved && saved.length) {
            this._messages = saved;
            this._reindexActions();
            this._syncMsgWindowToTail();
            this._render(false);
            return;
          }
        }
      } catch (e) {}
      this._render(false);
    },
  };

  document.addEventListener('DOMContentLoaded', function () {
    window.PluSor._init();
    window.PluSor._initDebugToggle();
  });
})();
