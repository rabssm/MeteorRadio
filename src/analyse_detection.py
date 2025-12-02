import numpy as np
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patheffects as path_effects
from matplotlib.mlab import specgram
import scipy.interpolate as si
from scipy.signal import ShortTimeFFT
from scipy.signal.windows import gaussian, hamming
import os
import shutil
from stat import S_IREAD, S_IRGRP, S_IROTH
import signal
import argparse
import re
import glob
from queue import LifoQueue


FULL_FREQUENCY_BAND = 18000   # Band for psd plot is +/- 18000 Hz
SPECGRAM_BAND = 500     # Band for displaying specgram plots is +/-500
DATA_DIR =  os.path.expanduser('~/radar_data')
ARCHIVE_DIR =  os.path.expanduser('~/radar_data/Archive')
CAPTURE_DIR =  os.path.expanduser('~/radar_data/Captures')
JUNK_DIR =  os.path.expanduser('~/radar_data/Junk')

OVERLAP = 0.75           # Overlap (0.75 is 75%)

NUM_FFT = 2**12
DEFAULT_SAMPLE_RATE = 37500
HOP=int(NUM_FFT*(1-OVERLAP))

HELP_TEXT = 'Command keys:\n' + \
    'Right arrow    next file\n' + \
    'Left arrow     previous file\n' + \
    'Delete         Move file to Junk directory and skip to next file\n' +  \
    'Backspace      Move file to Junk directory and skip to previous file\n' +  \
    'u              Restore last deleted files from Junk directory\n' + \
    'a              Move file to Archive directory\n' + \
    'c              Move file to Captures directory\n' + \
    '3              3d plot\n' + \
    't              Plot with real time axis\n' + \
    '0              Play audio and create wav file\n' + \
    'r              Rotate plot\n' + \
    'F              Show full frequency band\n' + \
    'S              Save the current plot to png image file in ~/radar_data/\n' + \
    'q              Close current plot\n' + \
    'Esc            Exit viewer'

def signalHandler (signum, frame) :
   os._exit(0)

# Create all necessary data directories
def make_directories() :
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    os.makedirs(CAPTURE_DIR, exist_ok=True)
    os.makedirs(JUNK_DIR, exist_ok=True)

