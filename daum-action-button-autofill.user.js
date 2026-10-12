// ==UserScript==
// @name         다음 채널 스튜디오 - 액션 버튼 자동 채우기
// @namespace    https://github.com/assxq/-
// @version      1.0.0
// @description  영상 업로드 화면의 "액션 버튼" 문구/링크 입력란을 자동으로 채웁니다.
// @match        https://channel.daum.net/studio/*
// @grant        GM_getValue
// @grant        GM_setValue
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  const DEFAULT_TEXT = '영상 더보기';
  const load = (k, d) => (typeof GM_getValue === 'function' ? GM_getValue(k, d) : d);
  const save = (k, v) => typeof GM_setValue === 'function' && GM_setValue(k, v);

  // React/Vue 등이 값 변경을 인식하도록 네이티브 setter + 이벤트 발생
  function setValue(el, value) {
    const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, value);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    el.dispatchEvent(new Event('blur', { bubbles: true }));
  }

  // "액션 버튼" 라벨 아래의 입력란 2개(문구, 링크)를 찾는다
  function findFields() {
    // 가장 확실한 방법: placeholder로 찾기
    const t = document.querySelector('input[placeholder^="버튼명"]');
    const u = document.querySelector('input[placeholder^="URL"]');
    if (t && u) return { text: t, url: u };
    const label = [...document.querySelectorAll('label, strong, span, h3, h4, dt, p, div')]
      .find((n) => n.children.length === 0 && n.textContent.trim() === '액션 버튼');
    if (!label) return null;
    let box = label.parentElement;
    for (let i = 0; box && i < 6; i++, box = box.parentElement) {
      const inputs = [...box.querySelectorAll('input[type="text"], input:not([type]), input[type="url"]')]
        .filter((e) => e.offsetParent !== null);
      if (inputs.length >= 2) return { text: inputs[0], url: inputs[1] };
    }
    return null;
  }

  function fill(text, url) {
    const f = findFields();
    if (!f) return false;
    setValue(f.text, text);
    setValue(f.url, url);
    return true;
  }

  // ---- 작은 컨트롤 패널 ----
  console.log('[액션버튼 자동채우기] 시작');
  const el = (tag, css, props) => {
    const e = document.createElement(tag);
    if (css) e.style.cssText = css;
    Object.assign(e, props || {});
    return e;
  };
  const field =
    'width:100%;box-sizing:border-box;height:40px;padding:0 12px;margin-bottom:8px;border:1px solid #dde3ea;' +
    'border-radius:8px;background:#f1f5f9;font-size:14px;color:#222;outline:none';

  const panel = el('div',
    'position:fixed;right:16px;bottom:196px;z-index:2147483647;background:#fff;border:1px solid #e2e5ea;' +
    'border-radius:16px;padding:16px;font:14px -apple-system,"Segoe UI",sans-serif;color:#222;' +
    'box-shadow:0 4px 16px rgba(0,0,0,.12);width:280px;box-sizing:border-box');

  const head = el('div', 'display:flex;justify-content:space-between;align-items:center;margin-bottom:12px');
  head.append(
    el('b', 'font-size:15px', { textContent: '액션 버튼 채우기' }),
    el('span', 'cursor:pointer;font-size:20px;line-height:1;color:#555', { id: 'aa-close', textContent: '×' })
  );
  const row = el('div', 'display:flex;gap:8px');
  row.append(
    el('input', field + ';flex:1;min-width:0', { id: 'aa-url', placeholder: 'https://youtu.be/...' }),
    el('button', 'height:40px;padding:0 14px;border:0;border-radius:8px;background:#2350d0;color:#fff;font-weight:600;font-size:14px;cursor:pointer',
      { id: 'aa-go', textContent: '채우기' })
  );
  const autoLabel = el('label', 'display:block;font-size:13px;color:#555;cursor:pointer');
  autoLabel.append(el('input', '', { id: 'aa-auto', type: 'checkbox' }), ' 입력란이 보이면 자동 채움');

  panel.append(
    head,
    el('input', field, { id: 'aa-text', placeholder: '버튼 문구' }),
    row,
    autoLabel,
    el('div', 'margin-top:4px;font-size:12px;color:#666;min-height:16px', { id: 'aa-msg' })
  );
  (document.body || document.documentElement).appendChild(panel);

  const $ = (id) => panel.querySelector(id);
  $('#aa-text').value = load('text', DEFAULT_TEXT);
  $('#aa-url').value = load('url', '');
  $('#aa-auto').checked = load('auto', false);

  const msg = (t) => ($('#aa-msg').textContent = t);
  const run = () => {
    const text = $('#aa-text').value.trim();
    const url = $('#aa-url').value.trim();
    save('text', text); save('url', url);
    if (!url) return msg('링크를 입력하세요.');
    msg(fill(text, url) ? '채웠습니다 ✔' : '액션 버튼 입력란을 못 찾았어요.');
  };
  $('#aa-go').onclick = run;
  $('#aa-close').onclick = () => panel.remove();
  $('#aa-auto').onchange = (e) => save('auto', e.target.checked);

  // 클립보드에 유튜브 링크가 있으면 패널에 붙여넣기 (패널 클릭 시)
  panel.addEventListener('focusin', async (e) => {
    if (e.target.id !== 'aa-url' || e.target.value) return;
    try {
      const t = (await navigator.clipboard.readText()).trim();
      if (/^https?:\/\/(youtu\.be|(www\.)?youtube\.com)\//.test(t)) e.target.value = t;
    } catch (_) { /* 권한 없으면 무시 */ }
  });

  // 자동 모드: 입력란이 나타나고 비어 있을 때만 채움
  let busy = false;
  new MutationObserver(() => {
    if (busy || !$('#aa-auto').checked) return;
    const url = $('#aa-url').value.trim();
    const f = url && findFields();
    if (f && !f.url.value) {
      busy = true;
      fill($('#aa-text').value.trim(), url);
      setTimeout(() => (busy = false), 500);
    }
  }).observe(document.body, { childList: true, subtree: true });
})();
