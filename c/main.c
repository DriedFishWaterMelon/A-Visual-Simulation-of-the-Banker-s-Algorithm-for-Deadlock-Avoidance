/*
 * main.c — ส่วนแสดงผลแบบ terminal ของ Banker's Algorithm Simulator
 * เรียกใช้ core (banker.c) เท่านั้น ไม่มีตรรกะ algorithm อยู่ที่นี่
 */
#include <ctype.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "banker.h"
#include "samples.h"

#ifdef _WIN32
#include <windows.h>
#endif

/* ---------- สี (ANSI) ---------- */
static int use_color = 1;
#define RESET "\x1b[0m"
#define BOLD "\x1b[1m"
#define DIM "\x1b[90m"
#define RED "\x1b[31m"
#define GREEN "\x1b[32m"
#define YELLOW "\x1b[33m"
#define BG_YELLOW "\x1b[43;30m"
static const char *C(const char *code) { return use_color ? code : ""; }

/* ---------- input ---------- */
static int read_line(char *buf, size_t n) {
    if (!fgets(buf, (int)n, stdin)) return 0;
    size_t len = strlen(buf);
    if (len && buf[len - 1] == '\n') {
        buf[--len] = 0;
    } else {
        int c; /* บรรทัดยาวเกินบัฟเฟอร์ ทิ้งส่วนที่เหลือ */
        while ((c = getchar()) != '\n' && c != EOF) {}
    }
    if (len && buf[len - 1] == '\r') buf[--len] = 0;
    return 1;
}

/* อ่านจำนวนเต็ม count ตัวจาก s ต้องไม่มีอะไรเหลือ */
static int parse_ints(const char *s, int *out, int count) {
    char *end;
    for (int k = 0; k < count; k++) {
        errno = 0;
        long v = strtol(s, &end, 10);
        if (end == s || errno || v < -1000000 || v > 1000000) return 0;
        out[k] = (int)v;
        s = end;
    }
    while (isspace((unsigned char)*s)) s++;
    return *s == 0;
}

/* ถามจนได้จำนวนเต็ม count ตัวที่ >= lo  คืน 0 ถ้าปิด input (EOF) */
static int ask_ints(const char *prompt, int *out, int count, int lo) {
    char line[256];
    for (;;) {
        printf("%s", prompt);
        fflush(stdout);
        if (!read_line(line, sizeof line)) return 0;
        if (!parse_ints(line, out, count)) {
            printf("%s  ต้องกรอกจำนวนเต็ม %d ตัว คั่นด้วยเว้นวรรค%s\n", C(RED), count, C(RESET));
            continue;
        }
        int ok = 1;
        for (int k = 0; k < count; k++)
            if (out[k] < lo) ok = 0;
        if (!ok) {
            printf("%s  ค่าต้องไม่น้อยกว่า %d%s\n", C(RED), lo, C(RESET));
            continue;
        }
        return 1;
    }
}

static int ask_range(const char *prompt, int lo, int hi, int *out) {
    for (;;) {
        if (!ask_ints(prompt, out, 1, lo)) return 0;
        if (*out <= hi) return 1;
        printf("%s  ต้องอยู่ระหว่าง %d ถึง %d%s\n", C(RED), lo, hi, C(RESET));
    }
}

static int ask_yes(const char *prompt) {
    char line[64];
    printf("%s (y/n): ", prompt);
    fflush(stdout);
    if (!read_line(line, sizeof line)) return 0;
    return line[0] == 'y' || line[0] == 'Y';
}

/* ---------- แสดงผลพื้นฐาน ---------- */
static char *vec_str(char *buf, const int *v, int m) {
    char *p = buf;
    *p++ = '(';
    for (int j = 0; j < m; j++) p += sprintf(p, j ? ", %d" : "%d", v[j]);
    *p++ = ')';
    *p = 0;
    return buf;
}

static void print_state(const State *s) {
    int need[MAX_P][MAX_R];
    compute_need(s, need);
    printf("\n%sAvailable%s:", C(BOLD), C(RESET));
    for (int j = 0; j < s->m; j++) printf("  %c=%d", 'A' + j, s->available[j]);
    printf("\n\n%-8s|%-*s|%-*s|%-*s\n", "Process", s->m * 3 + 1, "Allocation", s->m * 3 + 1, "Max", s->m * 3,
           "Need");
    printf("%-8s|", "");
    for (int t = 0; t < 3; t++) {
        for (int j = 0; j < s->m; j++) printf(" %c ", 'A' + j);
        printf(t < 2 ? " |" : "\n");
    }
    for (int i = 0; i < s->n; i++) {
        printf("P%-7d|", i);
        for (int j = 0; j < s->m; j++) printf("%2d ", s->alloc[i][j]);
        printf(" |");
        for (int j = 0; j < s->m; j++) printf("%2d ", s->max[i][j]);
        printf(" |");
        for (int j = 0; j < s->m; j++) printf("%2d ", need[i][j]);
        printf("\n");
    }
    printf("\n");
}

