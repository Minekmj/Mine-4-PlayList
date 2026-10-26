#include <math.h>
#include <stdint.h>
#include <stdlib.h>

#if defined(_WIN32) || defined(__CYGWIN__)
#define EXPORT __declspec(dllexport)
#else
#define EXPORT __attribute__((visibility("default")))
#endif

#define PI 3.14159265358979323846f
#define TWO_PI 6.28318530717958647692f

static inline void render_pixel_fast(
    uint32_t* out_pixel,
    float px,
    float cx, float cy, float inv_hw,
    float dy, float dy_sq, float ny,
    float vx1, float vy1,
    float scale_u, float scale_v,
    const uint32_t* video_src, int src_w, int src_h,
    float max_u, float max_v,
    const float* gamma_lut,
    float brightness, float lift_scale, float safe_lift,
    float decay, float decay_sq,
    int vignette_enabled, float base_max_dist, float glow_intensity, float shape_depth, float edge_darkness
) {
    float dx = px - cx;
    float nx = fabsf(dx) * inv_hw;
    float m = (nx > ny) ? nx : ny;
    float inv_clamp_m = (m > 1.0f) ? (1.0f / m) : 1.0f;

    float bx = cx + dx * inv_clamp_m;
    float by = cy + dy * inv_clamp_m;
    float u = (bx - vx1) * scale_u;
    float v = (by - vy1) * scale_v;

    u = fmaxf(0.0f, fminf(u, max_u));
    v = fmaxf(0.0f, fminf(v, max_v));

    int x0 = (int)u;
    int y0 = (int)v;
    int x1 = (x0 + 1 < src_w) ? (x0 + 1) : x0;
    int y1 = (y0 + 1 < src_h) ? (y0 + 1) : y0;
    float fx = u - (float)x0;
    float fy = v - (float)y0;

    const uint32_t* r0 = video_src + (size_t)y0 * src_w;
    const uint32_t* r1 = video_src + (size_t)y1 * src_w;
    uint32_t c00 = r0[x0], c10 = r0[x1];
    uint32_t c01 = r1[x0], c11 = r1[x1];

    float r00 = (float)((c00 >> 16) & 255), r10 = (float)((c10 >> 16) & 255);
    float r01 = (float)((c01 >> 16) & 255), r11 = (float)((c11 >> 16) & 255);
    int ir_samp = (int)(r00 + fx * (r10 - r00) + fy * ((r01 + fx * (r11 - r01)) - (r00 + fx * (r10 - r00))));

    float g00 = (float)((c00 >> 8) & 255), g10 = (float)((c10 >> 8) & 255);
    float g01 = (float)((c01 >> 8) & 255), g11 = (float)((c11 >> 8) & 255);
    int ig_samp = (int)(g00 + fx * (g10 - g00) + fy * ((g01 + fx * (g11 - g01)) - (g00 + fx * (g10 - g00))));

    float b00 = (float)(c00 & 255), b10 = (float)(c10 & 255);
    float b01 = (float)(c01 & 255), b11 = (float)(c11 & 255);
    int ib_samp = (int)(b00 + fx * (b10 - b00) + fy * ((b01 + fx * (b11 - b01)) - (b00 + fx * (b10 - b00))));

    if (ir_samp < 0) ir_samp = 0; else if (ir_samp > 255) ir_samp = 255;
    if (ig_samp < 0) ig_samp = 0; else if (ig_samp > 255) ig_samp = 255;
    if (ib_samp < 0) ib_samp = 0; else if (ib_samp > 255) ib_samp = 255;

    float r = gamma_lut[ir_samp];
    float g = gamma_lut[ig_samp];
    float b = gamma_lut[ib_samp];
    float factor = brightness;

    if (m > 1.0f) {
        float k = 1.0f - inv_clamp_m;
        float dist = k * sqrtf(dx * dx + dy_sq);

        if (vignette_enabled) {
            // 밝기(Luma) 및 채도(Chroma) 추출
            int iluma = (ir_samp * 77 + ig_samp * 150 + ib_samp * 29) >> 8;
            int max_c = (ir_samp > ig_samp) ? ((ir_samp > ib_samp) ? ir_samp : ib_samp) : ((ig_samp > ib_samp) ? ig_samp : ib_samp);
            int min_c = (ir_samp < ig_samp) ? ((ir_samp < ib_samp) ? ir_samp : ib_samp) : ((ig_samp < ib_samp) ? ig_samp : ib_samp);
            int chroma = max_c - min_c;

            float luma_f = (float)iluma * (1.0f / 255.0f);
            float chroma_f = (float)chroma * (1.0f / 255.0f);
            float color_power = luma_f * 0.70f + chroma_f * 0.30f;
            if (color_power > 1.0f) color_power = 1.0f;

            // 암부도 최소 40% 도달 보장, 밝은 곳은 140%까지 돌출되는 안전 형상 비율
            float shape_mod = (1.0f - shape_depth * 0.60f) + (shape_depth * 0.60f) * (0.40f + 1.0f * color_power);
            float effective_max_dist = base_max_dist * shape_mod;
            if (effective_max_dist < 12.0f) effective_max_dist = 12.0f;

            if (dist >= effective_max_dist) {
                *out_pixel = 0xFF000000u;
                return;
            }

            float t = dist / effective_max_dist; // 0.0 ~ 1.0
            float falloff = (1.0f - t * t);
            falloff = falloff * falloff; // (1 - t^2)^2

            float dark_fade = 1.0f - (t * t) * edge_darkness;
            if (dark_fade < 0.0f) dark_fade = 0.0f;

            factor = factor * glow_intensity * (0.55f + 0.75f * color_power) * falloff * dark_fade;

            // 채도 보존 (+20%)
            float avg = (r + g + b) * 0.3333333f;
            r = avg + (r - avg) * 1.20f;
            g = avg + (g - avg) * 1.20f;
            b = avg + (b - avg) * 1.20f;
            if (r < 0.0f) r = 0.0f;
            if (g < 0.0f) g = 0.0f;
            if (b < 0.0f) b = 0.0f;
        } else {
            float falloff = 1.0f / (1.0f + dist * decay + dist * dist * decay_sq);
            factor *= (falloff * lift_scale + safe_lift);
        }
    }

    float max_c = fmaxf(r, fmaxf(g, b));
    if (max_c > 1.0f) {
        float target = max_c * factor;
        float scale = (320.0f * factor) / (target + 45.0f);
        r *= scale;
        g *= scale;
        b *= scale;
    }

    uint32_t ir = (uint32_t)r;
    uint32_t ig = (uint32_t)g;
    uint32_t ib = (uint32_t)b;
    if (ir > 255) ir = 255;
    if (ig > 255) ig = 255;
    if (ib > 255) ib = 255;

    *out_pixel = 0xFF000000u | (ir << 16) | (ig << 8) | ib;
}

