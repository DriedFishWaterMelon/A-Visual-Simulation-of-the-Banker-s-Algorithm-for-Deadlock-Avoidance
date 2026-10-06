/* samples.h — ชุดตัวอย่าง + คำตอบที่ไล่ด้วยมือ (ใช้ทั้งในโปรแกรมและ test) */
#ifndef SAMPLES_H
#define SAMPLES_H

#include "banker.h"

typedef struct {
    const char *name;
    const char *desc;
    State state;
    int pid;
    int req[MAX_R];
    int exp_safe;
    int exp_seq[MAX_P];
    int exp_seq_len;
    ReqStatus exp_status;
} Sample;

extern const Sample SAMPLES[];
extern const int N_SAMPLES;

#endif