static void print_seq(const int *seq, int len) {
    for (int k = 0; k < len; k++) printf("%sP%d", k ? ", " : "", seq[k]);
}

/* ---------- ตัวเดินทีละขั้นของ Safety Algorithm ---------- */
static void render_step(const State *s, const SafetyResult *r, int idx, const char *label) {
    const Step *st = &r->steps[idx];
    int need[MAX_P][MAX_R];
    char b1[64], b2[64], b3[64];
    compute_need(s, need);

    printf("\n%s=== Safety Algorithm: %s — ขั้นที่ %d/%d ===%s\n", C(BOLD), label, idx + 1, r->nsteps, C(RESET));
    printf("Work = %s%s%s   Safe sequence = <", C(BOLD), vec_str(b1, st->work, s->m), C(RESET));
    print_seq(st->seq, st->seq_len);
    printf(">\n");

    /* คำอธิบายของขั้นนี้ */
    printf("%s>> ", C(YELLOW));
    switch (st->kind) {
    case STEP_INIT:
        printf("เริ่มต้น: Work = Available = %s, Finish[i] = false ทุกตัว", vec_str(b1, st->work, s->m));
        break;
    case STEP_CHECK:
        if (st->ok)
            printf("P%d: Need %s <= Work %s -> รันจนจบได้", st->pid, vec_str(b1, need[st->pid], s->m),
                   vec_str(b2, st->work, s->m));
        else
            printf("P%d: Need %s ไม่ <= Work %s -> ยังรันไม่ได้ ข้ามไปก่อน", st->pid, vec_str(b1, need[st->pid], s->m),
                   vec_str(b2, st->work, s->m));
        break;
    case STEP_FINISH:
        printf("P%d จบงานแล้วคืน Allocation %s: Work = %s + %s = %s", st->pid, vec_str(b1, s->alloc[st->pid], s->m),
               vec_str(b2, r->steps[idx - 1].work, s->m), b1, vec_str(b3, st->work, s->m));
        break;
    case STEP_DONE:
        if (st->ok) {
            printf("ทุก process จบได้ -> SAFE state, safe sequence = <");
            print_seq(st->seq, st->seq_len);
            printf(">");
        } else {
            printf("UNSAFE: process ที่ติดค้าง = {");
            int first = 1;
            for (int i = 0; i < s->n; i++)
                if (!st->finish[i]) printf(first ? "P%d" : ", P%d", i), first = 0;
            printf("} ไม่มีตัวใดที่ Need <= Work (เสี่ยง deadlock)");
        }
        break;
    }
    printf("%s\n\n", C(RESET));

    /* ตาราง: แถวที่กำลังตรวจไฮไลต์เหลือง, ช่อง Need เขียว/แดงตามผลเทียบกับ Work */
    printf("%-8s|%-*s|%-*s| Finish\n", "Process", s->m * 3 + 1, "Allocation", s->m * 3 + 1, "Need");
    for (int i = 0; i < s->n; i++) {
        int checking = (st->kind == STEP_CHECK || st->kind == STEP_FINISH) && st->pid == i;
        int done = st->finish[i] && !(st->kind == STEP_FINISH && st->pid == i);
        const char *rowc = checking ? BG_YELLOW : done ? DIM : "";
        printf("%s%s%-7d%s|", C(rowc), "P", i, C(RESET));
        for (int j = 0; j < s->m; j++) printf("%s%2d %s", C(rowc), s->alloc[i][j], C(RESET));
        printf(" |");
        for (int j = 0; j < s->m; j++) {
            const char *c = rowc;
            if (st->kind == STEP_CHECK && st->pid == i) c = need[i][j] <= st->work[j] ? GREEN : RED;
            printf("%s%2d %s", C(c), need[i][j], C(RESET));
        }
        printf(" | %s%s%s%s\n", C(rowc), st->finish[i] ? "true" : "false", C(RESET),
               checking && st->kind == STEP_CHECK ? "   <-- กำลังตรวจ" : "");
    }
}

