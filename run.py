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

from logger import initLogger
from ScreenCapture import ScreenCapture

LOGGER = initLogger('GUI')

class ShowImages(wx.Panel):
    def __init__(self, parent, dproxy, dproxy_lock, p, fps=60):
        wx.Panel.__init__(self, parent)
        parent.Bind(wx.EVT_CLOSE, self.OnClose)
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

        LOGGER.info("Started")
        img = None
        while img is None:
            with dproxy_lock:
                img = dproxy['frame']

        self.height, self.width = img.shape[:2]
        parent.SetSize((self.width, self.height))

        self.bmp = wx.BitmapFromBuffer(self.width, self.height, img)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
       
        self.t = Timer(1/fps, self.update_loop)
        self.t.start()

    def OnClose(self, event):
        self.t.cancel()
        with self.dproxy_lock:
            self.dproxy['stop'] = True
            self.p.terminate()
            LOGGER.info("p termianted")
            self.parent.Destroy()

    def OnPaint(self, evt):
        dc = wx.BufferedPaintDC(self)
        dc.DrawBitmap(self.bmp, 0, 0)

    def update_loop(self):
        loop_time = timeit.default_timer()
        LOGGER.debug("loop_time started")
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
        self.t = Timer(1/self.fps - time_taken - 1/1750, self.update_loop)
        self.t.start()

def update_image_loop(dproxy, dproxy_lock):
    sc = ScreenCapture("Untitled - Notepad")

    while True:
        frame = sc.get_frame()
        with dproxy_lock:
            if dproxy['stop']:
                LOGGER.debug("stop signal recieved")
                break;
            dproxy['frame'] = frame

if __name__ == "__main__":
    # initate getting image loop
    dproxy = Manager().dict()
    dproxy['frame'] = None
    dproxy['stop'] = False
    dproxy_lock = Lock()
    p = Process(target=update_image_loop, args=(dproxy, dproxy_lock))
    p.start()

    app = wx.App()
    frame = wx.Frame(None, -1, "Screen Replicator")
    cap = ShowImages(frame, dproxy, dproxy_lock, p)
    frame.Show()
    app.MainLoop()
    LOGGER.info("MainLoop ended")
