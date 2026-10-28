#pragma once
#include "common.h"

EXPORT void c_render_vanishing_perspective(
    uint32_t* RESTRICT out_buf, int out_w, int out_h,
    const uint32_t* RESTRICT video_src, int src_w, int src_h,
    float vx1, float vy1, float vx2, float vy2,
    float brightness, float black_lift, float gamma, float decay_scale,
    int blur_radius,
    int vignette_enabled, float max_dist_pct, float glow_intensity, float shape_depth, float edge_darkness,
    float saturation, float ca_strength
);