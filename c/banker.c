#include "banker.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int vec_leq(const int *a, const int *b, int m) {
    for (int j = 0; j < m; j++)
        if (a[j] > b[j]) return 0;
    return 1;
}

void compute_need(const State *s, int need[MAX_P][MAX_R]) {
    for (int i = 0; i < s->n; i++)
        for (int j = 0; j < s->m; j++) need[i][j] = s->max[i][j] - s->alloc[i][j];
}

int validate_state(const State *s, char errs[][ERR_LEN], int max_errs) {
    int cnt = 0;
#define ADD(...)                                              \
    do {                                                      \
        if (cnt < max_errs) snprintf(errs[cnt], ERR_LEN, __VA_ARGS__); \
        cnt++;                                                \
    } while (0)

    if (s->n < 1 || s->n > MAX_P || s->m < 1 || s->m > MAX_R) {
        ADD("จำนวน process ต้อง 1-%d และ resource ต้อง 1-%d", MAX_P, MAX_R);
        return cnt;
    }
    for (int j = 0; j < s->m; j++)
        if (s->available[j] < 0) ADD("Available[%c] ติดลบ", 'A' + j);
    for (int i = 0; i < s->n; i++)
        for (int j = 0; j < s->m; j++) {
            if (s->max[i][j] < 0) ADD("Max ของ P%d ช่อง %c ติดลบ", i, 'A' + j);
            if (s->alloc[i][j] < 0) ADD("Allocation ของ P%d ช่อง %c ติดลบ", i, 'A' + j);
            if (s->max[i][j] >= 0 && s->alloc[i][j] >= 0 && s->max[i][j] < s->alloc[i][j])
                ADD("P%d ช่อง %c: Max (%d) < Allocation (%d) ทำให้ Need ติดลบ", i, 'A' + j, s->max[i][j],
                    s->alloc[i][j]);
        }
#undef ADD
    return cnt;
}

static void push(SafetyResult *r, const State *s, StepKind kind, int pid, int ok, const int *work,
                 const int *finish, const int *seq, int seq_len) {
    Step *st = &r->steps[r->nsteps++];
    memset(st, 0, sizeof *st);
    st->kind = kind;
    st->pid = pid;
    st->ok = ok;
    memcpy(st->work, work, sizeof(int) * (size_t)s->m);
    memcpy(st->finish, finish, sizeof(int) * (size_t)s->n);
    memcpy(st->seq, seq, sizeof(int) * (size_t)seq_len);
    st->seq_len = seq_len;
}

void safety(const State *s, SafetyResult *out) {
    int need[MAX_P][MAX_R];
    int work[MAX_R], finish[MAX_P] = {0}, seq[MAX_P] = {0}, seq_len = 0;
    compute_need(s, need);
    memcpy(work, s->available, sizeof(int) * (size_t)s->m);
    out->nsteps = 0;

    push(out, s, STEP_INIT, -1, 0, work, finish, seq, seq_len);

    int progress = 1;
    while (seq_len < s->n && progress) {
        progress = 0;
        for (int i = 0; i < s->n; i++) {
            if (finish[i]) continue;
            int ok = vec_leq(need[i], work, s->m);
            push(out, s, STEP_CHECK, i, ok, work, finish, seq, seq_len);
            if (ok) {
                for (int j = 0; j < s->m; j++) work[j] += s->alloc[i][j];
                finish[i] = 1;
                seq[seq_len++] = i;
                progress = 1;
                push(out, s, STEP_FINISH, i, 1, work, finish, seq, seq_len);
            }
        }
    }
    push(out, s, STEP_DONE, -1, seq_len == s->n, work, finish, seq, seq_len);
    out->safe = (seq_len == s->n);
    out->seq_len = seq_len;
    memcpy(out->seq, seq, sizeof(int) * (size_t)seq_len);
}

void request(const State *s, int pid, const int req[MAX_R], RequestResult *out) {
    memset(out, 0, sizeof *out);
    out->new_state = *s;
    if (pid < 0 || pid >= s->n) {
        out->status = REQ_INVALID;
        return;
    }
    for (int j = 0; j < s->m; j++)
        if (req[j] < 0) {
            out->status = REQ_INVALID;
            return;
        }

    int need[MAX_P][MAX_R];
    compute_need(s, need);

    /* ขั้น 1: Request <= Need */
    if (!vec_leq(req, need[pid], s->m)) {
        out->status = REQ_DENIED_NEED;
        return;
    }
    /* ขั้น 2: Request <= Available */
    out->checked_avail = 1;
    if (!vec_leq(req, s->available, s->m)) {
        out->status = REQ_WAIT;
        return;
    }
    /* ขั้น 3: ทดลองจอง (ทำบนสำเนา) */
    out->trial = *s;
    out->has_trial = 1;
    for (int j = 0; j < s->m; j++) {
        out->trial.available[j] -= req[j];
        out->trial.alloc[pid][j] += req[j];
    }
    /* ขั้น 4: ตรวจ safety */
    safety(&out->trial, &out->safety);
    if (out->safety.safe) {
        out->status = REQ_GRANTED;
        out->new_state = out->trial;
    } else {
        out->status = REQ_DENIED_UNSAFE; /* rollback: new_state ยังเป็นค่าเดิม */
    }
}

void random_state(State *s, int n, int m) {
    memset(s, 0, sizeof *s);
    s->n = n;
    s->m = m;
    for (int i = 0; i < n; i++)
        for (int j = 0; j < m; j++) {
            int mx = rand() % 10;
            s->max[i][j] = mx;
            s->alloc[i][j] = rand() % (mx + 1);
        }
    for (int j = 0; j < m; j++) s->available[j] = rand() % 6;
}
