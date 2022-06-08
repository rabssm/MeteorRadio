#    This file is part of pyrlsdr.
#    Copyright (C) 2013 by Roger <https://github.com/roger-/pyrtlsdr>
#
#    pyrlsdr is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    pyrlsdr is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with pyrlsdr.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import division
import asyncio
from multiprocessing import Queue, Process
import matplotlib.animation as animation
from matplotlib.mlab import psd, specgram
import pylab as pyl
import numpy as np
import sys
from rtlsdr import RtlSdr
import threading
import time

# A simple waterfall, spectrum plotter for meteor radio

NFFT = 1024*4
NUM_SAMPLES_PER_SCAN = 131072 # NFFT*16
NUM_BUFFERED_SWEEPS = 100

SAMPLE_RATE = 300000       #    960000 (262144-causes noise near 143.05) 262144, 240000


# change this to control the number of scans that are combined in a single sweep
# (e.g. 2, 3, 4, etc.) Note that it can slow things down
NUM_SCANS_PER_SWEEP = 1

class Waterfall(Process):
    image_buffer = -100*np.ones((NUM_BUFFERED_SWEEPS,\
                                 NUM_SCANS_PER_SWEEP*NFFT))

    def __init__(self, fc, rs, waterfall_queue, fig=None):

        super(Waterfall, self).__init__()

        self.fc = fc
        self.rs = rs
        self.sample_queue = waterfall_queue
        self.fig = fig if fig else pyl.figure()

        self.init_plot()

    def run(self):
        self.start_p()


    def init_plot(self):
        self.ax = self.fig.add_subplot(1,1,1)
        self.image = self.ax.imshow(self.image_buffer, aspect='auto',\
                                    interpolation='nearest', vmin=-50, vmax=10, cmap='gist_heat')
        self.ax.set_xlabel('Current frequency (MHz)')
        self.ax.get_yaxis().set_visible(False)


    def update_plot_labels(self):
        fc = self.fc
        rs = self.rs
        freq_range = (fc - rs/2)/1e6, (fc + rs*(NUM_SCANS_PER_SWEEP - 0.5))/1e6

        self.image.set_extent(freq_range + (0, 1))
        self.fig.canvas.draw_idle()


    def update(self, *args):

        # prepare space in buffer
        # TODO: use indexing to avoid recreating buffer each time
        self.image_buffer = np.roll(self.image_buffer, 1, axis=0)

        # self.sdr.fc += self.sdr.rs*scan_num
        start_ind = 0
        
        # Get the raw sample data from the queue
        samples = self.sample_queue.get()
        psd_scan, f = psd(samples, NFFT=NFFT)
        self.image_buffer[0, start_ind: start_ind+NFFT] = 10*np.log10(psd_scan)

        # psd_scan1, f, _= specgram(samples, NFFT=NFFT)
        # psd_scan1, f = self.sample_queue.get()

        # freq_range = np.min(f)/1e6, np.max(f)/1e6
        # self.image.set_extent(freq_range + (0, 1))

        # Get specgram waterfall FFT data from queue
        # psd_scan1, f = self.sample_queue.get()
        # psd_scan2 = np.mean(psd_scan1, axis=1)
        # self.image_buffer[0, start_ind: start_ind+NFFT] = 10*np.log10(psd_scan2)

        # plot entire sweep
        self.image.set_array(self.image_buffer)

        return self.image,

    def start_p(self):
        self.update_plot_labels()
        blit = True
        ani = animation.FuncAnimation(self.fig, self.update, interval=50,
                blit=blit)

        pyl.show()

        return

def acquire() :
    while True :
        samples = sdr.read_samples(NUM_SAMPLES_PER_SCAN)
        print(len(samples))
        try: sample_queue.put_nowait(samples)
        except: pass


if __name__ == '__main__':
    sdr = RtlSdr()

    # some defaults
    sdr.rs = 2.4e6
    sdr.sample_rate = SAMPLE_RATE

    sdr.fc = 100.3e6
    sdr.fc = 143048000

    centre_freq = sdr.fc
    sdr_gain = 'auto'

    sample_queue = Queue(maxsize=10)

    th = threading.Thread(target=acquire)
    th.start()

    p = Waterfall(143048000, SAMPLE_RATE, sample_queue)
    p.start()

    # wf = Waterfall(sdr)
    # wf.start()

    time.sleep(10000)


    # cleanup
    sdr.close()
