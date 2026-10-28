#include "perspective.h"

static FORCE_INLINE int sample_single_channel(
    const uint32_t* RESTRICT src, int src_w, int src_h,
    float max_u, float max_v, float u, float v, int shift
) {
    if (u < 0.0f) u = 0.0f; else if (u > max_u) u = max_u;
    if (v < 0.0f) v = 0.0f; else if (v > max_v) v = max_v;
    int x0 = (int)u; int y0 = (int)v;
    int x1 = (x0 + 1 < src_w) ? x0 + 1 : x0;
    int y1 = (y0 + 1 < src_h) ? y0 + 1 : y0;
    int ifx = (int)((u - (float)x0) * 256.0f);
    int ify = (int)((v - (float)y0) * 256.0f);
    int w00 = (256 - ifx) * (256 - ify);
    int w10 = ifx * (256 - ify);
    int w01 = (256 - ifx) * ify;
    int w11 = ifx * ify;
    const uint32_t* r0 = src + (size_t)y0 * src_w;
    const uint32_t* r1 = src + (size_t)y1 * src_w;
    return ((((r0[x0] >> shift) & 255) * w00) +
            (((r0[x1] >> shift) & 255) * w10) +
            (((r1[x0] >> shift) & 255) * w01) +
            (((r1[x1] >> shift) & 255) * w11) + 32768) >> 16;
}

