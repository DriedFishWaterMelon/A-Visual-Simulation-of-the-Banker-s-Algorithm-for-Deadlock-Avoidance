# Banker's Algorithm Simulator — เวอร์ชัน C (terminal)

เขียนด้วย C99 ล้วน ไม่ใช้ไลบรารีเสริม ทำงานเหมือนเวอร์ชันเว็บ (โฟลเดอร์ `../`) ผลลัพธ์ตรงกันทุกตัวอย่าง

## คอมไพล์และรัน

ต้องมี C compiler (gcc / clang / MSVC)

**Linux / macOS / WSL / MSYS2 / MinGW**
```
make            # สร้าง ./banker
./banker
make test       # คอมไพล์และรันเทสต์ของ core
```
ถ้าไม่มี make:
```
gcc -std=c99 -O2 -o banker main.c banker.c samples.c
gcc -std=c99 -O2 -o banker_test test.c banker.c samples.c && ./banker_test
```

**Windows**
- ติดตั้ง gcc: `winget install BrechtSanders.WinLibs.POSIX.UCRT` (เปิด terminal ใหม่หลังติดตั้ง) แล้วใช้คำสั่ง gcc ด้านบน รันด้วย `banker.exe`
- หรือใช้ MSVC (Developer Command Prompt): `cl /utf-8 /O2 main.c banker.c samples.c /Fe:banker.exe`
- โปรแกรมตั้ง console เป็น UTF-8 และเปิดสี ANSI ให้เอง (Windows Terminal / Windows 10 ขึ้นไป) ถ้าสีหรือภาษาไทยเพี้ยน ให้รัน `banker --no-color`

## วิธีใช้

เปิดมาจะโหลดตัวอย่างที่ 1 ให้เลย แล้วเลือกเมนูด้วยตัวเลข

| เมนู | ทำอะไร |
|---|---|
| 1 | โหลดชุดตัวอย่าง 6 ชุด (safe, unsafe request, เกิน Need, รอ, resource ชนิดเดียว, unsafe เริ่มต้น) |
| 2 | แสดงตาราง Available / Allocation / Max / Need |
| 3 | กรอกข้อมูลเอง (ตรวจความถูกต้องก่อนบันทึก: ค่าติดลบ, Max < Allocation ฯลฯ) |
| 4 | Safety Algorithm ทีละขั้น |
| 5 | จำลอง request ของ process และดูเหตุผล |
| 6 | สุ่มข้อมูล |
| 7 / 8 | บันทึก / โหลดไฟล์ข้อความ (`n m`, Available, Max n แถว, Allocation n แถว) |

**ตัวเดินทีละขั้น** (เมนู 4 และเมื่อดู "สถานะทดลอง" ของ request):
`Enter`/`n` ถัดไป · `p` ย้อนกลับ · `r` เริ่มใหม่ · `e` ข้ามไปจบ · `a` เล่นที่เหลือทั้งหมด · `q` ออก

บนหน้าจอ: บรรทัด `>>` อธิบายขั้นนั้น, `Work` และ `Safe sequence` ปรับตามทุกขั้น,
แถวที่กำลังตรวจไฮไลต์เหลือง, ช่อง Need เขียว/แดงตามผลเทียบกับ Work รายคอลัมน์, แถวที่จบแล้วเป็นสีเทา

**ผลของ request**: `GRANTED` (ให้แล้วยัง safe, ยืนยันเพื่อใช้สถานะใหม่ได้) · `WAIT` (ของที่ว่างไม่พอ) ·
`DENIED` (ขอเกิน Need หรือให้แล้ว unsafe → rollback) ตอนถูกปฏิเสธเพราะ unsafe เลือกดูขั้นตอน Safety ของสถานะทดลอง
เพื่อเทียบกับกรณีไม่ใช้ Banker (ถ้าอนุมัติไปเลยจะ unsafe เสี่ยง deadlock)

## โครงสร้างโค้ด

| ไฟล์ | หน้าที่ |
|---|---|
| `banker.h` / `banker.c` | แกน algorithm ไม่มี I/O: `compute_need`, `validate_state`, `safety`, `request`, `random_state` |
| `samples.h` / `samples.c` | ตัวอย่าง 6 ชุด พร้อมคำตอบที่ไล่มือ |
| `main.c` | เมนู, input, ตารางและตัวเดินทีละขั้น (เรียกใช้ core เท่านั้น) |
| `test.c` | เทสต์เทียบกับคำตอบที่ไล่มือ + กรณีขอบ + ข้อมูลสุ่ม 500 ชุด (1281 เช็ก) |

## การทำงาน

- สถานะคือ struct `State` เก็บ `available`, `max`, `alloc` (ขนาดคงที่ 10 process × 6 resource) **Need ไม่เก็บ คำนวณจาก Max − Allocation ทุกครั้ง**
- `safety()` ทำตาม Safety Algorithm: `Work = Available`, หา process ที่ยังไม่จบและ `Need <= Work` (ทุกคอลัมน์), ให้จบแล้วคืน `Work += Allocation`, วนจนไม่มีใครเลือกได้ ถ้าจบครบ = safe
- `request()` ทำตามลำดับ: (1) `Request <= Need` ไม่ผ่าน → `REQ_DENIED_NEED` (2) `Request <= Available` ไม่ผ่าน → `REQ_WAIT` (3) จองให้บน **สำเนา** `trial` (4) รัน `safety()` กับ `trial`: safe → `REQ_GRANTED` ใช้ `trial` เป็นสถานะใหม่ / unsafe → `REQ_DENIED_UNSAFE` ทิ้ง `trial` (rollback: สถานะเดิมไม่ถูกแตะ)
- **ทำไมย้อนกลับได้**: `safety()` รันรวดเดียวและบันทึก "ภาพนิ่ง" ทุกขั้นลงอาร์เรย์ `steps[]` (ชนิดขั้น, process, Work, Finish, sequence) ตัวเดินใน `main.c` แค่เลื่อน index ไปมาแล้ววาดภาพขั้นนั้น
- ข้อความอธิบายแต่ละขั้นสร้างใน `main.c` จากข้อมูลของ step ส่วน core ไม่มีข้อความหรือการพิมพ์ จึงทดสอบแยกได้ง่าย
- ลำดับการไล่ตรวจ: วนผ่าน P0..Pn-1 แล้วค่อยวนรอบใหม่ (ตำราจะกลับไปเริ่มที่ P0 ทุกครั้งที่เจอ) ลำดับ safe sequence อาจต่างกันในบางข้อมูล แต่ผล safe/unsafe ตรงกันเสมอ
