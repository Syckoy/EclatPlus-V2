"""Viseur cliquable a travers. Dessine seulement quand le reglage change.

Fenetre classique transparente (clics qui passent). Pas de surface DirectComposition :
elle empeche le jeu de prendre la souris.
"""
from __future__ import annotations

import ctypes
import time
import uuid
from ctypes import wintypes

STYLES = ("cross", "dot", "circle", "crossdot")

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_LRESULT = ctypes.c_ssize_t
_WNDPROC = ctypes.WINFUNCTYPE(_LRESULT, wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM)
_bound = False
_class_ready = False


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _SIZE(ctypes.Structure):
    _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]


class _BLEND(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_ubyte),
        ("BlendFlags", ctypes.c_ubyte),
        ("SourceConstantAlpha", ctypes.c_ubyte),
        ("AlphaFormat", ctypes.c_ubyte),
    ]


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", _RECT),
        ("rcWork", _RECT),
        ("dwFlags", wintypes.DWORD),
    ]


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", ctypes.c_long),
        ("biHeight", ctypes.c_long),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class _BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", _BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


class _WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", _WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


def _as_int(handle) -> int:
    if not handle:
        return 0
    value = getattr(handle, "value", handle)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _wnd_proc(hwnd, msg, wparam, lparam):
    if msg == 0x0084:  # WM_NCHITTEST : le clic traverse le viseur
        return -1
    if msg == 0x0021:  # WM_MOUSEACTIVATE
        return 3
    return _user32.DefWindowProcW(hwnd, msg, wparam, lparam)


_PROC = _WNDPROC(_wnd_proc)
_CLASS = "EclatPlusCrosshair"


def _bind() -> None:
    global _bound
    if _bound:
        return
    u, g, k = _user32, _gdi32, _kernel32
    k.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    k.GetModuleHandleW.restype = wintypes.HMODULE
    u.DefWindowProcW.argtypes = [wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]
    u.DefWindowProcW.restype = _LRESULT
    u.RegisterClassW.argtypes = [ctypes.POINTER(_WNDCLASSW)]
    u.RegisterClassW.restype = wintypes.ATOM
    u.CreateWindowExW.argtypes = [
        wintypes.DWORD,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HWND,
        wintypes.HMENU,
        wintypes.HINSTANCE,
        wintypes.LPVOID,
    ]
    u.CreateWindowExW.restype = wintypes.HWND
    u.DestroyWindow.argtypes = [wintypes.HWND]
    u.DestroyWindow.restype = wintypes.BOOL
    u.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    u.ShowWindow.restype = wintypes.BOOL
    u.EnableWindow.argtypes = [wintypes.HWND, wintypes.BOOL]
    u.EnableWindow.restype = wintypes.BOOL
    u.SetWindowPos.argtypes = [
        wintypes.HWND,
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    u.SetWindowPos.restype = wintypes.BOOL
    u.GetForegroundWindow.argtypes = []
    u.GetForegroundWindow.restype = wintypes.HWND
    u.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(_RECT)]
    u.GetWindowRect.restype = wintypes.BOOL
    u.GetTopWindow.argtypes = [wintypes.HWND]
    u.GetTopWindow.restype = wintypes.HWND
    u.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
    u.GetWindow.restype = wintypes.HWND
    u.IsWindowVisible.argtypes = [wintypes.HWND]
    u.IsWindowVisible.restype = wintypes.BOOL
    u.IsIconic.argtypes = [wintypes.HWND]
    u.IsIconic.restype = wintypes.BOOL
    u.UpdateLayeredWindow.argtypes = [
        wintypes.HWND,
        wintypes.HDC,
        ctypes.POINTER(_POINT),
        ctypes.POINTER(_SIZE),
        wintypes.HDC,
        ctypes.POINTER(_POINT),
        wintypes.DWORD,
        ctypes.POINTER(_BLEND),
        wintypes.DWORD,
    ]
    u.UpdateLayeredWindow.restype = wintypes.BOOL
    u.GetDC.argtypes = [wintypes.HWND]
    u.GetDC.restype = wintypes.HDC
    u.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    u.ReleaseDC.restype = ctypes.c_int
    u.GetSystemMetrics.argtypes = [ctypes.c_int]
    u.GetSystemMetrics.restype = ctypes.c_int
    u.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    u.MonitorFromWindow.restype = wintypes.HANDLE
    u.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_MONITORINFO)]
    u.GetMonitorInfoW.restype = wintypes.BOOL
    g.CreateCompatibleDC.argtypes = [wintypes.HDC]
    g.CreateCompatibleDC.restype = wintypes.HDC
    g.DeleteDC.argtypes = [wintypes.HDC]
    g.DeleteDC.restype = wintypes.BOOL
    g.CreateDIBSection.argtypes = [
        wintypes.HDC,
        ctypes.POINTER(_BITMAPINFO),
        wintypes.UINT,
        ctypes.POINTER(ctypes.c_void_p),
        wintypes.HANDLE,
        wintypes.DWORD,
    ]
    g.CreateDIBSection.restype = wintypes.HBITMAP
    g.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    g.SelectObject.restype = wintypes.HGDIOBJ
    g.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    g.DeleteObject.restype = wintypes.BOOL
    _bound = True


