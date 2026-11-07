/**
 * PluSor full-page chat (/ai-hub/chat/) — sessions, SSE stream, welcome chips.
 */
(function () {
  'use strict';

  var SESSION_STORAGE_KEY = 'gdp_plusor_pcp_session';
  var PLUSOR_ASSISTANT_ICON = '/static/sticker/sticker-PLUSOR/plusor.png';
  var _memoriesLoading = false;

  var PCP = {
    currentSessionId: null,
    sessions: [],
    isStreaming: false,
    actionsById: {},
    abortController: null,
    pendingImage: null,
  };

  var COPY_ICON_SVG =
    '<svg xmlns="http://www.w3.org/2000/svg" class="pcp-copy-btn__svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>';

  function getEl(id) {
    return document.getElementById(id);
  }

  function getCsrfToken() {
    var m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

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

  function progressPayloadToLabel(p) {
    if (window.PluSor && typeof window.PluSor.progressPayloadToLabel === 'function') {
      return window.PluSor.progressPayloadToLabel(p);
    }
    return 'PluSor đang xử lý…';
  }

  function scrollToBottom() {
    var box = getEl('pcp-messages');
    if (!box) return;
    requestAnimationFrame(function () {
      box.scrollTop = box.scrollHeight;
    });
  }

  function getPreferredModel() {
    var sel = getEl('pcp-preferred-model');
    return sel && sel.value ? String(sel.value).trim() : '';
  }

  function persistSessionId(sid) {
    PCP.currentSessionId = sid || null;
    try {
      if (sid) localStorage.setItem(SESSION_STORAGE_KEY, sid);
      else localStorage.removeItem(SESSION_STORAGE_KEY);
    } catch (e) {}
  }

  function clearMessageRows() {
    var box = getEl('pcp-messages');
    if (!box) return;
    var welcome = getEl('pcp-welcome');
    var nodes = box.querySelectorAll('.plusor-msg-row, .pcp-msg-row');
    for (var i = 0; i < nodes.length; i++) nodes[i].remove();
    if (welcome && welcome.parentNode === box) {
      box.appendChild(welcome);
    }
    PCP.actionsById = {};
  }

  function syncChipsBar() {
    var bar = getEl('pcp-chips-bar');
    var welcome = getEl('pcp-welcome');
    var container = getEl('pcp-chips');
    if (!bar || !welcome || !container) return;
    var show = !welcome.hidden && container.children.length > 0;
    bar.hidden = !show;
  }

  function showWelcomeScreen() {
    var w = getEl('pcp-welcome');
    if (w) w.hidden = false;
    syncChipsBar();
  }

  function hideWelcomeScreen() {
    var w = getEl('pcp-welcome');
    if (w) w.hidden = true;
    var bar = getEl('pcp-chips-bar');
    if (bar) bar.hidden = true;
  }

  function hasConversation() {
    return getEl('pcp-messages') && getEl('pcp-messages').querySelector('.plusor-msg-row, .pcp-msg-row');
  }

  function updateSessionTitleDisplay() {
    var el = getEl('pcp-session-title');
    if (!el) return;
    if (!PCP.currentSessionId) {
      el.textContent = 'PluSor';
      return;
    }
    var sid = PCP.currentSessionId;
    var hit = null;
    for (var i = 0; i < PCP.sessions.length; i++) {
      if (PCP.sessions[i].session_id === sid) {
        hit = PCP.sessions[i];
        break;
      }
    }
    var t = (hit && hit.title && String(hit.title).trim()) || 'Phiên chat';
    el.textContent = t.length > 42 ? t.slice(0, 40) + '…' : t;
  }

  function syncModelSelectorToSession(sessionId) {
    var sel = getEl('pcp-preferred-model');
    if (!sel) return;
    if (!sessionId) {
      sel.value = '';
      return;
    }
    var hit = null;
    for (var i = 0; i < PCP.sessions.length; i++) {
      if (PCP.sessions[i].session_id === sessionId) {
        hit = PCP.sessions[i];
        break;
      }
    }
    var pm = hit && hit.preferred_model != null ? String(hit.preferred_model).trim() : '';
    if (!pm) {
      sel.value = '';
      return;
    }
    var found = false;
    for (var j = 0; j < sel.options.length; j++) {
      if (sel.options[j].value === pm) {
        found = true;
        break;
      }
    }
    sel.value = found ? pm : '';
  }

  function registerActionsFromMessages(msgs) {
    PCP.actionsById = PCP.actionsById || {};
    (msgs || []).forEach(function (m) {
      if (m && m.type === 'action' && (m.action_id || m.id)) {
        var id = m.action_id || m.id;
        PCP.actionsById[id] = {
          id: id,
          label: m.label || id,
          type: m.action_type || 'api_call',
          payload: m.payload || {},
          confidence: m.confidence,
          impact_estimate: m.impact_estimate,
          risk: m.risk,
        };
      }
    });
  }

  function renderThinkingBlock(msg) {
    var meta = msg.meta || {};
    var label = esc(meta.label || 'Quá trình suy luận');
    var budgetTokens = meta.budget_tokens || 0;
    var isStreaming = meta.streaming !== false;
    var badgeHtml = budgetTokens > 0 ? '<span class="pcp-thinking-badge">' + esc(String(budgetTokens) + ' tok') + '</span>' : '';
    var streamingClass = isStreaming ? ' pcp-thinking-block--streaming' : '';
    var inner = plusorMarkdownToSafeHtml(String(msg.content || ''));
    return (
      '<div class="pcp-thinking-block' + streamingClass + ' pcp-thinking-block--open" onclick="this.classList.toggle(\'pcp-thinking-block--open\')">' +
      '<div class="pcp-thinking-header">' +
      '<span class="pcp-thinking-icon">' +
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M6 4l4 4-4 4"/></svg>' +
      '</span>' +
      '<span>' + label + '</span>' +
      '<span class="pcp-thinking-pulse"></span>' +
      badgeHtml +
      '</div>' +
      '<div class="pcp-thinking-body">' +
      '<div class="pcp-thinking-content pcp-md">' + inner + '</div>' +
      '</div>' +
      '</div>'
    );
  }

  var _streamingThinkingEl = null;
  function injectStreamingThinking(text) {
    var box = getEl('pcp-messages');
    if (!box) return;
    if (_streamingThinkingEl && _streamingThinkingEl.parentNode) {
      _streamingThinkingEl.parentNode.removeChild(_streamingThinkingEl);
    }
    var t = String(text || '').trim();
    if (!t) return;
    var thMsg = { role: 'assistant', type: 'thinking', content: t, meta: { streaming: true, label: 'Đang suy nghĩ...', collapsible: true } };
    var html = '<div class="pcp-msg-row pcp-msg-row--assistant">' +
      '<div class="pcp-msg-body">' +
      renderThinkingBlock(thMsg) +
      '</div></div>';
    var wrap = document.createElement('div');
    wrap.innerHTML = html;
    var node = wrap.firstElementChild;
    if (node) {
      box.appendChild(node);
      _streamingThinkingEl = node;
      var block = node.querySelector('.pcp-thinking-block');
      if (block) block.classList.add('pcp-thinking-block--open');
      box.scrollTop = box.scrollHeight;
    }
  }

  function safeJsonStringify(obj) {
    try {
      return JSON.stringify(obj, null, 2);
    } catch (e) {
      return String(obj);
    }
  }

  function renderToolCallBlock(msg) {
    var name = esc(msg.tool_name || msg.name || 'tool');
    var args = msg.tool_args != null ? msg.tool_args : msg.content;
    var result = msg.result;
    var argsStr = esc(safeJsonStringify(args));
    var resBlock = '';
    if (result !== undefined && result !== null) {
      resBlock =
        '<hr style="border:none;border-top:1px solid var(--por-border2);margin:10px 0">' +
        '<pre>' +
        esc(safeJsonStringify(result)) +
        '</pre>';
    }
    return (
      '<details class="pcp-tool-call">' +
      '<summary class="pcp-tool-call__header">' +
      '<span class="pcp-tool-call__icon" aria-hidden="true">⚙</span>' +
      '<span class="pcp-tool-call__name">' +
      name +
      '</span>' +
      '</summary>' +
      '<div class="pcp-tool-call__body"><pre>' +
      argsStr +
      '</pre>' +
      resBlock +
      '</div>' +
      '</details>'
    );
  }

  function appendAssistantCustomRow(htmlInner) {
    var box = getEl('pcp-messages');
    if (!box) return;
    var row = document.createElement('div');
    row.className = 'pcp-msg-row pcp-msg-row--assistant';
    row.innerHTML =
      '<div class="pcp-msg-avatar" aria-hidden="true">' +
      '<img src="' +
      escAttr(PLUSOR_ASSISTANT_ICON) +
      '" alt="" width="32" height="32" loading="lazy" decoding="async" />' +
      '</div>' +
      '<div class="pcp-msg-content">' +
      htmlInner +
      '</div>';
    box.appendChild(row);
    scrollToBottom();
  }

  function attachCopyButtonToAssistantTextBubble(node) {
    if (!node) return;
    var bubble = node.querySelector('.plusor-msg-bubble');
    if (!bubble) return;
    var copyBtn = document.createElement('button');
    copyBtn.type = 'button';
    copyBtn.className = 'pcp-copy-btn';
    copyBtn.title = 'Sao chép';
    copyBtn.setAttribute('aria-label', 'Sao chép tin nhắn');
    copyBtn.innerHTML = COPY_ICON_SVG;
    copyBtn.addEventListener('click', function () {
      var txt = bubble.innerText || bubble.textContent || '';
      if (!txt.trim()) return;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(txt).then(
          function () {
            copyBtn.classList.add('pcp-copy-btn--done');
            setTimeout(function () {
              copyBtn.classList.remove('pcp-copy-btn--done');
            }, 1500);
          },
          function () {}
        );
      }
    });
    bubble.appendChild(copyBtn);
  }

  function appendMessage(msg) {
    var role = String(msg.role || 'assistant').toLowerCase();
    var t = msg.type || 'text';
    var box = getEl('pcp-messages');
    if (!box || !window.PluSor || typeof window.PluSor.renderMessageRowHtml !== 'function') return;

    if (role === 'assistant' && t === 'thinking') {
      appendAssistantCustomRow(renderThinkingBlock(msg));
      return;
    }
    if (role === 'assistant' && t === 'tool_call') {
      appendAssistantCustomRow(renderToolCallBlock(msg));
      return;
    }

    var wrap = document.createElement('div');
    wrap.innerHTML = window.PluSor.renderMessageRowHtml(msg);
    var node = wrap.firstElementChild;
    if (node) box.appendChild(node);
    if (role === 'assistant' && t === 'text' && node) {
      attachCopyButtonToAssistantTextBubble(node);
    }
    scrollToBottom();
  }

  function renderSessionList() {
    var list = getEl('pcp-session-list');
    if (!list) return;
    list.innerHTML = '';
    var sessions = PCP.sessions || [];
    if (!sessions.length) {
      var empty = document.createElement('div');
      empty.className = 'pcp-session-item';
      empty.style.cursor = 'default';
      empty.style.opacity = '0.7';
      empty.textContent = 'Chưa có phiên nào';
      list.appendChild(empty);
      return;
    }
    sessions.forEach(function (s) {
      var sid = s.session_id;
      var row = document.createElement('div');
      row.className = 'pcp-session-item';
      if (sid === PCP.currentSessionId) row.classList.add('pcp-session-item--active');
      var title = (s.title && String(s.title).trim()) || 'Chat';
      row.innerHTML =
        '<span class="pcp-session-item__title" title="' +
        escAttr(title) +
        '">' +
        esc(title.length > 36 ? title.slice(0, 34) + '…' : title) +
        '</span>' +
        '<button type="button" class="pcp-session-item__del" data-pcp-session-del="' +
        escAttr(sid) +
        '" aria-label="Xóa phiên">×</button>';
      row.querySelector('.pcp-session-item__title').addEventListener('click', function () {
        loadSession(sid);
        if (typeof window.__pcpCloseMobileSidebar === 'function') window.__pcpCloseMobileSidebar();
      });
      var delBtn = row.querySelector('[data-pcp-session-del]');
      if (delBtn) {
        delBtn.addEventListener('click', function (e) {
          e.stopPropagation();
          deleteSession(sid);
        });
      }
      list.appendChild(row);
    });
  }

  function loadSessions() {
    return fetch('/ai-hub/api/plusor/sessions/', { credentials: 'same-origin' })
      .then(function (r) {
        return r.json();
      })
      .then(function (body) {
        if (!body || !body.success || !body.data) return;
        PCP.sessions = body.data.sessions || [];
        renderSessionList();
        updateSessionTitleDisplay();
      })
      .catch(function () {});
  }

  function loadSession(sessionId) {
    PCP.currentSessionId = sessionId;
    persistSessionId(sessionId);
    syncModelSelectorToSession(sessionId);
    hideWelcomeScreen();
    clearMessageRows();
    return fetch('/ai-hub/api/plusor/sessions/' + encodeURIComponent(sessionId) + '/messages/', {
      credentials: 'same-origin',
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (body) {
        if (!body || !body.success || !body.data) {
          persistSessionId(null);
          clearMessageRows();
          showWelcomeScreen();
          syncModelSelectorToSession(null);
          return;
        }
        var msgs = body.data.messages || [];
        msgs.forEach(function (m) {
          appendMessage(m);
        });
        if (!msgs.length) showWelcomeScreen();
        scrollToBottom();
        renderSessionList();
        updateSessionTitleDisplay();
      })
      .catch(function () {
        persistSessionId(null);
        clearMessageRows();
        showWelcomeScreen();
        syncModelSelectorToSession(null);
      });
  }

  function deleteSession(sessionId) {
    return fetch('/ai-hub/api/plusor/sessions/' + encodeURIComponent(sessionId) + '/', {
      method: 'DELETE',
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': getCsrfToken() },
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (body) {
        if (!body || !body.success) return;
        PCP.sessions = (PCP.sessions || []).filter(function (s) {
          return s.session_id !== sessionId;
        });
        renderSessionList();
        if (PCP.currentSessionId === sessionId) {
          persistSessionId(null);
          clearMessageRows();
          showWelcomeScreen();
          updateSessionTitleDisplay();
          syncModelSelectorToSession(null);
        }
      })
      .catch(function () {});
  }

  function loadModels() {
    return fetch('/ai-hub/api/registry/models/', { credentials: 'same-origin' })
      .then(function (r) {
        return r.json();
      })
      .then(function (body) {
        if (!body || !body.success || !body.data) return;
        var sel = getEl('pcp-preferred-model');
        if (!sel) return;
        while (sel.options.length > 1) sel.remove(1);
        var groups = {};
        (body.data.models || []).forEach(function (mc) {
          if (!mc || !mc.is_active) return;
          var prov = mc.provider;
          var p = (prov && typeof prov === 'object' && prov.slug) || 'other';
          if (!groups[p]) groups[p] = [];
          groups[p].push(mc);
        });
        var GDP_AI = window.GDP_AI || {};
        Object.keys(groups)
          .sort()
          .forEach(function (p) {
            var og = document.createElement('optgroup');
            og.label = (GDP_AI.providerLabel && GDP_AI.providerLabel(p)) || p;
            groups[p].forEach(function (mc) {
              var opt = document.createElement('option');
              var mid = mc.model_id != null ? String(mc.model_id).trim() : '';
              if (!mid) return;
              opt.value = mid;
              var label = (mc.display_name && String(mc.display_name).trim()) || mid;
              opt.textContent = label;
              if (mc.is_default) opt.textContent += ' (mặc định)';
              og.appendChild(opt);
            });
            if (og.childNodes.length) sel.appendChild(og);
          });
        syncModelSelectorToSession(PCP.currentSessionId);
      })
      .catch(function () {});
  }

  function loadWelcomeChips() {
    return fetch('/ai-hub/api/plusor/welcome-chips/', { credentials: 'same-origin' })
      .then(function (r) {
        return r.json();
      })
      .then(function (body) {
        if (!body || !body.success || !body.data) return;
        var chips = body.data.welcome_chips || [];
        var container = getEl('pcp-chips');
        var titleEl = document.querySelector('.pcp-welcome__title');
        var name = (body.data.user_display_name || '').trim();
        if (titleEl) {
          titleEl.textContent = name ? 'Xin chào, ' + name + ' 👋' : 'Xin chào 👋';
        }
        if (!container) return;
        container.innerHTML = '';
        chips.forEach(function (chip) {
          var c = chip || {};
          var label = c.label || c.prompt || String(c);
          var prompt = c.prompt != null ? String(c.prompt) : String(label);
          var btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'pcp-chip';
          btn.textContent = label;
          btn.addEventListener('click', function () {
            sendMessage(prompt);
          });
          container.appendChild(btn);
        });
        syncChipsBar();
      })
      .catch(function () {});
  }

  function showActivity(text) {
    var wrap = getEl('pcp-activity');
    var lab = getEl('pcp-activity-label');
    if (wrap) wrap.hidden = false;
    if (lab && text != null) lab.textContent = text;
  }

  function hideActivity() {
    var wrap = getEl('pcp-activity');
    if (wrap) wrap.hidden = true;
  }

  function resetStreamUI() {
    PCP.isStreaming = false;
    PCP.abortController = null;
    var stopBtn = getEl('pcp-stop');
    var sendBtn = getEl('pcp-send');
    if (stopBtn) stopBtn.hidden = true;
    if (sendBtn) {
      sendBtn.hidden = false;
      sendBtn.disabled = false;
    }
    hideActivity();
  }

  function applyAction(action, btnEl) {
    var original = btnEl.innerHTML;
    btnEl.disabled = true;
    btnEl.innerHTML = '<span class="inline-block animate-spin">&#x21BB;</span>';

    var ctx = buildPlusorPageContext();
    var idem = 'pcp_' + (action.id || 'act') + '_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
    var body = {
      action_id: action.id,
      payload: action.payload || {},
      context: ctx,
      flow_run_id: '',
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
          btnEl.innerHTML = '&#10003; Đã áp dụng';
          btnEl.classList.add('opacity-70');
          if (window.GDPToast && GDPToast.success) {
            GDPToast.success(first.message || 'Thành công');
          }
          appendMessage({ role: 'assistant', type: 'text', content: first.message || 'Đã thực hiện.' });
        } else {
          var msg =
            (data.errors && data.errors[0] && data.errors[0].message) ||
            first.message ||
            'Lỗi thực thi action';
          btnEl.disabled = false;
          btnEl.innerHTML = original;
          if (window.GDPToast && GDPToast.error) {
            GDPToast.error(msg);
          }
          appendMessage({
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
  }

  function sendMessage(text) {
    var t = String(text == null ? '' : text).trim();
    var pendingImage = PCP.pendingImage;
    if ((!t && !pendingImage) || PCP.isStreaming) return;
    if (pendingImage && pendingImage.uploading) {
      if (window.GDPToast && GDPToast.info) GDPToast.info('Ảnh đang được tải lên.');
      return;
    }
    if (!window.PluSor || typeof window.PluSor.sendChatStream !== 'function') {
      if (window.GDPToast && GDPToast.error) GDPToast.error('PluSor chưa sẵn sàng (thiếu plusor.js).');
      return;
    }

    PCP.isStreaming = true;
    PCP.abortController = new AbortController();
    hideWelcomeScreen();
    appendMessage(pendingImage ? {
      role: 'user',
      type: 'image',
      content: t,
      image: { url: pendingImage.thumbnailUrl || pendingImage.previewUrl },
    } : { role: 'user', type: 'text', content: t });
    showActivity('Đang kết nối…');

    var ctx = buildPlusorPageContext();
    var sendBtn = getEl('pcp-send');
    var stopBtn = getEl('pcp-stop');
    var inp = getEl('pcp-input');
    if (stopBtn) stopBtn.hidden = false;
    if (sendBtn) {
      sendBtn.hidden = true;
      sendBtn.disabled = true;
    }

    var pm = getPreferredModel();

    window.PluSor
      .sendChatStream({
        message: t,
        page_context: ctx,
        session_id: PCP.currentSessionId || null,
        preferred_model: pm || undefined,
        image_id: pendingImage && pendingImage.imageId,
        signal: PCP.abortController.signal,
        onProgress: function (p) {
          if (p && p.kind === 'thinking_chunk') {
            injectStreamingThinking(p.text);
            return;
          }
          showActivity(progressPayloadToLabel(p));
        },
      })
      .then(function (body) {
        resetStreamUI();
        if (!body || !body.success) {
          var errMsg =
            (body && body.errors && body.errors[0] && body.errors[0].message) ||
            'Không gửi được tin nhắn PluSor.';
          appendMessage({ role: 'assistant', type: 'error', message: errMsg });
          return;
        }
        var data = body.data || {};
        if (data.session_id) {
          persistSessionId(data.session_id);
        }
        var payloadObj = data.payload || null;
        if (payloadObj && Array.isArray(payloadObj.messages) && payloadObj.messages.length) {
          registerActionsFromMessages(payloadObj.messages);
          payloadObj.messages.forEach(function (m) {
            appendMessage(m);
          });
        } else if (payloadObj) {
          var norm = normalizeClientPayload(payloadObj);
          registerActionsFromMessages(norm.messages || []);
          (norm.messages || []).forEach(function (m) {
            appendMessage(m);
          });
        } else {
          appendMessage({
            role: 'assistant',
            type: 'text',
            content: 'Không có phản hồi tin nhắn từ luồng AI.',
          });
        }
        loadSessions().then(function () {
          syncModelSelectorToSession(PCP.currentSessionId);
          scrollToBottom();
        });
      })
      .catch(function (err) {
        resetStreamUI();
        if (err && err.name === 'AbortError') return;
        appendMessage({ role: 'assistant', type: 'error', message: 'Lỗi mạng hoặc server.' });
      });

    if (pendingImage) clearPendingImage();

    if (inp) {
      inp.value = '';
      inp.style.height = 'auto';
    }
  }

  function clearPendingImage() {
    if (PCP.pendingImage && PCP.pendingImage.previewUrl) {
      URL.revokeObjectURL(PCP.pendingImage.previewUrl);
    }
    PCP.pendingImage = null;
    var preview = getEl('pcp-image-preview');
    var input = getEl('pcp-image-input');
    if (preview) preview.classList.add('hidden');
    if (input) input.value = '';
  }

  function selectProductImage(file) {
    if (!file || !window.PluSor || typeof window.PluSor.uploadProductImage !== 'function') return;
    clearPendingImage();
    var previewUrl = URL.createObjectURL(file);
    PCP.pendingImage = { previewUrl: previewUrl, uploading: true, imageId: null };
    var preview = getEl('pcp-image-preview');
    var image = getEl('pcp-image-preview-img');
    var name = getEl('pcp-image-preview-name');
    if (preview) preview.classList.remove('hidden');
    if (image) image.src = previewUrl;
    if (name) name.textContent = 'Đang tải ' + (file.name || 'ảnh') + '…';
    window.PluSor.uploadProductImage(file).then(function (data) {
      if (!PCP.pendingImage || PCP.pendingImage.previewUrl !== previewUrl) return;
      PCP.pendingImage.uploading = false;
      PCP.pendingImage.imageId = data.image_id;
      PCP.pendingImage.thumbnailUrl = data.thumbnail_url || previewUrl;
      if (name) name.textContent = file.name || 'Ảnh đã sẵn sàng';
    }).catch(function (error) {
      clearPendingImage();
      if (window.GDPToast && GDPToast.error) GDPToast.error(error.message || 'Không tải được ảnh.');
    });
  }

  function setupInputHandlers() {
    var input = getEl('pcp-input');
    var send = getEl('pcp-send');
    var stop = getEl('pcp-stop');
    if (!input || !send) return;

    if (stop) {
      stop.addEventListener('click', function () {
        if (PCP.abortController) PCP.abortController.abort();
      });
    }

    input.addEventListener('input', function () {
      input.style.height = 'auto';
      input.style.height = Math.min(input.scrollHeight, 200) + 'px';
    });

    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage(input.value);
      }
    });

    send.addEventListener('click', function () {
      sendMessage(input.value);
    });

    var imageButton = getEl('pcp-image-btn');
    var imageInput = getEl('pcp-image-input');
    var imageRemove = getEl('pcp-image-remove');
    var inputShell = document.querySelector('.pcp-input-shell');
    if (imageButton && imageInput) {
      imageButton.addEventListener('click', function () { imageInput.click(); });
      imageInput.addEventListener('change', function () {
        selectProductImage(imageInput.files && imageInput.files[0]);
      });
      if (imageRemove) imageRemove.addEventListener('click', clearPendingImage);
      if (inputShell) {
        inputShell.addEventListener('dragover', function (event) {
          if (event.dataTransfer && event.dataTransfer.types.indexOf('Files') >= 0) event.preventDefault();
        });
        inputShell.addEventListener('drop', function (event) {
          var file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
          if (!file) return;
          event.preventDefault();
          selectProductImage(file);
        });
        inputShell.addEventListener('paste', function (event) {
          var items = event.clipboardData && event.clipboardData.items;
          for (var i = 0; items && i < items.length; i++) {
            if (items[i].type.indexOf('image/') === 0) {
              selectProductImage(items[i].getAsFile());
              event.preventDefault();
              break;
            }
          }
        });
      }
    }
  }

  function setupSidebarHandlers() {
    var toggle = getEl('pcp-sidebar-toggle');
    var side = getEl('pcp-sidebar');
    var backdrop = getEl('pcp-sidebar-backdrop');
    var newChat = getEl('pcp-new-chat');
    var memBtn = getEl('pcp-memories-btn');
    var memPanel = getEl('pcp-memory-panel');
    var memClose = getEl('pcp-memory-close');
    var mainEl = getEl('pcp-main');

    function openMemoryPanel() {
      if (memPanel) memPanel.hidden = false;
      if (mainEl) mainEl.classList.add('pcp-main--memory-open');
      loadMemories();
    }

    function closeMemoryPanel() {
      if (memPanel) memPanel.hidden = true;
      if (mainEl) mainEl.classList.remove('pcp-main--memory-open');
    }

    function openSidebar() {
      if (side) side.classList.add('pcp-sidebar--open');
      if (backdrop) backdrop.hidden = false;
    }

    window.__pcpCloseMobileSidebar = function () {
      if (side) side.classList.remove('pcp-sidebar--open');
      if (backdrop) backdrop.hidden = true;
    };

    if (toggle) {
      toggle.addEventListener('click', function () {
        if (window.innerWidth < 768) {
          if (side && side.classList.contains('pcp-sidebar--open')) window.__pcpCloseMobileSidebar();
          else openSidebar();
        } else {
          var root = getEl('pcp-root');
          if (root) {
            var isCollapsed = root.classList.toggle('pcp-root--sidebar-collapsed');
            try {
              localStorage.setItem('gdp_plusor_pcp_sidebar_collapsed', isCollapsed ? '1' : '0');
            } catch (e) {}
          }
        }
      });
    }
    if (backdrop) {
      backdrop.addEventListener('click', function () {
        window.__pcpCloseMobileSidebar();
      });
    }

    if (newChat) {
      newChat.addEventListener('click', function () {
        persistSessionId(null);
        clearMessageRows();
        showWelcomeScreen();
        renderSessionList();
        updateSessionTitleDisplay();
        syncModelSelectorToSession(null);
        window.__pcpCloseMobileSidebar();
      });
    }

    if (memBtn) {
      memBtn.addEventListener('click', function () {
        openMemoryPanel();
      });
    }
    if (memClose) {
      memClose.addEventListener('click', function () {
        closeMemoryPanel();
      });
    }

    var memList = getEl('pcp-memory-list');
    if (memList) {
      memList.addEventListener('click', function (e) {
        var btn = e.target.closest('.pcp-memory-del');
        if (!btn || !memList.contains(btn)) return;
        var memId = btn.getAttribute('data-mem-id');
        if (!memId) return;
        btn.disabled = true;
        fetch('/ai-hub/api/plusor/memories/' + encodeURIComponent(memId) + '/', {
          method: 'DELETE',
          credentials: 'same-origin',
          headers: { 'X-CSRFToken': getCsrfToken() },
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (body) {
            if (body && body.success) {
              var item = btn.closest('.pcp-memory-item');
              if (item) item.remove();
              if (memList && !memList.querySelector('.pcp-memory-item')) {
                memList.innerHTML =
                  '<p class="pcp-memory-meta" style="padding:12px">Chưa có bộ nhớ nào.</p>';
              }
            } else {
              btn.disabled = false;
            }
          })
          .catch(function () {
            btn.disabled = false;
          });
      });
    }
  }

  function loadMemories() {
    if (_memoriesLoading) return Promise.resolve();
    _memoriesLoading = true;
    return fetch('/ai-hub/api/plusor/memories/', { credentials: 'same-origin' })
      .then(function (r) {
        return r.json();
      })
      .then(function (body) {
        if (!body || !body.success || !body.data) return;
        var list = getEl('pcp-memory-list');
        if (!list) return;
        list.innerHTML = '';
        var memories = body.data.memories || [];
        if (!memories.length) {
          list.innerHTML = '<p class="pcp-memory-meta" style="padding:12px">Chưa có bộ nhớ nào.</p>';
          return;
        }
        memories.forEach(function (mem) {
          var item = document.createElement('div');
          item.className = 'pcp-memory-item';
          var conf = mem.confidence != null ? Math.round(Number(mem.confidence) * 100) : '—';
          item.innerHTML =
            '<p class="pcp-memory-text">' +
            esc(mem.memory_text || '') +
            '</p>' +
            '<div class="pcp-memory-footer">' +
            '<span class="pcp-memory-meta">' +
            esc(mem.memory_type || '') +
            ' · ' +
            esc(conf) +
            '%</span>' +
            '<button type="button" class="pcp-memory-del" data-mem-id="' +
            escAttr(mem.id) +
            '" aria-label="Xóa bộ nhớ">✕</button>' +
            '</div>';
          list.appendChild(item);
        });
      })
      .catch(function () {})
      .finally(function () {
        _memoriesLoading = false;
      });
  }

  function setupMessageActions() {
    var box = getEl('pcp-messages');
    if (!box) return;
    box.addEventListener('click', function (e) {
      var btn = e.target.closest('.plusor-exec-btn');
      if (!btn || !box.contains(btn)) return;
      var aid = btn.getAttribute('data-plusor-action-id') || btn.getAttribute('data-action-index');
      var act = aid ? PCP.actionsById[aid] : null;
      if (!act) return;
      e.preventDefault();
      applyAction(act, btn);
    });
  }

  function tryRestoreSession() {
    var sid = null;
    try {
      sid = localStorage.getItem(SESSION_STORAGE_KEY);
    } catch (e) {}
    if (sid) {
      return loadSession(sid).catch(function () {
        persistSessionId(null);
        showWelcomeScreen();
        syncModelSelectorToSession(null);
      });
    }
    showWelcomeScreen();
    return Promise.resolve();
  }

  document.addEventListener('DOMContentLoaded', function () {
    var root = getEl('pcp-root');
    if (!root) return;

    if (window.innerWidth >= 768) {
      try {
        if (localStorage.getItem('gdp_plusor_pcp_sidebar_collapsed') === '1') {
          root.classList.add('pcp-root--sidebar-collapsed');
        }
      } catch (e) {}
    }

    resetStreamUI();
    setupInputHandlers();
    setupSidebarHandlers();
    setupMessageActions();

    Promise.all([loadSessions(), loadWelcomeChips(), loadModels()])
      .then(function () {
        return tryRestoreSession();
      })
      .then(function () {
        if (!hasConversation()) showWelcomeScreen();
        else hideWelcomeScreen();
      });
  });
})();
