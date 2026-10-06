# Banker's Algorithm — Visual Simulation

โปรแกรมจำลองแบบเห็นภาพของ Banker's Algorithm (Deadlock Avoidance) วิชา Operating Systems
เป็นเว็บแอป HTML/CSS/JavaScript ล้วน **ไม่ต้องติดตั้งอะไร ไม่ต้องมี server**

## วิธีรัน

1. ดับเบิลคลิกไฟล์ `index.html` (เปิดด้วย Chrome / Edge / Firefox)
2. (ทางเลือก) รันเทสต์ของ core: ต้องมี Node.js แล้วใช้คำสั่ง `node tests/test.js`

## วิธีใช้

1. **เลือกตัวอย่าง** จากเมนู (มี 6 ชุด) หรือกรอกเอง / กดสุ่ม / เพิ่ม-ลด Process และ Resource / บันทึก-โหลดเป็นไฟล์ JSON
   ช่องที่กรอกผิด (ติดลบ ว่าง ทศนิยม หรือ Max < Allocation) จะขึ้นสีแดงพร้อมข้อความอธิบาย และโปรแกรมจะไม่รัน algorithm จนกว่าจะแก้
2. **Safety Algorithm** กด `ถัดไป` ทีละขั้น (หรือ `ย้อนกลับ`, `เล่นอัตโนมัติ`, `ข้ามไปจบ`) แล้วดู
   - แถวสีเหลือง = process ที่กำลังตรวจ, ช่อง Need สีเขียว/แดง = เทียบกับ Work แล้วผ่าน/ไม่ผ่านทีละ resource
   - แถวสีเทา = จบแล้ว, แถบ Work และ Safe sequence ปรับตามทุกขั้น
   - กล่องคำอธิบายบอกเหตุผลของขั้นนั้น และ "บันทึกขั้นตอนทั้งหมด" รวมทุกขั้นไว้ให้
3. **จำลอง Request** เลือก process + จำนวนที่ขอ แล้วกด `ส่ง request` จะได้ผล 3 แบบ พร้อมเหตุผลทีละข้อ
   - ✅ **Granted** — ให้แล้วยัง safe (กด "ยืนยัน" เพื่อใช้สถานะใหม่ต่อ)
   - ⏳ **Wait** — ไม่เกิน Need แต่ resource ที่ว่างไม่พอ
   - ⛔ **Denied** — ขอเกิน Need (ผิดพลาด) หรือให้แล้วจะ unsafe (rollback)
   กดปุ่ม "ดูขั้นตอน Safety ของสถานะทดลอง" เพื่อดู safety ของสถานะที่ *ถ้า* อนุมัติ จะเกิดอะไรขึ้น
   ซึ่งใช้เทียบกรณี **ไม่ใช้ Banker** ได้ (ระบบเข้า unsafe → เสี่ยง deadlock)

## ชุดตัวอย่าง

| # | สถานการณ์ | ผลที่คาด (ไล่มือแล้ว) |
|---|---|---|
| 1 | ตัวอย่างตำรา 5 process / 3 resource, P1 ขอ (1,0,2) | safe `<P1,P3,P4,P0,P2>`, Granted |
| 2 | หลังข้อ 1, P0 ขอ (0,2,0) | Denied: unsafe (rollback) |
| 3 | P1 (Need = 1,2,2) ขอ (3,0,0) | Denied: เกิน Need |
| 4 | หลังข้อ 1, P4 ขอ (3,3,0) | Wait: Available (2,3,0) ไม่พอ |
| 5 | resource ชนิดเดียว (เทป 12 ตัว) P2 ขอเพิ่ม 1 | Denied: unsafe |
| 6 | สถานะเริ่มต้นที่ unsafe อยู่แล้ว | unsafe |

## โปรแกรมทำงานอย่างไร

### โครงสร้างโฟลเดอร์

```
index.html            หน้าเว็บ
core/banker.js        ตัว algorithm ล้วน ๆ (ไม่ยุ่งกับหน้าเว็บ ทดสอบด้วย Node ได้)
simulation/stepper.js ตัวควบคุมทีละขั้น (ถัดไป/ย้อนกลับ/เริ่มใหม่)
ui/app.js, style.css  ส่วนแสดงผลและรับ input
samples/samples.js    ชุดข้อมูลตัวอย่าง + คำตอบที่ไล่มือ
tests/test.js         เทสต์เทียบกับคำตอบที่ไล่มือ
```

