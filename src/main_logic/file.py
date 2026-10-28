import os
import json

from PyQt6.QtCore import QTimer
from src.base import *


def get_default_sub_config() -> dict:
    return {
        "font": "HY견고딕",
        "size": 25,
        "color": "#f9f9f9",
        "outline_color": "#232323",
        "border_size": 4,
        "blur": 1,
        "pos": 95,
        "bold": True,
        "typewriter_enabled": False,
        "typewriter_speed": 28,
        "fade_in_enabled": True,
        "fade_duration": 220,
        "slide_direction": "아래에서 위로",
        "slide_distance": 16,
        "anim_style": "팝업 바운스",
        "max_width_ratio": 0.88,
        "visible": True,
        "outside_video": True,
        "bg_color": "#000000",
        "bg_opacity": 0.0,
        "shadow_enabled": True,
        "shadow_color": "#000000",
        "shadow_opacity": 0.3,
        "shadow_offset": 2,
        "shadow_blur": 3,
        "fps_subtitle": 20
    }


def get_default_engine_config() -> dict:
    return {
        "ambient_glow": True,
        "aurora_enabled": True,
        "aurora_style": "물결",
        "aurora_palette": "파랑",
        "aurora_intensity": 0.35,
        "aurora_speed": 0.33,
        "aurora_size": 1.0,
        "particle_enabled": True,
        "particle_type": "먼지",
        "particle_direction": "아래로",
        "particle_palette": "흰색",
        "particle_density": 0.2,
        "particle_speed": 0.42,
        "particle_size": 1.8,
        "ambient_brightness": 0.8,
        "ambient_saturation": 1.1,
        "ambient_gamma": 1.0,
        "ambient_black_lift": 0.0,
        "ambient_ca_strength": 0.0,
        "ambient_blur_radius": 16,
        "ambient_motion_intensity": 0.42,
        "ambient_motion_speed": 2.5,
        "ambient_crop_margin": 0,
        "video_floating_rim": True,
        "video_shadow_enabled": True,
        "video_shadow_opacity": 0.05,
        "video_shadow_radius": 25,
        "video_shadow_offset": 2,
        "ambient_tint_enabled": False,
        "ambient_tint_color": "#ffffff",
        "ambient_tint_ratio": 0.3,
        "audio_norm": True,
        "hwdec": True,
        "border_margin": 0,
        "border_glow_spread": 20,
        "border_color_mode": "단색",
        "border_color1": "#f8f8f8",
        "border_color2": "#b3b3b3",
        "border_anim_mode": "정지",
        "border_anim_speed": 0.2,
        "border_wave_intensity": 0.2,
        "border_pulse_depth": 0.0,
        "border_reactive": True,
        "border_enabled": True,
        "border_style": "기본",
        "border_width": 5,
        "border_radius": 25,
        "border_opacity": 0.15,
        "window_radius": 25,
        "video_radius": 25,
        "window_radius_individual": False,
        "video_radius_individual": False,
        "ambient_quality_percent": 50,
        "ambient_vignette_enabled": True,
        "ambient_vignette_max_dist": 45,
        "ambient_vignette_intensity": 1.0,
        "ambient_vignette_shape_depth": 0.8,
        "ambient_vignette_darkness": 0.8,
        "fps_effect": 24,
        "fps_ambient": 30,
        "fps_shadow": 5,
        "fps_subtitle": 20
    }


def read_session_state(filepath: str = SESSION_FILE) -> dict:
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"세션 로드 오류: {e}")
        return {}


def write_session_state(filepath: str, data: dict) -> None:
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"세션 저장 오류: {e}")