static FORCE_INLINE void render_pixel_fast(
    uint32_t* RESTRICT out_pixel,
    float px,
    float cx, float cy, float inv_hw,
    float dy, float dy_sq, float ny,
    float vx1, float vy1,
    float scale_u, float scale_v,
    const uint32_t* RESTRICT video_src, int src_w, int src_h,
    float max_u, float max_v,
    const float* RESTRICT gamma_lut,
    float brightness, float lift_scale, float safe_lift,
    float decay, float decay_sq,
    int vignette_enabled, float base_max_dist, float glow_intensity,
    float sd_base, float sd_scale, float edge_darkness,
    float saturation, float ca_strength
) {
    float dx = px - cx;
    float nx = fabsf(dx) * inv_hw;
    float m = (nx > ny) ? nx : ny;
    float inv_clamp_m = (m > 1.0f) ? (1.0f / m) : 1.0f;

    float bx = cx + dx * inv_clamp_m;
    float by = cy + dy * inv_clamp_m;
    float u = (bx - vx1) * scale_u;
    float v = (by - vy1) * scale_v;

    int ir_samp, ig_samp, ib_samp;

    if (ca_strength > 0.001f && m > 1.0f) {
        float inv_dist = 1.0f / sqrtf(dx * dx + dy_sq + 1e-5f);
        float off_u = dx * inv_dist * ca_strength * scale_u;
        float off_v = dy * inv_dist * ca_strength * scale_v;

        ir_samp = sample_single_channel(video_src, src_w, src_h, max_u, max_v, u - off_u, v - off_v, 16);
        ig_samp = sample_single_channel(video_src, src_w, src_h, max_u, max_v, u, v, 8);
        ib_samp = sample_single_channel(video_src, src_w, src_h, max_u, max_v, u + off_u, v + off_v, 0);
    } else {
        if (u < 0.0f) u = 0.0f; else if (u > max_u) u = max_u;
        if (v < 0.0f) v = 0.0f; else if (v > max_v) v = max_v;
        int x0 = (int)u; int y0 = (int)v;
        int x1 = (x0 + 1 < src_w) ? x0 + 1 : x0;
        int y1 = (y0 + 1 < src_h) ? y0 + 1 : y0;
        int ifx = (int)((u - (float)x0) * 256.0f);
        int ify = (int)((v - (float)y0) * 256.0f);
        int wx0 = 256 - ifx; int wy0 = 256 - ify;
        int w00 = wx0 * wy0; int w10 = ifx * wy0;
        int w01 = wx0 * ify; int w11 = ifx * ify;

        const uint32_t* r0 = video_src + (size_t)y0 * src_w;
        const uint32_t* r1 = video_src + (size_t)y1 * src_w;
        uint32_t c00 = r0[x0]; uint32_t c10 = r0[x1];
        uint32_t c01 = r1[x0]; uint32_t c11 = r1[x1];

        ir_samp = ((((c00 >> 16) & 255) * w00) + (((c10 >> 16) & 255) * w10) + (((c01 >> 16) & 255) * w01) + (((c11 >> 16) & 255) * w11) + 32768) >> 16;
        ig_samp = ((((c00 >> 8) & 255) * w00) + (((c10 >> 8) & 255) * w10) + (((c01 >> 8) & 255) * w01) + (((c11 >> 8) & 255) * w11) + 32768) >> 16;
        ib_samp = (((c00 & 255) * w00) + ((c10 & 255) * w10) + ((c01 & 255) * w01) + ((c11 & 255) * w11) + 32768) >> 16;
    }

    float r = gamma_lut[ir_samp];
    float g = gamma_lut[ig_samp];
    float b = gamma_lut[ib_samp];
    float factor = brightness;

    if (m > 1.0f) {
        float k = 1.0f - inv_clamp_m;
        float dist = k * sqrtf(dx * dx + dy_sq);

        if (vignette_enabled) {
            int iluma = (ir_samp * 77 + ig_samp * 150 + ib_samp * 29) >> 8;
            int max_c = (ir_samp > ig_samp) ? ((ir_samp > ib_samp) ? ir_samp : ib_samp) : ((ig_samp > ib_samp) ? ig_samp : ib_samp);
            int min_c = (ir_samp < ig_samp) ? ((ir_samp < ib_samp) ? ir_samp : ib_samp) : ((ig_samp < ib_samp) ? ig_samp : ib_samp);
            int chroma = max_c - min_c;

            float color_power = (iluma * 0.70f + chroma * 0.30f) * (1.0f / 255.0f);
            if (color_power > 1.0f) color_power = 1.0f;

            float shape_mod = sd_base + sd_scale * color_power;
            float effective_max_dist = base_max_dist * shape_mod;
            if (effective_max_dist < 12.0f) effective_max_dist = 12.0f;

            if (dist >= effective_max_dist) {
                *out_pixel = 0xFF000000u;
                return;
            }

            float t = dist / effective_max_dist;
            float t2 = t * t;
            float falloff = 1.0f - t2;
            falloff *= falloff;

            float dark_fade = 1.0f - t2 * edge_darkness;
            if (dark_fade < 0.0f) dark_fade = 0.0f;

            factor *= glow_intensity * (0.55f + 0.75f * color_power) * falloff * dark_fade;
        } else {
            float falloff = 1.0f / (1.0f + dist * decay + dist * dist * decay_sq);
            factor *= falloff * lift_scale + safe_lift;
        }

        if (saturation != 1.0f) {
            float avg = (r + g + b) * 0.33333333f;
            r = avg + (r - avg) * saturation;
            g = avg + (g - avg) * saturation;
            b = avg + (b - avg) * saturation;
            if (r < 0.0f) r = 0.0f;
            if (g < 0.0f) g = 0.0f;
            if (b < 0.0f) b = 0.0f;
        }
    }

    float max_c = (r > g) ? ((r > b) ? r : b) : ((g > b) ? g : b);
    if (max_c > 1.0f) {
        float target = max_c * factor;
        float scale = (320.0f * factor) / (target + 45.0f);
        r *= scale; g *= scale; b *= scale;
    }

    uint32_t ir = (uint32_t)r; uint32_t ig = (uint32_t)g; uint32_t ib = (uint32_t)b;
    if (ir > 255) ir = 255; if (ig > 255) ig = 255; if (ib > 255) ib = 255;

    *out_pixel = 0xFF000000u | (ir << 16) | (ig << 8) | ib;
}

