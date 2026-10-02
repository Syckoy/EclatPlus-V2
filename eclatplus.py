"""EclatPlus — éclat des couleurs, Python stdlib, inactif hors changement."""
from __future__ import annotations

import atexit
import ctypes
import json
import os
import sys
import tempfile
import threading
import tkinter as tk
import urllib.request
import zipfile
from ctypes import wintypes
from pathlib import Path
from tkinter import colorchooser, messagebox

from crosshair import CrosshairOverlay

APP_NAME = "EclatPlus"
LOCAL_VERSION = "1.2.0"
GITHUB_PAGE = "https://github.com/Syckoy/EclatPlus-V2"
GITHUB_VERSION_URLS = (
    "https://raw.githubusercontent.com/Syckoy/EclatPlus-V2/main/version.json",
    "https://raw.githubusercontent.com/Syckoy/EclatPlus-V2/master/version.json",
)
GITHUB_ZIP_URLS = (
    "https://github.com/Syckoy/EclatPlus-V2/archive/refs/heads/main.zip",
    "https://github.com/Syckoy/EclatPlus-V2/archive/refs/heads/master.zip",
)
UPDATE_FILES = (
    "eclatplus.py",
    "crosshair.py",
    "lancer.bat",
    "build_exe.bat",
    "README.md",
    "version.json",
    ".gitignore",
)



def settings_path() -> Path:
    root = Path.home() / "AppData" / "Roaming" / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root / "settings.json"


def load_settings() -> dict:
    defaults = {
        "eclat": 50,
        "limiter": False,
        "startup": False,
        "crosshair": False,
        "ch_style": "cross",
        "ch_color": "#00FF00",
        "ch_size": 8,
        "ch_thick": 2,
        "ch_gap": 4,
        "ch_outline": True,
        "ch_opacity": 100,
    }
    path = settings_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            defaults.update(data)
    except (OSError, json.JSONDecodeError):
        pass
    defaults["eclat"] = max(0, min(200, int(defaults.get("eclat") or 50)))
    defaults["limiter"] = bool(defaults.get("limiter"))
    defaults["startup"] = bool(defaults.get("startup"))
    if defaults.get("ch_style") not in ("cross", "dot", "circle", "crossdot"):
        defaults["ch_style"] = "cross"
    defaults["crosshair"] = bool(defaults.get("crosshair"))
    defaults["ch_outline"] = bool(defaults.get("ch_outline"))
    color = str(defaults.get("ch_color") or "#00FF00").strip()
    if len(color) != 7 or not color.startswith("#"):
        color = "#00FF00"
    else:
        try:
            int(color[1:], 16)
        except ValueError:
            color = "#00FF00"
    defaults["ch_color"] = color.upper()
    for key, default, lo, hi in (
        ("ch_size", 8, 1, 40),
        ("ch_thick", 2, 1, 10),
        ("ch_gap", 4, 0, 40),
        ("ch_opacity", 100, 1, 100),
    ):
        try:
            defaults[key] = _clamp(int(defaults.get(key, default)), lo, hi)
        except (TypeError, ValueError):
            defaults[key] = default
    return defaults


def save_settings(data: dict) -> None:
    payload = {
        "eclat": int(data["eclat"]),
        "limiter": bool(data["limiter"]),
        "startup": bool(data["startup"]),
        "crosshair": bool(data.get("crosshair")),
        "ch_style": str(data.get("ch_style") or "cross"),
        "ch_color": str(data.get("ch_color") or "#00FF00"),
        "ch_size": int(data.get("ch_size", 8)),
        "ch_thick": int(data.get("ch_thick", 2)),
        "ch_gap": int(data.get("ch_gap", 4)),
        "ch_outline": bool(data.get("ch_outline", True)),
        "ch_opacity": int(data.get("ch_opacity", 100)),
    }
    settings_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")


def exe_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --tray'
    script = Path(__file__).resolve()
    pyw = Path(sys.executable).with_name("pythonw.exe")
    exe = str(pyw if pyw.exists() else sys.executable)
    return f'"{exe}" "{script}" --tray'