EXPORT void c_render_vanishing_perspective(
    uint32_t* out_buf, int out_w, int out_h,
    const uint32_t* video_src, int src_w, int src_h,
    float vx1, float vy1, float vx2, float vy2,
    float brightness, float black_lift, float gamma, float decay_scale,
    int blur_radius,
    int vignette_enabled, float max_dist_pct, float glow_intensity, float shape_depth, float edge_darkness
) {
    if (!out_buf || !video_src || out_w <= 0 || out_h <= 0 || src_w <= 0 || src_h <= 0) return;
    
    float vw = vx2 - vx1, vh = vy2 - vy1;
    size_t out_count = (size_t)out_w * (size_t)out_h;
    if (vw < 1.0f || vh < 1.0f) {
        size_t i;
        for (i = 0; i < out_count; ++i) out_buf[i] = 0xFF000000u;
        return;
    }

    float inv_vw = 1.0f / vw, inv_vh = 1.0f / vh;
    float scale_u = (float)(src_w - 1) * inv_vw;
    float scale_v = (float)(src_h - 1) * inv_vh;
    float max_u = (float)(src_w - 1);
    float max_v = (float)(src_h - 1);

    float cx = (vx1 + vx2) * 0.5f, cy = (vy1 + vy2) * 0.5f;
    float hw = vw * 0.5f, hh = vh * 0.5f;
    float inv_hw = 1.0f / hw, inv_hh = 1.0f / hh;

    float inv_gamma = 1.0f / (gamma > 0.1f ? gamma : 1.0f);
    float safe_lift = fminf(1.0f, fmaxf(0.0f, black_lift));
    float lift_scale = 1.0f - safe_lift;

    float gamma_lut[256];
    int i;
    for (i = 0; i < 256; ++i) {
        gamma_lut[i] = powf((float)i / 255.0f, inv_gamma) * 255.0f;
    }

    float decay = decay_scale * 0.016f;
    float decay_sq = decay_scale * decay_scale * 0.00012f;

    // 대각선 기준 도달 거리(%) 계산 (버퍼 크기 맞춤)
    float screen_diag = sqrtf((float)(out_w * out_w + out_h * out_h)) * 0.50f;
    float base_max_dist = screen_diag * (max_dist_pct * 0.01f);
    if (base_max_dist < 15.0f) base_max_dist = 15.0f;

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

    int y;
    #pragma omp parallel for schedule(static)
    for (y = 0; y < out_h; ++y) {
        float py = (float)y;
        float dy = py - cy;
        float dy_sq = dy * dy;
        float ny = fabsf(dy) * inv_hh;
        uint32_t* out_row = out_buf + (size_t)y * out_w;

        int in_core_y = (has_core && py >= core_y1 && py <= core_y2 && core_left <= core_right);

        if (in_core_y) {
            int x;
            for (x = 0; x < core_left; ++x) {
                render_pixel_fast(
                    &out_row[x], (float)x, cx, cy, inv_hw, dy, dy_sq, ny,
                    vx1, vy1, scale_u, scale_v, video_src, src_w, src_h,
                    max_u, max_v, gamma_lut, brightness, lift_scale, safe_lift,
                    decay, decay_sq,
                    vignette_enabled, base_max_dist, glow_intensity, shape_depth, edge_darkness
                );
            }
            for (x = core_left; x <= core_right; ++x) {
                out_row[x] = 0xFF000000u;
            }
            for (x = core_right + 1; x < out_w; ++x) {
                render_pixel_fast(
                    &out_row[x], (float)x, cx, cy, inv_hw, dy, dy_sq, ny,
                    vx1, vy1, scale_u, scale_v, video_src, src_w, src_h,
                    max_u, max_v, gamma_lut, brightness, lift_scale, safe_lift,
                    decay, decay_sq,
                    vignette_enabled, base_max_dist, glow_intensity, shape_depth, edge_darkness
                );
            }
        } else {
            int x;
            for (x = 0; x < out_w; ++x) {
                render_pixel_fast(
                    &out_row[x], (float)x, cx, cy, inv_hw, dy, dy_sq, ny,
                    vx1, vy1, scale_u, scale_v, video_src, src_w, src_h,
                    max_u, max_v, gamma_lut, brightness, lift_scale, safe_lift,
                    decay, decay_sq,
                    vignette_enabled, base_max_dist, glow_intensity, shape_depth, edge_darkness
                );
            }
        }
    }
}