static void step_viewer(const State *s, const SafetyResult *r, const char *label) {
    int idx = 0;
    char line[64];
    for (;;) {
        render_step(s, r, idx, label);
        printf("\n[Enter/n]=ถัดไป  p=ย้อนกลับ  r=เริ่มใหม่  e=ข้ามไปจบ  a=เล่นต่อทั้งหมด  q=ออก > ");
        fflush(stdout);
        if (!read_line(line, sizeof line)) return;
        char c = line[0];
        if (c == 'q' || c == 'Q') return;
        if (c == 'p' || c == 'P') idx = idx > 0 ? idx - 1 : 0;
        else if (c == 'r' || c == 'R') idx = 0;
        else if (c == 'e' || c == 'E') idx = r->nsteps - 1;
        else if (c == 'a' || c == 'A') {
            for (idx++; idx < r->nsteps; idx++) render_step(s, r, idx, label);
            idx = r->nsteps - 1;
            printf("\n(จบแล้ว) p=ย้อนกลับ r=เริ่มใหม่ q=ออก\n");
        } else if (idx < r->nsteps - 1) idx++;
        else printf("อยู่ขั้นสุดท้ายแล้ว (p=ย้อนกลับ r=เริ่มใหม่ q=ออก)\n");
    }
}

/* ---------- Request ---------- */
static void do_request(State *cur, int sample_idx) {
    int pid, req[MAX_R] = {0}, need[MAX_P][MAX_R];
    char b1[64], b2[64], prompt[96];

    if (!ask_range("เลือก process (หมายเลข): ", 0, cur->n - 1, &pid)) return;
    compute_need(cur, need);
    printf("P%d: Need = %s, Available = %s\n", pid, vec_str(b1, need[pid], cur->m), vec_str(b2, cur->available, cur->m));

    int use_sample = 0;
    if (sample_idx >= 0 && SAMPLES[sample_idx].pid == pid) {
        printf("request ของตัวอย่างนี้: %s\n", vec_str(b1, SAMPLES[sample_idx].req, cur->m));
        use_sample = ask_yes("ใช้ค่านี้");
    }
    if (use_sample) memcpy(req, SAMPLES[sample_idx].req, sizeof req);
    else {
        snprintf(prompt, sizeof prompt, "จำนวนที่ขอ %d ตัว (เช่น 1 0 2): ", cur->m);
        if (!ask_ints(prompt, req, cur->m, 0)) return;
    }

    RequestResult rr;
    request(cur, pid, req, &rr);
    printf("\n%sP%d ขอ %s%s\n", C(BOLD), pid, vec_str(b1, req, cur->m), C(RESET));
    printf("  ขั้น 1: Request <= Need?      %s%s%s  %s %s %s\n", C(rr.status == REQ_DENIED_NEED ? RED : GREEN),
           rr.status == REQ_DENIED_NEED ? "ไม่ผ่าน" : "ผ่าน", C(RESET), b1, rr.status == REQ_DENIED_NEED ? "เกิน" : "<=",
           vec_str(b2, need[pid], cur->m));
    if (rr.status != REQ_DENIED_NEED && rr.status != REQ_INVALID)
        printf("  ขั้น 2: Request <= Available? %s%s%s\n", C(rr.status == REQ_WAIT ? RED : GREEN),
               rr.status == REQ_WAIT ? "ไม่ผ่าน" : "ผ่าน", C(RESET));
    if (rr.has_trial) {
        printf("  ขั้น 3: จองให้แบบทดลอง  Available = %s\n", vec_str(b1, rr.trial.available, cur->m));
        printf("  ขั้น 4: สถานะหลังทดลองเป็น safe? %s%s%s\n", C(rr.safety.safe ? GREEN : RED),
               rr.safety.safe ? "ใช่" : "ไม่ใช่", C(RESET));
    }

    printf("\n");
    switch (rr.status) {
    case REQ_GRANTED:
        printf("%s[GRANTED] อนุมัติ: หลังให้แล้วระบบยัง safe, safe sequence = <", C(GREEN));
        print_seq(rr.safety.seq, rr.safety.seq_len);
        printf(">%s\n", C(RESET));
        break;
    case REQ_WAIT:
        printf("%s[WAIT] ต้องรอ: resource ที่ว่างอยู่ไม่พอ%s\n", C(YELLOW), C(RESET));
        break;
    case REQ_DENIED_NEED:
        printf("%s[DENIED] ปฏิเสธ: ขอเกิน Need (เกิน Max ที่ประกาศไว้) ถือเป็นข้อผิดพลาด%s\n", C(RED), C(RESET));
        break;
    case REQ_DENIED_UNSAFE:
        printf("%s[DENIED] ปฏิเสธ: ถ้าให้แล้วระบบเข้า unsafe state -> rollback กลับสถานะเดิม ให้ P%d รอ%s\n", C(RED),
               pid, C(RESET));
        printf("เทียบกรณีไม่ใช้ Banker: ถ้าอนุมัติไปเลย ระบบจะเข้า unsafe state ตามที่ดูได้จากขั้นตอนทดลองถัดไป (เสี่ยง deadlock)\n");
        break;
    case REQ_INVALID:
        printf("%s[INVALID] request ไม่ถูกต้อง%s\n", C(RED), C(RESET));
        break;
    }

    if (rr.has_trial && ask_yes("ดูขั้นตอน Safety ของสถานะทดลอง")) {
        snprintf(prompt, sizeof prompt, "สถานะทดลองหลังให้ P%d", pid);
        step_viewer(&rr.trial, &rr.safety, prompt);
    }
    if (rr.status == REQ_GRANTED && ask_yes("ยืนยันใช้สถานะใหม่ต่อ")) {
        *cur = rr.new_state;
        printf("อัปเดตสถานะแล้ว\n");
        print_state(cur);
    }
}