def _clamp(n: int, lo: int, hi: int) -> int:
    return lo if n < lo else hi if n > hi else n


def _parse_color(text: str) -> tuple[int, int, int]:
    s = str(text or "").strip()
    if s.startswith("#"):
        s = s[1:]
    if len(s) == 6:
        try:
            return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
        except ValueError:
            pass
    return 0, 255, 0


def _pick(cfg: dict, *keys: str, default=None):
    for key in keys:
        if key in cfg and cfg[key] is not None:
            return cfg[key]
    return default


def normalize(cfg: dict) -> dict:
    style = str(_pick(cfg, "style", "ch_style", default="cross") or "cross")
    if style not in STYLES:
        style = "cross"

    def num(*keys: str, default: int, lo: int, hi: int) -> int:
        try:
            value = int(_pick(cfg, *keys, default=default))
        except (TypeError, ValueError):
            value = default
        return _clamp(value, lo, hi)

    return {
        "enabled": bool(_pick(cfg, "enabled", "crosshair", default=False)),
        "style": style,
        "color": "#{:02X}{:02X}{:02X}".format(
            *_parse_color(str(_pick(cfg, "color", "ch_color", default="#00FF00") or "#00FF00"))
        ),
        "size": num("size", "ch_size", default=8, lo=1, hi=40),
        "thick": num("thick", "ch_thick", default=2, lo=1, hi=10),
        "gap": num("gap", "ch_gap", default=4, lo=0, hi=40),
        "outline": bool(_pick(cfg, "outline", "ch_outline", default=True)),
        "opacity": num("opacity", "ch_opacity", default=100, lo=1, hi=100),
    }


def _fill(buf: bytearray, w: int, h: int, x0: int, y0: int, x1: int, y1: int, px: bytes) -> None:
    if x0 > x1 or y0 > y1:
        return
    x0 = 0 if x0 < 0 else x0
    y0 = 0 if y0 < 0 else y0
    x1 = w - 1 if x1 >= w else x1
    y1 = h - 1 if y1 >= h else y1
    if x0 > x1 or y0 > y1:
        return
    span = px * (x1 - x0 + 1)
    stride = w * 4
    width = len(span)
    for y in range(y0, y1 + 1):
        i = y * stride + x0 * 4
        buf[i : i + width] = span


def _disk(buf: bytearray, w: int, h: int, cx: int, cy: int, radius: int, px: bytes) -> None:
    if radius < 0:
        return
    r2 = radius * radius
    stride = w * 4
    for y in range(cy - radius, cy + radius + 1):
        if y < 0 or y >= h:
            continue
        dy = y - cy
        row = y * stride
        for x in range(cx - radius, cx + radius + 1):
            if x < 0 or x >= w:
                continue
            dx = x - cx
            if dx * dx + dy * dy <= r2:
                i = row + x * 4
                buf[i : i + 4] = px