def set_startup(enabled: bool) -> None:
    import winreg

    key = winreg.CreateKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
    )
    try:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_command())
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
    finally:
        key.Close()


def _parse_version(text: str) -> tuple[int, ...]:
    parts = []
    for bit in str(text).strip().lstrip("vV").split("."):
        if bit.isdigit():
            parts.append(int(bit))
        else:
            break
    return tuple(parts or (0,))


def _http_get(url: str, timeout: float) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": f"EclatPlus/{LOCAL_VERSION}"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def remote_version() -> str | None:
    for url in GITHUB_VERSION_URLS:
        try:
            data = json.loads(_http_get(url, 8).decode("utf-8"))
            ver = str(data.get("version") or "").strip()
            if ver:
                return ver
        except Exception:
            continue
    return None


def install_repo_update() -> None:
    raw = b""
    last_err: Exception | None = None
    for url in GITHUB_ZIP_URLS:
        try:
            raw = _http_get(url, 60)
            if raw[:2] == b"PK":
                break
        except Exception as exc:
            last_err = exc
            raw = b""
    if not raw:
        raise RuntimeError(last_err or "telechargement GitHub impossible")

    staging = Path(tempfile.mkdtemp(prefix="eclatplus-upd-"))
    zpath = staging / "repo.zip"
    zpath.write_bytes(raw)
    extracted = staging / "extracted"
    extracted.mkdir()
    with zipfile.ZipFile(zpath) as zf:
        zf.extractall(extracted)
    kids = [p for p in extracted.iterdir() if p.is_dir()]
    root = kids[0] if len(kids) == 1 else extracted
    dest = Path(__file__).resolve().parent
    for name in UPDATE_FILES:
        src = root / name
        if src.is_file():
            (dest / name).write_bytes(src.read_bytes())

    launcher = dest / "lancer.bat"
    if not (dest / "eclatplus.py").is_file() or not launcher.is_file():
        raise RuntimeError("fichiers manquants apres copie")

    bat = Path(tempfile.gettempdir()) / "eclatplus-apply-update.bat"
    pid = os.getpid()
    bat.write_text(
        "\n".join(
            [
                "@echo off",
                f":wait{pid}",
                f'tasklist /FI "PID eq {pid}" | find "{pid}" >nul',
                f"if not errorlevel 1 (timeout /t 1 /nobreak >nul & goto wait{pid})",
                f'start "" "{launcher}"',
                f'rd /s /q "{staging}"',
                'del "%~f0"',
                "",
            ]
        ),
        encoding="ascii",
        errors="replace",
    )
    os.startfile(str(bat))


def _clamp(n: int, lo: int, hi: int) -> int:
    return lo if n < lo else hi if n > hi else n


def _map_percent(percent: int, min_l: int, def_l: int, max_l: int) -> int:
    percent = _clamp(percent, 0, 100)
    if percent <= 50:
        t = percent / 50.0
        return int(round(min_l + (def_l - min_l) * t))
    u = (percent - 50) / 50.0
    return int(round(def_l + (max_l - def_l) * u))


def _level_to_percent(level: int, min_l: int, def_l: int, max_l: int) -> int:
    if level <= def_l:
        span = def_l - min_l
        if span <= 0:
            return 50
        return int(round(50.0 * (level - min_l) / span))
    span = max_l - def_l
    if span <= 0:
        return 50
    return 50 + int(round(50.0 * (level - def_l) / span))


class DvcInfo(ctypes.Structure):
    _fields_ = [
        ("Version", ctypes.c_uint32),
        ("CurrentLevel", ctypes.c_int32),
        ("MinLevel", ctypes.c_int32),
        ("MaxLevel", ctypes.c_int32),
    ]


class DvcInfoEx(ctypes.Structure):
    _fields_ = [
        ("Version", ctypes.c_uint32),
        ("CurrentLevel", ctypes.c_int32),
        ("MinLevel", ctypes.c_int32),
        ("MaxLevel", ctypes.c_int32),
        ("DefaultLevel", ctypes.c_int32),
    ]


