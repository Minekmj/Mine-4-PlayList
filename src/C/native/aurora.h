#pragma once
#include "common.h"

EXPORT void c_compute_aurora_wave(
    float* RESTRICT out_y,
    int steps,
    float h,
    float base_ratio,
    float amp,
    float phase,
    int band_index
);