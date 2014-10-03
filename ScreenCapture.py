#!/usr/bin/python
import ctypes
from ctypes.wintypes import BOOL, LONG, DWORD, WORD
import logging
import numpy as np
import cv2

from logger import initLogger

LOGGER = initLogger('ScreenCapture')

# Function constants
EnumWindows = ctypes.windll.user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(BOOL, ctypes.POINTER(LONG), ctypes.POINTER(LONG))
GetWindowText = ctypes.windll.user32.GetWindowTextW
GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
IsWindowVisible = ctypes.windll.user32.IsWindowVisible
GetDC = ctypes.windll.user32.GetDC
CreateCompatibleDC = ctypes.windll.gdi32.CreateCompatibleDC
SetStretchBltMode = ctypes.windll.gdi32.SetStretchBltMode
GetClientRect = ctypes.windll.user32.GetClientRect
CreateCompatibleBitmap = ctypes.windll.gdi32.CreateCompatibleBitmap
SelectObject = ctypes.windll.gdi32.SelectObject
StretchBlt = ctypes.windll.gdi32.StretchBlt
GetDIBits = ctypes.windll.gdi32.GetDIBits
DeleteDC = ctypes.windll.gdi32.DeleteDC
ReleaseDC = ctypes.windll.user32.ReleaseDC
DeleteObject = ctypes.windll.gdi32.DeleteObject

# Structures and Constants
COLORONCOLOR = 3
SRCCOPY = 0x00CC0020 # dest = source
BI_RGB = 0
class RECT(ctypes.Structure):
    _fields_ = [("left", LONG),
                ("top", LONG),
                ("right", LONG),
                ("bottom", LONG)]

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [('biSize', DWORD),
                ('biWidth', LONG),
                ('biHeight', LONG),
                ('biPlanes', WORD),
                ('biBitCount', WORD),
                ('biCompression', DWORD),
                ('biSizeImage', DWORD),
                ('biXPelsPerMeter', LONG),
                ('biYPelsPerMeter', LONG),
                ('biClrUsed', DWORD),
                ('biClrImportant', DWORD)]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [('bmiHeader', BITMAPINFOHEADER),
                ('bmiColors', DWORD * 3)]

def get_all_window_names():
    windows = []
    def foreach_window(hwnd, lParam):
        if IsWindowVisible(hwnd):
            length = GetWindowTextLength(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            GetWindowText(hwnd, buff, length + 1)
            windows.append(buff.value)
        return True

    EnumWindows(EnumWindowsProc(foreach_window), 0)
    return windows

class ScreenCapture(object):
    def __init__(self, name):
        self.hwnd = self.__get_window_handle(name)
        if self.hwnd is None:
            raise RuntimeError("Can't get window")

    def __get_window_handle(self, name):
        wanted_hwnd = []
        def foreach_window(hwnd, lParam):
            if IsWindowVisible(hwnd):
                length = GetWindowTextLength(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buff, length + 1)
                if buff.value == name:
                    wanted_hwnd.append(hwnd)
                    LOGGER.debug("name: {0}, {1}, {2}".format(name, hwnd, wanted_hwnd))
                    return False
            return True

        EnumWindows(EnumWindowsProc(foreach_window), 0)

        # if we found one and only one handle return it
        # else return None
        if len(wanted_hwnd) == 1:
            return wanted_hwnd[0]
        else:
            return None

    def get_frame(self, x=0, y=0, w=0, h=0):
        DCsrc = GetDC(self.hwnd)
        DC = CreateCompatibleDC(DCsrc)
        SetStretchBltMode(DC, COLORONCOLOR)

        size = RECT()
        GetClientRect(self.hwnd, ctypes.byref(size))
        LOGGER.debug("sizes (l, r, t, b): {0}, {1}, {2}, {3}".format(size.left, size.right, size.top, size.bottom))

        width = size.right - size.left
        height = size.bottom - size.top

        if x == y == w == h == 0:
            x = 0
            y = 0
            w = width
            h = height

        remainder = w % 8
        if remainder:
            w -= remainder
            if w < 0:
                w = 0

        HBmp = CreateCompatibleBitmap(DCsrc, w, h)
        SelectObject(DC, HBmp)
        retval = StretchBlt(DC, 0, 0, w, h, DCsrc, x, y, w, h, SRCCOPY)

        LOGGER.debug("StretchBlt: {0}".format(retval))

        bih = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), w, -h, 1, 24, BI_RGB, 0, 0, 0, 0, 0)
        bi = BITMAPINFO(bih)

        buf = np.zeros([h, w, 3], dtype=np.uint8)
        bits = GetDIBits(DC, HBmp, 0, h, buf.ctypes.data_as(ctypes.POINTER(ctypes.c_char)), ctypes.pointer(bi), 0)

        LOGGER.debug("Bits: {0} Height: {1}".format(bits, h))

        DeleteDC(DC)
        ReleaseDC(self.hwnd, DCsrc)
        DeleteObject(HBmp)

        if bits != h:
            return None

        buf = cv2.cvtColor(buf, cv2.COLOR_BGR2RGB)
        return buf
