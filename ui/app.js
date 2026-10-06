/* ui/app.js — เชื่อม core + stepper + samples เข้ากับหน้าเว็บ */
(function () {
  const C = BankerCore;
  const samples = BankerSamples;
  const $ = (id) => document.getElementById(id);
  const MAX_P = 10;
  const MAX_R = 6;

  let model = null; // { available[], max[][], alloc[][] } ค่าที่ผู้ใช้กรอก (อาจไม่ valid)
  let current = null; // state ที่ valid ล่าสุด (null ถ้า input ผิด)
  let view = null; // { state, label, trial } สิ่งที่แผง Safety กำลังแสดง
  let stepper = null;
  let lastResult = null;
  let timer = null;

  const rname = (j) => (j < 26 ? String.fromCharCode(65 + j) : 'R' + j);
  const clone = (s) => C.clone(s);
  const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));

  /* ---------- editor (ตารางกรอกข้อมูล) ---------- */
  function buildEditor() {
    const n = model.max.length;
    const m = model.available.length;
    const cols = (cls) => Array.from({ length: m }, (_, j) => `<th class="${cls}">${rname(j)}</th>`).join('');
    let h = '<table class="editor"><tr><th>Available</th>' + cols('') + '</tr><tr><td class="name">ว่างอยู่</td>';
    for (let j = 0; j < m; j++) h += `<td>${input('avail', 0, j, model.available[j])}</td>`;
    h += '</tr></table>';
    h += `<table class="editor"><tr><th rowspan="2">Process</th><th colspan="${m}">Allocation</th><th colspan="${m}">Max</th><th colspan="${m}">Need</th></tr><tr>${cols('')}${cols('')}${cols('')}</tr>`;
    for (let i = 0; i < n; i++) {
      h += `<tr><td class="name">P${i}</td>`;
      for (let j = 0; j < m; j++) h += `<td>${input('alloc', i, j, model.alloc[i][j])}</td>`;
      for (let j = 0; j < m; j++) h += `<td>${input('max', i, j, model.max[i][j])}</td>`;
      for (let j = 0; j < m; j++) h += `<td class="need" data-need="${i},${j}">–</td>`;
      h += '</tr>';
    }
    h += '</table>';
    $('editor').innerHTML = h;
  }
  function input(k, i, j, v) {
    return `<input type="number" step="1" data-k="${k}" data-i="${i}" data-j="${j}" value="${Number.isNaN(v) ? '' : v}">`;
  }

  function readModel() {
    const num = (el) => (el.value.trim() === '' ? NaN : Number(el.value));
    document.querySelectorAll('#editor input').forEach((el) => {
      const { k, i, j } = el.dataset;
      const v = num(el);
      if (k === 'avail') model.available[+j] = v;
      else model[k][+i][+j] = v;
    });
  }

  /* ---------- refresh: อ่านข้อมูล → validate → รีเซ็ต safety ---------- */
  function refresh(keepView) {
    readModel();
    const errors = C.validateState(model);
    // ไฮไลต์ช่องที่ผิด
    document.querySelectorAll('#editor input').forEach((el) => {
      const { k, i, j } = el.dataset;
      const v = k === 'avail' ? model.available[+j] : model[k][+i][+j];
      let bad = !C.isNonNegInt(v);
      if (!bad && k !== 'avail') bad = model.max[+i][+j] < model.alloc[+i][+j];
      el.classList.toggle('invalid', bad);
    });
    const box = $('errors');
    box.hidden = errors.length === 0;
    box.innerHTML = errors.length ? '<b>ข้อมูลไม่ถูกต้อง:</b><ul>' + errors.map((e) => `<li>${esc(e)}</li>`).join('') + '</ul>' : '';

    document.querySelectorAll('[data-need]').forEach((td) => {
      const [i, j] = td.dataset.need.split(',').map(Number);
      td.textContent = errors.length ? '–' : model.max[i][j] - model.alloc[i][j];
    });

    stopPlay();
    lastResult = null;
    $('req-result').hidden = true;
    current = errors.length ? null : clone(model);
    buildRequestForm();
    if (current) {
      if (!keepView) setView(current, 'สถานะปัจจุบัน', false);
    } else {
      view = null;
      stepper = null;
      renderSafety();
    }
    const dis = !current;
    ['btn-req', 'req-pid'].forEach((id) => ($(id).disabled = dis));
  }

  function setView(state, label, isTrial) {
    stopPlay();
    view = { state, label, trial: isTrial };
    stepper = new BankerStepper.Stepper(C.safety(state).steps);
    renderSafety();
  }

  /* ---------- Safety panel ---------- */
  function chips(vec, prev) {
    return vec.map((v, j) => `<span class="chip"><small>${rname(j)}</small>${v}</span>`).join('');
  }

  function renderSafety() {
    const ctrls = ['s-reset', 's-prev', 's-next', 's-end', 's-play'];
    if (!view) {
      ctrls.forEach((id) => ($(id).disabled = true));
      $('safety-table').innerHTML = '';
      $('work').innerHTML = $('seq').innerHTML = '';
      $('explain').textContent = 'แก้ข้อมูลให้ถูกต้องก่อน จึงจะรัน Safety Algorithm ได้';
      $('explain').className = 'explain';
      $('log').innerHTML = '';
      $('s-counter').textContent = '';
      $('view-label').textContent = '–';
      $('btn-back-current').hidden = true;
      return;
    }
    const st = stepper.current;
    const s = view.state;
    const need = C.computeNeed(s);
    $('view-label').textContent = 'กำลังแสดง: ' + view.label;
    $('btn-back-current').hidden = !view.trial;
    $('s-reset').disabled = $('s-prev').disabled = stepper.atStart;
    $('s-next').disabled = $('s-end').disabled = $('s-play').disabled = stepper.atEnd;
    $('s-counter').textContent = `ขั้นที่ ${stepper.index + 1} / ${stepper.steps.length}`;
    $('work').innerHTML = chips(st.work);
    $('seq').innerHTML = st.sequence.length
      ? st.sequence.map((p) => `<span class="seq-item">P${p}</span>`).join('') +
        (st.kind === 'done' && !st.safe ? ' <span class="muted">(ได้เท่านี้ แล้วติด)</span>' : '')
      : '<span class="muted">ยังไม่มี</span>';
    $('explain').textContent = st.text;
    $('explain').className = 'explain' + (st.kind === 'done' ? (st.safe ? ' safe' : ' unsafe') : '');

    const m = s.available.length;
    let h = `<tr><th rowspan="2">Process</th><th colspan="${m}">Allocation</th><th colspan="${m}">Need</th><th rowspan="2">Finish</th></tr><tr>`;
    for (let k = 0; k < 2; k++) for (let j = 0; j < m; j++) h += `<th>${rname(j)}</th>`;
    h += '</tr>';
    for (let i = 0; i < s.max.length; i++) {
      const checking = st.kind === 'check' && st.pid === i;
      const finishing = st.kind === 'finish' && st.pid === i;
      const cls = st.finish[i] && !finishing ? 'finished' : checking || finishing ? 'checking' : '';
      h += `<tr class="${cls}"><td class="name">P${i}</td>`;
      s.alloc[i].forEach((v) => (h += `<td>${v}</td>`));
      need[i].forEach((v, j) => {
        const c = checking ? (v <= st.work[j] ? 'ok' : 'bad') : '';
        h += `<td class="${c}">${v}</td>`;
      });
      h += `<td>${st.finish[i] ? '✓ true' : 'false'}</td></tr>`;
    }
    $('safety-table').innerHTML = h;

    $('log').innerHTML = stepper.steps
      .map((x, k) => `<li class="${k === stepper.index ? 'current' : ''}">${esc(x.text)}</li>`)
      .join('');
  }

  function stopPlay() {
    if (timer) clearInterval(timer);
    timer = null;
    if ($('s-play')) $('s-play').textContent = '▶ เล่นอัตโนมัติ';
  }
  function togglePlay() {
    if (timer) return stopPlay();
    if (stepper.atEnd) stepper.reset();
    $('s-play').textContent = '⏸ หยุด';
    timer = setInterval(() => {
      stepper.next();
      renderSafety();
      if (stepper.atEnd) stopPlay();
      $('s-play').disabled = stepper.atEnd;
    }, 900);
    renderSafety();
    $('s-play').disabled = false;
  }

  /* ---------- Request panel ---------- */
  function buildRequestForm() {
    if (!model) return;
    const n = model.max.length;
    const m = model.available.length;
    const sel = $('req-pid');
    const keep = sel.value;
    sel.innerHTML = Array.from({ length: n }, (_, i) => `<option value="${i}">P${i}</option>`).join('');
    if (keep !== '' && +keep < n) sel.value = keep;
    $('req-inputs').innerHTML = Array.from(
      { length: m },
      (_, j) => `<label>${rname(j)} <input type="number" min="0" step="1" value="0" data-r="${j}"></label>`
    ).join('');
    updateReqNeed();
  }
  function updateReqNeed() {
    if (!current) return ($('req-need').textContent = '');
    const i = +$('req-pid').value;
    const need = C.computeNeed(current)[i];
    $('req-need').textContent = `P${i}: Need = (${need.join(', ')}), Available = (${current.available.join(', ')})`;
  }

  function sendRequest() {
    if (!current) return;
    const pid = +$('req-pid').value;
    const req = [...document.querySelectorAll('#req-inputs input')].map((el) =>
      el.value.trim() === '' ? NaN : Number(el.value)
    );
    const r = C.request(current, pid, req);
    lastResult = { r, pid, req };
    const title = { granted: '✅ อนุมัติ (Granted)', wait: '⏳ ต้องรอ (Wait)', denied: '⛔ ปฏิเสธ (Denied)', invalid: '⚠ request ไม่ถูกต้อง' }[r.status];
    let h = `<div class="result ${r.status}"><h3>${title} — P${pid} ขอ (${req.join(', ')})</h3><div>${esc(r.reason)}</div><ul>`;
    for (const c of r.checks) {
      const t = c.ok === null ? '·' : c.ok ? '✓' : '✗';
      const tc = c.ok === null ? '' : c.ok ? 'y' : 'n';
      h += `<li><span class="tick ${tc}">${t}</span><b>${esc(c.label)}</b> — ${esc(c.detail)}</li>`;
    }
    h += '</ul><div class="actions">';
    if (r.trial) {
      h += '<button data-act="trial">ดูขั้นตอน Safety ของสถานะทดลอง</button>';
    }
    if (r.status === 'granted') h += '<button class="primary" data-act="apply">ยืนยัน: ใช้สถานะใหม่</button>';
    h += '</div>';
    if (r.code === 'UNSAFE') {
      h +=
        '<div class="muted">เทียบกรณีไม่ใช้ Banker: ถ้าอนุมัติไปเลยระบบจะเข้า unsafe state ตามที่ปุ่มด้านบนแสดง ซึ่งอาจเกิด deadlock ได้</div>';
    }
    h += '</div>';
    $('req-result').innerHTML = h;
    $('req-result').hidden = false;
    if (r.trial) setView(r.trial, `สถานะทดลองหลังให้ P${pid} (${req.join(', ')})`, true);
  }

  function applyGranted() {
    if (!lastResult || lastResult.r.status !== 'granted') return;
    const s = lastResult.r.newState;
    model = clone(s);
    buildEditor();
    refresh();
    $('sample-desc').textContent = 'ใช้สถานะหลังอนุมัติ request แล้ว';
  }

  /* ---------- โหลด/สุ่ม/บันทึก/โครงสร้าง ---------- */
  function loadState(s, desc) {
    model = clone(s);
    buildEditor();
    refresh();
    $('sample-desc').textContent = desc || '';
  }
  function resize(dp, dr) {
    readModel();
    const n = model.max.length + dp;
    const m = model.available.length + dr;
    if (n < 1 || m < 1 || n > MAX_P || m > MAX_R) return;
    if (dp > 0) {
      model.max.push(new Array(m).fill(0));
      model.alloc.push(new Array(m).fill(0));
    }
    if (dp < 0) {
      model.max.pop();
      model.alloc.pop();
    }
    if (dr > 0) {
      model.available.push(0);
      model.max.forEach((r) => r.push(0));
      model.alloc.forEach((r) => r.push(0));
    }
    if (dr < 0) {
      model.available.pop();
      model.max.forEach((r) => r.pop());
      model.alloc.forEach((r) => r.pop());
    }
    buildEditor();
    refresh();
  }
  function save() {
    readModel();
    const blob = new Blob([JSON.stringify(model, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'banker-state.json';
    a.click();
    URL.revokeObjectURL(a.href);
  }
  function loadFile(file) {
    const rd = new FileReader();
    rd.onload = () => {
      try {
        const s = JSON.parse(rd.result);
        if (!Array.isArray(s.available) || !Array.isArray(s.max) || !Array.isArray(s.alloc)) throw new Error('รูปแบบไม่ถูกต้อง');
        loadState(s, 'โหลดจากไฟล์: ' + file.name);
      } catch (e) {
        alert('โหลดไฟล์ไม่สำเร็จ: ' + e.message + '\nต้องเป็น JSON ที่มี available, max, alloc');
      }
    };
    rd.readAsText(file);
  }

  /* ---------- init ---------- */
  function init() {
    $('sample-select').innerHTML = samples.map((s, i) => `<option value="${i}">${esc(s.name)}</option>`).join('');
    const pick = () => {
      const s = samples[+$('sample-select').value];
      loadState(s.state, s.description);
      // เตรียมฟอร์ม request ให้ตรงกับตัวอย่าง
      $('req-pid').value = s.request.pid;
      document.querySelectorAll('#req-inputs input').forEach((el, j) => (el.value = s.request.req[j]));
      updateReqNeed();
    };
    $('sample-select').addEventListener('change', pick);
    $('editor').addEventListener('input', () => refresh());
    $('btn-random').addEventListener('click', () => {
      readModel();
      const n = model.max.length;
      const m = model.available.length;
      loadState(C.randomState(n, m), 'ข้อมูลสุ่ม (รับประกันว่า Max ≥ Allocation)');
    });
    $('btn-add-p').addEventListener('click', () => resize(1, 0));
    $('btn-del-p').addEventListener('click', () => resize(-1, 0));
    $('btn-add-r').addEventListener('click', () => resize(0, 1));
    $('btn-del-r').addEventListener('click', () => resize(0, -1));
    $('btn-save').addEventListener('click', save);
    $('file-load').addEventListener('change', (e) => e.target.files[0] && loadFile(e.target.files[0]));
    $('s-reset').addEventListener('click', () => { stopPlay(); stepper.reset(); renderSafety(); });
    $('s-prev').addEventListener('click', () => { stopPlay(); stepper.prev(); renderSafety(); });
    $('s-next').addEventListener('click', () => { stopPlay(); stepper.next(); renderSafety(); });
    $('s-end').addEventListener('click', () => { stopPlay(); stepper.end(); renderSafety(); });
    $('s-play').addEventListener('click', togglePlay);
    $('btn-back-current').addEventListener('click', () => current && setView(current, 'สถานะปัจจุบัน', false));
    $('req-pid').addEventListener('change', updateReqNeed);
    $('btn-req').addEventListener('click', sendRequest);
    $('req-result').addEventListener('click', (e) => {
      const act = e.target.dataset && e.target.dataset.act;
      if (act === 'apply') applyGranted();
      if (act === 'trial' && lastResult && lastResult.r.trial) {
        setView(lastResult.r.trial, `สถานะทดลองหลังให้ P${lastResult.pid} (${lastResult.req.join(', ')})`, true);
      }
    });
    pick();
  }
  init();
})();
