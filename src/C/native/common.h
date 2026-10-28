#pragma once

#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#if defined(_WIN32) || defined(__CYGWIN__)
#define EXPORT __declspec(dllexport)
#else
#define EXPORT __attribute__((visibility("default")))
#endif

#if defined(_MSC_VER)
#define FORCE_INLINE __forceinline
#define RESTRICT __restrict
#else
#define FORCE_INLINE inline __attribute__((always_inline))
#define RESTRICT __restrict__
#endif

#define PI 3.14159265358979323846f
#define TWO_PI 6.28318530717958647692f
#define STACK_THRESHOLD 2048