def _nv_ver(size: int) -> int:
    return size | 0x10000


class NvidiaBackend:
    ID_INIT = 0x0150E828
    ID_UNLOAD = 0xD22BDD7E
    ID_ENUM = 0x9ABDD40D
    ID_GET = 0x4085DE45
    ID_GET_EX = 0x0E45002D
    ID_SET = 0x172409B4
    ID_SET_EX = 0x4A82C2B1
    OK = 0
    END = -7

    def __init__(self) -> None:
        self.dll = ctypes.WinDLL("nvapi64.dll")
        self.query = self.dll.nvapi_QueryInterface
        self.query.restype = ctypes.c_void_p
        self.query.argtypes = [ctypes.c_uint32]

        init = self._fn(self.ID_INIT, ctypes.CFUNCTYPE(ctypes.c_int))
        if init() != self.OK:
            raise OSError("NvAPI_Initialize")

        self.unload = self._fn(self.ID_UNLOAD, ctypes.CFUNCTYPE(ctypes.c_int), optional=True)
        self.enum_display = self._fn(
            self.ID_ENUM,
            ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p)),
        )
        self.get_ex = self._fn(
            self.ID_GET_EX,
            ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(DvcInfoEx)),
            optional=True,
        )
        self.set_ex = self._fn(
            self.ID_SET_EX,
            ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(DvcInfoEx)),
            optional=True,
        )
        self.get = self._fn(
            self.ID_GET,
            ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(DvcInfo)),
            optional=True,
        )
        self.set = self._fn(
            self.ID_SET,
            ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int),
            optional=True,
        )
        self.use_ex = bool(self.get_ex and self.set_ex)
        if not self.enum_display or (not self.use_ex and not (self.get and self.set)):
            raise OSError("NvAPI DVC")

        self.targets: list[dict] = []
        for i in range(64):
            display = ctypes.c_void_p()
            status = self.enum_display(i, ctypes.byref(display))
            if status == self.END or not display.value:
                break
            if status != self.OK:
                continue
            handle = ctypes.c_void_p(display.value)
            info = self._read(handle)
            if info is None:
                continue
            min_l, def_l, max_l, cur = info
            self.targets.append(
                {
                    "display": handle,
                    "original": cur,
                    "min": min_l,
                    "def": def_l,
                    "max": max_l,
                }
            )
        if not self.targets:
            raise OSError("Aucun écran NVIDIA DVC")

    def _fn(self, ident: int, proto, optional: bool = False):
        ptr = self.query(ident)
        if not ptr:
            if optional:
                return None
            raise OSError(hex(ident))
        return proto(ptr)

    def _read(self, display: ctypes.c_void_p):
        if self.use_ex and self.get_ex:
            info = DvcInfoEx()
            info.Version = _nv_ver(ctypes.sizeof(DvcInfoEx))
            if self.get_ex(display, 0, ctypes.byref(info)) == self.OK:
                return info.MinLevel, info.DefaultLevel, info.MaxLevel, info.CurrentLevel
        if self.get:
            info = DvcInfo()
            info.Version = _nv_ver(ctypes.sizeof(DvcInfo))
            if self.get(display, 0, ctypes.byref(info)) == self.OK:
                return info.MinLevel, info.MinLevel, info.MaxLevel, info.CurrentLevel
        return None

    def _set_level(self, display: ctypes.c_void_p, level: int) -> bool:
        if self.use_ex and self.set_ex and self.get_ex:
            info = DvcInfoEx()
            info.Version = _nv_ver(ctypes.sizeof(DvcInfoEx))
            if self.get_ex(display, 0, ctypes.byref(info)) != self.OK:
                return False
            info.CurrentLevel = _clamp(level, info.MinLevel, info.MaxLevel)
            return self.set_ex(display, 0, ctypes.byref(info)) == self.OK
        if self.set:
            return self.set(display, 0, level) == self.OK
        return False

    @property
    def name(self) -> str:
        return "NVIDIA Éclat numérique"

    def apply_percent(self, percent: int) -> bool:
        ok = False
        for t in self.targets:
            level = _map_percent(percent, t["min"], t["def"], t["max"])
            if self._set_level(t["display"], level):
                ok = True
        return ok

    def restore(self) -> None:
        for t in self.targets:
            self._set_level(t["display"], t["original"])

    def original_percent(self) -> int:
        t = self.targets[0]
        return _level_to_percent(t["original"], t["min"], t["def"], t["max"])

    def close(self) -> None:
        self.restore()
        if self.unload:
            self.unload()


