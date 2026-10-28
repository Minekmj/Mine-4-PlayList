#include "audio.h"

EXPORT float c_calculate_frame_db(const float* RESTRICT samples, int count) {
    if (count <= 0 || !samples) return -120.0f;

    float s0 = 0.0f, s1 = 0.0f, s2 = 0.0f, s3 = 0.0f;
    float s4 = 0.0f, s5 = 0.0f, s6 = 0.0f, s7 = 0.0f;

    int i = 0;
    int count_simd = count & ~7;

    for (; i < count_simd; i += 8) {
        float v0 = samples[i];
        float v1 = samples[i + 1];
        float v2 = samples[i + 2];
        float v3 = samples[i + 3];
        float v4 = samples[i + 4];
        float v5 = samples[i + 5];
        float v6 = samples[i + 6];
        float v7 = samples[i + 7];

        s0 += v0 * v0;
        s1 += v1 * v1;
        s2 += v2 * v2;
        s3 += v3 * v3;
        s4 += v4 * v4;
        s5 += v5 * v5;
        s6 += v6 * v6;
        s7 += v7 * v7;
    }

    float sum_sq = (s0 + s1 + s2 + s3) + (s4 + s5 + s6 + s7);

    for (; i < count; ++i) {
        float val = samples[i];
        sum_sq += val * val;
    }

    float mean_sq = sum_sq / (float)count;
    
    if (mean_sq < 1e-10f) {
        return -100.0f;
    }

    return 10.0f * log10f(mean_sq);
}