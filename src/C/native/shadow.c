#include "shadow.h"

EXPORT void c_render_rounded_box_shadow(
    uint32_t* RESTRICT out_buf, int out_w, int out_h,
    float rect_x, float rect_y, float rect_w, float rect_h,
    float corner_radius, float shadow_radius,
    uint8_t s_r, uint8_t s_g, uint8_t s_b, float s_opacity
) {
    if (!out_buf || out_w <= 0 || out_h <= 0) return;

    if (shadow_radius <= 0.0f || s_opacity <= 0.001f) {
        memset(out_buf, 0, (size_t)out_w * out_h * sizeof(uint32_t));
        return;
    }

    float cx = rect_x + rect_w * 0.5f;
    float cy = rect_y + rect_h * 0.5f;
    float r = corner_radius < 0.0f ? 0.0f : corner_radius;
    float max_r = (rect_w < rect_h ? rect_w : rect_h) * 0.5f;
    if (r > max_r) r = max_r;

    float hw = rect_w * 0.5f - r;
    float hh = rect_h * 0.5f - r;
    float inv_sr = 1.0f / shadow_radius;

    float reach_x = hw + r + shadow_radius + 0.5f;
    float reach_y = hh + r + shadow_radius + 0.5f;

    int min_x = (int)floorf(cx - reach_x);
    int max_x = (int)ceilf(cx + reach_x);
    int min_y = (int)floorf(cy - reach_y);
    int max_y = (int)ceilf(cy + reach_y);

    if (min_x < 0) min_x = 0;
    if (min_y < 0) min_y = 0;
    if (max_x >= out_w) max_x = out_w - 1;
    if (max_y >= out_h) max_y = out_h - 1;

    if (min_x > max_x || min_y > max_y) {
        memset(out_buf, 0, (size_t)out_w * out_h * sizeof(uint32_t));
        return;
    }

    if (min_y > 0) memset(out_buf, 0, (size_t)min_y * out_w * sizeof(uint32_t));

    if (max_y + 1 < out_h) {
        memset(out_buf + (size_t)(max_y + 1) * out_w, 0, (size_t)(out_h - 1 - max_y) * out_w * sizeof(uint32_t));
    }

    uint32_t shadow_lut[SHADOW_LUT_SIZE + 1];
    float inv_lut_max = 1.0f / (float)SHADOW_LUT_SIZE;
    float alpha_scale = s_opacity * 255.0f;

    for (int i = 0; i <= SHADOW_LUT_SIZE; ++i) {
        float t = (float)i * inv_lut_max;
        float alpha = expf(-3.2f * t * t) * (1.0f - t);
        uint32_t a = (uint32_t)(alpha * alpha_scale + 0.5f);
        if (a > 255) a = 255;

        if (a > 0) {
            uint32_t pr = ((uint32_t)s_r * a) / 255;
            uint32_t pg = ((uint32_t)s_g * a) / 255;
            uint32_t pb = ((uint32_t)s_b * a) / 255;
            shadow_lut[i] = (a << 24) | (pr << 16) | (pg << 8) | pb;
        } else {
            shadow_lut[i] = 0;
        }
    }

    float lut_scale = inv_sr * (float)SHADOW_LUT_SIZE;

    int span_x = max_x - min_x + 1;
    float stack_qx[STACK_THRESHOLD];
    float stack_ox[STACK_THRESHOLD];

    float* qx_arr = (span_x <= STACK_THRESHOLD) ? stack_qx : (float*)malloc((size_t)span_x * sizeof(float));
    float* ox_arr = (span_x <= STACK_THRESHOLD) ? stack_ox : (float*)malloc((size_t)span_x * sizeof(float));

    if (qx_arr && ox_arr) {
        for (int x = min_x; x <= max_x; ++x) {
            float px = (float)x + 0.5f;
            float qx = fabsf(px - cx) - hw;
            qx_arr[x - min_x] = qx;
            ox_arr[x - min_x] = (qx > 0.0f) ? qx : 0.0f;
        }

        for (int y = min_y; y <= max_y; ++y) {
            float py = (float)y + 0.5f;
            float qy = fabsf(py - cy) - hh;
            float oy = qy > 0.0f ? qy : 0.0f;
            float oy_sq = oy * oy;
            uint32_t* RESTRICT row = out_buf + (size_t)y * out_w;

            if (min_x > 0) memset(row, 0, (size_t)min_x * sizeof(uint32_t));
            if (max_x + 1 < out_w) memset(row + max_x + 1, 0, (size_t)(out_w - 1 - max_x) * sizeof(uint32_t));

            for (int x = min_x; x <= max_x; ++x) {
                float qx = qx_arr[x - min_x];
                float ox = ox_arr[x - min_x];

                float d_outside = (ox > 0.0f && oy > 0.0f) ? sqrtf(ox * ox + oy_sq) : ox + oy;
                float max_q = qx > qy ? qx : qy;
                float d_inside = max_q < 0.0f ? max_q : 0.0f;
                float dist = d_outside + d_inside - r;

                if (dist <= 0.0f) {
                    row[x] = shadow_lut[0];
                } else if (dist < shadow_radius) {
                    int idx = (int)(dist * lut_scale);
                    row[x] = shadow_lut[idx];
                } else {
                    row[x] = 0x00000000u;
                }
            }
        }
    }

    if (qx_arr != stack_qx) free(qx_arr);
    if (ox_arr != stack_ox) free(ox_arr);
}