def save_session(self):
    pos = 0.0
    if self.core and self.core.player and self.core.player.time_pos:
        try:
            pos = float(self.core.player.time_pos)
        except Exception:
            pass

    cur_pl_preset = getattr(self, "current_playlist_preset", "기본")
    playlist_presets = getattr(self, "playlist_preset", {})
    if not isinstance(playlist_presets, dict):
        playlist_presets = {}

    playlist_presets[cur_pl_preset] = [os.path.abspath(p) for p in self.playlist]
    if "기본" not in playlist_presets:
        playlist_presets["기본"] = [os.path.abspath(p) for p in self.playlist]
    self.playlist_preset = playlist_presets

    setting_presets = getattr(self, "setting_preset", {})
    if "기본" not in setting_presets:
        setting_presets["기본"] = {
            "sub_config": dict(self.sub_config),
            "engine_config": dict(self.engine_config)
        }

    data = {
        "playlist": [os.path.abspath(p) for p in self.playlist],
        "current_idx": self.current_idx,
        "time_pos": pos,
        "mode": self.playback_mode,
        "volume": self.vol_slider.value(),
        "sub_visible": self.sub_visible,
        "sub_config": self.sub_config,
        "engine_config": self.engine_config,
        "setting_preset": setting_presets,
        "playlist_preset": playlist_presets,
        "current_setting_preset": getattr(self, "current_setting_preset", "기본"),
        "current_playlist_preset": cur_pl_preset
    }
    write_session_state(SESSION_FILE, data)


def load_session(self):
    try:
        d = read_session_state(SESSION_FILE)
        if not d:
            self.setting_preset = {
                "기본": {
                    "sub_config": dict(self.sub_config),
                    "engine_config": dict(self.engine_config)
                }
            }
            self.playlist_preset = {
                "기본": list(self.playlist)
            }
            self.current_setting_preset = "기본"
            self.current_playlist_preset = "기본"
            return

        raw_list = d.get("playlist", [])
        self.playlist = [os.path.abspath(p) for p in raw_list if os.path.exists(p)]

        saved_idx = d.get("current_idx", -1)
        self.current_idx = saved_idx if (0 <= saved_idx < len(self.playlist)) else (0 if self.playlist else -1)

        self.playback_mode = d.get("mode", 0)
        self.vol_slider.setValue(d.get("volume", 80))
        self.sub_visible = d.get("sub_visible", True)
        self._update_sub_icon()

        if isinstance(d.get("sub_config"), dict):
            self.sub_config.update(d.get("sub_config"))
        if isinstance(d.get("engine_config"), dict):
            self.engine_config.update(d.get("engine_config"))

        loaded_setting_presets = d.get("setting_preset", {})
        if not isinstance(loaded_setting_presets, dict):
            loaded_setting_presets = {}
        if "기본" not in loaded_setting_presets:
            loaded_setting_presets["기본"] = {
                "sub_config": dict(self.sub_config),
                "engine_config": dict(self.engine_config)
            }
        self.setting_preset = loaded_setting_presets

        loaded_playlist_presets = d.get("playlist_preset", {})
        if not isinstance(loaded_playlist_presets, dict):
            loaded_playlist_presets = {}
        cleaned_pl_presets = {}
        for k, v in loaded_playlist_presets.items():
            if isinstance(v, list):
                cleaned_pl_presets[k] = [os.path.abspath(p) for p in v if os.path.exists(p)]
        if "기본" not in cleaned_pl_presets:
            cleaned_pl_presets["기본"] = list(self.playlist)
        self.playlist_preset = cleaned_pl_presets

        self.current_setting_preset = d.get("current_setting_preset", "기본")
        self.current_playlist_preset = d.get("current_playlist_preset", "기본")

        self.btn_mode.setText(PLAYBACK_MODE_NAMES[self.playback_mode])
        self.refresh_playlist_view()

        if self.core:
            self.core.apply_subtitle_config(self.sub_config, self.sub_visible)
            self.core.set_audio_normalization(self.engine_config.get("audio_norm", True))
            self.core.set_hwdec(self.engine_config.get("hwdec", True))
            self.core.set_ambient_crop_margin(self.engine_config.get("ambient_crop_margin", 10) / 100.0)
            self.core.preload_playlist_gains(self.playlist)

        self.ambient_container.set_ambient_params(self.engine_config)
        self.update_window_and_video_radius()

        saved_pos = d.get("time_pos", 0.0)
        if self.playlist and 0 <= self.current_idx < len(self.playlist):
            QTimer.singleShot(250, lambda: restore_playback(self, saved_pos))
    except Exception:
        pass


def restore_playback(self, saved_pos: float):
    if 0 <= self.current_idx < len(self.playlist):
        self.play_index(self.current_idx)
        if saved_pos > 3.0:
            QTimer.singleShot(350, lambda: self.core.seek(saved_pos))