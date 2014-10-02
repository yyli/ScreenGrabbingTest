#!/usr/bin/python
from __future__ import print_function
from __future__ import division
import logging
import numpy as np
import wx
import sys
import time
import timeit
import ctypes
from multiprocessing import Process, Manager, Lock, Queue
from threading import Timer
from collections import deque

from logger import initLogger
from ScreenCapture import ScreenCapture

LOGGER = initLogger('GUI')

class ImagePanel(wx.Panel):
    def __init__(self, parent, dproxy, dproxy_lock, fps=60):
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

        LOGGER.info("ImagePanel Started")
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

    def Destroy(self):
        with self.dproxy_lock:
            self.t.cancel()
        LOGGER.info("Panel Destroyed")
        super(ImagePanel, self).Destroy()

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

class WindowSelectorDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "Window Selector", size=(350,300))

        vbox = wx.BoxSizer(wx.VERTICAL)
        stline = wx.StaticText(self, 11, 'placeholder')
        vbox.Add(stline, 1, wx.ALIGN_CENTER|wx.TOP, 45)

        button_box = wx.BoxSizer(wx.HORIZONTAL)
        okay_button = wx.Button(self, label='Okay')
        quit_button = wx.Button(self, label='Quit')
        button_box.Add(okay_button)
        button_box.Add(quit_button)
        
        vbox.Add(button_box, 0, wx.CENTER)

        self.SetSizer(vbox)

        self.Bind(wx.EVT_BUTTON, self.OnClose, okay_button)

    def OnClose(self, event):
        print("close")
        self.Close()

class Frame(wx.Frame):
    def __init__(self, title):
        wx.Frame.__init__(self, None, title=title)

        self.dproxy = Manager().dict()
        self.dproxy['frame'] = None
        self.dproxy['stop'] = False
        self.dproxy_lock = Lock()
        self.p = Process(target=update_image_loop, args=(self.dproxy, self.dproxy_lock))
        self.p.start()

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        windows_dialog = WindowSelectorDialog(self);

        print(windows_dialog.ShowModal())

        windows_dialog.Destroy()

        self.image_panel = ImagePanel(self, self.dproxy, self.dproxy_lock)

    def OnClose(self, event):
        with self.dproxy_lock:
            self.dproxy['stop'] = True
            self.p.terminate()
            LOGGER.info("p termianted")
        
        self.image_panel.Destroy()
        self.Destroy()

def update_image_loop(dproxy, dproxy_lock):
    try:
        sc = ScreenCapture("Task Manager")
        while True:
            frame = sc.get_frame()
            with dproxy_lock:
                if dproxy['stop']:
                    LOGGER.debug("stop signal recieved")
                    break;
                dproxy['frame'] = frame
    except RuntimeError:
        pass

if __name__ == "__main__":
    # initate getting image loop
    app = wx.App()
    frame = Frame("Screen Replicator")
    # cap = ShowImages(frame, dproxy, dproxy_lock, p)
    frame.Show()
    app.MainLoop()
    LOGGER.info("MainLoop ended")
