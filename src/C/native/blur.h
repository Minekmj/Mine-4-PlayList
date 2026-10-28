#pragma once
#include "common.h"

EXPORT void c_apply_optical_gaussian_blur(
    uint32_t* RESTRICT buf,
    uint32_t* RESTRICT temp,
    int w,
    int h,
    int radius
);