def _ring(buf: bytearray, w: int, h: int, cx: int, cy: int, inner: float, outer: float, px: bytes) -> None:
    if outer < 0:
        return
    if inner < 0:
        inner = 0
    o2 = outer * outer
    i2 = inner * inner
    rad = int(outer) + 1
    stride = w * 4
    for y in range(cy - rad, cy + rad + 1):
        if y < 0 or y >= h:
            continue
        dy = y - cy
        row = y * stride
        for x in range(cx - rad, cx + rad + 1):
            if x < 0 or x >= w:
                continue
            dx = x - cx
            d2 = dx * dx + dy * dy
            if i2 <= d2 <= o2:
                i = row + x * 4
                buf[i : i + 4] = px


def _bgra(r: int, g: int, b: int) -> bytes:
    return bytes((b, g, r, 255))


def _cross(buf: bytearray, w: int, h: int, cx: int, cy: int, size: int, thick: int, gap: int, px: bytes, expand: int) -> None:
    g = gap - expand
    if g < 0:
        g = 0
    length = size + expand
    t = thick + 2 * expand
    y0 = cy - t // 2
    y1 = y0 + t - 1
    _fill(buf, w, h, cx - g - length, y0, cx - g, y1, px)
    _fill(buf, w, h, cx + g, y0, cx + g + length, y1, px)
    x0 = cx - t // 2
    x1 = x0 + t - 1
    _fill(buf, w, h, x0, cy - g - length, x1, cy - g, px)
    _fill(buf, w, h, x0, cy + g, x1, cy + g + length, px)


def render(cfg: dict) -> tuple[int, int, bytes]:
    n = normalize(cfg)
    size, thick, gap = n["size"], n["thick"], n["gap"]
    reach = size + gap + thick + 4
    side = reach * 2 + 1
    cx = cy = reach
    buf = bytearray(side * side * 4)
    r, g, b = _parse_color(n["color"])
    color = _bgra(r, g, b)
    black = _bgra(0, 0, 0)
    outline = bool(n["outline"])
    style = n["style"]
    if style in ("cross", "crossdot"):
        if outline:
            _cross(buf, side, side, cx, cy, size, thick, gap, black, 1)
        _cross(buf, side, side, cx, cy, size, thick, gap, color, 0)
    if style == "crossdot":
        dot = max(1, (thick + 1) // 2)
        if outline:
            _disk(buf, side, side, cx, cy, dot + 1, black)
        _disk(buf, side, side, cx, cy, dot, color)
    elif style == "dot":
        if outline:
            _disk(buf, side, side, cx, cy, size + 1, black)
        _disk(buf, side, side, cx, cy, size, color)
    elif style == "circle":
        if outline:
            _ring(buf, side, side, cx, cy, size - thick / 2.0 - 1, size + thick / 2.0 + 1, black)
        _ring(buf, side, side, cx, cy, size - thick / 2.0, size + thick / 2.0, color)
    return side, side, bytes(buf)


def _primary_rect() -> tuple[int, int, int, int]:
    return 0, 0, _user32.GetSystemMetrics(0), _user32.GetSystemMetrics(1)


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def _guid(text: str) -> _GUID:
    value = uuid.UUID(text)
    data = value.bytes_le
    guid = _GUID()
    guid.Data1 = int.from_bytes(data[0:4], "little")
    guid.Data2 = int.from_bytes(data[4:6], "little")
    guid.Data3 = int.from_bytes(data[6:8], "little")
    guid.Data4 = (ctypes.c_ubyte * 8).from_buffer_copy(data[8:16])
    return guid


def _com(this, index: int, restype, argtypes, *args):
    ptr = this if isinstance(this, ctypes.c_void_p) else ctypes.c_void_p(this)
    table = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
    fn = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(table[index])
    return fn(ptr, *args)


def _release(ptr) -> None:
    if ptr:
        _com(ptr, 2, ctypes.c_ulong, ())


def _query(obj, name: str):
    out = ctypes.c_void_p()
    hr = _com(
        obj,
        0,
        ctypes.c_long,
        (ctypes.POINTER(_GUID), ctypes.POINTER(ctypes.c_void_p)),
        ctypes.byref(_guid(name)),
        ctypes.byref(out),
    )
    if hr < 0 or not out.value:
        raise OSError(f"QueryInterface {name} {hr & 0xFFFFFFFF:08X}")
    return out


class _DxDesc(ctypes.Structure):
    _fields_ = [
        ("Width", ctypes.c_uint),
        ("Height", ctypes.c_uint),
        ("MipLevels", ctypes.c_uint),
        ("ArraySize", ctypes.c_uint),
        ("Format", ctypes.c_uint),
        ("SampleCount", ctypes.c_uint),
        ("SampleQuality", ctypes.c_uint),
        ("Usage", ctypes.c_uint),
        ("BindFlags", ctypes.c_uint),
        ("CPUAccessFlags", ctypes.c_uint),
        ("MiscFlags", ctypes.c_uint),
    ]


class _SwapDesc(ctypes.Structure):
    _fields_ = [
        ("Width", ctypes.c_uint),
        ("Height", ctypes.c_uint),
        ("Format", ctypes.c_uint),
        ("Stereo", ctypes.c_int),
        ("SampleCount", ctypes.c_uint),
        ("SampleQuality", ctypes.c_uint),
        ("BufferUsage", ctypes.c_uint),
        ("BufferCount", ctypes.c_uint),
        ("Scaling", ctypes.c_uint),
        ("SwapEffect", ctypes.c_uint),
        ("AlphaMode", ctypes.c_uint),
        ("Flags", ctypes.c_uint),
    ]


class _Mapped(ctypes.Structure):
    _fields_ = [
        ("pData", ctypes.c_void_p),
        ("RowPitch", ctypes.c_uint),
        ("DepthPitch", ctypes.c_uint),
    ]


class _DxgiMap(ctypes.Structure):
    _fields_ = [("Pitch", ctypes.c_int), ("pBits", ctypes.c_void_p)]


class _Box(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_uint),
        ("top", ctypes.c_uint),
        ("front", ctypes.c_uint),
        ("right", ctypes.c_uint),
        ("bottom", ctypes.c_uint),
        ("back", ctypes.c_uint),
    ]