EXPORT void c_render_vanishing_perspective(
    uint32_t* RESTRICT out_buf, int out_w, int out_h,
    const uint32_t* RESTRICT video_src, int src_w, int src_h,
    float vx1, float vy1, float vx2, float vy2,
    float brightness, float black_lift, float gamma, float decay_scale,
    int blur_radius,
    int vignette_enabled, float max_dist_pct, float glow_intensity, float shape_depth, float edge_darkness,
    float saturation, float ca_strength
) {
    if (!out_buf || !video_src || out_w <= 0 || out_h <= 0 || src_w <= 0 || src_h <= 0) return;

    float vw = vx2 - vx1;
    float vh = vy2 - vy1;
    size_t out_count = (size_t)out_w * (size_t)out_h;

    if (vw < 1.0f || vh < 1.0f) {
        for (size_t i = 0; i < out_count; ++i) out_buf[i] = 0xFF000000u;
        return;
    }

    float inv_vw = 1.0f / vw;
    float inv_vh = 1.0f / vh;
    float scale_u = (float)(src_w - 1) * inv_vw;
    float scale_v = (float)(src_h - 1) * inv_vh;
    float max_u = (float)(src_w - 1);
    float max_v = (float)(src_h - 1);

    float cx = (vx1 + vx2) * 0.5f;
    float cy = (vy1 + vy2) * 0.5f;
    float hw = vw * 0.5f;
    float hh = vh * 0.5f;
    float inv_hw = 1.0f / hw;
    float inv_hh = 1.0f / hh;

    float inv_gamma = 1.0f / (gamma > 0.1f ? gamma : 1.0f);
    float safe_lift = fminf(1.0f, fmaxf(0.0f, black_lift));
    float lift_scale = 1.0f - safe_lift;

    float gamma_lut[256];
    for (int i = 0; i < 256; ++i) gamma_lut[i] = powf((float)i * (1.0f / 255.0f), inv_gamma) * 255.0f;

    float decay = decay_scale * 0.016f;
    float decay_sq = decay_scale * decay_scale * 0.00012f;

    float fw = (float)out_w;
    float fh = (float)out_h;
    float screen_diag = sqrtf(fw * fw + fh * fh) * 0.50f;
    float base_max_dist = screen_diag * (max_dist_pct * 0.01f);
    if (base_max_dist < 15.0f) base_max_dist = 15.0f;

    float sd60 = shape_depth * 0.60f;
    float sd_base = (1.0f - sd60) + sd60 * 0.40f;
    float sd_scale = sd60;

    float safe_margin = (float)(blur_radius > 2 ? blur_radius : 2);
    float core_x1 = vx1 + safe_margin;
    float core_x2 = vx2 - safe_margin;
    float core_y1 = vy1 + safe_margin;
    float core_y2 = vy2 - safe_margin;
    int has_core = (core_x2 > core_x1 && core_y2 > core_y1);

    int core_left = (int)ceilf(core_x1);
    int core_right = (int)floorf(core_x2);
    if (core_left < 0) core_left = 0;
    if (core_right >= out_w) core_right = out_w - 1;

    for (int y = 0; y < out_h; ++y) {
        float py = (float)y;
        float dy = py - cy;
        float dy_sq = dy * dy;
        float ny = fabsf(dy) * inv_hh;
        uint32_t* RESTRICT out_row = out_buf + (size_t)y * out_w;

        int in_core_y = has_core && py >= core_y1 && py <= core_y2 && core_left <= core_right;

        if (in_core_y) {
            for (int x = 0; x < core_left; ++x) {
                render_pixel_fast(&out_row[x], (float)x, cx, cy, inv_hw, dy, dy_sq, ny,
                    vx1, vy1, scale_u, scale_v, video_src, src_w, src_h, max_u, max_v,
                    gamma_lut, brightness, lift_scale, safe_lift, decay, decay_sq,
                    vignette_enabled, base_max_dist, glow_intensity, sd_base, sd_scale, edge_darkness,
                    saturation, ca_strength);
            }

            for (int x = core_left; x <= core_right; ++x) out_row[x] = 0xFF000000u;

            for (int x = core_right + 1; x < out_w; ++x) {
                render_pixel_fast(&out_row[x], (float)x, cx, cy, inv_hw, dy, dy_sq, ny,
                    vx1, vy1, scale_u, scale_v, video_src, src_w, src_h, max_u, max_v,
                    gamma_lut, brightness, lift_scale, safe_lift, decay, decay_sq,
                    vignette_enabled, base_max_dist, glow_intensity, sd_base, sd_scale, edge_darkness,
                    saturation, ca_strength);
            }
        } else {
            for (int x = 0; x < out_w; ++x) {
                render_pixel_fast(&out_row[x], (float)x, cx, cy, inv_hw, dy, dy_sq, ny,
                    vx1, vy1, scale_u, scale_v, video_src, src_w, src_h, max_u, max_v,
                    gamma_lut, brightness, lift_scale, safe_lift, decay, decay_sq,
                    vignette_enabled, base_max_dist, glow_intensity, sd_base, sd_scale, edge_darkness,
                    saturation, ca_strength);
            }
        }
    }
}