class AmdBackend:
    OK = 0
    SAT = 1 << 2

    def __init__(self) -> None:
        self.dll = ctypes.WinDLL("atiadlxx.dll")
        alloc_t = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_int)
        self._bufs: list = []

        def alloc(n: int) -> int:
            buf = ctypes.create_string_buffer(n)
            self._bufs.append(buf)
            return ctypes.addressof(buf)

        self._alloc = alloc_t(alloc)
        self.dll.ADL2_Main_Control_Create.restype = ctypes.c_int
        self.dll.ADL2_Main_Control_Create.argtypes = [alloc_t, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
        self.dll.ADL2_Main_Control_Destroy.argtypes = [ctypes.c_void_p]
        self.dll.ADL2_Display_Color_Get.restype = ctypes.c_int
        self.dll.ADL2_Display_Color_Get.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
        ]
        self.dll.ADL2_Display_Color_Set.restype = ctypes.c_int
        self.dll.ADL2_Display_Color_Set.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ]
        ctx = ctypes.c_void_p()
        if self.dll.ADL2_Main_Control_Create(self._alloc, 1, ctypes.byref(ctx)) != self.OK or not ctx.value:
            raise OSError("ADL2_Main_Control_Create")
        self.ctx = ctx
        self.targets: list[dict] = []
        for adapter in range(16):
            for display in range(8):
                cur = ctypes.c_int()
                defv = ctypes.c_int()
                min_l = ctypes.c_int()
                max_l = ctypes.c_int()
                step = ctypes.c_int()
                if (
                    self.dll.ADL2_Display_Color_Get(
                        self.ctx,
                        adapter,
                        display,
                        self.SAT,
                        ctypes.byref(cur),
                        ctypes.byref(defv),
                        ctypes.byref(min_l),
                        ctypes.byref(max_l),
                        ctypes.byref(step),
                    )
                    != self.OK
                ):
                    continue
                self.targets.append(
                    {
                        "adapter": adapter,
                        "display": display,
                        "original": cur.value,
                        "min": min_l.value,
                        "def": defv.value,
                        "max": max_l.value,
                    }
                )
        if not self.targets:
            self.dll.ADL2_Main_Control_Destroy(self.ctx)
            raise OSError("Aucun écran AMD saturation")

    @property
    def name(self) -> str:
        return "AMD Saturation"

    def apply_percent(self, percent: int) -> bool:
        ok = False
        for t in self.targets:
            level = _map_percent(percent, t["min"], t["def"], t["max"])
            if self.dll.ADL2_Display_Color_Set(self.ctx, t["adapter"], t["display"], self.SAT, level) == self.OK:
                ok = True
        return ok

    def restore(self) -> None:
        for t in self.targets:
            self.dll.ADL2_Display_Color_Set(self.ctx, t["adapter"], t["display"], self.SAT, t["original"])

    def original_percent(self) -> int:
        t = self.targets[0]
        return _level_to_percent(t["original"], t["min"], t["def"], t["max"])

    def close(self) -> None:
        self.restore()
        self.dll.ADL2_Main_Control_Destroy(self.ctx)


