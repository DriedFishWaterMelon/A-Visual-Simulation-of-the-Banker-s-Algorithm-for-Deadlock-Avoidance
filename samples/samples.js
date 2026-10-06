/*
 * samples/samples.js — ชุดข้อมูลตัวอย่าง พร้อมคำตอบที่ไล่ด้วยมือ (ใช้ทั้งใน UI และใน tests)
 * ตัวเลขชุดหลักมาจากตัวอย่างมาตรฐานในตำรา Operating System Concepts (Silberschatz et al.)
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.BankerSamples = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  const base = {
    available: [3, 3, 2],
    max: [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]],
    alloc: [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]],
  };
  // สถานะหลังอนุมัติ P1 ขอ (1,0,2)
  const afterP1 = {
    available: [2, 3, 0],
    max: base.max,
    alloc: [[0, 1, 0], [3, 0, 2], [3, 0, 2], [2, 1, 1], [0, 0, 2]],
  };
  const tape = (alloc, available) => ({ available, max: [[10], [4], [9]], alloc });

  return [
    {
      id: 'safe',
      name: '1) Safe state + อนุมัติ request',
      description: 'ตัวอย่างตำรา 5 process / 3 resource (A=10, B=5, C=7) ระบบ safe และ P1 ขอ (1,0,2) ได้รับอนุมัติ',
      state: base,
      request: { pid: 1, req: [1, 0, 2] },
      expected: { safe: true, sequence: [1, 3, 4, 0, 2], requestStatus: 'granted', requestCode: 'GRANTED' },
    },
    {
      id: 'unsafe-request',
      name: '2) Request ถูกปฏิเสธเพราะ unsafe',
      description: 'หลัง P1 ได้ (1,0,2) แล้ว P0 ขอ (0,2,0) ทรัพยากรมีพอ แต่ถ้าให้จะเข้า unsafe state จึงถูกปฏิเสธ',
      state: afterP1,
      request: { pid: 0, req: [0, 2, 0] },
      expected: { safe: true, sequence: [1, 3, 4, 0, 2], requestStatus: 'denied', requestCode: 'UNSAFE' },
    },
    {
      id: 'exceed-need',
      name: '3) Request เกิน Need',
      description: 'P1 มี Need = (1,2,2) แต่ขอ (3,0,0) เกิน Need ของ A จึงถูกปฏิเสธ (ผิดพลาด)',
      state: base,
      request: { pid: 1, req: [3, 0, 0] },
      expected: { safe: true, sequence: [1, 3, 4, 0, 2], requestStatus: 'denied', requestCode: 'EXCEEDS_NEED' },
    },
    {
      id: 'wait',
      name: '4) Resource ไม่พอ → ต้องรอ',
      description: 'P4 ขอ (3,3,0) ไม่เกิน Need (4,3,1) แต่ Available มีแค่ (2,3,0) จึงต้องรอ',
      state: afterP1,
      request: { pid: 4, req: [3, 3, 0] },
      expected: { safe: true, sequence: [1, 3, 4, 0, 2], requestStatus: 'wait', requestCode: 'NOT_AVAILABLE' },
    },
    {
      id: 'tape-unsafe-request',
      name: '5) Resource ชนิดเดียว: ให้เพิ่ม 1 ตัวแล้ว unsafe',
      description: 'ตัวอย่างเทปไดรฟ์ 12 ตัว (Max 10,4,9) ตอนนี้ safe แต่ถ้าให้ P2 เพิ่มอีก 1 จะ unsafe',
      state: tape([[5], [2], [2]], [3]),
      request: { pid: 2, req: [1] },
      expected: { safe: true, sequence: [1, 0, 2], requestStatus: 'denied', requestCode: 'UNSAFE' },
    },
    {
      id: 'unsafe-start',
      name: '6) สถานะเริ่มต้นเป็น unsafe',
      description: 'สถานะจากข้อ 5 หลังเผลอให้ P2 เพิ่ม 1 ตัว (เหมือนไม่ใช้ Banker) มีเพียง P1 ที่จบได้ P0 และ P2 ติดค้าง (รับประกันไม่ได้ว่าทุกตัวจะจบ)',
      state: tape([[5], [2], [3]], [2]),
      request: { pid: 1, req: [2] },
      expected: { safe: false, sequence: [1], requestStatus: 'denied', requestCode: 'UNSAFE' },
    },
  ];
});