class DxLayer:
    """Image fixe, composee par Windows. Redessinee seulement si le viseur change."""

    def __init__(self) -> None:
        self.d3d = None
        self.context = None
        self.dxgi = None
        self.dcomp = None
        self.target = None
        self.visual = None
        self.surface = None
        self.w = 0
        self.h = 0
        self.ok = False

    def open(self, hwnd, w: int, h: int, raw: bytes, alpha: int) -> bool:
        self.close()
        try:
            self._boot()
            self._tree(hwnd, w, h)
            self.upload(raw, w, h, alpha)
        except OSError:
            self.close()
            return False
        self.ok = True
        return True

    def upload(self, raw: bytes, w: int, h: int, alpha: int) -> None:
        if not self.surface or not self.context or w != self.w or h != self.h:
            raise OSError("taille")
        drawn = ctypes.c_void_p()
        offset = _POINT()
        hr = _com(
            self.surface,
            3,
            ctypes.c_long,
            (ctypes.c_void_p, ctypes.POINTER(_GUID), ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(_POINT)),
            None,
            ctypes.byref(_guid("cafcb56c-6ac3-4889-bf47-9e23bbd260ec")),
            ctypes.byref(drawn),
            ctypes.byref(offset),
        )
        if hr < 0 or not drawn.value:
            raise OSError(f"BeginDraw {hr & 0xFFFFFFFF:08X}")
        tex = None
        try:
            tex = _query(drawn, "6f15aaf2-d208-4e89-9ab4-489535d34f9c")
            src = raw if alpha >= 255 else self._fade(raw, alpha / 255.0)
            box = _Box(offset.x, offset.y, 0, offset.x + w, offset.y + h, 1)
            buf = ctypes.create_string_buffer(src)
            _com(
                self.context,
                48,
                None,
                (
                    ctypes.c_void_p,
                    ctypes.c_uint,
                    ctypes.POINTER(_Box),
                    ctypes.c_void_p,
                    ctypes.c_uint,
                    ctypes.c_uint,
                ),
                tex,
                0,
                ctypes.byref(box),
                ctypes.cast(buf, ctypes.c_void_p),
                w * 4,
                0,
            )
        finally:
            _release(tex)
            _release(drawn)
        hr = _com(self.surface, 4, ctypes.c_long, ())
        if hr < 0:
            raise OSError(f"EndDraw {hr & 0xFFFFFFFF:08X}")
        hr = _com(self.dcomp, 3, ctypes.c_long, ())
        if hr < 0:
            raise OSError(f"Commit {hr & 0xFFFFFFFF:08X}")

    def close(self) -> None:
        self.ok = False
        for item in (self.surface, self.visual, self.target, self.dcomp, self.dxgi, self.context, self.d3d):
            _release(item)
        self.surface = self.visual = self.target = self.dcomp = self.dxgi = self.context = self.d3d = None
        self.w = self.h = 0

    def _fade(self, raw: bytes, scale: float) -> bytes:
        out = bytearray(len(raw))
        for i in range(0, len(raw), 4):
            a = int(raw[i + 3] * scale)
            if a <= 0:
                continue
            k = a / 255.0
            out[i] = int(raw[i] * k)
            out[i + 1] = int(raw[i + 1] * k)
            out[i + 2] = int(raw[i + 2] * k)
            out[i + 3] = a
        return bytes(out)

    def _boot(self) -> None:
        d3d = ctypes.WinDLL("d3d11.dll")
        d3d.D3D11CreateDevice.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.POINTER(ctypes.c_uint),
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_uint),
            ctypes.POINTER(ctypes.c_void_p),
        ]
        d3d.D3D11CreateDevice.restype = ctypes.c_long
        levels = (ctypes.c_uint * 3)(0xB000, 0xA100, 0xA000)
        device = ctypes.c_void_p()
        context = ctypes.c_void_p()
        level = ctypes.c_uint()
        hr = d3d.D3D11CreateDevice(
            None, 1, None, 0x20, levels, 3, 7, ctypes.byref(device), ctypes.byref(level), ctypes.byref(context)
        )
        if hr < 0 or not device.value:
            raise OSError(f"D3D11CreateDevice {hr & 0xFFFFFFFF:08X}")
        self.d3d = device
        self.context = context
        self.dxgi = _query(device, "54ec77fa-1377-44e6-8c32-88fd5f44c84c")
        dcomp = ctypes.WinDLL("dcomp.dll")
        dcomp.DCompositionCreateDevice.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(_GUID),
            ctypes.POINTER(ctypes.c_void_p),
        ]
        dcomp.DCompositionCreateDevice.restype = ctypes.c_long
        comp = ctypes.c_void_p()
        hr = dcomp.DCompositionCreateDevice(
            self.dxgi,
            ctypes.byref(_guid("C37EA93A-E7AA-450D-B16F-9746CB0407F3")),
            ctypes.byref(comp),
        )
        if hr < 0 or not comp.value:
            raise OSError(f"DCompositionCreateDevice {hr & 0xFFFFFFFF:08X}")
        self.dcomp = comp

    def _tree(self, hwnd, w: int, h: int) -> None:
        target = ctypes.c_void_p()
        hr = _com(
            self.dcomp,
            6,
            ctypes.c_long,
            (wintypes.HWND, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)),
            wintypes.HWND(hwnd),
            1,
            ctypes.byref(target),
        )
        if hr < 0 or not target.value:
            raise OSError(f"CreateTargetForHwnd {hr & 0xFFFFFFFF:08X}")
        self.target = target
        visual = ctypes.c_void_p()
        hr = _com(self.dcomp, 7, ctypes.c_long, (ctypes.POINTER(ctypes.c_void_p),), ctypes.byref(visual))
        if hr < 0 or not visual.value:
            raise OSError(f"CreateVisual {hr & 0xFFFFFFFF:08X}")
        self.visual = visual
        surface = ctypes.c_void_p()
        hr = _com(
            self.dcomp,
            8,
            ctypes.c_long,
            (ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p)),
            w,
            h,
            87,
            1,
            ctypes.byref(surface),
        )
        if hr < 0 or not surface.value:
            raise OSError(f"CreateSurface {hr & 0xFFFFFFFF:08X}")
        self.surface = surface
        self.w = w
        self.h = h
        hr = _com(self.visual, 15, ctypes.c_long, (ctypes.c_void_p,), self.surface)
        if hr < 0:
            raise OSError(f"SetContent {hr & 0xFFFFFFFF:08X}")
        hr = _com(self.target, 3, ctypes.c_long, (ctypes.c_void_p,), self.visual)
        if hr < 0:
            raise OSError(f"SetRoot {hr & 0xFFFFFFFF:08X}")


