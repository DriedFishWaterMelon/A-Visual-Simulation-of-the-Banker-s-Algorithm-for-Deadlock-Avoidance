// รัน: node tests/test.js
const assert = require('assert');
const C = require('../core/banker');
const samples = require('../samples/samples');
const { Stepper } = require('../simulation/stepper');

let passed = 0;
function test(name, fn) {
  try {
    fn();
    passed++;
    console.log('  ok  ' + name);
  } catch (e) {
    console.error('FAIL  ' + name + '\n      ' + e.message);
    process.exitCode = 1;
  }
}

// ---- เทียบกับคำตอบที่ไล่ด้วยมือ ----
for (const s of samples) {
  test(`sample ${s.id}: validate ผ่าน`, () => assert.deepStrictEqual(C.validateState(s.state), []));
  test(`sample ${s.id}: safety ตรงกับที่ไล่มือ`, () => {
    const r = C.safety(s.state);
    assert.strictEqual(r.safe, s.expected.safe);
    assert.deepStrictEqual(r.sequence, s.expected.sequence);
  });
  test(`sample ${s.id}: request ตรงกับที่ไล่มือ`, () => {
    const r = C.request(s.state, s.request.pid, s.request.req);
    assert.strictEqual(r.status, s.expected.requestStatus);
    assert.strictEqual(r.code, s.expected.requestCode);
  });
}

test('Need = Max - Allocation (ตัวอย่างตำรา)', () => {
  assert.deepStrictEqual(C.computeNeed(samples[0].state), [[7, 4, 3], [1, 2, 2], [6, 0, 0], [0, 1, 1], [4, 3, 1]]);
});

test('granted: newState คือสถานะหลังให้ (Available ลด, Allocation เพิ่ม)', () => {
  const r = C.request(samples[0].state, 1, [1, 0, 2]);
  assert.deepStrictEqual(r.newState.available, [2, 3, 0]);
  assert.deepStrictEqual(r.newState.alloc[1], [3, 0, 2]);
});

test('denied UNSAFE: rollback — state เดิมไม่ถูกแก้', () => {
  const st = samples[1].state;
  const before = JSON.stringify(st);
  const r = C.request(st, 0, [0, 2, 0]);
  assert.strictEqual(JSON.stringify(st), before);
  assert.strictEqual(r.newState, st);
  assert.strictEqual(r.safety.safe, false);
});

// ---- กรณีขอบ ----
test('edge: Available = 0 ทั้งหมด และมี process ที่ Need > 0 → unsafe', () => {
  const st = { available: [0, 0], max: [[1, 1]], alloc: [[0, 0]] };
  assert.strictEqual(C.safety(st).safe, false);
});

test('edge: ทุก process จบแล้ว (Need = 0 ทั้งหมด) → safe', () => {
  const st = { available: [0], max: [[2], [3]], alloc: [[2], [3]] };
  const r = C.safety(st);
  assert.strictEqual(r.safe, true);
  assert.deepStrictEqual(r.sequence, [0, 1]);
});

test('edge: request = 0 ถูกอนุมัติ และสถานะไม่เปลี่ยน', () => {
  const st = samples[0].state;
  const r = C.request(st, 2, [0, 0, 0]);
  assert.strictEqual(r.status, 'granted');
  assert.deepStrictEqual(r.newState, st);
});

test('edge: request ที่ Available พอดี แล้ว safe', () => {
  const st = { available: [1], max: [[1]], alloc: [[0]] };
  assert.strictEqual(C.request(st, 0, [1]).status, 'granted');
});

test('edge: request ไม่ใช่จำนวนเต็ม/ติดลบ/ความยาวผิด → invalid', () => {
  const st = samples[0].state;
  assert.strictEqual(C.request(st, 0, [-1, 0, 0]).status, 'invalid');
  assert.strictEqual(C.request(st, 0, [1.5, 0, 0]).status, 'invalid');
  assert.strictEqual(C.request(st, 0, [1]).status, 'invalid');
  assert.strictEqual(C.request(st, 9, [0, 0, 0]).status, 'invalid');
  assert.strictEqual(C.request(st, 0, [NaN, 0, 0]).status, 'invalid');
});

// ---- validation ----
test('validate: ค่าติดลบ', () => {
  const st = { available: [-1], max: [[1]], alloc: [[0]] };
  assert.ok(C.validateState(st).length > 0);
});
test('validate: Max < Allocation', () => {
  const st = { available: [1], max: [[1]], alloc: [[2]] };
  assert.ok(C.validateState(st).some((e) => e.includes('Max')));
});
test('validate: ค่าว่าง/NaN/ทศนิยม', () => {
  assert.ok(C.validateState({ available: [NaN], max: [[1]], alloc: [[0]] }).length > 0);
  assert.ok(C.validateState({ available: [1], max: [[1.5]], alloc: [[0]] }).length > 0);
});
test('validate: ไม่มี process', () => {
  assert.ok(C.validateState({ available: [1], max: [], alloc: [] }).length > 0);
});

// ---- ประวัติขั้นตอน + stepper ----
test('safety steps: เริ่มด้วย init จบด้วย done และ work สุดท้ายถูกต้อง', () => {
  const r = C.safety(samples[0].state);
  assert.strictEqual(r.steps[0].kind, 'init');
  assert.strictEqual(r.steps[r.steps.length - 1].kind, 'done');
  // Work สุดท้าย = Available + Allocation ทั้งหมด = (10,5,7)
  assert.deepStrictEqual(r.steps[r.steps.length - 1].work, [10, 5, 7]);
});

test('stepper: next/prev/reset/end', () => {
  const r = C.safety(samples[0].state);
  const s = new Stepper(r.steps);
  assert.ok(s.atStart);
  s.next();
  assert.strictEqual(s.index, 1);
  s.prev();
  assert.strictEqual(s.index, 0);
  s.prev();
  assert.strictEqual(s.index, 0);
  s.end();
  assert.ok(s.atEnd);
  s.next();
  assert.strictEqual(s.index, r.steps.length - 1);
  s.reset();
  assert.strictEqual(s.index, 0);
});

// ---- property: safe ที่ได้ต้องไล่ตามลำดับแล้วจบได้จริง / ข้อมูลสุ่ม valid ----
test('random: 500 สถานะ — validate ผ่าน และ safe sequence ตรวจย้อนได้จริง', () => {
  let seed = 12345;
  const rng = () => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);
  for (let k = 0; k < 500; k++) {
    const st = C.randomState(1 + Math.floor(rng() * 6), 1 + Math.floor(rng() * 4), rng);
    assert.deepStrictEqual(C.validateState(st), []);
    const r = C.safety(st);
    if (r.safe) {
      const need = C.computeNeed(st);
      let work = st.available.slice();
      for (const i of r.sequence) {
        assert.ok(C.leq(need[i], work));
        work = work.map((w, j) => w + st.alloc[i][j]);
      }
      assert.strictEqual(r.sequence.length, st.max.length);
    }
  }
});

console.log(`\n${passed} tests passed` + (process.exitCode ? ' (มีที่ล้มเหลว)' : ''));
