#!/usr/bin/python
from __future__ import print_function
import logging
import numpy as np
import wx
import time
from ScreenCapture import ScreenCapture

LOGGER = logging.getLogger()

def init_logger():
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)

    fh = logging.FileHandler('spam.log')
    fh.setFormatter(formatter)

    # LOGGER.addHandler(fh)
    LOGGER.addHandler(ch)
    LOGGER.setLevel(logging.INFO)

    LOGGER.info("Log started.")

class ShowImages(wx.Panel):
    def __init__(self, parent, sc, fps=60):
        wx.Panel.__init__(self, parent)

        self.sc = sc
        img = sc.get_frame()

        height, width = img.shape[:2]
        parent.SetSize((width, height))

        self.bmp = wx.BitmapFromBuffer(width, height, img)

        self.timer = wx.Timer(self)
        self.timer.Start(1000./fps)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_TIMER, self.NextFrame)


    def OnPaint(self, evt):
        dc = wx.BufferedPaintDC(self)
        dc.DrawBitmap(self.bmp, 0, 0)

    def NextFrame(self, event):
        start = time.time()
        img = sc.get_frame()
        if img is not None:
            self.bmp.CopyFromBuffer(img)
            self.Refresh()
        end = time.time()

if __name__ == "__main__":
    init_logger()

    # while True:
    #     img = get_frame(hwnd)
    #     cv2.imshow('image', img)
    #     print("hi")
    #     k = cv2.waitKey(5)
    #     if k == 27:
    #         cv2.destroyAllWindows()
    #         break

    app = wx.App()
    frame = wx.Frame(None, -1, "Screen Replicator")
    sc = ScreenCapture("TERA")
    cap = ShowImages(frame, sc)
    frame.Show()
    app.MainLoop()
