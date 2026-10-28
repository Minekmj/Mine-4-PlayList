#include "particle.h"

EXPORT void c_update_particles(
    NativeParticle* RESTRICT particles,
    int count,
    float w,
    float h,
    float dt,
    float phase_dt,
    float sway_speed
) {
    if (!particles || count <= 0) return;

    float diag_scale = 0.9f * dt;
    float float_scale = 0.7f * dt;
    float sway_speed_dt = sway_speed * dt;

    for (int i = 0; i < count; ++i) {
        NativeParticle* RESTRICT p = &particles[i];
        p->phase += phase_dt;

        float new_rot = p->rot + p->rot_speed * dt;
        if (new_rot >= 360.0f) {
            new_rot -= 360.0f;
            if (new_rot >= 360.0f) new_rot = fmodf(new_rot, 360.0f);
        } else if (new_rot < 0.0f) {
            new_rot += 360.0f;
            if (new_rot < 0.0f) new_rot = fmodf(new_rot, 360.0f) + 360.0f;
        }
        p->rot = new_rot;

        float base_speed_dt = p->base_speed * dt;

        switch (p->direction) {
            case 0:
                p->vx = sinf(p->phase) * sway_speed_dt;
                p->vy = -base_speed_dt;
                break;
            case 1:
                p->vx = -p->base_speed * diag_scale;
                p->vy = p->base_speed * diag_scale;
                break;
            case 2:
                p->vx = p->base_speed * diag_scale;
                p->vy = p->base_speed * diag_scale;
                break;
            case 3:
                p->vx = cosf(p->phase * 0.8f) * (p->base_speed * float_scale);
                p->vy = sinf(p->phase) * (p->base_speed * float_scale);
                break;
            case 4:
            default:
                p->vx = sinf(p->phase) * sway_speed_dt;
                p->vy = base_speed_dt;
                break;
        }

        p->x += p->vx;
        p->y += p->vy;

        float pad = p->pad;
        p->out_of_bounds = (p->x < -pad || p->x > w + pad || p->y < -pad || p->y > h + pad) ? 1 : 0;
    }
}