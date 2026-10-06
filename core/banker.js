/*
 * core/banker.js — Banker's Algorithm (ไม่ยุ่งกับ UI)
 *
 * state = { available: number[m], max: number[n][m], alloc: number[n][m] }
 * Need = Max - Allocation (คำนวณเสมอ ไม่เก็บซ้ำ)
 *
 * ทั้ง safety() และ request() "บันทึกประวัติทุกขั้น" ไว้ใน steps[]
 * เพื่อให้ UI เล่นทีละขั้น / ย้อนกลับได้โดยไม่ต้องรัน algorithm ซ้ำ
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.BankerCore = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  const isNonNegInt = (v) => Number.isInteger(v) && v >= 0;
  const leq = (a, b) => a.every((x, j) => x <= b[j]);
  const add = (a, b) => a.map((x, j) => x + b[j]);
  const sub = (a, b) => a.map((x, j) => x - b[j]);
  const clone = (s) => ({
    available: s.available.slice(),
    max: s.max.map((r) => r.slice()),
    alloc: s.alloc.map((r) => r.slice()),
  });
  const pname = (i) => 'P' + i;
  const fmt = (v) => '(' + v.join(', ') + ')';

  function computeNeed(state) {
    return state.max.map((row, i) => row.map((x, j) => x - state.alloc[i][j]));
  }

  /** ตรวจความถูกต้องของข้อมูลนำเข้า คืนรายการข้อความผิดพลาด ([] = ใช้ได้) */
  function validateState(s) {
    const errors = [];
    const n = s.max.length;
    const m = s.available.length;
    if (n === 0 || m === 0) return ['ต้องมีอย่างน้อย 1 process และ 1 resource'];
    if (s.alloc.length !== n) errors.push('จำนวนแถวของ Allocation ไม่ตรงกับ Max');
    s.available.forEach((v, j) => {
      if (!isNonNegInt(v)) errors.push(`Available[${j}] ต้องเป็นจำนวนเต็มไม่ติดลบ`);
    });
    for (let i = 0; i < n; i++) {
      if (s.max[i].length !== m || (s.alloc[i] || []).length !== m) {
        errors.push(`${pname(i)}: จำนวนคอลัมน์ไม่ตรงกับจำนวน resource`);
        continue;
      }
      for (let j = 0; j < m; j++) {
        const mx = s.max[i][j];
        const al = s.alloc[i][j];
        if (!isNonNegInt(mx)) errors.push(`Max ของ ${pname(i)} คอลัมน์ ${j} ต้องเป็นจำนวนเต็มไม่ติดลบ`);
        if (!isNonNegInt(al)) errors.push(`Allocation ของ ${pname(i)} คอลัมน์ ${j} ต้องเป็นจำนวนเต็มไม่ติดลบ`);
        if (isNonNegInt(mx) && isNonNegInt(al) && mx < al) {
          errors.push(`${pname(i)} คอลัมน์ ${j}: Max (${mx}) น้อยกว่า Allocation (${al}) ทำให้ Need ติดลบ`);
        }
      }
    }
    return errors;
  }

  /**
   * Safety Algorithm (สถานะต้องผ่าน validateState แล้ว)
   * ไล่ตรวจ process ตามลำดับ P0..Pn-1 วนซ้ำจนไม่มีใครเลือกเพิ่มได้
   * คืน { safe, sequence, steps }
   * step = { kind: init|check|finish|done, pid?, ok?, need?, text, work, finish, sequence }
   */
  function safety(state) {
    const n = state.max.length;
    const need = computeNeed(state);
    let work = state.available.slice();
    const finish = new Array(n).fill(false);
    const sequence = [];
    const steps = [];
    const snap = (o) =>
      steps.push(Object.assign({}, o, { work: work.slice(), finish: finish.slice(), sequence: sequence.slice() }));

    snap({ kind: 'init', text: `เริ่มต้น: Work = Available = ${fmt(work)}, Finish[i] = false ทุกตัว` });

    let progress = true;
    while (sequence.length < n && progress) {
      progress = false;
      for (let i = 0; i < n; i++) {
        if (finish[i]) continue;
        const ok = leq(need[i], work);
        snap({
          kind: 'check',
          pid: i,
          ok,
          need: need[i].slice(),
          text: ok
            ? `${pname(i)}: Need ${fmt(need[i])} ≤ Work ${fmt(work)} → รันจนจบได้`
            : `${pname(i)}: Need ${fmt(need[i])} ≰ Work ${fmt(work)} → ยังรันไม่ได้ ข้ามไปก่อน`,
        });
        if (ok) {
          const before = work;
          work = add(work, state.alloc[i]);
          finish[i] = true;
          sequence.push(i);
          progress = true;
          snap({
            kind: 'finish',
            pid: i,
            text: `${pname(i)} จบงานแล้วคืน Allocation ${fmt(state.alloc[i])}: Work = ${fmt(before)} + ${fmt(state.alloc[i])} = ${fmt(work)}`,
          });
        }
      }
    }

    const safe = sequence.length === n;
    const stuck = finish.map((f, i) => (f ? -1 : i)).filter((i) => i >= 0);
    snap({
      kind: 'done',
      safe,
      text: safe
        ? `ทุก process จบได้ → SAFE state, safe sequence = <${sequence.map(pname).join(', ')}>`
        : `ไม่มี process ใดใน {${stuck.map(pname).join(', ')}} ที่ Need ≤ Work → UNSAFE state (เสี่ยง deadlock)`,
    });
    return { safe, sequence, steps };
  }

  /**
   * Resource-Request Algorithm
   * คืน { status: granted|wait|denied, code, reason, checks[], trial, safety, newState }
   *   denied/EXCEEDS_NEED : request เกิน Need (process ละเมิด Max ที่แจ้งไว้)
   *   wait/NOT_AVAILABLE  : resource ไม่พอ ต้องรอ
   *   denied/UNSAFE       : ถ้าให้แล้วเข้า unsafe → rollback (newState = state เดิม)
   *   granted             : ให้ได้ (newState = สถานะหลังให้)
   */
  function request(state, pid, req) {
    const m = state.available.length;
    if (!Number.isInteger(pid) || pid < 0 || pid >= state.max.length) {
      return { status: 'invalid', code: 'BAD_PID', reason: 'ไม่มี process นี้', checks: [], newState: state };
    }
    if (!Array.isArray(req) || req.length !== m || !req.every(isNonNegInt)) {
      return {
        status: 'invalid',
        code: 'BAD_REQUEST',
        reason: 'request ต้องเป็นจำนวนเต็มไม่ติดลบ ครบทุก resource',
        checks: [],
        newState: state,
      };
    }
    const need = computeNeed(state)[pid];
    const checks = [];

    const withinNeed = leq(req, need);
    checks.push({
      label: 'ขั้น 1: Request ≤ Need?',
      ok: withinNeed,
      detail: `${fmt(req)} ${withinNeed ? '≤' : '≰'} ${fmt(need)}`,
    });
    if (!withinNeed) {
      return {
        status: 'denied',
        code: 'EXCEEDS_NEED',
        reason: `${pname(pid)} ขอเกิน Need ที่เหลือ (ขอเกิน Max ที่ประกาศไว้) จึงถือว่าผิดพลาดและปฏิเสธ`,
        checks,
        newState: state,
      };
    }

    const enough = leq(req, state.available);
    checks.push({
      label: 'ขั้น 2: Request ≤ Available?',
      ok: enough,
      detail: `${fmt(req)} ${enough ? '≤' : '≰'} ${fmt(state.available)}`,
    });
    if (!enough) {
      return {
        status: 'wait',
        code: 'NOT_AVAILABLE',
        reason: `resource ที่ว่างอยู่ไม่พอ ${pname(pid)} ต้องรอ`,
        checks,
        newState: state,
      };
    }

    const trial = clone(state);
    trial.available = sub(trial.available, req);
    trial.alloc[pid] = add(trial.alloc[pid], req);
    checks.push({
      label: 'ขั้น 3: จองให้แบบทดลอง',
      ok: null,
      detail: `Available = ${fmt(trial.available)}, Allocation[${pname(pid)}] = ${fmt(trial.alloc[pid])}`,
    });

    const s = safety(trial);
    checks.push({
      label: 'ขั้น 4: สถานะหลังทดลองเป็น safe?',
      ok: s.safe,
      detail: s.safe ? `safe sequence = <${s.sequence.map(pname).join(', ')}>` : 'ไม่พบ safe sequence',
    });

    if (s.safe) {
      return {
        status: 'granted',
        code: 'GRANTED',
        reason: `อนุมัติ: หลังให้แล้วระบบยัง safe`,
        checks,
        trial,
        safety: s,
        newState: trial,
      };
    }
    return {
      status: 'denied',
      code: 'UNSAFE',
      reason: `ปฏิเสธ: ถ้าให้แล้วระบบเข้า unsafe state จึง rollback กลับสถานะเดิมและให้ ${pname(pid)} รอ`,
      checks: checks.concat([{ label: 'Rollback', ok: null, detail: 'คืน Available/Allocation/Need เป็นค่าก่อนทดลอง' }]),
      trial,
      safety: s,
      newState: state,
    };
  }

  /** สร้างข้อมูลสุ่มที่ valid เสมอ */
  function randomState(n, m, rng) {
    rng = rng || Math.random;
    const ri = (lo, hi) => lo + Math.floor(rng() * (hi - lo + 1));
    const max = [];
    const alloc = [];
    for (let i = 0; i < n; i++) {
      const mx = [];
      const al = [];
      for (let j = 0; j < m; j++) {
        const x = ri(0, 9);
        mx.push(x);
        al.push(ri(0, x));
      }
      max.push(mx);
      alloc.push(al);
    }
    const available = [];
    for (let j = 0; j < m; j++) available.push(ri(0, 5));
    return { available, max, alloc };
  }

  return { computeNeed, validateState, safety, request, randomState, clone, leq, isNonNegInt };
});
