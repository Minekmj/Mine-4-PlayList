import os
import sys
import shutil
import ctypes
import subprocess
import platform

class NativeParticle(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("vx", ctypes.c_float),
        ("vy", ctypes.c_float),
        ("size", ctypes.c_float),
        ("base_speed", ctypes.c_float),
        ("alpha_factor", ctypes.c_float),
        ("rot", ctypes.c_float),
        ("rot_speed", ctypes.c_float),
        ("phase", ctypes.c_float),
        ("pad", ctypes.c_float),
        ("type", ctypes.c_int32),
        ("direction", ctypes.c_int32),
        ("out_of_bounds", ctypes.c_int32),
    ]

_cached_lib = None


def _find_vcvarsall():
    arch = "x64" if sys.maxsize > 2**32 else "x86"

    for prog_files in [os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles")]:
        if not prog_files:
            continue
        vswhere = os.path.join(prog_files, "Microsoft Visual Studio", "Installer", "vswhere.exe")
        if os.path.exists(vswhere):
            try:
                res = subprocess.run(
                    [
                        vswhere,
                        "-latest",
                        "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                        "-property", "installationPath"
                    ],
                    capture_output=True,
                    text=True,
                    check=True
                )
                vs_path = res.stdout.strip()
                if vs_path:
                    vcvars = os.path.join(vs_path, "VC", "Auxiliary", "Build", "vcvarsall.bat")
                    if os.path.exists(vcvars):
                        return vcvars, arch
            except Exception:
                pass

    for env_var in ["VS170COMNTOOLS", "VS160COMNTOOLS", "VS150COMNTOOLS"]:
        val = os.environ.get(env_var)
        if val:
            vcvars = os.path.abspath(os.path.join(val, r"..\..\VC\Auxiliary\Build\vcvarsall.bat"))
            if os.path.exists(vcvars):
                return vcvars, arch

    return None, arch


def _compile_with_msvc(base_dir: str, c_src_name: str, lib_name: str):
    vcvars_bat, arch = _find_vcvarsall()
    if shutil.which("cl") is not None:
        cmd = ["cl", "/O2", "/arch:AVX2", "/LD", f"/Fe:{lib_name}", c_src_name]
        res = subprocess.run(cmd, cwd=base_dir, capture_output=True, text=True)
    elif vcvars_bat and os.path.exists(vcvars_bat):
        cmd = f'call "{vcvars_bat}" {arch} && cl /O2 /openmp /LD /Fe:"{lib_name}" "{c_src_name}"'
        res = subprocess.run(cmd, shell=True, cwd=base_dir, capture_output=True, text=True)
    else:
        raise RuntimeError("MSVC (cl.exe) 또는 vcvarsall.bat를 찾을 수 없습니다. Visual Studio C++ 빌드 도구를 확인하세요.")

    if res.returncode != 0:
        raise RuntimeError(f"MSVC Compile failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")

    base_name = os.path.splitext(lib_name)[0]
    for ext in [".obj", ".exp", ".lib"]:
        temp_file = os.path.join(base_dir, base_name + ext)
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass


def get_native_engine():
    global _cached_lib
    if _cached_lib is not None:
        return _cached_lib

    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    c_src_name = "native_effects.c"
    c_src = os.path.join(base_dir, c_src_name)

    system = platform.system()
    if system == "Windows":
        lib_name = "native_effects.dll"
    elif system == "Darwin":
        lib_name = "libnative_effects.dylib"
    else:
        lib_name = "libnative_effects.so"

    lib_path = os.path.join(base_dir, lib_name)

    if not os.path.exists(lib_path) and os.path.exists(c_src):
        try:
            if system == "Windows":
                _compile_with_msvc(base_dir, c_src_name, lib_name)
            else:
                cmd = ["gcc", "-O3", "-shared", "-fPIC", "-o", lib_path, c_src, "-lm"]
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            print(f"[NativeBridge] Compilation failed: {e}")

    if not os.path.exists(lib_path):
        return None

    try:
        lib = ctypes.CDLL(lib_path)

        lib.c_render_vanishing_perspective.argtypes = [
            ctypes.POINTER(ctypes.c_uint32), ctypes.c_int, ctypes.c_int,
            ctypes.POINTER(ctypes.c_uint32), ctypes.c_int, ctypes.c_int,
            ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
            ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
            ctypes.c_int,
            ctypes.c_int, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float
        ]
        lib.c_render_vanishing_perspective.restype = None

        lib.c_apply_optical_gaussian_blur.argtypes = [
            ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_int, ctypes.c_int, ctypes.c_int
        ]
        lib.c_apply_optical_gaussian_blur.restype = None

        lib.c_render_rounded_box_shadow.argtypes = [
            ctypes.POINTER(ctypes.c_uint32), ctypes.c_int, ctypes.c_int,
            ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
            ctypes.c_float, ctypes.c_float,
            ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_float
        ]
        lib.c_render_rounded_box_shadow.restype = None

        lib.c_update_particles.argtypes = [
            ctypes.POINTER(NativeParticle), ctypes.c_int,
            ctypes.c_float, ctypes.c_float, ctypes.c_float,
            ctypes.c_float, ctypes.c_float
        ]
        lib.c_update_particles.restype = None

        lib.c_compute_aurora_wave.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.c_int,
            ctypes.c_float, ctypes.c_float, ctypes.c_float,
            ctypes.c_float, ctypes.c_int
        ]
        lib.c_compute_aurora_wave.restype = None

        lib.c_calculate_frame_db.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.c_int
        ]
        lib.c_calculate_frame_db.restype = ctypes.c_float

        _cached_lib = lib
        return _cached_lib
    except Exception as e:
        print(f"[NativeBridge] Failed to bind native functions: {e}")
        return None