class Gpu:
    def __init__(self) -> None:
        self.backend = None
        self._last = -1
        try:
            self.backend = NvidiaBackend()
        except OSError:
            try:
                self.backend = AmdBackend()
            except OSError:
                self.backend = None

    @property
    def name(self) -> str:
        return self.backend.name if self.backend else "Aucun pilote NVIDIA/AMD"

    def apply_percent(self, percent: int) -> bool:
        if not self.backend:
            return False
        percent = _clamp(percent, 0, 100)
        if percent == self._last:
            return True
        ok = self.backend.apply_percent(percent)
        if ok:
            self._last = percent
        return ok

    def restore(self) -> None:
        self._last = -1
        if self.backend:
            self.backend.restore()

    def original_percent(self) -> int:
        return self.backend.original_percent() if self.backend else 50

    def close(self) -> None:
        self._last = -1
        if self.backend:
            self.backend.close()
            self.backend = None


class MagColorEffect(ctypes.Structure):
    _fields_ = [("transform", ctypes.c_float * 25)]


class Magnification:
    def __init__(self) -> None:
        self._dll = None
        self._on = False
        self._last = 0.0

    def _load(self) -> bool:
        if self._dll:
            return True
        try:
            dll = ctypes.WinDLL("Magnification.dll")
        except OSError:
            return False
        dll.MagInitialize.restype = wintypes.BOOL
        dll.MagUninitialize.restype = wintypes.BOOL
        dll.MagSetFullscreenColorEffect.restype = wintypes.BOOL
        dll.MagSetFullscreenColorEffect.argtypes = [ctypes.POINTER(MagColorEffect)]
        try:
            dll.MagSetFullscreenUseBitmapSmoothing.argtypes = [wintypes.BOOL]
            dll.MagSetFullscreenUseBitmapSmoothing.restype = wintypes.BOOL
        except AttributeError:
            pass
        self._dll = dll
        return True

    def shutdown(self) -> None:
        if not self._on:
            self._last = 0.0
            return
        try:
            self._dll.MagUninitialize()
        except Exception:
            pass
        self._on = False
        self._last = 0.0

    def apply_amount(self, amount: float) -> bool:
        if amount <= 1.001:
            self.shutdown()
            return True
        if self._on and abs(amount - self._last) < 0.0005:
            return True
        if not self._load():
            return False
        if not self._on:
            if not self._dll.MagInitialize():
                return False
            smooth = getattr(self._dll, "MagSetFullscreenUseBitmapSmoothing", None)
            if smooth:
                smooth(False)
            self._on = True
            self._last = 0.0
        inv = 1.0 - amount
        g = (1.0 / 3.0) * inv
        d = g + amount
        m = MagColorEffect()
        vals = [0.0] * 25
        vals[0], vals[1], vals[2] = d, g, g
        vals[5], vals[6], vals[7] = g, d, g
        vals[10], vals[11], vals[12] = g, g, d
        vals[18] = 1.0
        vals[24] = 1.0
        for i, v in enumerate(vals):
            m.transform[i] = v
        if not self._dll.MagSetFullscreenColorEffect(ctypes.byref(m)):
            self.shutdown()
            return False
        self._last = amount
        return True


GPU = Gpu()
MAG = Magnification()
CROSSHAIR = CrosshairOverlay()
_closed = False


def apply_eclat(value: int, limiter: bool) -> str:
    value = _clamp(int(value), 0, 200)
    if limiter:
        value = min(value, 100)
    GPU.apply_percent(_clamp(value, 0, 100))
    if (not limiter) and value > 100:
        t = (value - 100) / 100.0
        amount = 1.0 + t * 2.0
        MAG.apply_amount(amount)
        extra = "couche extra ON"
    else:
        MAG.shutdown()
        extra = "couche extra OFF"
    return f"{GPU.name} | driver {min(value, 100)} | {extra}"


def restore_all() -> None:
    MAG.shutdown()
    GPU.restore()


def shutdown_all() -> None:
    global _closed
    if _closed:
        return
    _closed = True
    try:
        CROSSHAIR.shutdown()
    except Exception:
        pass
    MAG.shutdown()
    GPU.close()


atexit.register(shutdown_all)


