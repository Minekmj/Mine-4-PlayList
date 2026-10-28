#pragma once
#include "common.h"

#define SHADOW_LUT_SIZE 1024

EXPORT void c_render_rounded_box_shadow(
    uint32_t* RESTRICT out_buf, int out_w, int out_h,
    float rect_x, float rect_y, float rect_w, float rect_h,
    float corner_radius, float shadow_radius,
    uint8_t s_r, uint8_t s_g, uint8_t s_b, float s_opacity
);