/* ---------- แก้ไข / ไฟล์ ---------- */
static int report_errors(const State *s) {
    char errs[8][ERR_LEN];
    int cnt = validate_state(s, errs, 8);
    if (cnt) {
        printf("%sข้อมูลไม่ถูกต้อง (ไม่บันทึก):%s\n", C(RED), C(RESET));
        for (int k = 0; k < cnt && k < 8; k++) printf("  - %s\n", errs[k]);
        if (cnt > 8) printf("  ... และอีก %d ข้อ\n", cnt - 8);
    }
    return cnt;
}

static void edit_state(State *cur) {
    State s;
    char prompt[96];
    memset(&s, 0, sizeof s);
    if (!ask_range("จำนวน process (1-10): ", 1, MAX_P, &s.n)) return;
    if (!ask_range("จำนวนชนิด resource (1-6): ", 1, MAX_R, &s.m)) return;
    snprintf(prompt, sizeof prompt, "Available (%d ค่า): ", s.m);
    if (!ask_ints(prompt, s.available, s.m, 0)) return;
    for (int i = 0; i < s.n; i++) {
        snprintf(prompt, sizeof prompt, "P%d Allocation (%d ค่า): ", i, s.m);
        if (!ask_ints(prompt, s.alloc[i], s.m, 0)) return;
        snprintf(prompt, sizeof prompt, "P%d Max        (%d ค่า): ", i, s.m);
        if (!ask_ints(prompt, s.max[i], s.m, 0)) return;
    }
    if (report_errors(&s)) return;
    *cur = s;
    printf("บันทึกข้อมูลแล้ว\n");
    print_state(cur);
}

static void save_file(const State *s) {
    char path[256];
    printf("ชื่อไฟล์ที่จะบันทึก: ");
    fflush(stdout);
    if (!read_line(path, sizeof path) || !path[0]) return;
    FILE *f = fopen(path, "w");
    if (!f) {
        printf("%sเปิดไฟล์ไม่ได้%s\n", C(RED), C(RESET));
        return;
    }
    fprintf(f, "%d %d\n", s->n, s->m);
    for (int j = 0; j < s->m; j++) fprintf(f, "%d ", s->available[j]);
    fprintf(f, "\n");
    for (int i = 0; i < s->n; i++) {
        for (int j = 0; j < s->m; j++) fprintf(f, "%d ", s->max[i][j]);
        fprintf(f, "\n");
    }
    for (int i = 0; i < s->n; i++) {
        for (int j = 0; j < s->m; j++) fprintf(f, "%d ", s->alloc[i][j]);
        fprintf(f, "\n");
    }
    fclose(f);
    printf("บันทึกแล้ว (รูปแบบ: n m / Available / Max n แถว / Allocation n แถว)\n");
}