def monitor_rect(host_hwnd: int) -> tuple[int, int, int, int]:
    _bind()
    if host_hwnd:
        mon = _user32.MonitorFromWindow(wintypes.HWND(host_hwnd), 1)
        info = _MONITORINFO()
        info.cbSize = ctypes.sizeof(_MONITORINFO)
        if mon and _user32.GetMonitorInfoW(mon, ctypes.byref(info)):
            r = info.rcMonitor
            if r.right > r.left and r.bottom > r.top:
                return r.left, r.top, r.right, r.bottom
    return _primary_rect()


class CrosshairOverlay:
    def __init__(self) -> None:
        self._hwnd = None
        self._key = None
        self._visible = False
        self._game_rect = None
        self._x = 0
        self._y = 0
        self._w = 0
        self._h = 0
        self._last_fg = 0
        self._fg_large = False
        self._boost_until = 0.0
        self._dx = None

    def apply(self, cfg: dict, host_hwnd: int = 0) -> None:
        n = normalize(cfg)
        if not n["enabled"]:
            self.hide()
            return
        _bind()
        left, top, right, bottom = self._target_rect(host_hwnd)
        w, h, raw = render(cfg)
        x = left + (right - left - w) // 2
        y = top + (bottom - top - h) // 2
        key = (n["style"], n["color"], n["size"], n["thick"], n["gap"], n["outline"], n["opacity"], x, y, w)
        if key == self._key and self._visible and self._hwnd:
            return
        self._present(x, y, w, h, raw, n["opacity"])
        self._key = key
        self._visible = True

    def tick(self) -> None:
        """Recentre si la resolution change. Ne reprend pas la souris du jeu."""
        if not self._visible or not self._hwnd:
            return
        _bind()
        fg = _as_int(_user32.GetForegroundWindow())
        me = _as_int(self._hwnd)
        if not fg or fg == me or fg == self._last_fg:
            return
        self._last_fg = fg
        self._track_foreground(fg)

    def _target_rect(self, host_hwnd: int) -> tuple[int, int, int, int]:
        if self._game_rect:
            return self._game_rect
        return monitor_rect(host_hwnd)

    def _track_foreground(self, fg: int) -> bool:
        if _user32.IsIconic(wintypes.HWND(fg)):
            return False
        mon = monitor_rect(fg)
        wr = _RECT()
        if not _user32.GetWindowRect(wintypes.HWND(fg), ctypes.byref(wr)):
            return False
        mw = mon[2] - mon[0]
        mh = mon[3] - mon[1]
        if mw <= 0 or mh <= 0:
            return False
        ww = wr.right - wr.left
        wh = wr.bottom - wr.top
        if ww * 2 < mw or wh * 2 < mh:
            return False
        if mon == self._game_rect:
            return True
        self._game_rect = mon
        if self._w <= 0 or not self._hwnd:
            return True
        x = mon[0] + max(0, (mw - self._w) // 2)
        y = mon[1] + max(0, (mh - self._h) // 2)
        self._x, self._y = x, y
        if self._key is not None:
            self._key = (*self._key[:-3], x, y, self._key[-1])
        _user32.SetWindowPos(self._hwnd, ctypes.c_void_p(-1), x, y, 0, 0, 0x0011)
        return True

    def _is_behind(self) -> bool:
        fg = _as_int(_user32.GetForegroundWindow())
        me = _as_int(self._hwnd)
        if not fg or fg == me:
            return False
        hwnd = _user32.GetTopWindow(None)
        for _ in range(48):
            current = _as_int(hwnd)
            if not current:
                return False
            if current == me:
                return False
            if current == fg and _user32.IsWindowVisible(hwnd):
                return True
            hwnd = _user32.GetWindow(hwnd, 2)
        return False

    def _raise(self, force: bool) -> None:
        if not force or not self._hwnd:
            return
        _user32.SetWindowPos(self._hwnd, ctypes.c_void_p(-1), 0, 0, 0, 0, 0x0013)

    def hide(self) -> None:
        self._visible = False
        self._key = None
        self._game_rect = None
        self._last_fg = 0
        self._fg_large = False
        self._boost_until = 0.0
        if self._dx:
            self._dx.close()
            self._dx = None
        hwnd = self._hwnd
        self._hwnd = None
        if hwnd:
            _user32.DestroyWindow(hwnd)

    def shutdown(self) -> None:
        self.hide()

    def _ensure_class(self) -> None:
        global _class_ready
        if _class_ready:
            return
        wc = _WNDCLASSW()
        wc.lpfnWndProc = _PROC
        wc.hInstance = _kernel32.GetModuleHandleW(None)
        wc.lpszClassName = _CLASS
        atom = _user32.RegisterClassW(ctypes.byref(wc))
        if not atom and ctypes.get_last_error() not in (1410,):
            raise OSError("RegisterClassW")
        _class_ready = True

    def _present(self, x: int, y: int, w: int, h: int, raw: bytes, opacity: int) -> None:
        alpha = int(round(max(1, min(100, opacity)) * 255 / 100))
        self._ensure_class()
        if self._dx:
            self._dx.close()
            self._dx = None
        if self._hwnd:
            _user32.DestroyWindow(self._hwnd)
            self._hwnd = None
        self._hwnd = self._open_window(x, y, w, h, layered=True)
        self._blit_gdi(x, y, w, h, raw, alpha)
        self._x, self._y, self._w, self._h = x, y, w, h
        _user32.ShowWindow(self._hwnd, 4)
        _user32.SetWindowPos(self._hwnd, ctypes.c_void_p(-1), x, y, w, h, 0x0010)

    def _open_window(self, x: int, y: int, w: int, h: int, layered: bool):
        ex = 0x00000020 | 0x00000008 | 0x00000080 | 0x08000000
        ex |= 0x00080000 if layered else 0x00200000
        hwnd = _user32.CreateWindowExW(
            ex,
            _CLASS,
            "EclatPlus",
            0x80000000,
            x,
            y,
            w,
            h,
            None,
            None,
            _kernel32.GetModuleHandleW(None),
            None,
        )
        if not hwnd:
            raise OSError(f"CreateWindowExW {ctypes.get_last_error()}")
        return hwnd

    def _open_dx(self, x: int, y: int, w: int, h: int, raw: bytes, alpha: int) -> bool:
        hwnd = self._open_window(x, y, w, h, layered=False)
        layer = DxLayer()
        if not layer.open(int(hwnd), w, h, raw, alpha):
            _user32.DestroyWindow(hwnd)
            return False
        self._hwnd = hwnd
        self._dx = layer
        return True

    def _blit_gdi(self, x: int, y: int, w: int, h: int, raw: bytes, alpha: int) -> None:
        bmi = _BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = -h
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0
        bmi.bmiHeader.biSizeImage = w * h * 4
        bits = ctypes.c_void_p()
        screen = _user32.GetDC(None)
        mem = _gdi32.CreateCompatibleDC(screen)
        hbmp = None
        old = None
        try:
            hbmp = _gdi32.CreateDIBSection(mem, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
            if not hbmp or not bits:
                raise OSError("CreateDIBSection")
            old = _gdi32.SelectObject(mem, hbmp)
            ctypes.memmove(bits, raw, len(raw))
            pos = _POINT(x, y)
            size = _SIZE(w, h)
            src = _POINT(0, 0)
            blend = _BLEND(0, 0, alpha, 1)
            ok = _user32.UpdateLayeredWindow(
                self._hwnd,
                screen,
                ctypes.byref(pos),
                ctypes.byref(size),
                mem,
                ctypes.byref(src),
                0,
                ctypes.byref(blend),
                2,
            )
            if not ok:
                raise OSError(f"UpdateLayeredWindow {ctypes.get_last_error()}")
        finally:
            if old:
                _gdi32.SelectObject(mem, old)
            if hbmp:
                _gdi32.DeleteObject(hbmp)
            if mem:
                _gdi32.DeleteDC(mem)
            if screen:
                _user32.ReleaseDC(None, screen)
