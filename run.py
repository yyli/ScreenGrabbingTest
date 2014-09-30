#!/usr/bin/python
from __future__ import print_function
from __future__ import division
import logging
import numpy as np
import wx
import time
import timeit
import ctypes
from multiprocessing import Process, Manager, Lock
from threading import Timer
from collections import deque


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
    def __init__(self, parent, dproxy, dproxy_lock, p, fps=60):
        wx.Panel.__init__(self, parent)
        self.SetDoubleBuffered(True)

        self.fps_timer = 0
        self.fps_counter = 0
        self.fps_ring_buffer = deque(maxlen=30)
        self.fps = fps
        self.dproxy = dproxy
        self.dproxy_lock = dproxy_lock

        self.fps_label = wx.StaticText(self, label="FPS: 0", pos=(1, 0))

        self.parent = parent
        self.p = p

        print("started")
        img = None
        while img is None:
            with dproxy_lock:
                img = dproxy['frame']

        self.height, self.width = img.shape[:2]
        parent.SetSize((self.width, self.height))

        self.bmp = wx.BitmapFromBuffer(self.width, self.height, img)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_CLOSE, self._when_closed)
       
        t = Timer(1/fps, self.update_loop)
        t.start()

    def _when_closed(self, event):
        print("p termianted")
        self.p.terminate()
        self.Close()

    def OnPaint(self, evt):
        dc = wx.BufferedPaintDC(self)
        dc.DrawBitmap(self.bmp, 0, 0)

    def update_loop(self):
        loop_time = timeit.default_timer()
        with self.dproxy_lock:
            img = self.dproxy['frame']
            if img is not None:
                h, w = img.shape[:2]
                if h != self.height or w != self.width:
                    self.height = h
                    self.width = w
                    self.parent.SetSize((self.width, self.height))
                    self.bmp = wx.BitmapFromBuffer(self.width, self.height, img)
                else:
                    self.bmp.CopyFromBuffer(img)

            end_timer = timeit.default_timer()

            cur_fps = 1/(end_timer - self.fps_timer)
            self.fps_ring_buffer.append(cur_fps)

            moving_avg_fps = sum(self.fps_ring_buffer)/len(self.fps_ring_buffer)
            LOGGER.debug("cur_fps: {0}, moving_avg_fps: {1}".format(cur_fps, moving_avg_fps))

            if self.fps_counter % 10 == 0:
                self.fps_label.SetLabel("FPS: {0}".format(moving_avg_fps))

            self.fps_timer = end_timer
            self.fps_counter += 1
            self.Refresh()

        time_taken = timeit.default_timer() - loop_time
        t = Timer(1/self.fps - time_taken - 1/1750, self.update_loop)
        t.start()

def update_image_loop(dproxy, dproxy_lock):
    sc = ScreenCapture("Untitled - Notepad")

    while True:
        frame = sc.get_frame()
        with dproxy_lock:
            dproxy['frame'] = frame

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

    # initate getting image loop
    dproxy = Manager().dict()
    dproxy['frame'] = None
    dproxy_lock = Lock()
    p = Process(target=update_image_loop, args=(dproxy, dproxy_lock))
    p.start()

    app = wx.App()
    frame = wx.Frame(None, -1, "Screen Replicator")
    cap = ShowImages(frame, dproxy, dproxy_lock, p)
    frame.Show()
    app.MainLoop()
    p.terminate()
    print("p termianted")
