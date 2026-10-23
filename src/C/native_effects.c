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

// 블러
static inline uint32_t sample_bgrx(
    const uint32_t* src, 
    int w, 
    int h, 
    float u, 
    float v
) {
    if (!src || w <= 0 || h <= 0) return 0xFF000000u;
    if (u < 0.0f) u = 0.0f;
    if (v < 0.0f) v = 0.0f;
    float max_x = (float)(w - 1), max_y = (float)(h - 1);
    if (u > max_x) u = max_x;
    if (v > max_y) v = max_y;

    int x0 = (int)u, y0 = (int)v;
    int x1 = x0 + 1 < w ? x0 + 1 : x0;
    int y1 = y0 + 1 < h ? y0 + 1 : y0;
    float fx = u - (float)x0, fy = v - (float)y0;
    const uint32_t* row0 = src + (size_t)y0 * w;
    const uint32_t* row1 = src + (size_t)y1 * w;
    uint32_t c00 = row0[x0], c10 = row0[x1], c01 = row1[x0], c11 = row1[x1];
    float a = (1.0f - fx) * (1.0f - fy), b = fx * (1.0f - fy);
    float c = (1.0f - fx) * fy, d = fx * fy;
    int r = (int)(a * ((c00 >> 16) & 255) + b * ((c10 >> 16) & 255) + c * ((c01 >> 16) & 255) + d * ((c11 >> 16) & 255));
    int g = (int)(a * ((c00 >> 8) & 255) + b * ((c10 >> 8) & 255) + c * ((c01 >> 8) & 255) + d * ((c11 >> 8) & 255));
    int bl = (int)(a * (c00 & 255) + b * (c10 & 255) + c * (c01 & 255) + d * (c11 & 255));
    return 0xFF000000u | ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)bl;
}

EXPORT void c_render_vanishing_perspective(
    uint32_t* out_buf, int out_w, int out_h,
    const uint32_t* video_src, int src_w, int src_h,
    float vx1, float vy1, float vx2, float vy2,
    float brightness, float black_lift, float gamma, float decay_scale
) {
    if (!out_buf || !video_src || out_w <= 0 || out_h <= 0 || src_w <= 0 || src_h <= 0) return;
    float vw = vx2 - vx1, vh = vy2 - vy1;
    size_t out_count = (size_t)out_w * (size_t)out_h;
    if (vw < 1.0f || vh < 1.0f) {
        for (size_t i = 0; i < out_count; ++i) out_buf[i] = 0xFF000000u;
        return;
    }

    float cx = (vx1 + vx2) * 0.5f, cy = (vy1 + vy2) * 0.5f;
    float hw = vw * 0.5f, hh = vh * 0.5f;
    float inv_gamma = 1.0f / (gamma > 0.1f ? gamma : 1.0f);
    float safe_lift = fminf(1.0f, fmaxf(0.0f, black_lift));
    float gamma_lut[256];
    for (int i = 0; i < 256; ++i) gamma_lut[i] = powf((float)i / 255.0f, inv_gamma) * 255.0f;
    float decay = decay_scale * 0.016f;
    float decay_sq = decay_scale * decay_scale * 0.00012f;

    for (int y = 0; y < out_h; ++y) {
        float py = (float)y, dy = py - cy, ny = fabsf(dy) / hh;
        uint32_t* out_row = out_buf + (size_t)y * out_w;
        for (int x = 0; x < out_w; ++x) {
            float px = (float)x, dx = px - cx, nx = fabsf(dx) / hw;
            float m = nx > ny ? nx : ny;
            float clamp_m = m > 1.0f ? m : 1.0f;
            float bx = cx + dx / clamp_m, by = cy + dy / clamp_m;
            float u = ((bx - vx1) / vw) * (src_w - 1), v = ((by - vy1) / vh) * (src_h - 1);
            uint32_t col = sample_bgrx(video_src, src_w, src_h, u, v);
            float r = gamma_lut[(col >> 16) & 255], g = gamma_lut[(col >> 8) & 255], b = gamma_lut[col & 255];
            float factor = brightness;

            if (m > 1.0f) {
                float ox = px - bx, oy = py - by;
                float dist = sqrtf(ox * ox + oy * oy);
                float falloff = 1.0f / (1.0f + dist * decay + dist * dist * decay_sq);
                factor *= falloff * (1.0f - safe_lift) + safe_lift;
            }

            float max_c = r > g ? r : g;
            if (b > max_c) max_c = b;
            if (max_c > 1.0f) {
                float target = max_c * factor;
                float mapped = 305.0f * target / (target + 50.0f);
                float scale = mapped / max_c;
                r *= scale;
                g *= scale;
                b *= scale;
            }

            int ir = (int)r, ig = (int)g, ib = (int)b;
            if (ir < 0) ir = 0; else if (ir > 255) ir = 255;
            if (ig < 0) ig = 0; else if (ig > 255) ig = 255;
            if (ib < 0) ib = 0; else if (ib > 255) ib = 255;
            out_row[x] = 0xFF000000u | ((uint32_t)ir << 16) | ((uint32_t)ig << 8) | (uint32_t)ib;
        }
    }
}