// 블러
EXPORT void c_apply_optical_gaussian_blur(
    uint32_t* buf, 
    uint32_t* temp, 
    int w, 
    int h, 
    int radius
) {
    if (!buf || !temp || w <= 0 || h <= 0 || radius <= 0) return;
    int max_dim = (w > h) ? w : h;
    if (radius > max_dim) radius = max_dim;

    for (int y = 0; y < h; ++y) {
        uint32_t sr = 0, sg = 0, sb = 0;
        const uint32_t* row = buf + (size_t)y * w;
        uint32_t* temp_row = temp + (size_t)y * w;
        
        int initial_right = (radius < w - 1) ? radius : (w - 1);
        for (int k = 0; k <= initial_right; ++k) {
            uint32_t c = row[k];
            sr += (c >> 16) & 255;
            sg += (c >> 8) & 255;
            sb += c & 255;
        }

        for (int px = 0; px < w; ++px) {
            int left = (px - radius > 0) ? (px - radius) : 0;
            int right = (px + radius < w - 1) ? (px + radius) : (w - 1);
            uint32_t count = (uint32_t)(right - left + 1);

            temp_row[px] = 0xFF000000u | (((sr / count)) << 16)
                                       | (((sg / count)) << 8)
                                       | ((sb / count));

            int remove_x = px - radius;
            int add_x = px + radius + 1;

            if (remove_x >= 0) {
                uint32_t c = row[remove_x];
                sr -= (c >> 16) & 255;
                sg -= (c >> 8) & 255;
                sb -= c & 255;
            }
            if (add_x < w) {
                uint32_t c = row[add_x];
                sr += (c >> 16) & 255;
                sg += (c >> 8) & 255;
                sb += c & 255;
            }
        }
    }

    for (int x = 0; x < w; ++x) {
        uint32_t sr = 0, sg = 0, sb = 0;
        int initial_bottom = (radius < h - 1) ? radius : (h - 1);

        for (int k = 0; k <= initial_bottom; ++k) {
            uint32_t c = temp[(size_t)k * w + x];
            sr += (c >> 16) & 255;
            sg += (c >> 8) & 255;
            sb += c & 255;
        }

        for (int py = 0; py < h; ++py) {
            int top = (py - radius > 0) ? (py - radius) : 0;
            int bottom = (py + radius < h - 1) ? (py + radius) : (h - 1);
            uint32_t count = (uint32_t)(bottom - top + 1);

            buf[(size_t)py * w + x] = 0xFF000000u | (((sr / count)) << 16)
                                                  | (((sg / count)) << 8)
                                                  | ((sb / count));

            int remove_y = py - radius;
            int add_y = py + radius + 1;

            if (remove_y >= 0) {
                uint32_t c = temp[(size_t)remove_y * w + x];
                sr -= (c >> 16) & 255;
                sg -= (c >> 8) & 255;
                sb -= c & 255;
            }
            if (add_y < h) {
                uint32_t c = temp[(size_t)add_y * w + x];
                sr += (c >> 16) & 255;
                sg += (c >> 8) & 255;
                sb += c & 255;
            }
        }
    }
}