class MeteorPlotter() :

    def __init__(self):

        self.cmap_color = 'gist_heat'
        self.cmap_color_list = plt.colormaps()
        self.cmap_index = self.cmap_color_list.index(self.cmap_color)
        self.last_deleted_file_queue = LifoQueue()
        self.file_name = ''

    def set_file_name(self, file_name) :
        self.file_name = file_name

    # Show help window
    def help(self) :
        fig = plt.figure(figsize=(10, 5))
        text = fig.text(0.1, 0.1, HELP_TEXT, fontfamily='monospace', size=12)
        text.set_path_effects([path_effects.Normal()])
        plt.show(block=False)

    # Trap a key press to keep or delete files, or 3 to show the 3d plot
    def press(self, event):

        global file_index, file_index_movement
        print(event.key)

        # Move data and audio file to Archive folder
        if event.key == 'a':
            os.chmod(self.file_name, S_IREAD|S_IRGRP|S_IROTH)
            try:
                shutil.move(self.file_name, ARCHIVE_DIR + '/' + os.path.basename(self.file_name))
                audio_file = self.file_name.replace("SPG", "AUD")
                audio_file = audio_file.replace("npz", "raw")
                shutil.move(audio_file, ARCHIVE_DIR + '/' + os.path.basename(audio_file))
            except: pass
            plt.close()
        elif event.key == 'c':
            try:
                shutil.move(self.file_name, CAPTURE_DIR + '/' + os.path.basename(self.file_name))
                audio_file = self.file_name.replace("SPG", "AUD")
                audio_file = audio_file.replace("npz", "raw")
                shutil.move(audio_file, CAPTURE_DIR + '/' + os.path.basename(audio_file))
            except: pass
            plt.close()

        # Undo last delete
        elif event.key == 'u':
            try:
                last_deleted_file = self.last_deleted_file_queue.get_nowait()
                shutil.move(JUNK_DIR + '/' + os.path.basename(last_deleted_file), last_deleted_file)
                audio_file = last_deleted_file.replace("SPG", "AUD")
                audio_file = audio_file.replace("npz", "raw")
                shutil.move(JUNK_DIR + '/' + os.path.basename(audio_file), audio_file)
            except Exception as e:
                print(e)

        # Move data and audio file to Junk folder. Backspace key moves back to previous file
        elif event.key == 'delete' or event.key == 'backspace':
            try:
                if event.key == 'backspace' : file_index_movement = -1
                else: file_index_movement = 1
                shutil.move(self.file_name, JUNK_DIR + '/' + os.path.basename(self.file_name))
                self.last_deleted_file_queue.put_nowait(self.file_name)
                audio_file = self.file_name.replace("SPG", "AUD")
                audio_file = audio_file.replace("npz", "raw")
                shutil.move(audio_file, JUNK_DIR + '/' + os.path.basename(audio_file))
            except Exception as e:
                print(e)
            plt.close()
        elif event.key == 'escape':
            os._exit(0)
        elif event.key == '3':                 # 3 key shows the 3d plot
            self.plot_3dspecgram(Pxx, f, bins, centre_freq)
        elif event.key == 'r':                 # r key rotates the plot
            self.plot_specgram(Pxx, f, bins, centre_freq, obs_time, flipped=True, utc_time=True)
        elif event.key == 't':                 # t key rotates the plot and sets x axis to UTC
            self.plot_specgram(Pxx, f, bins, centre_freq, obs_time, flipped=False, utc_time=True)
        elif event.key == 'F':                 # F key shows full frequency band
            self.plot_specgram(Pxx, f, bins, centre_freq, obs_time, full_frequency_band=True, utc_time=True)
        elif event.key == 'h':                 # h key shows histogram
            self.plot_hist(Pxx)
            # plot_psd(Pxx, f, centre_freq)
        elif event.key == 'right':
            file_index_movement = 1
            plt.close()
        elif event.key == 'left':
            file_index_movement = -1
            plt.close()
        elif event.key == 'pagedown':
            file_index_movement = 10
            plt.close()
        elif event.key == 'pageup':
            file_index_movement = -10
            plt.close()
        elif event.key == 'S' :                 # S key saves current plot to image
            try:
                image_filename = DATA_DIR + "/" + os.path.basename(self.file_name.replace("npz", "png"))
                print("Saving", image_filename)
                plt.savefig(image_filename)
            except:
                pass

        # 0 key plays the audio file and converts to a wav file to allow analysis using audacity
        elif event.key == '0':
            # If the file is a raw sample file
            if 'SMP' in self.file_name and 'npz' in self.file_name :
                # Scale samples to adjust volume
                x7 = samples * (10000 / np.max(np.abs(samples)))

                # Save to file as 16-bit signed single-channel audio samples
                # Note that we can throw away the imaginary part of the IQ sample data for USB
                audio_filename = self.file_name.replace("SMP", "AUD")
                audio_filename = audio_filename.replace("npz", "raw")
                wav_filename = audio_filename.replace("raw", "wav")
                print("Saving", audio_filename)
                x7.astype("int16").tofile(audio_filename)

                try :
                    os.system('play -r 37.5k -b 16 -e signed-integer -c 1 ' + audio_filename + " sinc 1500-3000 &")
                    os.system('sox -r 37.5k -b 16 -e signed-integer -c 1 ' + audio_filename + " " + wav_filename + " &")
                except: pass

            else:
                try:
                    audio_file = self.file_name.replace("SPG", "AUD")
                    audio_file = audio_file.replace("npz", "raw")
                    wav_file = audio_file.replace("raw", "wav")
                    os.system('play -r 37.5k -b 16 -e signed-integer -c 1 ' + audio_file + " sinc 1500-3000 &")
                    os.system('sox -r 37.5k -b 16 -e signed-integer -c 1 ' + audio_file + " " + wav_file + " &")
                except:
                    pass

        elif event.key == '+' :
            self.cmap_index += 1
            self.cmap_color = self.cmap_color_list[self.cmap_index]
            print("Colour changed to", self.cmap_color)
            file_index_movement = 0
            plt.close()

        elif event.key == '-' :
            self.cmap_index -= 1
            self.cmap_color = self.cmap_color_list[self.cmap_index]
            print("Colour changed to", self.cmap_color)
            file_index_movement = 0
            plt.close()

        elif event.key == 'f1' :
            self.help()


    def plot_specgram(self, Pxx, f, bins, centre_freq, obs_time, flipped=False, utc_time=False, full_frequency_band=False, save_images=False, noplot=False) :

        # Limit the data to the required frequency band
        if full_frequency_band :
            freq_slice = np.where((f >= (centre_freq-FULL_FREQUENCY_BAND)/1e6) & (f <= (centre_freq+FULL_FREQUENCY_BAND)/1e6))
        else:
            freq_slice = np.where((f >= (centre_freq-SPECGRAM_BAND)/1e6) & (f <= (centre_freq+SPECGRAM_BAND)/1e6))

        f = f[freq_slice]
        f *= 1e6
        f -= (centre_freq)
        Pxx = Pxx[freq_slice,:][0]

        # Collect the detection stats
        mn, sigmax, init_freq, peak_freq, snr = get_capture_stats(Pxx, f, bins)

        # Convert the plot data to dB
        X = np.float16(Pxx)
        Pxx = 10.0*np.log10(Pxx)

        # bins += (obs_time.second + (obs_time.microsecond/1e6))
        #
        if utc_time:
            bins = [obs_time + datetime.timedelta(seconds=i) for i in bins]
            # bins = mdates.date2num(bins)

        fmt = mdates.DateFormatter('%H:%M:%S')

        # Form the stats string
        stats_string = 'Mean:{0:8.2f}  Max:{1:8.2f}  PeakF:{2:7.1f}  SNR:{3:7.2f} dB'.format(mn, sigmax, peak_freq, snr)


        # Plot the spectrogram data 2d
        if flipped :
            fig, ax = plt.subplots(figsize=(9,7))
            ax.pcolormesh(bins, f, Pxx, cmap=self.cmap_color, shading='auto')
            ax.set_title('Meteor Radio Detection  ' + str(obs_time)[:-3] + '\n' + stats_string, fontsize=10)
            ax.set_ylabel('Frequency (Hz) around ' + str(centre_freq/1e6) + ' MHz')
            ax.set_xlabel('Time (s)' )
            ax.ticklabel_format(axis='y', useOffset=False)
            ax.set_ylim([np.min(f), np.max(f)])
            # fig.colorbar(qmesh,ax=ax)
            # ax.xaxis.set_major_formatter(fmt)
            if utc_time :
                ax.set_xlabel('Time (UTC)' )
                # fig.autofmt_xdate()
                # ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
                plt.xticks(rotation = 30)
                ax.fmt_xdata = mdates.DateFormatter('%H:%M:%S.%f')
        else :
            fig, ax = plt.subplots(figsize=(6,9))
            ax.pcolormesh(f, bins, Pxx.T, cmap=self.cmap_color, shading='auto')
            ax.set_title('Meteor Radio Detection  ' + str(obs_time)[:-3] + '\n' + stats_string, fontsize=10)
            ax.set_xlabel('Frequency (Hz) around ' + str(centre_freq/1e6) + ' MHz')
            ax.set_ylabel('Time (s)' )
            ax.ticklabel_format(axis='x', useOffset=False)
            ax.set_xlim([np.min(f), np.max(f)])
            # fig.colorbar(qmesh,ax=ax)

            # ax.yaxis.set_major_formatter(fmt)
            # fig.autofmt_xdate()
        # fig.tight_layout()


        fig.canvas.mpl_connect('key_press_event', self.press)

        if save_images :
            # Save PSD as an image file
            image_filename = DATA_DIR + '/PSD_' + str(int(centre_freq)) + obs_time.strftime('_%Y%m%d_%H%M%S_%f.png')
            print("Saving", image_filename)
            plt.savefig(image_filename)
            plt.close()

        #### Displays Z value of mouse cursor ####
        if not utc_time :
            func = si.RectBivariateSpline(bins, f, Pxx.T)
            def fmt(x, y):
                z = np.take(func(x, y), 0)
                return 'x={x:.5f}  y={y:.5f}  z={z:.5f}'.format(x=x, y=y, z=z)
            plt.gca().format_coord = fmt
        ##########################################

        if not noplot: plt.show(block=len(plt.get_fignums()) < 2)


    def plot_3dspecgram(self, Pxx, f, bins, centre_freq) :

        # Limit the data to the narrow frequency band
        freq_slice = np.where((f >= (centre_freq-SPECGRAM_BAND)/1e6) & (f <= (centre_freq+SPECGRAM_BAND)/1e6))
        f = f[freq_slice]
        Pxx = Pxx[freq_slice,:][0]

        # Plot the 3d spectrogram
        fig = plt.figure(figsize=(10,7.5))
        ax = plt.axes(projection='3d')
        # ax = fig.gca(projection='3d')
        f -= (centre_freq/1e6)
        f *= 1e6
        ax.plot_surface(bins[None, :], f[:, None], 10.0*np.log10(Pxx), cmap='coolwarm')
        plt.title('Meteor Radio Detection  ' + str(obs_time)[:-3], y=1.08)
        ax.set_xlabel('Time (s)' )
        ax.set_ylabel('Frequency (Hz) around ' + str(centre_freq/1e6) + ' MHz')
        ax.set_zlabel('Relative power (dB)')
        # ax.view_init(30, 135)
        ax.set_xlim(max(bins), min(bins))
        plt.ticklabel_format(axis='y', useOffset=False)
        fig.tight_layout()

        if save_images :
            # Save spectrogram as an image file
            image_filename = DATA_DIR + '/SPG_' + str(int(centre_freq)) + '_' + str(int(sample_rate)) + obs_time.strftime('_%Y%m%d_%H%M%S_%f.png')
            print("Saving", image_filename)
            plt.savefig(image_filename)

        if not noplot: plt.show(block=False)


    def plot_psd(self, Pxx, f, centre_freq) :
        # Restrict the band for plotting to a band around the required centre frequency
        detection_band = np.where((f*1e6 > (centre_freq - FULL_FREQUENCY_BAND)) & (f*1e6 <= (centre_freq + FULL_FREQUENCY_BAND)))
        X = np.float16(Pxx[detection_band])
        sigdb = 10*np.log10(X)
        fplot = f[detection_band]
        plt.plot(fplot, sigdb)

        plt.xlabel('Frequency (MHz)')
        plt.ylabel('Relative power (dB)')
        plt.ticklabel_format(axis='x', useOffset=False)

        if save_images :
            # Save PSD as an image file
            image_filename = DATA_DIR + '/PSD_' + str(int(centre_freq)) + '_' + str(int(sample_rate)) + obs_time.strftime('_%Y%m%d_%H%M%S_%f.png')
            print("Saving", image_filename)
            plt.savefig(image_filename)

        if not noplot: plt.show(block=False)


    def plot_hist(self, Pxx) :

        fig, ax = plt.subplots(figsize=(9,7))
        ax.hist(Pxx.flatten(), bins=500, range=(0,0.2))
        plt.show(block=False)