static int load_file(State *cur) {
    char path[256];
    printf("ชื่อไฟล์ที่จะโหลด: ");
    fflush(stdout);
    if (!read_line(path, sizeof path) || !path[0]) return 0;
    FILE *f = fopen(path, "r");
    if (!f) {
        printf("%sเปิดไฟล์ไม่ได้%s\n", C(RED), C(RESET));
        return 0;
    }
    State s;
    memset(&s, 0, sizeof s);
    int ok = fscanf(f, "%d %d", &s.n, &s.m) == 2 && s.n >= 1 && s.n <= MAX_P && s.m >= 1 && s.m <= MAX_R;
    for (int j = 0; ok && j < s.m; j++) ok = fscanf(f, "%d", &s.available[j]) == 1;
    for (int i = 0; ok && i < s.n; i++)
        for (int j = 0; ok && j < s.m; j++) ok = fscanf(f, "%d", &s.max[i][j]) == 1;
    for (int i = 0; ok && i < s.n; i++)
        for (int j = 0; ok && j < s.m; j++) ok = fscanf(f, "%d", &s.alloc[i][j]) == 1;
    fclose(f);
    if (!ok) {
        printf("%sรูปแบบไฟล์ไม่ถูกต้อง%s\n", C(RED), C(RESET));
        return 0;
    }
    if (report_errors(&s)) return 0;
    *cur = s;
    printf("โหลดแล้ว\n");
    print_state(cur);
    return 1;
}

/* ---------- เมนูหลัก ---------- */
static void print_menu(void) {
    printf("\n%s==== Banker's Algorithm Simulator ====%s\n", C(BOLD), C(RESET));
    printf(" 1) โหลดชุดตัวอย่าง\n");
    printf(" 2) แสดงสถานะ (Available / Allocation / Max / Need)\n");
    printf(" 3) กรอก/แก้ไขข้อมูลเอง\n");
    printf(" 4) Safety Algorithm ทีละขั้น\n");
    printf(" 5) จำลอง Resource Request\n");
    printf(" 6) สุ่มข้อมูล\n");
    printf(" 7) บันทึกลงไฟล์   8) โหลดจากไฟล์\n");
    printf(" 0) ออก\n");
}

int main(int argc, char **argv) {
    for (int k = 1; k < argc; k++)
        if (strcmp(argv[k], "--no-color") == 0) use_color = 0;

#ifdef _WIN32
    SetConsoleOutputCP(65001); /* แสดงภาษาไทย (UTF-8) */
    HANDLE h = GetStdHandle(STD_OUTPUT_HANDLE);
    DWORD mode = 0;
    if (GetConsoleMode(h, &mode)) SetConsoleMode(h, mode | 0x0004); /* เปิด ANSI color */
    else use_color = 0;
#endif
    srand((unsigned)time(NULL));

    State cur = SAMPLES[0].state;
    int sample_idx = 0;
    char line[64];

    printf("โหลดตัวอย่างที่ 1 ให้เริ่มต้นแล้ว: %s\n", SAMPLES[0].desc);
    print_state(&cur);

    for (;;) {
        print_menu();
        printf("เลือก > ");
        fflush(stdout);
        if (!read_line(line, sizeof line)) break;
        int choice;
        if (!parse_ints(line, &choice, 1)) {
            printf("%sกรอกตัวเลขของเมนู%s\n", C(RED), C(RESET));
            continue;
        }
        switch (choice) {
        case 0:
            return 0;
        case 1: {
            for (int k = 0; k < N_SAMPLES; k++) printf(" %s\n    %s%s%s\n", SAMPLES[k].name, C(DIM), SAMPLES[k].desc, C(RESET));
            int k;
            if (!ask_range("เลือกตัวอย่าง (1-6): ", 1, N_SAMPLES, &k)) return 0;
            cur = SAMPLES[k - 1].state;
            sample_idx = k - 1;
            printf("โหลด: %s\n", SAMPLES[k - 1].name);
            print_state(&cur);
            break;
        }
        case 2:
            print_state(&cur);
            break;
        case 3:
            edit_state(&cur);
            sample_idx = -1;
            break;
        case 4: {
            SafetyResult sr;
            safety(&cur, &sr);
            step_viewer(&cur, &sr, "สถานะปัจจุบัน");
            break;
        }
        case 5:
            do_request(&cur, sample_idx);
            break;
        case 6:
            random_state(&cur, cur.n, cur.m);
            sample_idx = -1;
            printf("สุ่มข้อมูลแล้ว (%d process, %d resource, รับประกัน Max >= Allocation)\n", cur.n, cur.m);
            print_state(&cur);
            break;
        case 7:
            save_file(&cur);
            break;
        case 8:
            if (load_file(&cur)) sample_idx = -1;
            break;
        default:
            printf("%sไม่มีเมนูนี้%s\n", C(RED), C(RESET));
        }
    }
    return 0;
}