// 파티클
typedef struct {
    float x;
    float y;
    float vx;
    float vy;
    float size;
    float base_speed;
    float alpha_factor;
    float rot;
    float rot_speed;
    float phase;
    float pad;
    int32_t type;
    int32_t direction; // 0: 위로, 1: 왼쪽 대각선, 2: 오른쪽 대각선, 3: 부유/흩날림, 4: 아래
    int32_t out_of_bounds;
} NativeParticle;

EXPORT void c_update_particles(
    NativeParticle* particles,
    int count,
    float w,
    float h,
    float dt,
    float phase_dt,
    float sway_speed
) {
    float diag_scale = 0.9f * dt;
    float float_scale = 0.7f * dt;
    for (int i = 0; i < count; ++i) {
        NativeParticle* p = &particles[i];
        p->phase += phase_dt;
        float new_rot = p->rot + p->rot_speed * dt;
        if (new_rot >= 0.0f && new_rot < 360.0f) {
            p->rot = new_rot;
        } else {
            new_rot = fmodf(new_rot, 360.0f);
            if (new_rot < 0.0f) new_rot += 360.0f;
            p->rot = new_rot;
        }

        switch (p->direction) {
            case 0: // 위로
                p->vx = sinf(p->phase) * sway_speed;
                p->vy = -p->base_speed * dt;
                break;
            case 1: // 왼쪽 대각선
                p->vx = -p->base_speed * diag_scale;
                p->vy = p->base_speed * diag_scale;
                break;
            case 2: // 오른쪽 대각선
                p->vx = p->base_speed * diag_scale;
                p->vy = p->base_speed * diag_scale;
                break;
            case 3: // 부유 / 흩날림
                p->vx = cosf(p->phase * 0.8f) * (p->base_speed * float_scale);
                p->vy = sinf(p->phase) * (p->base_speed * float_scale);
                break;
            case 4: // 아래
            default:
                p->vx = sinf(p->phase) * sway_speed;
                p->vy = p->base_speed * dt;
                break;
        }

        p->x += p->vx;
        p->y += p->vy;

        float pad = p->pad;
        p->out_of_bounds = (p->x < -pad || p->x > w + pad || p->y < -pad || p->y > h + pad) ? 1 : 0;
    }
}