class App(tk.Tk):
    def __init__(self, start_tray: bool) -> None:
        super().__init__()
        self.title("EclatPlus")
        self.resizable(False, False)
        self.cfg = load_settings()
        self._applied = None

        frm = tk.Frame(self, padx=10, pady=10)
        frm.pack()

        tk.Label(frm, text="ECLAT (0-200)").grid(row=0, column=0, sticky="w")
        self.lbl = tk.Label(frm, text=str(self.cfg["eclat"]), width=5)
        self.lbl.grid(row=0, column=1, sticky="e")

        self.var = tk.IntVar(value=self.cfg["eclat"])
        self.scale = tk.Scale(
            frm,
            from_=0,
            to=200,
            orient="horizontal",
            length=280,
            showvalue=False,
            variable=self.var,
            command=self._on_scale,
        )
        self.scale.grid(row=1, column=0, columnspan=2, pady=4)

        self.limiter = tk.BooleanVar(value=self.cfg["limiter"])
        tk.Checkbutton(
            frm,
            text="Limiter au pilote (max 100, pas de Loupe)",
            variable=self.limiter,
            command=self._on_limiter,
        ).grid(row=2, column=0, columnspan=2, sticky="w")

        self.startup = tk.BooleanVar(value=self.cfg["startup"])
        tk.Checkbutton(
            frm,
            text="Demarrer avec Windows",
            variable=self.startup,
            command=self._on_startup,
        ).grid(row=3, column=0, columnspan=2, sticky="w")

        btns = tk.Frame(frm)
        btns.grid(row=4, column=0, columnspan=2, pady=8, sticky="ew")
        tk.Button(btns, text="Appliquer", command=self._apply_now).pack(side="left", expand=True, fill="x")
        tk.Button(btns, text="Restaurer", command=self._restore).pack(side="left", expand=True, fill="x", padx=6)
        tk.Button(btns, text="Quitter", command=self._quit_restore).pack(side="left", expand=True, fill="x")

        self.status = tk.Label(frm, text=GPU.name, wraplength=320, justify="left")
        self.status.grid(row=12, column=0, columnspan=2, sticky="w")

        self._build_crosshair(frm)

        self.protocol("WM_DELETE_WINDOW", self._quit_restore)
        self._ch_armed = False
        self._apply_now()
        self._sync_crosshair()
        if start_tray:
            self.iconify()
        threading.Thread(target=self._update_worker, daemon=True).start()

    def _build_crosshair(self, frm: tk.Frame) -> None:
        styles = {"Croix": "cross", "Point": "dot", "Cercle": "circle", "Croix + point": "crossdot"}
        self._style_to_code = styles
        self._code_to_style = {code: label for label, code in styles.items()}
        self._ch_color = self.cfg["ch_color"]

        tk.Label(frm, text="VISEUR").grid(row=5, column=0, columnspan=2, sticky="w", pady=(10, 0))

        flags = tk.Frame(frm)
        flags.grid(row=6, column=0, columnspan=2, sticky="w")
        self.ch_on = tk.BooleanVar(value=self.cfg["crosshair"])
        tk.Checkbutton(flags, text="Afficher", variable=self.ch_on, command=lambda: self._sync_crosshair(True)).pack(side="left")
        self.ch_outline = tk.BooleanVar(value=self.cfg["ch_outline"])
        tk.Checkbutton(flags, text="Contour", variable=self.ch_outline, command=lambda: self._sync_crosshair(True)).pack(side="left", padx=8)

        form = tk.Frame(frm)
        form.grid(row=7, column=0, columnspan=2, sticky="w", pady=2)
        tk.Label(form, text="Forme").pack(side="left")
        self.ch_style = tk.StringVar(value=self._code_to_style.get(self.cfg["ch_style"], "Croix"))
        menu = tk.OptionMenu(form, self.ch_style, *styles.keys(), command=lambda _v: self._sync_crosshair(True))
        menu.config(width=14)
        menu.pack(side="left", padx=6)

        colors = tk.Frame(frm)
        colors.grid(row=8, column=0, columnspan=2, sticky="w")
        for hex_color in ("#00FF00", "#FF0000", "#00FFFF", "#FFFF00", "#FFFFFF", "#FF00FF"):
            tk.Button(
                colors,
                width=2,
                bg=hex_color,
                activebackground=hex_color,
                command=lambda h=hex_color: self._set_ch_color(h),
            ).pack(side="left", padx=1)
        self._color_btn = tk.Button(colors, text="Autre", command=self._pick_ch_color)
        self._color_btn.pack(side="left", padx=6)
        self._paint_color_btn()

        self.ch_size = tk.IntVar(value=self.cfg["ch_size"])
        self.ch_thick = tk.IntVar(value=self.cfg["ch_thick"])
        self.ch_gap = tk.IntVar(value=self.cfg["ch_gap"])
        self.ch_opacity = tk.IntVar(value=self.cfg["ch_opacity"])
        self._ch_scale(frm, 9, 0, "Taille", self.ch_size, 1, 40)
        self._ch_scale(frm, 9, 1, "Epaisseur", self.ch_thick, 1, 10)
        self._ch_scale(frm, 10, 0, "Ecart", self.ch_gap, 0, 40)
        self._ch_scale(frm, 10, 1, "Opacite", self.ch_opacity, 1, 100)

        self.ch_hint = tk.Label(
            frm,
            text="Visible en fenetre et en borderless. Plein ecran total : Windows le cache.",
            wraplength=300,
            justify="left",
            fg="#555555",
        )
        self.ch_hint.grid(row=11, column=0, columnspan=2, sticky="w", pady=(2, 6))

    def _ch_scale(self, frm: tk.Frame, row: int, col: int, label: str, var: tk.IntVar, lo: int, hi: int) -> None:
        tk.Scale(
            frm,
            from_=lo,
            to=hi,
            orient="horizontal",
            length=145,
            resolution=1,
            label=label,
            variable=var,
            command=self._on_ch_scale,
        ).grid(row=row, column=col, sticky="w")

    def _paint_color_btn(self) -> None:
        color = self._ch_color
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        fg = "#000000" if (r * 299 + g * 587 + b * 114) > 140000 else "#FFFFFF"
        self._color_btn.config(bg=color, fg=fg, activebackground=color, activeforeground=fg)

    def _set_ch_color(self, color: str) -> None:
        self._ch_color = color.upper()
        self._paint_color_btn()
        self._sync_crosshair(True)

    def _pick_ch_color(self) -> None:
        chosen = colorchooser.askcolor(color=self._ch_color, parent=self)
        if chosen and chosen[1]:
            self._set_ch_color(str(chosen[1]))

    def _on_ch_scale(self, _raw: str) -> None:
        self._sync_crosshair(False)

    def _sync_crosshair(self, save: bool = False) -> None:
        self._mark()
        if save:
            save_settings(self.cfg)
        try:
            host = int(self.winfo_id())
        except tk.TclError:
            host = 0
        try:
            CROSSHAIR.apply(self.cfg, host)
        except Exception:
            self.ch_hint.config(text="Viseur indisponible")
        else:
            self.ch_hint.config(text="Visible en fenetre et en borderless. Plein ecran total : Windows le cache.")
            self._arm_crosshair_tick()

    def _arm_crosshair_tick(self) -> None:
        if self._ch_armed or not bool(self.ch_on.get()):
            return
        self._ch_armed = True
        self.after(250, self._crosshair_tick)

    def _crosshair_tick(self) -> None:
        if not self.winfo_exists():
            self._ch_armed = False
            return
        if not bool(self.ch_on.get()):
            self._ch_armed = False
            return
        try:
            CROSSHAIR.tick()
        except Exception:
            pass
        self.after(250, self._crosshair_tick)

    def _update_worker(self) -> None:
        try:
            remote = remote_version()
            if not remote:
                return
            if _parse_version(remote) <= _parse_version(LOCAL_VERSION):
                return
            self.after(0, lambda: self._ask_update(remote))
        except Exception:
            return

    def _ask_update(self, remote: str) -> None:
        if not self.winfo_exists():
            return
        self.deiconify()
        self.lift()
        ok = messagebox.askyesno(
            "EclatPlus",
            f"Nouvelle version sur GitHub : {remote}\n"
            f"Version actuelle : {LOCAL_VERSION}\n\n"
            "Installer depuis le depot (pas les Releases) ?\n"
            "Tes reglages ne sont pas modifies.",
            parent=self,
        )
        if not ok:
            return
        try:
            self.config(cursor="watch")
            self.update_idletasks()
            self._mark()
            save_settings(self.cfg)
            install_repo_update()
            restore_all()
            shutdown_all()
            self.destroy()
        except Exception as exc:
            self.config(cursor="")
            messagebox.showerror(
                "EclatPlus",
                f"Mise a jour impossible :\n{exc}\n\nOuverture de GitHub.",
                parent=self,
            )
            os.startfile(GITHUB_PAGE)

    def _mark(self) -> None:
        self.cfg["eclat"] = int(self.var.get())
        self.cfg["limiter"] = bool(self.limiter.get())
        self.cfg["startup"] = bool(self.startup.get())
        if hasattr(self, "ch_on"):
            self.cfg["crosshair"] = bool(self.ch_on.get())
            self.cfg["ch_outline"] = bool(self.ch_outline.get())
            self.cfg["ch_style"] = self._style_to_code.get(self.ch_style.get(), "cross")
            self.cfg["ch_color"] = self._ch_color
            self.cfg["ch_size"] = int(self.ch_size.get())
            self.cfg["ch_thick"] = int(self.ch_thick.get())
            self.cfg["ch_gap"] = int(self.ch_gap.get())
            self.cfg["ch_opacity"] = int(self.ch_opacity.get())

    def _on_scale(self, _raw: str) -> None:
        self.lbl.config(text=str(int(self.var.get())))
        self._mark()
        self._apply_now()

    def _on_limiter(self) -> None:
        self._mark()
        save_settings(self.cfg)
        self._apply_now()

    def _on_startup(self) -> None:
        self._mark()
        set_startup(bool(self.startup.get()))
        save_settings(self.cfg)

    def _apply_now(self) -> None:
        value = int(self.var.get())
        limiter = bool(self.limiter.get())
        key = (value, limiter)
        if key == self._applied:
            return
        self.status.config(text=apply_eclat(value, limiter))
        self._applied = key
        self._mark()

    def _restore(self) -> None:
        restore_all()
        orig = GPU.original_percent()
        self.var.set(orig)
        self.lbl.config(text=str(orig))
        MAG.shutdown()
        self._applied = (orig, bool(self.limiter.get()))
        self._mark()
        self.status.config(text=f"Restaure au niveau d'origine ({orig}). {GPU.name}")

    def _quit_restore(self) -> None:
        self._mark()
        save_settings(self.cfg)
        restore_all()
        shutdown_all()
        self.destroy()


def selftest() -> int:
    lines = [f"backend={GPU.name}"]
    try:
        lines.append(f"apply50={GPU.apply_percent(50)}")
        lines.append(f"apply100={GPU.apply_percent(100)}")
        restore_all()
        lines.append("restore=ok")
        mag_ok = MAG.apply_amount(1.0)
        MAG.shutdown()
        lines.append(f"mag_identity_off={mag_ok and not MAG._on}")
        limiter_status = apply_eclat(150, True)
        mag_was = MAG._on
        MAG.shutdown()
        GPU.restore()
        lines.append(f"limiter150 mag_active={mag_was} status={limiter_status}")
        print("\n".join(lines))
        return 0
    except Exception as ex:
        print("\n".join(lines))
        print("FAIL", ex)
        restore_all()
        return 1
    finally:
        shutdown_all()


def main() -> int:
    args = sys.argv[1:]
    if "--selftest" in args:
        return selftest()
    App(start_tray="--tray" in args).mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