EXPORT void c_apply_optical_gaussian_blur(
    uint32_t* buf, 
    uint32_t* temp, 
    int w, 
    int h, 
    int radius
) {
    if (!buf || !temp || w <= 0 || h <= 0 || radius <= 0) return;
    int max_dim = w > h ? w : h;
    if (radius > max_dim) radius = max_dim;

    for (int y = 0; y < h; ++y) {
        uint64_t sr = 0, sg = 0, sb = 0;
        int initial_right = radius < w - 1 ? radius : w - 1;
        const uint32_t* row = buf + (size_t)y * w;
        uint32_t* temp_row = temp + (size_t)y * w;
        for (int k = 0; k <= initial_right; ++k) {
            uint32_t c = row[k];
            sr += (c >> 16) & 255; sg += (c >> 8) & 255; sb += c & 255;
        }
        for (int x = 0; x < w; ++x) {
            int left = x - radius, right = x + radius;
            if (left < 0) left = 0;
            if (right >= w) right = w - 1;
            uint32_t count = (uint32_t)(right - left + 1);
            temp_row[x] = 0xFF000000u | ((uint32_t)(sr / count) << 16) | ((uint32_t)(sg / count) << 8) | (uint32_t)(sb / count);
            int remove_x = x - radius, add_x = x + radius + 1;
            if (remove_x >= 0) {
                uint32_t c = row[remove_x];
                sr -= (c >> 16) & 255; sg -= (c >> 8) & 255; sb -= c & 255;
            }
            if (add_x < w) {
                uint32_t c = row[add_x];
                sr += (c >> 16) & 255; sg += (c >> 8) & 255; sb += c & 255;
            }
        }
    }

    for (int x = 0; x < w; ++x) {
        uint64_t sr = 0, sg = 0, sb = 0;
        int initial_bottom = radius < h - 1 ? radius : h - 1;
        for (int k = 0; k <= initial_bottom; ++k) {
            uint32_t c = temp[(size_t)k * w + x];
            sr += (c >> 16) & 255; sg += (c >> 8) & 255; sb += c & 255;
        }
        for (int y = 0; y < h; ++y) {
            int top = y - radius, bottom = y + radius;
            if (top < 0) top = 0;
            if (bottom >= h) bottom = h - 1;
            uint32_t count = (uint32_t)(bottom - top + 1);
            buf[(size_t)y * w + x] = 0xFF000000u | ((uint32_t)(sr / count) << 16) | ((uint32_t)(sg / count) << 8) | (uint32_t)(sb / count);
            int remove_y = y - radius, add_y = y + radius + 1;
            if (remove_y >= 0) {
                uint32_t c = temp[(size_t)remove_y * w + x];
                sr -= (c >> 16) & 255; sg -= (c >> 8) & 255; sb -= c & 255;
            }
            if (add_y < h) {
                uint32_t c = temp[(size_t)add_y * w + x];
                sr += (c >> 16) & 255; sg += (c >> 8) & 255; sb += c & 255;
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
    for (int i = 0; i < count; ++i) {
        NativeParticle* p = &particles[i];
        p->phase += phase_dt;
        p->rot = fmodf(p->rot + p->rot_speed * dt, 360.0f);
        if (p->rot < 0.0f) p->rot += 360.0f;

        switch (p->direction) {
            case 0: // 위로
                p->vx = sinf(p->phase) * sway_speed;
                p->vy = -p->base_speed * dt;
                break;
            case 1: // 왼쪽 대각선
                p->vx = -p->base_speed * 0.9f * dt;
                p->vy = p->base_speed * 0.9f * dt;
                break;
            case 2: // 오른쪽 대각선
                p->vx = p->base_speed * 0.9f * dt;
                p->vy = p->base_speed * 0.9f * dt;
                break;
            case 3: // 부유 / 흩날림
                p->vx = cosf(p->phase * 0.8f) * p->base_speed * (0.7f * dt);
                p->vy = sinf(p->phase) * p->base_speed * (0.7f * dt);
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
        if (p->x < -pad || p->x > w + pad || p->y < -pad || p->y > h + pad) {
            p->out_of_bounds = 1;
        } else {
            p->out_of_bounds = 0;
        }
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

    for (int n = 0; n <= steps; ++n) {
        float ratio = (float)n * inv_steps;
        float w1 = sinf(ratio * w1_freq + w1_offset);
        float w2 = sinf(ratio * w2_freq + w2_offset);
        out_y[n] = h * base_ratio + h * amp * w1 + h * 0.016f * w2;
    }
}

// 오디오
EXPORT float c_calculate_frame_db(const float* samples, int count) {
    if (count <= 0 || !samples) return -120.0f;

    double sum_sq = 0.0;
    for (int i = 0; i < count; ++i) {
        double val = (double)samples[i];
        sum_sq += val * val;
    }

    double mean_sq = sum_sq / (double)count;
    double rms = sqrt(mean_sq + 1e-9);
    float db = (float)(20.0 * log10(rms + 1e-9));
    return db;
}