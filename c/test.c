/* test.c — เทียบแกน algorithm กับคำตอบที่ไล่ด้วยมือ  (make test) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "banker.h"
#include "samples.h"

static int passed = 0, failed = 0;
#define CHECK(cond, ...)                                  \
    do {                                                  \
        if (cond) {                                       \
            passed++;                                     \
        } else {                                          \
            failed++;                                     \
            printf("FAIL %s:%d: ", __FILE__, __LINE__);   \
            printf(__VA_ARGS__);                          \
            printf("\n");                                 \
        }                                                 \
    } while (0)

static int vec_eq(const int *a, const int *b, int n) { return memcmp(a, b, sizeof(int) * (size_t)n) == 0; }

static void test_samples(void) {
    char errs[4][ERR_LEN];
    for (int k = 0; k < N_SAMPLES; k++) {
        const Sample *sm = &SAMPLES[k];
        CHECK(validate_state(&sm->state, errs, 4) == 0, "sample %d validate", k + 1);

        SafetyResult sr;
        safety(&sm->state, &sr);
        CHECK(sr.safe == sm->exp_safe, "sample %d safe=%d", k + 1, sr.safe);
        CHECK(sr.seq_len == sm->exp_seq_len && vec_eq(sr.seq, sm->exp_seq, sr.seq_len), "sample %d sequence", k + 1);

        RequestResult rr;
        request(&sm->state, sm->pid, sm->req, &rr);
        CHECK(rr.status == sm->exp_status, "sample %d request status=%d expected=%d", k + 1, rr.status, sm->exp_status);
    }
}

static void test_need(void) {
    int need[MAX_P][MAX_R];
    int expect[5][3] = {{7, 4, 3}, {1, 2, 2}, {6, 0, 0}, {0, 1, 1}, {4, 3, 1}};
    compute_need(&SAMPLES[0].state, need);
    for (int i = 0; i < 5; i++) CHECK(vec_eq(need[i], expect[i], 3), "need P%d", i);
}

static void test_request_effects(void) {
    RequestResult rr;
    request(&SAMPLES[0].state, 1, SAMPLES[0].req, &rr);
    int av[3] = {2, 3, 0}, al[3] = {3, 0, 2};
    CHECK(vec_eq(rr.new_state.available, av, 3), "granted: available");
    CHECK(vec_eq(rr.new_state.alloc[1], al, 3), "granted: alloc");

    State before = SAMPLES[1].state;
    request(&before, 0, SAMPLES[1].req, &rr);
    CHECK(rr.status == REQ_DENIED_UNSAFE && memcmp(&before, &SAMPLES[1].state, sizeof before) == 0,
          "rollback: state เดิมไม่ถูกแก้");
    CHECK(memcmp(&rr.new_state, &before, sizeof before) == 0, "rollback: new_state = เดิม");
    CHECK(rr.has_trial && !rr.safety.safe, "denied unsafe มีสถานะทดลองที่ unsafe ให้ดู");
}

static void test_edges(void) {
    SafetyResult sr;
    RequestResult rr;
    State s;

    memset(&s, 0, sizeof s);
    s.n = 1; s.m = 2; s.max[0][0] = 1; s.max[0][1] = 1;
    safety(&s, &sr);
    CHECK(!sr.safe, "available=0 และ Need>0 -> unsafe");

    memset(&s, 0, sizeof s);
    s.n = 2; s.m = 1; s.max[0][0] = 2; s.alloc[0][0] = 2; s.max[1][0] = 3; s.alloc[1][0] = 3;
    safety(&s, &sr);
    CHECK(sr.safe && sr.seq_len == 2, "ทุก process จบแล้ว -> safe");

    int zero[MAX_R] = {0};
    request(&SAMPLES[0].state, 2, zero, &rr);
    CHECK(rr.status == REQ_GRANTED && memcmp(&rr.new_state, &SAMPLES[0].state, sizeof(State)) == 0,
          "request = 0 -> granted และสถานะไม่เปลี่ยน");

    int neg[MAX_R] = {-1, 0, 0};
    request(&SAMPLES[0].state, 0, neg, &rr);
    CHECK(rr.status == REQ_INVALID, "request ติดลบ -> invalid");
    request(&SAMPLES[0].state, 9, zero, &rr);
    CHECK(rr.status == REQ_INVALID, "pid เกิน -> invalid");

    memset(&s, 0, sizeof s);
    s.n = 1; s.m = 1; s.available[0] = 1; s.max[0][0] = 1;
    int one[MAX_R] = {1};
    request(&s, 0, one, &rr);
    CHECK(rr.status == REQ_GRANTED, "ขอพอดี Available แล้ว safe");
}

static void test_validate(void) {
    char errs[8][ERR_LEN];
    State s;
    memset(&s, 0, sizeof s);
    s.n = 1; s.m = 1; s.available[0] = -1;
    CHECK(validate_state(&s, errs, 8) > 0, "available ติดลบ");
    s.available[0] = 1; s.max[0][0] = 1; s.alloc[0][0] = 2;
    CHECK(validate_state(&s, errs, 8) > 0, "Max < Allocation");
    s.n = 0;
    CHECK(validate_state(&s, errs, 8) > 0, "ไม่มี process");
    s.n = MAX_P + 1;
    CHECK(validate_state(&s, errs, 8) > 0, "process เกินขีดจำกัด");
}

static void test_steps(void) {
    SafetyResult sr;
    safety(&SAMPLES[0].state, &sr);
    CHECK(sr.steps[0].kind == STEP_INIT, "step แรก = init");
    CHECK(sr.steps[sr.nsteps - 1].kind == STEP_DONE, "step สุดท้าย = done");
    int final_work[3] = {10, 5, 7};
    CHECK(vec_eq(sr.steps[sr.nsteps - 1].work, final_work, 3), "Work สุดท้าย = (10,5,7)");
    CHECK(sr.nsteps <= MAX_STEPS, "ไม่เกินขนาดบัฟเฟอร์");
}

static void test_random(void) {
    char errs[4][ERR_LEN];
    srand(12345);
    for (int k = 0; k < 500; k++) {
        State s;
        random_state(&s, 1 + rand() % MAX_P, 1 + rand() % MAX_R);
        CHECK(validate_state(&s, errs, 4) == 0, "random valid");
        SafetyResult sr;
        safety(&s, &sr);
        CHECK(sr.nsteps <= MAX_STEPS, "random: steps ไม่ล้น");
        if (!sr.safe) continue;
        /* ไล่ตาม safe sequence ย้อนตรวจว่าจบได้จริง */
        int need[MAX_P][MAX_R], work[MAX_R], ok = (sr.seq_len == s.n);
        compute_need(&s, need);
        memcpy(work, s.available, sizeof(int) * (size_t)s.m);
        for (int t = 0; t < sr.seq_len && ok; t++) {
            int i = sr.seq[t];
            for (int j = 0; j < s.m; j++) {
                if (need[i][j] > work[j]) ok = 0;
                work[j] += s.alloc[i][j];
            }
        }
        CHECK(ok, "random: safe sequence ตรวจย้อนแล้วถูก");
    }
}

int main(void) {
    test_samples();
    test_need();
    test_request_effects();
    test_edges();
    test_validate();
    test_steps();
    test_random();
    printf("%d passed, %d failed\n", passed, failed);
    return failed ? 1 : 0;
}
