import math
from typing import Dict, Type


class BaseBorderAnimation:
    is_rotating: bool = False

    def update(self, sys, dt: float):
        sys.flicker_val = 1.0

    def get_alpha_mult(self, sys) -> float:
        return 1.0

    def get_glow_spread_offset(self, sys) -> float:
        return 0.0


ANIMATION_REGISTRY: Dict[str, BaseBorderAnimation] = {}


def register_animation(name: str):
    def decorator(cls: Type[BaseBorderAnimation]):
        ANIMATION_REGISTRY[name] = cls()
        return cls
    return decorator


def get_animation(name: str) -> BaseBorderAnimation:
    return ANIMATION_REGISTRY.get(name, DEFAULT_STATIC_ANIM)


@register_animation("정적")
class StaticAnimation(BaseBorderAnimation):
    pass


@register_animation("숨쉬기")
class BreathingAnimation(BaseBorderAnimation):
    def get_alpha_mult(self, sys) -> float:
        return 1.0 - (sys.pulse_depth * 0.5) + (math.sin(sys.phase * 2.0) * 0.5 * sys.pulse_depth)


@register_animation("깜빡임")
class FlickerAnimation(BaseBorderAnimation):
    def update(self, sys, dt: float):
        flicker_noise = math.sin(sys.phase * 11.2) * math.cos(sys.phase * 19.4)
        sys.flicker_val = 0.65 + 0.35 * max(0.0, flicker_noise)

    def get_alpha_mult(self, sys) -> float:
        return sys.flicker_val


@register_animation("회전")
class RotateAnimation(BaseBorderAnimation):
    is_rotating = True


@register_animation("브리딩 펄스")
class BreathingPulseAnimation(BaseBorderAnimation):
    def get_glow_spread_offset(self, sys) -> float:
        return math.sin(sys.phase * 2.0) * (sys.glow_spread * 0.25 * sys.pulse_depth)


DEFAULT_STATIC_ANIM = StaticAnimation()