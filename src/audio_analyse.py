import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.colors as colors
from matplotlib.mlab import psd, specgram
import scipy.interpolate as si
import scipy.signal as signal

OVERLAP = 0.75             # Overlap for audio file analysis
NUM_FFT = 2**13

MIN_FREQUENCY = 1500
MAX_FREQUENCY = 2500

# Main program
if __name__ == "__main__":


    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=str, help="File or directory to analyse. AUDIO file AUD*.raw ")
    args = vars(ap.parse_args())

    inputFilename = args['file']

    print(inputFilename)
    f = open(inputFilename, "r")
    samples = np.fromfile(f, dtype = 'int16')
    if len(samples) > (10 * 50000) : sample_rate=50000
    else : sample_rate=37500

    """
    # Create a bandpass filter around 2 kHz
    sos = signal.butter(10, [1500, 2500], 'bandpass', fs=sample_rate, output='sos')
    x2 = signal.sosfilt(sos, samples)
    samples = x2

    # x2.astype("int16").tofile('test.raw')
    """

    Pxx, f, bins = specgram(samples, NFFT=NUM_FFT, Fs=sample_rate, noverlap=OVERLAP*NUM_FFT)

    freq_slice = np.where((f > MIN_FREQUENCY) & (f <= MAX_FREQUENCY))
    f = f[freq_slice]

    Pxx = Pxx[freq_slice,:][0]
    Pxx = 10.0*np.log10(Pxx)

    fig, ax = plt.subplots(figsize=(6,9))
    ax.pcolormesh(f, bins, Pxx.T, cmap='gist_heat', shading='auto')
    ax.set_title('Audio', fontsize=10)
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('Time (s)' )
    ax.ticklabel_format(axis='x', useOffset=False)
    ax.set_xlim([np.min(f), np.max(f)])

    #"""
    func = si.interp2d(f, bins, Pxx.T)
    def fmt(x, y):
        z = np.take(func(x, y), 0)
        return 'x={x:.5f}  y={y:.5f}  z={z:.5f}'.format(x=x, y=y, z=z)
    plt.gca().format_coord = fmt
    #"""

    plt.show()
