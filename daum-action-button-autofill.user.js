// ==UserScript==
// @name         다음 채널 스튜디오 - 액션 버튼 자동 채우기
// @namespace    https://github.com/assxq/-
// @version      1.0.0
// @description  영상 업로드 화면의 "액션 버튼" 문구/링크 입력란을 자동으로 채웁니다.
// @match        https://channel.daum.net/studio/channels/*/videos/*
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
  const panel = document.createElement('div');
  panel.style.cssText =
    'position:fixed;right:16px;bottom:16px;z-index:99999;background:#fff;border:1px solid #ccc;' +
    'border-radius:8px;padding:10px;font:13px sans-serif;box-shadow:0 2px 8px rgba(0,0,0,.2);width:260px';
  panel.innerHTML = `
    <div style="font-weight:600;margin-bottom:6px">액션 버튼 자동 채우기</div>
    <input id="aa-text" placeholder="버튼 문구" style="width:100%;box-sizing:border-box;margin-bottom:4px">
    <input id="aa-url" placeholder="링크 (예: https://youtu.be/...)" style="width:100%;box-sizing:border-box;margin-bottom:4px">
    <label style="display:block;margin-bottom:6px"><input id="aa-auto" type="checkbox"> 입력란이 보이면 자동 채움</label>
    <button id="aa-go" style="width:100%">지금 채우기</button>
    <div id="aa-msg" style="margin-top:4px;color:#666"></div>`;
  document.body.appendChild(panel);

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