### โครงสร้างข้อมูล

สถานะระบบคือ `{ available[m], max[n][m], alloc[n][m] }` (n = จำนวน process, m = จำนวนชนิด resource)
**Need ไม่ถูกเก็บ แต่คำนวณใหม่ทุกครั้งจาก Max − Allocation** จึงไม่มีทางไม่ตรงกัน

### Safety Algorithm (`safety`)

1. `Work = Available`, `Finish[i] = false` ทุกตัว
2. ไล่ตรวจ P0..Pn-1 หา process ที่ยังไม่จบและ `Need[i] ≤ Work` (เทียบทุก resource)
3. ถ้าเจอ ให้ถือว่า process นั้นรันจนจบและคืน resource: `Work = Work + Allocation[i]`, `Finish[i] = true`, ต่อท้าย safe sequence
4. วนซ้ำจนไม่มีใครเลือกได้เพิ่ม ถ้าทุกตัวจบ → **safe**, ไม่ครบ → **unsafe**
   (กรณี unsafe โปรแกรมแสดงลำดับที่ไปได้ก่อนจะติด และบอกว่า process ไหนติดค้าง)

> หมายเหตุ: โปรแกรมไล่ตรวจแบบวนผ่านทุก process แล้วค่อยวนรอบใหม่ ส่วนตำราจะกลับไปเริ่มที่ P0 ทุกครั้งที่เจอ
> ลำดับที่ได้จึงอาจต่างกันในบางข้อมูล แต่ทั้งสองแบบให้ผล safe/unsafe ตรงกันเสมอ และลำดับที่ได้ถูกต้องทั้งคู่

### Resource-Request Algorithm (`request`)

1. `Request ≤ Need` ? ไม่ใช่ → **Denied** (process ขอเกิน Max ที่ประกาศไว้)
2. `Request ≤ Available` ? ไม่ใช่ → **Wait**
3. ทดลองจองให้: `Available −= Request`, `Allocation[i] += Request` (ทำบนสำเนา)
4. รัน Safety Algorithm กับสถานะทดลอง
   - safe → **Granted** ใช้สถานะทดลองเป็นสถานะจริง
   - unsafe → **Denied** และ **rollback**: ทิ้งสำเนา สถานะจริงไม่ถูกแตะเลย

request = 0 ผ่านขั้นตอนเดียวกัน (ผลคือ Granted ถ้าสถานะปัจจุบัน safe)

### ทำไมกดทีละขั้นและย้อนกลับได้

algorithm ไม่ได้ถูกรันทีละขั้นตอนตามที่ผู้ใช้กด แต่ `safety()` **รันรวดเดียวและบันทึก "ภาพนิ่ง" ของทุกขั้น** ไว้ในอาร์เรย์ `steps`
(ชนิดขั้น, process ที่ตรวจ, ค่า Work, Finish, safe sequence ณ ขั้นนั้น, ข้อความอธิบาย)
`Stepper` แค่เลื่อนตัวชี้ index ไปมา และหน้าเว็บวาดภาพจากขั้นที่ตัวชี้อยู่ ปุ่มย้อนกลับจึงทำได้ง่ายและไม่ผิดเพี้ยน

### การจัดการ input ผิดปกติ

`validateState` ตรวจ: ค่าติดลบ, ค่าว่าง/ไม่ใช่จำนวนเต็ม, Max < Allocation, ขนาดตารางไม่ตรงกัน
ส่วน request ที่ไม่ใช่จำนวนเต็มไม่ติดลบจะได้สถานะ `invalid`

## ข้อจำกัด

- เป็นการจำลอง ไม่ได้จัดการ process/resource จริงของระบบปฏิบัติการ และไม่มี deadlock detection/recovery
- ต้องรู้ Max ของทุก process ล่วงหน้า และจำนวน process/resource ต้องคงที่ ซึ่งเป็นข้อจำกัดของ Banker's Algorithm เองด้วย
- UI รองรับสูงสุด 10 process × 6 resource
