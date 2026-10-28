#pragma once
#include "common.h"

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
    int32_t direction;
    int32_t out_of_bounds;
} NativeParticle;

EXPORT void c_update_particles(
    NativeParticle* RESTRICT particles,
    int count,
    float w,
    float h,
    float dt,
    float phase_dt,
    float sway_speed
);