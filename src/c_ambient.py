import os
import ctypes

_lib = None

def get_compiled_c_engine():
    global _lib
    if _lib is not None:
        return _lib

    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "C")
    dll_path = os.path.join(base_dir, f"ambient_core.dll")

    if os.path.exists(dll_path):
        try:
            lib = ctypes.CDLL(dll_path)
            lib.c_render_vanishing_perspective.argtypes = [
                ctypes.POINTER(ctypes.c_uint32), ctypes.c_int, ctypes.c_int,
                ctypes.POINTER(ctypes.c_uint32), ctypes.c_int, ctypes.c_int,
                ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
                ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float
            ]
            lib.c_render_vanishing_perspective.restype = None

            lib.c_apply_optical_gaussian_blur.argtypes = [
                ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
                ctypes.c_int, ctypes.c_int, ctypes.c_int
            ]
            lib.c_apply_optical_gaussian_blur.restype = None

            _lib = lib
            return _lib
        except Exception as e:
            print(f"[C-Engine] 로드 오류: {e}")

    return None