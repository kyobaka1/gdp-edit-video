/**
 * PluSor chat persistence — localStorage, 7-day TTL, ~200KB cap.
 */
(function () {
  'use strict';

  var TTL_MS = 7 * 24 * 3600 * 1000;
  var MAX_MESSAGES = 50;
  var MAX_BYTES = 200 * 1024;

  function _key() {
    try {
      return 'plusor_chat_' + btoa(window.location.pathname).replace(/[^a-zA-Z0-9]/g, '').slice(0, 40);
    } catch (e) {
      return 'plusor_chat_fallback';
    }
  }

  var SERIAL_KEYS = [
    'role',
    'type',
    'content',
    'title',
    'severity',
    'sku',
    'image',
    'action_id',
    'id',
    'label',
    'payload',
    'confidence',
    'impact_estimate',
    'risk',
    'action_type',
    'insight_type',
    'message',
    'raw',
    '_ts',
    'meta',
    'name',
  ];

  function serializeOne(m) {
    if (!m || typeof m !== 'object') return null;
    var o = {};
    for (var i = 0; i < SERIAL_KEYS.length; i++) {
      var k = SERIAL_KEYS[i];
      if (m[k] !== undefined && m[k] !== null) o[k] = m[k];
    }
    return o;
  }

  function trimToSize(messages) {
    var list = messages.slice(-MAX_MESSAGES);
    while (list.length > 0) {
      var json = JSON.stringify({
        v: 1,
        ts: Date.now(),
        messages: list,
      });
      if (json.length <= MAX_BYTES) return json;
      list = list.slice(1);
    }
    return JSON.stringify({ v: 1, ts: Date.now(), messages: [] });
  }

  window.PluSorHistory = {
    TTL_MS: TTL_MS,
    MAX_MESSAGES: MAX_MESSAGES,

    _key: _key,

    save: function (messages) {
      if (!messages || !messages.length) return;
      try {
        var trimmed = messages.slice(-MAX_MESSAGES).map(serializeOne).filter(Boolean);
        var json = trimToSize(trimmed);
        if (json && json.length <= MAX_BYTES) {
          localStorage.setItem(_key(), json);
        }
      } catch (e) {
        try {
          localStorage.removeItem(_key());
        } catch (e2) {}
      }
    },

    load: function () {
      try {
        var raw = localStorage.getItem(_key());
        if (!raw) return null;
        var data = JSON.parse(raw);
        if (!data || typeof data !== 'object') return null;
        var ts = data.ts;
        if (typeof ts !== 'number' || Date.now() - ts > TTL_MS) {
          localStorage.removeItem(_key());
          return null;
        }
        var msgs = data.messages;
        if (!Array.isArray(msgs)) return null;
        return msgs;
      } catch (e) {
        return null;
      }
    },

    clear: function () {
      try {
        localStorage.removeItem(_key());
      } catch (e) {}
    },
  };
})();