def get_observation_data(filename) :
    m = re.search('_(\d+)_(\d+)_(\d+)_(\d+)_(\d+)', filename, re.IGNORECASE)
    if m is None :
        m = re.search('_(\d+)_(\d+)_(\d+)_(\d+)', filename, re.IGNORECASE)

    i = 1
    if m is not None :
        centre_freq = float(m.group(i)) ; i+=1
        if len(m.groups()) == 5 : sample_rate = int(m.group(i)) ; i+=1
        else: sample_rate = None
        obs_date = m.group(i) ; i+=1
        obs_time = m.group(i) ; i+=1
        obs_timefrac = m.group(i) ; i+=1
        obs_time = datetime.datetime.strptime(obs_date + '_' + obs_time + '_' + obs_timefrac, '%Y%m%d_%H%M%S_%f')
        print("Observation time", obs_time, "Frequency", centre_freq, "Sample rate", sample_rate)

        return obs_time, centre_freq, sample_rate


def get_capture_stats(Pxx, f, bins) :
    # Calculate the signal level stats over the detection band
    raw_mean = np.mean(Pxx[0:13])
    mn = 10.0*np.log10(raw_mean)
    sigmax = 10.0*np.log10(np.max(Pxx))
    maxpos = np.argmax(np.max(Pxx, axis=1))
    peak_freq = f[maxpos]
    snr = sigmax - mn
    snr_threshold = 22

    # Find time range where snr > threshold
    try:
        Pxx_snr = Pxx/raw_mean
        s = np.nonzero(Pxx_snr > snr_threshold)
        imin, imax = np.min(s[1]), np.max(s[1])
        detection_time = bins[imax] - bins[imin]
        detection_freq = f[s[0][-1]]
    except Exception as e:
        print(e)
        detection_time = 0.0
        detection_freq = peak_freq

    stats_string = 'Mean:{0:10.4f}  Max:{1:10.4f}  Duration:{2:7.2f}  Frequency:{3:12.6f}  MaxSNR:{4:7.2f} dB'.format(mn, sigmax, detection_time, detection_freq, snr)
    print(stats_string)
    return(mn, sigmax, detection_freq, peak_freq, snr)


