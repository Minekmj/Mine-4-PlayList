#include "blur.h"

static FORCE_INLINE uint32_t blur_pack_pixel(uint32_t sr, uint32_t sg, uint32_t sb, float inv_count) {
    uint32_t r = (uint32_t)((float)sr * inv_count + 1e-5f);
    uint32_t g = (uint32_t)((float)sg * inv_count + 1e-5f);
    uint32_t b = (uint32_t)((float)sb * inv_count + 1e-5f);
    return 0xFF000000u | (r << 16) | (g << 8) | b;
}

static FORCE_INLINE void blur_write_vertical_row(
    uint32_t* RESTRICT out_row,
    const uint32_t* RESTRICT col_sr,
    const uint32_t* RESTRICT col_sg,
    const uint32_t* RESTRICT col_sb,
    int w,
    float inv_count
) {
    for (int x = 0; x < w; ++x) out_row[x] = blur_pack_pixel(col_sr[x], col_sg[x], col_sb[x], inv_count);
}

static FORCE_INLINE void blur_add_vertical_row(
    uint32_t* RESTRICT col_sr,
    uint32_t* RESTRICT col_sg,
    uint32_t* RESTRICT col_sb,
    const uint32_t* RESTRICT row,
    int w
) {
    for (int x = 0; x < w; ++x) {
        uint32_t c = row[x];
        col_sr[x] += (c >> 16) & 255u;
        col_sg[x] += (c >> 8) & 255u;
        col_sb[x] += c & 255u;
    }
}

static FORCE_INLINE void blur_remove_vertical_row(
    uint32_t* RESTRICT col_sr,
    uint32_t* RESTRICT col_sg,
    uint32_t* RESTRICT col_sb,
    const uint32_t* RESTRICT row,
    int w
) {
    for (int x = 0; x < w; ++x) {
        uint32_t c = row[x];
        col_sr[x] -= (c >> 16) & 255u;
        col_sg[x] -= (c >> 8) & 255u;
        col_sb[x] -= c & 255u;
    }
}

static FORCE_INLINE void blur_slide_vertical_rows(
    uint32_t* RESTRICT col_sr,
    uint32_t* RESTRICT col_sg,
    uint32_t* RESTRICT col_sb,
    const uint32_t* RESTRICT rem_row,
    const uint32_t* RESTRICT add_row,
    int w
) {
    for (int x = 0; x < w; ++x) {
        uint32_t c_rem = rem_row[x];
        uint32_t c_add = add_row[x];
        col_sr[x] = col_sr[x] - ((c_rem >> 16) & 255u) + ((c_add >> 16) & 255u);
        col_sg[x] = col_sg[x] - ((c_rem >> 8) & 255u) + ((c_add >> 8) & 255u);
        col_sb[x] = col_sb[x] - (c_rem & 255u) + (c_add & 255u);
    }
}