// 오로라
EXPORT void c_compute_aurora_wave(
    float* out_y,
    int steps,
    float h,
    float base_ratio,
    float amp,
    float phase,
    int band_index
) {
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

    for (int n = 0; n <= steps; ++n) {
        float fn = (float)n;
        float w1 = sinf(fn * step_w1 + w1_offset);
        float w2 = sinf(fn * step_w2 + w2_offset);
        out_y[n] = h_base + h_amp * w1 + h_w2 * w2;
    }
}

// 오디오
EXPORT float c_calculate_frame_db(const float* samples, int count) {
    if (count <= 0 || !samples) return -120.0f;

    double sum0 = 0.0, sum1 = 0.0, sum2 = 0.0, sum3 = 0.0;
    int i = 0;
    for (; i <= count - 4; i += 4) {
        double v0 = (double)samples[i];
        double v1 = (double)samples[i + 1];
        double v2 = (double)samples[i + 2];
        double v3 = (double)samples[i + 3];
        sum0 += v0 * v0;
        sum1 += v1 * v1;
        sum2 += v2 * v2;
        sum3 += v3 * v3;
    }
    double sum_sq = (sum0 + sum1) + (sum2 + sum3);
    for (; i < count; ++i) {
        double val = (double)samples[i];
        sum_sq += val * val;
    }

    double mean_sq = sum_sq / (double)count;
    double rms = sqrt(mean_sq + 1e-9);
    float db = (float)(20.0 * log10(rms + 1e-9));
    return db;
}

// 그림자
EXPORT void c_render_rounded_box_shadow(
    uint32_t* out_buf, int out_w, int out_h,
    float rect_x, float rect_y, float rect_w, float rect_h,
    float corner_radius, float shadow_radius,
    uint8_t s_r, uint8_t s_g, uint8_t s_b, float s_opacity
) {
    if (!out_buf || out_w <= 0 || out_h <= 0 || shadow_radius <= 0.0f || s_opacity <= 0.001f) {
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

    for (int y = 0; y < out_h; ++y) {
        float py = (float)y + 0.5f;
        float qy = fabsf(py - cy) - hh;
        uint32_t* row = out_buf + (size_t)y * out_w;

        for (int x = 0; x < out_w; ++x) {
            float px = (float)x + 0.5f;
            float qx = fabsf(px - cx) - hw;

            float ox = qx > 0.0f ? qx : 0.0f;
            float oy = qy > 0.0f ? qy : 0.0f;
            float d_outside = sqrtf(ox * ox + oy * oy);
            float max_q = qx > qy ? qx : qy;
            float d_inside = max_q < 0.0f ? max_q : 0.0f;
            float dist = d_outside + d_inside - r;

            float alpha = 0.0f;
            if (dist <= 0.0f) {
                alpha = 1.0f;
            } else if (dist < shadow_radius) {
                float t = dist * inv_sr;
                alpha = expf(-3.2f * t * t) * (1.0f - t);
            }

            uint32_t a = (uint32_t)(alpha * s_opacity * 255.0f);
            if (a > 255) a = 255;

            if (a > 0) {
                uint32_t pr = ((uint32_t)s_r * a) / 255;
                uint32_t pg = ((uint32_t)s_g * a) / 255;
                uint32_t pb = ((uint32_t)s_b * a) / 255;
                row[x] = (a << 24) | (pr << 16) | (pg << 8) | pb;
            } else {
                row[x] = 0x00000000u;
            }
        }
    }
}