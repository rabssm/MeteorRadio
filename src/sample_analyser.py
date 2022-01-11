import argparse
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.colors as colors
from matplotlib.mlab import psd, specgram
import scipy.interpolate as si
import scipy.signal as signal

OVERLAP = 0.75             # Overlap for sample file analysis
NUM_FFT = 2**15

SAMPLE_RATE = 300000
DECIMATION = 8

MIN_FREQUENCY = 1500
MAX_FREQUENCY = 2500

def print_stats(samples) :
    vabs = samples
    vmax = np.max(vabs)
    vmean = np.mean(vabs)
    pmax = np.square(vmax) / 50
    pmean = np.square(vmean) / 50
    pmaxdb = 10 * np.log(pmax)
    pmeandb = 10 * np.log(pmean)

    print("vmax:", vmax, "vmean:", vmean)
    print("pmax:", pmax, "pmean:", pmean)
    print("pmaxdb:", pmaxdb, "pmeandb:", pmeandb)


def convert_to_fm_audio(samples) :
    Fs = int(SAMPLE_RATE/DECIMATION)         # Sample rate
    F_offset = 2000               # Offset

    # Convert samples to a numpy array
    x1 = np.array(samples).astype("complex64")

    """
    plt.specgram(x1, NFFT=2048, Fs=Fs)
    plt.title("x1")
    plt.ylim(-Fs/2, Fs/2)
    plt.savefig("x1_spec.pdf", bbox_inches='tight', pad_inches=0.5)
    plt.close()
    """

    # To mix the data down, generate a digital complex exponential
    # (with the same length as x1) with phase -F_offset/Fs
    fc1 = np.exp(-1.0j*2.0*np.pi* F_offset/Fs*np.arange(len(x1)))
    # Now, just multiply x1 and the digital complex expontential
    x2 = x1 * fc1

    """
    plt.specgram(x2, NFFT=2048, Fs=Fs)
    plt.title("x2")
    plt.xlabel("Time (s)")
    plt.ylabel("Frequency (Hz)")
    plt.ylim(-Fs/2, Fs/2)
    plt.xlim(0,len(x2)/Fs)
    plt.ticklabel_format(style='plain', axis='y' )
    plt.savefig("x2_spec.pdf", bbox_inches='tight', pad_inches=0.5)
    plt.close()

    # An FM broadcast signal has a bandwidth of 200 kHz
    f_bw = 140000
    n_taps = 64
    # Use Remez algorithm to design filter coefficients
    lpf = signal.remez(n_taps, [0, f_bw, f_bw+(Fs/2-f_bw)/4, Fs/2], [1,0], Hz=Fs)
    x3 = signal.lfilter(lpf, 1.0, x2)

    dec_rate = int(Fs / f_bw)
    x4 = x3[0::dec_rate]
    # Calculate the new sampling rate
    """
    Fs_y = Fs

    """
    plt.specgram(x4, NFFT=2048, Fs=Fs_y)
    plt.title("x4")
    plt.ylim(-Fs_y/2, Fs_y/2)
    plt.xlim(0,len(x4)/Fs_y)
    plt.ticklabel_format(style='plain', axis='y' )
    plt.savefig("x4_spec.pdf", bbox_inches='tight', pad_inches=0.5)
    plt.close()

    # Plot the constellation of x4.  What does it look like?
    plt.scatter(np.real(x4[0:50000]), np.imag(x4[0:50000]), color="red", alpha=0.05)
    plt.title("x4")
    plt.xlabel("Real")
    plt.xlim(-1.1,1.1)
    plt.ylabel("Imag")
    plt.ylim(-1.1,1.1)
    plt.savefig("x4_const.pdf", bbox_inches='tight', pad_inches=0.5)
    plt.close()
    """

    ### Polar discriminator
    x4 = x2
    y5 = x4[1:] * np.conj(x4[:-1])
    x5 = np.angle(y5)

    """
    # Note: x5 is now an array of real, not complex, values
    # As a result, the PSDs will now be plotted single-sided by default (since
    # a real signal has a symmetric spectrum)
    # Plot the PSD of x5
    plt.psd(x5, NFFT=2048, Fs=Fs_y, color="blue")
    plt.title("x5")
    plt.axvspan(0,             15000,         color="red", alpha=0.2)
    plt.axvspan(19000-500,     19000+500,     color="green", alpha=0.4)
    plt.axvspan(19000*2-15000, 19000*2+15000, color="orange", alpha=0.2)
    plt.axvspan(19000*3-1500,  19000*3+1500,  color="blue", alpha=0.2)
    plt.ticklabel_format(style='plain', axis='y' )
    plt.savefig("x5_psd.pdf", bbox_inches='tight', pad_inches=0.5)
    plt.close()
    """

    # The de-emphasis filter
    # Given a signal 'x5' (in a numpy array) with sampling rate Fs_y
    d = Fs_y * 75e-6   # Calculate the # of samples to hit the -3dB point
    x = np.exp(-1/d)   # Calculate the decay between each sample
    b = [1-x]          # Create the filter coefficients
    a = [1,-x]
    x6 = signal.lfilter(b,a,x5)

    # Find a decimation rate to achieve audio sampling rate between 44-48 kHz
    audio_freq = 44100.0
    dec_audio = int(Fs_y/audio_freq)
    #Fs_audio = Fs_y / dec_audio

    #print("Decimation:", dec_audio, Fs_audio)

    # x7 = signal.decimate(x6, dec_audio)
    x7 = x6

    # Scale audio to adjust volume
    x7 *= 10000 / np.max(np.abs(x7))
    # Save to file as 16-bit signed single-channel audio samples
    x7.astype("int16").tofile("wbfm-mono.raw")



