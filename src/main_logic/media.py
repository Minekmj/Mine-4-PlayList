import os
import random
from typing import List, Optional
from src.base import *

def format_time(seconds: float) -> str:
    sec = max(0, int(seconds))
    return f"{sec // 60:02d}:{sec % 60:02d}"


def collect_media_files(paths: List[str]) -> List[str]:
    results = []
    for p in paths:
        abs_p = os.path.abspath(p)
        if os.path.isdir(abs_p):
            for root, _, files in os.walk(abs_p):
                for f in sorted(files):
                    if f.lower().endswith(SUPPORTED_MEDIA_EXTS):
                        results.append(os.path.join(root, f))
        elif abs_p.lower().endswith(SUPPORTED_MEDIA_EXTS):
            results.append(abs_p)
    return results


def get_next_track_index(current_idx: int, total_count: int, mode: int) -> Optional[int]:
    """재생 모드에 맞춰 다음 곡 인덱스 계산 (재생 중지 시 None 반환)"""
    if total_count <= 0:
        return None
    if mode == 3:  # 랜덤 재생
        return random.randint(0, total_count - 1)
    if mode == 1 and 0 <= current_idx < total_count:  # 1곡 반복
        return current_idx

    next_idx = current_idx + 1 if current_idx != -1 else 0
    if next_idx >= total_count:
        if mode == 0:  # 순차 재생 (끝에 도달하면 정지)
            return None
        next_idx = 0  # 전체 반복
    return next_idx


def get_prev_track_index(current_idx: int, total_count: int, mode: int) -> Optional[int]:
    if total_count <= 0:
        return None
    if mode == 3:  # 랜덤 재생
        return random.randint(0, total_count - 1)

    start = current_idx if current_idx != -1 else 0
    return (start - 1) % total_count