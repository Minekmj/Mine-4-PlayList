#include "aurora.h"

EXPORT void c_compute_aurora_wave(
    float* RESTRICT out_y,
    int steps,
    float h,
    float base_ratio,
    float amp,
    float phase,
    int band_index
) {
    if (!out_y || steps < 0) return;

    float inv_steps = 1.0f / (float)steps;
    float band_f = (float)band_index;
    float w1_freq = (1.15f + band_f * 0.4f) * TWO_PI;
    float w1_offset = phase * 4.0f + band_f * 1.6f;
    float w2_freq = PI * 1.1f;
    float w2_offset = -phase * 1.8f + band_f;

    float h_base = h * base_ratio;
    float h_amp = h * amp;
    float h_w2 = h * 0.016f;
    float step_w1 = inv_steps * w1_freq;
    float step_w2 = inv_steps * w2_freq;

    float phase1 = w1_offset;
    float phase2 = w2_offset;

    for (int n = 0; n <= steps; ++n) {
        out_y[n] = h_base + h_amp * sinf(phase1) + h_w2 * sinf(phase2);
        phase1 += step_w1;
        phase2 += step_w2;
    }
}