# Main program
if __name__ == "__main__":


    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=str, help="File or directory to analyse. Raw sample file SMP*.npz ")
    args = vars(ap.parse_args())

    inputFilename = args['file']

    print(inputFilename)
    npz_data = np.load(inputFilename)

    samples = npz_data['samples']
    sample_rate=int(SAMPLE_RATE/DECIMATION)

    print(type(samples[0]))

    convert_to_fm_audio(samples)

    # samples = np.abs(samples)

    # Save as audio
    # x1 = np.array(samples).astype("complex64")
    # Decimate to reduce sample rate from 300 kHz to 50 kHz
    # x2 = signal.decimate(x1, 6)

    # Scale audio to adjust volume
    # x2 *= 10000 / np.max(np.abs(x2))
    # Save to file as 16-bit signed single-channel audio samples
    # audio_filename = inputFilename + '.raw'
    # print("Saving", audio_filename)
    # x2.astype("int16").tofile(audio_filename)
    # Audo saved


    print_stats(samples)
    vmean = np.mean(samples)
    vmedian = np.median(samples)

    # Show the specgram
    if "SMP" in inputFilename :
        NUM_FFT = 2**12
        Pxx, f, bins = specgram(samples, NFFT=NUM_FFT, Fs=sample_rate, noverlap=OVERLAP*NUM_FFT, sides='onesided')
        # f, bins, Pxx = signal.spectrogram(samples, nfft=NUM_FFT, fs=sample_rate, return_onesided=True)
        # print(f,bins)

        freq_slice = np.where((f > MIN_FREQUENCY) & (f <= MAX_FREQUENCY))
        f = f[freq_slice]
        Pxx = Pxx[freq_slice,:][0]

        Pxx = 10.0*np.log10(Pxx)

        fig, ax = plt.subplots(figsize=(6,9))
        ax.pcolormesh(f, bins, Pxx.T, cmap='gist_heat', shading='auto')
        ax.set_title('Meteor Radar Detection', fontsize=10)
        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel('Time (s)' )
        ax.ticklabel_format(axis='x', useOffset=False)
        ax.set_xlim([np.min(f), np.max(f)])

        plt.show()


    # Show the PSD
    Pxx, f = plt.psd(samples, NFFT=sample_rate, Fs=sample_rate)
    plt.xlabel('Frequency (MHz)')
    plt.ylabel('Relative power (dB)')

    plt.pause(0.01)


    #"""
    # Create a bandpass filter around 2 kHz
    sos = signal.butter(10, [1500, 2500], 'bandpass', fs=sample_rate, output='sos')
    samples = signal.sosfilt(sos, samples)
    #"""

    print("\nAfter Butterworth filter")
    print_stats(samples)

    vmax = np.max(samples)
    print("Max SNR", vmax/vmean)

    #samples_for_detection = samples[samples > cutoff]
    #print("\nAfter cutoff filter")
    #print_stats(samples_for_detection)

    # Show the PSD
    Pxx, f = plt.psd(samples, NFFT=sample_rate, Fs=sample_rate)
    plt.xlabel('Frequency (MHz)')
    plt.ylabel('Relative power (dB)')

    plt.pause(0.01)


    # Show the spectrogram
    Pxx, f, bins = specgram(samples, NFFT=NUM_FFT, Fs=sample_rate, noverlap=OVERLAP*NUM_FFT, sides='onesided')

    freq_slice = np.where((f > MIN_FREQUENCY) & (f <= MAX_FREQUENCY))
    #f = f[freq_slice]

    #Pxx = Pxx[freq_slice,:][0]
    Pxx = 10.0*np.log10(Pxx)

    fig, ax = plt.subplots(figsize=(6,9))
    ax.pcolormesh(f, bins, Pxx.T, cmap='gist_heat', shading='auto')
    ax.set_title('Raw Samples', fontsize=10)
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