# Main program
if __name__ == "__main__":

    # Add some signal handlers to trap SIGKILL and SIGTERM so we can close
    # down gracefully
    signal.signal(signal.SIGINT,signalHandler)
    signal.signal(signal.SIGTERM,signalHandler)

    # construct the argument parser and parse the arguments
    ap = argparse.ArgumentParser(description='Analyse npz spectrogram files create by meteor_radar')
    ap.add_argument("file", type=str, nargs='+', help="File or directory to analyse. Spectrogram files SPG*.npz")
    ap.add_argument("-n", "--noplot", action='store_true', help="Do not plot. Convert sample data to specgram data file only")
    ap.add_argument("-s", "--save", action='store_true', help="Save image files of plotted data")
    ap.add_argument("-c", "--combine", action='store_true', help="Combine data from npz files for plotting")
    ap.add_argument("-t", "--sortbyctime", action='store_true', help="View files sorted by ctime")
    # ap.add_argument("-f", "--frequency", type=float, default=143.05e6, help="Centre frequency")
    # ap.add_argument("-r", "--rate", type=int, default=960000, help="Sample rate")
    # ap.add_argument("-3", "--3d", action='store_true', help="Show 3d specgram")

    args = vars(ap.parse_args())

    file_or_dir = args['file']
    noplot = args['noplot']
    save_images = args['save']
    combine = args['combine']
    sort_by_ctime = args['sortbyctime']
    # sample_rate = args['rate']
    # centre_freq = args['frequency']
    # show_3d = args['3d']

    # Print command key help
    print(HELP_TEXT)

    # Make directories required
    make_directories()

    # Create a meteor plotter object
    meteor_plotter = MeteorPlotter()

    file_index = 0
    file_index_movement = 1

    # Combine several files for analysis
    if combine :
        obs_times = []
        file_names = file_or_dir
        for index, file_name in enumerate(file_names) :
            # Get observation data from file name e.g. SPG_143050000_300000_20210204_222326_281976.npz
            new_obs_time, centre_freq, sample_rate = get_observation_data(file_name)
            obs_times.append(new_obs_time)

            # Unpack the data
            if 'SMP' in file_name and 'npz' in file_name :
                npz_data = np.load(file_name)
                samples = npz_data['samples']
                sample_rate = DEFAULT_SAMPLE_RATE
                try:
                    centre_freq = npz_data['centre_freq']
                    sample_rate = npz_data['sample_rate']
                    obs_time = datetime.datetime.strptime(str(npz_data['obs_time']), "%Y-%m-%d %H:%M:%S.%f")
                except Exception as e :
                    print(e)

                window = hamming(NUM_FFT, sym=True)  # symmetric Gaussian window
                sft = ShortTimeFFT(window, hop=HOP, fs=sample_rate, mfft=NUM_FFT, fft_mode='centered')
                new_Pxx = sft.spectrogram(samples)

                T_x, N = HOP / sample_rate, new_Pxx.shape[1]
                new_bins = np.arange(N) * T_x

                f = sft.f
                f = (f + centre_freq - 2000) / 1e6
                new_f = f


            if 'SPG' in file_name and 'npz' in file_name :
                npz_data = np.load(file_name)

                new_bins = npz_data['bins']
                new_f = npz_data['f']
                new_Pxx = npz_data['Pxx']

            # Set the variables for the first observation
            if len(obs_times) == 1 :
                Pxx = new_Pxx
                bins = new_bins
                f = new_f
                obs_time = new_obs_time

            # Add the time difference between observations
            else:
                new_time_diff = (obs_times[-1] - obs_times[-2]).total_seconds()

                # If the observations don't overlap in time, then break
                if new_time_diff > new_bins[-1] : break

                # Add the time difference between 1st observation and this observation to the new set of time bins
                time_diff = (obs_times[-1] - obs_times[0]).total_seconds()
                new_bins += time_diff

                # Concatenate the observation data
                Pxx = np.concatenate((Pxx, new_Pxx), axis=1)
                bins = np.concatenate((bins, new_bins), axis=0)

        obs_time = obs_times[0]
        meteor_plotter.set_file_name(file_names[0])
        meteor_plotter.plot_specgram(Pxx, f, bins, centre_freq, obs_time, flipped=False, utc_time=True)

        os._exit(0)



    # Get all filenames in directory to allow scrolling through
    if os.path.isdir(file_or_dir[0]) :
        dirname = file_or_dir[0]
        filenames = sorted(glob.glob(dirname + '/*.npz'))
    else:
        filenames = file_or_dir
        if len(filenames) == 1 :
            dirname = os.path.dirname(filenames[0])
            npz_filenames = sorted(glob.glob(dirname + '/*.npz'), reverse=False)
            if len(npz_filenames) > 1 :
                # npz_filenames = list(dict.fromkeys(npz_filenames))    # Ensure filename list is unique
                file_index = npz_filenames.index(filenames[0])
                filenames = npz_filenames

    if sort_by_ctime : filenames.sort(key=os.path.getctime)

    num_smp_files = sum(['SMP' in el for el in filenames])

    # Loop through files, displaying plots
    while file_index < len(filenames) :
        filename = filenames[file_index]
        if os.path.isfile(filename) :

            # Get observation data from file name e.g. SPG_143050000_300000_20210204_222326_281976.npz
            obs_time, centre_freq, sample_rate = get_observation_data(filename)
            meteor_plotter.set_file_name(filename)

            # If this is specgram data, plot the spectrogram only
            if 'SPG' in filename and 'npz' in filename :
                # Get the np data from file
                npz_data = np.load(filename)

                # Extract the FFT data. bins is time in seconds, but old format required division by the sample rate
                bins = npz_data['bins']
                if sample_rate is not None : bins /= sample_rate
                f = npz_data['f']
                Pxx = npz_data['Pxx']

                meteor_plotter.plot_specgram(Pxx, f, bins, centre_freq, obs_time, flipped=False)
                # if show_3d : plot_3dspecgram(Pxx, f, bins, centre_freq)

            # If this is raw sample data, create the spectrogram display data and display it
            if 'SMP' in filename and 'npz' in filename :
                npz_data = np.load(filename)
                samples = npz_data['samples']
                sample_rate = DEFAULT_SAMPLE_RATE
                try:
                    centre_freq = npz_data['centre_freq']
                    sample_rate = npz_data['sample_rate']
                    obs_time = datetime.datetime.strptime(str(npz_data['obs_time']), "%Y-%m-%d %H:%M:%S.%f")
                except Exception as e :
                    print(e)

                window = hamming(NUM_FFT, sym=True)  # symmetric Gaussian window
                sft = ShortTimeFFT(window, hop=HOP, fs=sample_rate, mfft=NUM_FFT, fft_mode='centered')
                Pxx = sft.spectrogram(samples)

                T_x, N = HOP / sample_rate, Pxx.shape[1]
                bins = np.arange(N) * T_x

                f = sft.f
                f = (f + centre_freq - 2000) / 1e6

                if save_images :
                    meteor_plotter.set_file_name(filename)
                    meteor_plotter.plot_specgram(Pxx, f, bins, centre_freq, obs_time, flipped=False, save_images=True, noplot=True)
                    if file_index == num_smp_files-1 :
                        os._exit(0)
                else:
                    meteor_plotter.plot_specgram(Pxx, f, bins, centre_freq, obs_time, flipped=False)


        file_index += file_index_movement

        # Allow the index to be circular
        if file_index == len(filenames) : file_index = 0
        elif file_index < 0 : file_index = len(filenames) - 1

