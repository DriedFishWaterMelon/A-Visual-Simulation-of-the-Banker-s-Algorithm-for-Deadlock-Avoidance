/*
 * banker.h — แกน Banker's Algorithm (C99 ล้วน ไม่มี I/O)
 *
 * ทั้ง safety() และ request() บันทึก "ภาพนิ่ง" ของทุกขั้นไว้ใน steps[]
 * ส่วนแสดงผล (main.c) แค่เลื่อน index ไปมา จึงกดถัดไป/ย้อนกลับได้
 */
#ifndef BANKER_H
#define BANKER_H

#define MAX_P 10
#define MAX_R 6
#define MAX_STEPS 256
#define ERR_LEN 160

/* Need ไม่ถูกเก็บ คำนวณจาก max - alloc ทุกครั้ง */
typedef struct {
    int n, m; /* จำนวน process / ชนิด resource */
    int available[MAX_R];
    int max[MAX_P][MAX_R];
    int alloc[MAX_P][MAX_R];
} State;

typedef enum { STEP_INIT, STEP_CHECK, STEP_FINISH, STEP_DONE } StepKind;

typedef struct {
    StepKind kind;
    int pid; /* process ที่ตรวจ/จบ (-1 ถ้าไม่เกี่ยว) */
    int ok;  /* STEP_CHECK: Need <= Work หรือไม่ */
    int work[MAX_R];
    int finish[MAX_P];
    int seq[MAX_P];
    int seq_len;
} Step;

typedef struct {
    int safe;
    int seq[MAX_P]; /* ถ้า unsafe คือลำดับที่ไปได้ก่อนติด */
    int seq_len;
    Step steps[MAX_STEPS];
    int nsteps;
} SafetyResult;

typedef enum {
    REQ_GRANTED,       /* ให้ได้ ยัง safe */
    REQ_WAIT,          /* resource ที่ว่างไม่พอ */
    REQ_DENIED_NEED,   /* ขอเกิน Need */
    REQ_DENIED_UNSAFE, /* ให้แล้ว unsafe -> rollback */
    REQ_INVALID        /* request ไม่ถูกรูปแบบ */
} ReqStatus;

typedef struct {
    ReqStatus status;
    int checked_avail; /* ผ่านขั้น 1 แล้วถึงตรวจขั้น 2 */
    int has_trial;     /* มีสถานะทดลอง (ผ่านขั้น 1-2) */
    State trial;       /* สถานะหลังจองให้แบบทดลอง */
    SafetyResult safety; /* safety ของสถานะทดลอง */
    State new_state;   /* สถานะจริงหลังตัดสิน (denied/wait = เหมือนเดิม) */
} RequestResult;

void compute_need(const State *s, int need[MAX_P][MAX_R]);

/* คืนจำนวนข้อผิดพลาด (0 = ใช้ได้) เขียนข้อความไม่เกิน max_errs ข้อลง errs */
int validate_state(const State *s, char errs[][ERR_LEN], int max_errs);

void safety(const State *s, SafetyResult *out);
void request(const State *s, int pid, const int req[MAX_R], RequestResult *out);

/* สร้างข้อมูลสุ่มที่ valid เสมอ (ใช้ rand()) */
void random_state(State *s, int n, int m);

#endif