EXPORT void c_apply_optical_gaussian_blur(
    uint32_t* RESTRICT buf,
    uint32_t* RESTRICT temp,
    int w,
    int h,
    int radius
) {
    if (!buf || !temp || w <= 0 || h <= 0 || radius <= 0) return;

    int max_dim = (w > h) ? w : h;
    if (radius > max_dim) radius = max_dim;

    float stack_inv_x[STACK_THRESHOLD];
    float* inv_count_x = (w <= STACK_THRESHOLD) ? stack_inv_x : (float*)malloc((size_t)w * sizeof(float));
    if (!inv_count_x) return;

    for (int px = 0; px < w; ++px) {
        int left = (px - radius > 0) ? px - radius : 0;
        int right = (px + radius < w - 1) ? px + radius : w - 1;
        inv_count_x[px] = 1.0f / (float)(right - left + 1);
    }

    int initial_right = (radius < w - 1) ? radius : w - 1;
    int mid_start_x = radius;
    int mid_end_x = w - 1 - radius;

    for (int y = 0; y < h; ++y) {
        uint32_t sr = 0, sg = 0, sb = 0;
        const uint32_t* RESTRICT row = buf + (size_t)y * w;
        uint32_t* RESTRICT temp_row = temp + (size_t)y * w;

        for (int k = 0; k <= initial_right; ++k) {
            uint32_t c = row[k];
            sr += (c >> 16) & 255u;
            sg += (c >> 8) & 255u;
            sb += c & 255u;
        }

        if (mid_start_x < mid_end_x) {
            for (int px = 0; px < mid_start_x; ++px) {
                temp_row[px] = blur_pack_pixel(sr, sg, sb, inv_count_x[px]);

                uint32_t c = row[px + radius + 1];
                sr += (c >> 16) & 255u;
                sg += (c >> 8) & 255u;
                sb += c & 255u;
            }

            float inv_mid = 1.0f / (float)(2 * radius + 1);

            for (int px = mid_start_x; px < mid_end_x; ++px) {
                temp_row[px] = blur_pack_pixel(sr, sg, sb, inv_mid);

                uint32_t c_rem = row[px - radius];
                uint32_t c_add = row[px + radius + 1];
                sr = sr - ((c_rem >> 16) & 255u) + ((c_add >> 16) & 255u);
                sg = sg - ((c_rem >> 8) & 255u) + ((c_add >> 8) & 255u);
                sb = sb - (c_rem & 255u) + (c_add & 255u);
            }

            int px = mid_end_x;
            temp_row[px] = blur_pack_pixel(sr, sg, sb, inv_mid);

            uint32_t c_rem = row[px - radius];
            sr -= (c_rem >> 16) & 255u;
            sg -= (c_rem >> 8) & 255u;
            sb -= c_rem & 255u;

            for (px = mid_end_x + 1; px < w; ++px) {
                temp_row[px] = blur_pack_pixel(sr, sg, sb, inv_count_x[px]);

                c_rem = row[px - radius];
                sr -= (c_rem >> 16) & 255u;
                sg -= (c_rem >> 8) & 255u;
                sb -= c_rem & 255u;
            }
        } else {
            for (int px = 0; px < w; ++px) {
                temp_row[px] = blur_pack_pixel(sr, sg, sb, inv_count_x[px]);

                int remove_x = px - radius;
                int add_x = px + radius + 1;

                if (remove_x >= 0) {
                    uint32_t c = row[remove_x];
                    sr -= (c >> 16) & 255u;
                    sg -= (c >> 8) & 255u;
                    sb -= c & 255u;
                }

                if (add_x < w) {
                    uint32_t c = row[add_x];
                    sr += (c >> 16) & 255u;
                    sg += (c >> 8) & 255u;
                    sb += c & 255u;
                }
            }
        }
    }

    if (inv_count_x != stack_inv_x) free(inv_count_x);

    uint32_t stack_col_mem[STACK_THRESHOLD * 3];
    uint32_t* col_mem = (w <= STACK_THRESHOLD) ? stack_col_mem : (uint32_t*)malloc((size_t)w * 3 * sizeof(uint32_t));
    if (!col_mem) return;

    uint32_t* RESTRICT col_sr = col_mem;
    uint32_t* RESTRICT col_sg = col_mem + w;
    uint32_t* RESTRICT col_sb = col_mem + w * 2;
    memset(col_mem, 0, (size_t)w * 3 * sizeof(uint32_t));

    int initial_bottom = (radius < h - 1) ? radius : h - 1;

    for (int k = 0; k <= initial_bottom; ++k) {
        const uint32_t* RESTRICT row = temp + (size_t)k * w;
        blur_add_vertical_row(col_sr, col_sg, col_sb, row, w);
    }

    int mid_start_y = radius;
    int mid_end_y = h - 1 - radius;

    if (mid_start_y < mid_end_y) {
        for (int py = 0; py < mid_start_y; ++py) {
            float inv_count = 1.0f / (float)(py + radius + 1);
            uint32_t* RESTRICT out_row = buf + (size_t)py * w;
            blur_write_vertical_row(out_row, col_sr, col_sg, col_sb, w, inv_count);

            const uint32_t* RESTRICT add_row = temp + (size_t)(py + radius + 1) * w;
            blur_add_vertical_row(col_sr, col_sg, col_sb, add_row, w);
        }

        float inv_mid = 1.0f / (float)(2 * radius + 1);

        for (int py = mid_start_y; py < mid_end_y; ++py) {
            uint32_t* RESTRICT out_row = buf + (size_t)py * w;
            blur_write_vertical_row(out_row, col_sr, col_sg, col_sb, w, inv_mid);

            const uint32_t* RESTRICT rem_row = temp + (size_t)(py - radius) * w;
            const uint32_t* RESTRICT add_row = temp + (size_t)(py + radius + 1) * w;

            blur_slide_vertical_rows(col_sr, col_sg, col_sb, rem_row, add_row, w);
        }

        int py = mid_end_y;
        uint32_t* RESTRICT out_row = buf + (size_t)py * w;
        blur_write_vertical_row(out_row, col_sr, col_sg, col_sb, w, inv_mid);

        const uint32_t* RESTRICT rem_row = temp + (size_t)(py - radius) * w;
        blur_remove_vertical_row(col_sr, col_sg, col_sb, rem_row, w);

        for (py = mid_end_y + 1; py < h; ++py) {
            float inv_count = 1.0f / (float)(h - py + radius);
            out_row = buf + (size_t)py * w;
            blur_write_vertical_row(out_row, col_sr, col_sg, col_sb, w, inv_count);

            rem_row = temp + (size_t)(py - radius) * w;
            blur_remove_vertical_row(col_sr, col_sg, col_sb, rem_row, w);
        }
    } else {
        for (int py = 0; py < h; ++py) {
            int top = (py - radius > 0) ? py - radius : 0;
            int bottom = (py + radius < h - 1) ? py + radius : h - 1;
            float inv_count = 1.0f / (float)(bottom - top + 1);
            uint32_t* RESTRICT out_row = buf + (size_t)py * w;

            blur_write_vertical_row(out_row, col_sr, col_sg, col_sb, w, inv_count);

            int remove_y = py - radius;
            int add_y = py + radius + 1;

            if (py >= mid_start_y && py < mid_end_y) {
                const uint32_t* RESTRICT rem_row = temp + (size_t)remove_y * w;
                const uint32_t* RESTRICT add_row = temp + (size_t)add_y * w;
                blur_slide_vertical_rows(col_sr, col_sg, col_sb, rem_row, add_row, w);
            } else {
                if (remove_y >= 0 && add_y < h) {
                    const uint32_t* RESTRICT rem_row = temp + (size_t)remove_y * w;
                    const uint32_t* RESTRICT add_row = temp + (size_t)add_y * w;
                    blur_slide_vertical_rows(col_sr, col_sg, col_sb, rem_row, add_row, w);
                } else if (remove_y >= 0) {
                    const uint32_t* RESTRICT rem_row = temp + (size_t)remove_y * w;
                    blur_remove_vertical_row(col_sr, col_sg, col_sb, rem_row, w);
                } else if (add_y < h) {
                    const uint32_t* RESTRICT add_row = temp + (size_t)add_y * w;
                    blur_add_vertical_row(col_sr, col_sg, col_sb, add_row, w);
                }
            }
        }
    }

    if (col_mem != stack_col_mem) free(col_mem);
}