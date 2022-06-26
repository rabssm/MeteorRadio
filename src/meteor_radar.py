from rtlsdr import *
import asyncio
import numpy as np
import datetime
import re
# import matplotlib.pyplot as plt
from matplotlib.mlab import specgram
import scipy.signal as scipy_signal
from collections import deque
from queue import Queue
import os
import syslog
# import logging
import threading
import signal
import argparse
from multiprocessing import Process, Queue as mpQueue
from waterfall import Waterfall

DATA_DIR =  os.path.expanduser('~/radar_data/')
CAPTURES_DIR = DATA_DIR + 'Captures/'
ARCHIVE_DIR = DATA_DIR + 'Archive/'
LOG_DIR = DATA_DIR + 'Logs/'
CONFIG_FILE = os.path.expanduser('~/.radar_config')

SAMPLES_LENGTH = 24                   # Length of the deque for recording samples data
SAMPLES_BEFORE_TRIGGER = 6            # Number of samples wanted before the trigger (2 = 1 second)
# CENTRE_FREQUENCY = 92.9e6           # Radio 4
# CENTRE_FREQUENCY = 100.3e6          # Radio 3
# CENTRE_FREQUENCY = 100.8e6          # FM narrow band Test?
# CENTRE_FREQUENCY = 144.0e6
# CENTRE_FREQUENCY = 144.428e6        # Test signal
# CENTRE_FREQUENCY = 143.060640e6     # Narrow signal near Graves
# CENTRE_FREQUENCY = 143.06160e6      # Narrow signal near Graves
# CENTRE_FREQUENCY = 143.05e6         # GRAVES

# RTL SDR settings - 225001 to 300000 and 900001 to 3200000
SAMPLE_RATE = 300000       #    960000 (262144-causes noise near 143.05) 262144, 240000
SDR_GAIN = 50
DECIMATION = 8             # Reduce audio sample rate from 300k to 37.5k

# FFT Settings
FREQUENCY_OFFSET = -2000   # Tuning frequency offset from centre (so signal appears as 2kHz audio on upper sideband)
DETECTION_FREQUENCY_BAND = [-120,+120]    # Band for detection is +/- F Hz
NOISE_CALCULATION_BAND = [-500,+500]    # Band for noise calculation is +/- F Hz
OVERLAP = 0.75             # Overlap for saved FFT data (0.75 is 75%)
ANALYSIS_OVERLAP = 0.5     # Overlap for detection analysis
COMPRESSION_FREQUENCY_BAND = 1000   # Band for compression data saving is +/- 1000 Hz
AUDIO_FREQUENCY_BANDPASS = [1500, 3000]   # Bandpass filter for audio around 2 kHz
NUM_FFT = 2**15

# Trigger condition settings
TRIGGERS_REQUIRED = 1

# Handle process signals
def signalHandler (signum, frame) :
    # If we have a SIGUSR1 (kill -USR1 <pid>) signal, save current sample buffer
    if signum == signal.SIGUSR1 :
        syslog.syslog(syslog.LOG_DEBUG, "SIGUSR1 caught")
        sample_analyser.save_samples()
    else:
        os._exit(0)

# Create all necessary data directories for acquisition
def make_directories() :
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(CAPTURES_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

# Class for containing sample data and time of sample
class TimedSample():

    def __init__(self, sample, sample_time) :
        self.sample = sample
        self.sample_time = sample_time


# Class for logging detections to RMOB file
class RMBLogger():

    def __init__(self):

        self.id = ""
        self.Long = 0.0
        self.Lat = 0.0
        self.Alt = 0.0
        self.Ver = "RMOB"
        self.Tz = 0

        self.get_config()

    def get_config(self) :
        config_file_name = CONFIG_FILE
        try:
            with open(config_file_name) as fp:
                for cnt, line in enumerate(fp):
                    line_words = (re.split("[: \n]+", line))
                    if line_words[0] == 'stationID' : self.id = line_words[1]
                    if line_words[0] == 'latitude'  : self.Lat = float(line_words[1])
                    if line_words[0] == 'longitude' : self.Long = float(line_words[1])
                    if line_words[0] == 'elevation' : self.Alt = float(line_words[1])

        except Exception as e :
            print(e)
            syslog.syslog(syslog.LOG_DEBUG, str(e))
        # print(self.id,self.Lat,self.Long,self.Alt)


    # Write to RMB format R<date>_<location>.csv file as:
    # Ver,Y,M,D,h,m,s,Bri,Dur,freq,ID,Long,Lat,Alt,Tz
    def log_data(self,obs_time,Bri,Dur,freq) :
        filename = "R" + obs_time.strftime("%Y%m%d_") + self.id + ".csv"
        try:
            rmb_file = open(LOG_DIR + filename, "r")
            rmb_file.close()
        except:
            rmb_file = open(LOG_DIR + filename, "a")
            rmb_file.write("Ver,Y,M,D,h,m,s,Bri,Dur,freq,ID,Long,Lat,Alt,Tz\n")
            rmb_file.close()

        try:
            rmb_file = open(LOG_DIR + filename, "a")
            rmb_string = '{0:s},{1:s},{2:.2f},{3:.2f},{4:.2f},{5:s},{6:.5f},{7:.5f},{8:.1f},{9:d}\n'.format(self.Ver, obs_time.strftime("%Y,%m,%d,%H,%M,%S.%f")[:-3], Bri, Dur, freq, self.id, self.Long, self.Lat, self.Alt, self.Tz)
            syslog.syslog(syslog.LOG_DEBUG, "Writing to RMB file " + filename + " " + rmb_string)
            rmb_file.write(rmb_string)
            rmb_file.close()
        except Exception as e :
            syslog.syslog(syslog.LOG_DEBUG, str(e))


# Class for logging detections to monthly csv file
class MonthlyCsvLogger():
    def __init__(self):

        self.id = ""
        self.Lat = 0.0
        self.Long = 0.0
        self.foff = 0.0
        self.tx_source = ""
        self.time_sync = ""

        self.get_config()

    def get_config(self) :
        config_file_name = CONFIG_FILE
        try:
            with open(config_file_name) as fp:
                for cnt, line in enumerate(fp):
                    line_words = (re.split("[: \n]+", line))
                    if line_words[0] == 'ID_NUM'    : self.id = line_words[1]
                    if line_words[0] == 'latitude'  : self.Lat = float(line_words[1])
                    if line_words[0] == 'longitude' : self.Long = float(line_words[1])
                    if line_words[0] == 'foff'      : self.foff = float(line_words[1])
                    if line_words[0] == 'TxSource'  : self.tx_source = line_words[1]
                    if line_words[0] == 'TimeSync'  : self.time_sync = line_words[1]

        except Exception as e :
            print(e)
            syslog.syslog(syslog.LOG_DEBUG, str(e))


    def log_data(self, obs_time, centre_freq, frequency, signal, noise, duration, max_snr) :

        try:
            filename = obs_time.strftime('%Y-%m.csv')
            csv_file = open(LOG_DIR + filename, "r")
            csv_file.close()
        except:
            csv_file = open(LOG_DIR + filename, "a")
            csv_file.write("user_ID,date,time,signal,noise,frequency,durationc,durations,lat,long,source,timesync,snratio,doppler_estimate\n")
            csv_file.close()

        try:
            date = obs_time.strftime('%Y-%m-%d')
            time = obs_time.strftime('%H:%M:%S.%f')
            doppler_estimate = int((float(frequency)) - float(centre_freq) - self.foff)
            offset_frequency = int(2000 + (float(frequency)) - float(centre_freq) - self.foff)

            output_line = "%s,%s,%s,%.3f,%.3f,%s,%s,%.2f,%.2f,%.2f,%s,%s,%.2f,%s\n" % (self.id, date, time, signal, noise, offset_frequency, '0', duration, self.Lat, self.Long, self.tx_source, self.time_sync, max_snr, doppler_estimate)
            if verbose : print("csv output:", output_line)

            filename = obs_time.strftime('%Y-%m.csv')
            csv_file = open(LOG_DIR + filename, "a")
            csv_file.write(output_line)
            csv_file.close()
        except Exception as e :
            syslog.syslog(syslog.LOG_DEBUG, str(e))
            # print(str(e))


# Class for determining the meteor capture statistics
class CaptureStatistics() :
    def __init__(self, Pxx, f, bins, obs_time, snr_threshold) :
        self.Pxx = Pxx
        self.f = f
        self.bins = bins
        self.obs_time = obs_time
        self.snr_threshold = snr_threshold
        self.meteor_detections = []


    def calculate(self) :
        # Calculate the signal level stats over the detection band
        self.raw_median = np.median(self.Pxx[0:13])    # Calculate noise before detection
        self.log_mn = 10.0*np.log10(self.raw_median)
        self.log_sigmax = 10.0*np.log10(np.max(self.Pxx))
        self.maxpos = np.argmax(np.max(self.Pxx, axis=1))
        self.peak_freq = self.f[self.maxpos]
        self.snr = self.log_sigmax - self.log_mn

        # Set default statistics in case of an exception
        self.min_detection_duration = self.bins[1] - self.bins[0]
        self.detection_duration = self.min_detection_duration
        self.detection_freq = self.peak_freq
        self.detection_time = self.obs_time + datetime.timedelta(seconds=2)


        try:
            # Find detection time and duration
            times_gt_thresh = self.bins[np.where(np.any(self.Pxx > self.raw_median * self.snr_threshold, axis = 0))]
            if len(times_gt_thresh) > 0 :
                prev_time = times_gt_thresh[0]
                det_start_time = 0.0
                for det_time in times_gt_thresh :
                    if det_time - prev_time > 1.0 :
                        break
                    prev_time = det_time

                self.detection_time = self.obs_time + datetime.timedelta(seconds=times_gt_thresh[0])
                self.detection_duration = prev_time - times_gt_thresh[0] + self.min_detection_duration
                # print("Detection time", self.detection_time, "Duration", prev_time - times_gt_thresh[0])

            # Find initial frequency of detection
            Pxx_snr = self.Pxx/self.raw_median
            s = np.nonzero(Pxx_snr > self.snr_threshold)
            imin, imax = np.min(s[1]), np.max(s[1])
            self.detection_freq = self.f[s[0][-1]]
        except Exception as e : print(e)


    # Get capture statistics for each detection in the observation data
    def get_detections(self, centre_freq) :

        # Narrow the frequency band for the calculations
        self.centre_freq = centre_freq
        self.noise_calculation_band = np.where((self.f*1e6 > (self.centre_freq + noise_calculation_band[0])) & (self.f*1e6 <= (self.centre_freq + noise_calculation_band[1])))
        self.detection_band = np.where((self.f*1e6 > (self.centre_freq + detection_frequency_band[0])) & (self.f*1e6 <= (self.centre_freq + detection_frequency_band[1])))
        self.Pxx = self.Pxx[self.noise_calculation_band]
        self.f = self.f[self.noise_calculation_band]

        # Calculate the signal level stats over the detection band
        self.raw_median = np.median(self.Pxx[0:13])    # Calculate noise before detection
        self.log_mn = 10.0*np.log10(self.raw_median)
        self.log_sigmax = 10.0*np.log10(np.max(self.Pxx))
        self.maxpos = np.argmax(np.max(self.Pxx, axis=1))
        self.peak_freq = self.f[self.maxpos]
        self.snr = self.log_sigmax - self.log_mn
        self.min_detection_duration = self.bins[1] - self.bins[0]

        readings_gt_thresh = np.array(np.argwhere(self.Pxx > self.raw_median * self.snr_threshold))
        readings_gt_thresh = readings_gt_thresh[readings_gt_thresh[:, 1].argsort()]

        if len(readings_gt_thresh) == 0 :
            return self.meteor_detections

        first_time = self.bins[readings_gt_thresh[0][1]]
        prev_time = first_time
        new_detection = True


        for reading in readings_gt_thresh :
            det_time = self.bins[reading[1]]
            det_freq = self.f[reading[0]]
            power = self.Pxx[reading[0],reading[1]]

            if new_detection :
                new_detection = False
                det_start_time = det_time
                real_detection_time = self.obs_time + datetime.timedelta(seconds=det_start_time)
                max_power = self.Pxx[reading[0],reading[1]]
                initial_frequency = det_freq

            # If there is a one second gap in the signal register a completed detection and set the start time for a new one
            if det_time - prev_time > 1.0 :
                duration = prev_time - det_start_time + self.min_detection_duration
                max_snr = 10 * np.log10(max_power) - self.log_mn
                self.meteor_detections.append(MeteorDetection(real_detection_time, duration, initial_frequency, max_snr))

                det_start_time = det_time
                real_detection_time = self.obs_time + datetime.timedelta(seconds=det_start_time)
                max_power = self.Pxx[reading[0],reading[1]]
                initial_frequency = det_freq

            # Less than 1 second gap, so check max power
            if power > max_power : max_power = power

            prev_time = det_time

        duration = prev_time - det_start_time + self.min_detection_duration
        max_snr = 10 * np.log10(max_power) - self.log_mn
        self.meteor_detections.append(MeteorDetection(real_detection_time, duration, initial_frequency, max_snr))

        return self.meteor_detections


# Class for recording meteor detections data
class MeteorDetection() :

    def __init__(self, start_time, duration, initial_frequency, max_snr) :
        self.start_time = start_time
        self.duration = duration
        self.initial_frequency = initial_frequency
        self.max_snr = max_snr
        print("Meteor detection: Time", self.start_time, "duration", self.duration, "initial frequency", self.initial_frequency, "max SNR", self.max_snr)


# Sample analyser. Threaded class for taking data from the sample queue for analysis
class SampleAnalyser(threading.Thread):
    def __init__(self, centre_freq):
        # Initialise the thread
        threading.Thread.__init__(self)


        # Initialise variables
        self.noise_deque = deque(maxlen=8)
        self.fmax3_deque = deque(maxlen=16)      # Deque for storing 3 frequencies with most signal
        self.median_noise = 10.0
        self.ave_noise = 10.0

        self.trigger_count = 0
        self.trigger_wait_counter = 0

        self.analysis_thread = None
        self.save_process1 = None
        self.save_process2 = None

        self.sdr_freq = 0
        self.sdr_freq_mhz = 0
        self.sample_time = 0
        self.samples_per_second = 0
        self.centre_freq = centre_freq
        self.save_raw_samples = save_raw_samples
        self.no_audio = no_audio
        self.decimate_before_saving = decimate_before_saving

        self.rmb_logger = RMBLogger()
        self.csv_logger = MonthlyCsvLogger()

        self.captures_dir = DATA_DIR


    def run(self):
        global sdr

        psd_queue = Queue(maxsize=10)

        # Get the first set of samples
        samples = sample_queue.get()

        # Initialise SDR frequency centre variables
        self.sdr_freq = sdr.center_freq
        self.sdr_freq_mhz = sdr.center_freq/1e6
        self.sdr_sample_rate = sdr.sample_rate

        samples_length = len(samples)
        self.sample_time = samples_length/self.sdr_sample_rate
        self.samples_per_second = samples_length/self.sample_time
        self.decimated_sample_rate = self.sdr_sample_rate / DECIMATION

        print("Samples length:", samples_length, "Sample rate:", self.sdr_sample_rate)
        print("Time for each sample", self.sample_time)
        print("SDR tuning frequency:", sdr.center_freq)
        print("SDR gain:", sdr.gain)

        # Do a first PSD to get frequency bands
        # decimated_samples = scipy_signal.decimate(samples, DECIMATION)
        # Pxx, f, bins = specgram(decimated_samples, NFFT=int(NUM_FFT/DECIMATION), Fs=self.decimated_sample_rate/1e6, noverlap=int(OVERLAP*(NUM_FFT/DECIMATION)))
        Pxx, f, bins = specgram(samples, NFFT=int(NUM_FFT), Fs=self.sdr_sample_rate/1e6, noverlap=int(ANALYSIS_OVERLAP*NUM_FFT))

        f += self.sdr_freq_mhz
        self.noise_calculation_band = np.where((f*1e6 > (self.centre_freq + noise_calculation_band[0])) & (f*1e6 <= (self.centre_freq + noise_calculation_band[1])))
        self.detection_band = np.where((f*1e6 > (self.centre_freq + detection_frequency_band[0])) & (f*1e6 <= (self.centre_freq + detection_frequency_band[1])))
        print("Sampling frequency band", f[0], f[-1])
        print("Noise calculation frequency band", f[self.noise_calculation_band])
        print("Detection frequency band", f[self.detection_band])
        print("Spectrogram shape for detection", Pxx.shape)


        # Get samples from the queue as they arrive, analyse them and check for a detection trigger
        while True :
            samples = sample_queue.get()

            if self.analysis_thread is not None and self.analysis_thread.is_alive() : continue

            # Do the PSD analysis in a thread. If the queue is full then we must skip to the next set of samples
            if psd_queue.full() : continue
            # self.analyse_psd(samples, fcentre, psd_queue)
            self.analysis_thread = threading.Thread(target = self.analyse_psd, args = (samples, psd_queue))
            self.analysis_thread.start()

            # Get the PSD results as they become available
            if psd_queue.empty() : continue
            psd_results = psd_queue.get()
            self.check_trigger(psd_results)


    # Check FFT data for a detection, and save the samples if a detection is triggered
    def check_trigger(self, psd_results) :
        mn, sigmedian, sigmax, peak_freq = psd_results
        self.median_noise = sigmedian

        # Use the median noise for the SNR calculation
        snr = sigmax/self.median_noise

        stats = ' Mean:{0:8.4f}  Median:{1:8.4f}  Max:{2:10.4f}  PeakF:{3:12.6f}  SNR:{4:10.2f}'.format(mn, sigmedian, sigmax, peak_freq, snr)
        if verbose : print(datetime.datetime.now(), stats)

        # If the signal level is high enough above the noise level, trigger a detection and log it
        trigger = snr > snr_threshold
        if trigger :
            print("Triggered at", datetime.datetime.now())
            if self.trigger_count == 0 :
                syslog.syslog(syslog.LOG_DEBUG, "Radio detection triggered at " + str(datetime.datetime.now()) + stats)
            self.trigger_count += 1
            print("Trigger count:", self.trigger_count)

        else:
            # Compute rolling average noise
            self.noise_deque.append(mn)
            # self.ave_noise = np.average(self.noise_deque)

        # If we have had a detection, wait for further samples before saving the detection in a thread.
        if self.trigger_count >= TRIGGERS_REQUIRED :
            self.trigger_wait_counter += 1
            # print("Trigger waiting for samples:", self.trigger_wait_counter)
            if self.trigger_wait_counter >= SAMPLES_LENGTH-SAMPLES_BEFORE_TRIGGER :
                # Don't save any more sample data until any previous saves have completed
                # if self.save_process is None or not self.save_process.is_alive() :
                self.save_samples()
                self.trigger_count = 0
                self.trigger_wait_counter = 0

        # Otherwise reset the trigger count
        else :
            if not trigger: self.trigger_count = 0


    # Convert sample data to FFT, restrict to narrow freq band and save
    def save_samples(self) :
        timed_sample_snapshot = timed_sample_deque.copy()
        all_samples = []

        # Subtract sample time to give actual obs_time of start of 1st sample
        obs_time = timed_sample_snapshot[0].sample_time - datetime.timedelta(seconds=self.sample_time)
        for timed_sample in timed_sample_snapshot :
            all_samples.append(timed_sample.sample)

        samples_forspecgram = np.asarray(all_samples).flatten()

        print("Saving sample data")

        # Change the capture directory to Captures/{date} if required
        if capturetodated :
            self.captures_dir = CAPTURES_DIR + obs_time.strftime('%Y%m%d') +'/'
            os.makedirs(self.captures_dir, exist_ok=True)
            pass

        # If set for raw samples, only save the raw sample data
        if self.save_raw_samples :
            # Set the raw sample saving process off in one of 2 available subprocesses
            if self.save_process1 is None or not self.save_process1.is_alive() :
                self.save_process1 = Process(target=self.save_raw_sample_data, args=(samples_forspecgram, self.sdr_freq, self.centre_freq, self.sdr_sample_rate, obs_time))
                self.save_process1.start()
            elif self.save_process2 is None or not self.save_process2.is_alive() :
                self.save_process2 = Process(target=self.save_raw_sample_data, args=(samples_forspecgram, self.sdr_freq, self.centre_freq, self.sdr_sample_rate, obs_time))
                self.save_process2.start()


        # Otherwise, save FFT spectrogram and raw audio
        else:
            # Set the FFT saving process off in one of 2 available subprocesses
            if self.save_process1 is None or not self.save_process1.is_alive() :
                self.save_process1 = Process(target=self.save_fft, args=(samples_forspecgram, self.sdr_freq, self.centre_freq, self.sdr_sample_rate, obs_time))
                self.save_process1.start()
            elif self.save_process2 is None or not self.save_process2.is_alive() :
                self.save_process2 = Process(target=self.save_fft, args=(samples_forspecgram, self.sdr_freq, self.centre_freq, self.sdr_sample_rate, obs_time))
                self.save_process2.start()

            if not self.no_audio :
                print("Saving audio")
                self.audio_process = Process(target=self.save_audio, args=(samples_forspecgram, self.sdr_freq, self.centre_freq, self.sdr_sample_rate, obs_time))
                self.audio_process.start()


    # Function to save the raw sample data as an SMP file
    def save_raw_sample_data(self, raw_samples, sda_centre_freq, centre_freq, sample_rate, obs_time) :

        # Decimate to reduce sample rate from 300 kHz to 37.5 kHz
        decimated_samples = scipy_signal.decimate(raw_samples, DECIMATION)

        # Save the decimated raw samples
        sample_filename = self.captures_dir + '/SMP_' + str(int(centre_freq)) + obs_time.strftime('_%Y%m%d_%H%M%S_%f.npz')
        syslog.syslog(syslog.LOG_DEBUG, "Saving " + sample_filename)
        print("Saving", sample_filename)
        np.savez(sample_filename, obs_time=str(obs_time), centre_freq=centre_freq, sample_rate=self.decimated_sample_rate, samples=np.array(decimated_samples).astype("complex64"))

        # Log the data
        Pxx, f, bins = specgram(decimated_samples, NFFT=int(NUM_FFT/DECIMATION), Fs=self.decimated_sample_rate/1e6, noverlap=int(OVERLAP*(NUM_FFT/DECIMATION)))
        f += sda_centre_freq/1e6

        # Restrict the band for saving to a band around the required centre frequency
        freq_slice = np.where((f >= (centre_freq-COMPRESSION_FREQUENCY_BAND)/1e6) & (f <= (centre_freq+COMPRESSION_FREQUENCY_BAND)/1e6))
        f = f[freq_slice]
        Pxx = Pxx[freq_slice,:][0]
        bins /= 1e6      # Convert bins data to time in seconds

        # Log the capture stats
        self.log_capture_stats(Pxx, f, bins, obs_time)



    # Function to save the sample data as a spectrogram file - run in a multiprocess
    def save_fft(self, samples_forspecgram, sda_centre_freq, centre_freq, sample_rate, obs_time) :

        # Create the specgram
        # Pxx, f, bins, im = plt.specgram(samples_forspecgram, NFFT=NUM_FFT, Fs=sample_rate/1e6, Fc=sda_centre_freq/1e6, noverlap=COMPRESSION_OVERLAP*NUM_FFT, xextent=[0, len(samples_forspecgram)/sample_rate])
        # Pxx, f = psd(samples, NFFT=NUM_FFT, Fs=sdr.sample_rate/1e6, noverlap=OVERLAP*NUM_FFT)

        if self.decimate_before_saving :
            decimated_samples = scipy_signal.decimate(samples_forspecgram, DECIMATION)
            Pxx, f, bins = specgram(decimated_samples, NFFT=int(NUM_FFT/DECIMATION), Fs=self.decimated_sample_rate/1e6, noverlap=int(OVERLAP*(NUM_FFT/DECIMATION)))
        else:
            Pxx, f, bins = specgram(samples_forspecgram, NFFT=NUM_FFT, Fs=sample_rate/1e6, noverlap=OVERLAP*NUM_FFT)

        f += sda_centre_freq/1e6

        # Restrict the band for saving to a band around the required centre frequency
        freq_slice = np.where((f >= (centre_freq-COMPRESSION_FREQUENCY_BAND)/1e6) & (f <= (centre_freq+COMPRESSION_FREQUENCY_BAND)/1e6))
        f = f[freq_slice]
        Pxx = Pxx[freq_slice,:][0]
        bins /= 1e6      # Convert bins data to time in seconds

        # Log the capture stats
        self.log_capture_stats(Pxx, f, bins, obs_time)
        # Correct time=0 at trigger time
        # time_before_trigger = (SAMPLES_BEFORE_TRIGGER/SAMPLES_LENGTH) * (bins[-1] - bins[0])
        # bins -= time_before_trigger

        # Save the data
        specgram_filename = self.captures_dir + '/SPG_' + str(int(centre_freq)) + obs_time.strftime('_%Y%m%d_%H%M%S_%f.npz')
        syslog.syslog(syslog.LOG_DEBUG, "Saving " + specgram_filename)
        print("Saving", specgram_filename)
        np.savez(specgram_filename, Pxx=Pxx, f=f, bins=bins)
        print("\a")


    # Function to save the sample data as a raw audio file - run in a multiprocess
    def save_audio(self, samples_foraudio, sda_centre_freq, centre_freq, sample_rate, obs_time) :

        # Decimate to reduce sample rate from 300 kHz to 37.5 kHz
        x1 = scipy_signal.decimate(samples_foraudio, DECIMATION)

        # Create a bandpass filter for the audio signal
        #sos = scipy_signal.butter(10, AUDIO_FREQUENCY_BANDPASS, 'bandpass', fs=sample_rate, output='sos')
        #x2 = scipy_signal.sosfilt(sos, x1)

        x7 = x1

        # Scale audio to adjust volume
        x7 *= 10000 / np.max(np.abs(x7))

        # Save to file as 16-bit signed single-channel audio samples
        # Note that we can throw away the imaginary part of the IQ sample data for USB
        audio_filename = self.captures_dir + '/AUD_' + str(int(centre_freq)) + obs_time.strftime('_%Y%m%d_%H%M%S_%f.raw')
        syslog.syslog(syslog.LOG_DEBUG, "Saving " + audio_filename)
        print("Saving", audio_filename)
        x7.astype("int16").tofile(audio_filename)


    # Log the detection statistics
    def log_capture_stats(self, Pxx, f, bins, obs_time) :

        # Calculate the detection statistics from the PSD data
        capture_statistics = CaptureStatistics(Pxx, f, bins, obs_time, snr_threshold)
        capture_statistics.calculate()

        # Log to syslog
        stats_string = 'Mean:{0:10.4f}  Max:{1:10.4f}  Duration:{2:7.2f}  Frequency:{3:12.6f}  MaxSNR:{4:7.2f} dB'.format(capture_statistics.log_mn, capture_statistics.log_sigmax, capture_statistics.detection_duration, capture_statistics.detection_freq, capture_statistics.snr)
        syslog.syslog(syslog.LOG_DEBUG, "Radio detection stats log " + capture_statistics.detection_time.strftime("%d/%m/%Y %H:%M:%S.%f")[:-3] + " " + stats_string)

        # Log to RMB .csv file
        self.rmb_logger.log_data(capture_statistics.detection_time, capture_statistics.snr, capture_statistics.detection_duration, (capture_statistics.detection_freq*1e6) - centre_freq)

        # Produce the log for the monthly csv reports
        self.csv_logger.log_data(capture_statistics.detection_time, self.centre_freq, capture_statistics.detection_freq*1e6, capture_statistics.log_sigmax, capture_statistics.log_mn, capture_statistics.detection_duration, capture_statistics.snr)
        # capture_statistics.get_detections()


    # Perform a PSD analysis on the raw samples data
    def analyse_psd(self, samples, psd_queue) :
        # Do the PSD
        # NOTE: Decimation before taking the specgram is slower than doing the specgram on the raw sample data
        # decimated_samples = scipy_signal.decimate(samples, DECIMATION)
        # Pxx, f, bins = specgram(decimated_samples, NFFT=int(NUM_FFT/DECIMATION), Fs=self.decimated_sample_rate/1e6, noverlap=int(OVERLAP*(NUM_FFT/DECIMATION)))
        Pxx, f, bins = specgram(samples, NFFT=int(NUM_FFT), Fs=self.sdr_sample_rate/1e6, noverlap=int(ANALYSIS_OVERLAP*NUM_FFT))

        f += self.sdr_freq_mhz

        # Add this to add processed specgram to waterfall queue for waterfall display
        # try:
        #     waterfall_queue.put_nowait((Pxx, f))
        # except: pass

        f = f[self.detection_band]

        # Calculate the mean and median (noise) level over the larger noise calculation band
        nx = np.float16(Pxx[self.noise_calculation_band])
        mn = np.mean(nx)
        sigmedian = np.median(nx)

        # Calculate the signal level stats over the detection band
        x = np.float16(Pxx[self.detection_band])
        sigmax = np.max(x)
        maxpos = np.argmax(np.max(x, axis=1))
        peak_freq = f[maxpos]

        # self.find3f(x)

        psd_queue.put((mn, sigmedian, sigmax, peak_freq))


    # Find 3 frequencies with most signal
    def find3f(self, x) :
        fmax3 = np.argpartition(x, -3, axis=1)[:, -3:]
        if np.max(fmax3) == np.min(fmax3) + 2 :
            if verbose: print("Max 3 f triggered", fmax3)
            syslog.syslog(syslog.LOG_DEBUG, "Max 3 f triggered " + str(fmax3))
        return

        for i in range(0, x.shape[1]) :
            # pmax = np.max(x[:,i])
            fmax3 = x[:,i].argsort()[-3:][::-1]
            if np.max(fmax3) == np.min(fmax3) + 2 :
                self.fmax3_deque.append((i,np.sort(fmax3)))
                if verbose: print(i, np.sort(fmax3))

                # Have we had successive detections of 3f
                if len(self.fmax3_deque) > 1 :
                    diff_pos = abs(self.fmax3_deque[-1][0] - self.fmax3_deque[-2][0])
                    if diff_pos == 1 or diff_pos == (x.shape[1]-1) :
                        # print("2 successive")

                    # Check last 2 in deque for an overlap in frequencies
                        # print(self.fmax3_deque[-2], self.fmax3_deque[-1])
                        if abs(self.fmax3_deque[-2][1][0] - self.fmax3_deque[-1][1][0]) < 3 :
                            print("Overlap:", self.fmax3_deque[-2], self.fmax3_deque[-1])


# Main sample streaming loop run async
async def streaming():

    # configure device
    # sdr = RtlSdr()
    sdr.sample_rate = SAMPLE_RATE
    sdr.center_freq = centre_freq + FREQUENCY_OFFSET       # Tuning frequency for SDR
    # sdr.set_bandwidth(10e3)
    if sdr_gain == 'auto' : sdr.gain = sdr_gain
    else: sdr.gain = float(sdr_gain)
    # sdr.freq_correction = 0.0      # PPM

    # Loop forever taking samples
    async for samples in sdr.stream():
        # Get the time stamp and store the sample data temporarily
        time_stamp = datetime.datetime.now()
        timed_sample_deque.append(TimedSample(samples, time_stamp))

        # Add the sample data to the queue for the sample analyser
        sample_queue.put(samples)

        # Add the sample data to the waterfall queue for the waterfall display
        try:
            if waterfall_queue.full() : waterfall_queue.get_nowait()
            waterfall_queue.put_nowait(samples)
        except: pass

    # to stop streaming:
    await sdr.stop()

    # done
    sdr.close()


# Main program
if __name__ == "__main__":

    # Add some signal handlers to trap SIGKILL and SIGTERM so we can close
    # down gracefully
    signal.signal(signal.SIGINT,signalHandler)
    signal.signal(signal.SIGTERM,signalHandler)
    signal.signal(signal.SIGUSR1,signalHandler)

    # construct the argument parser and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-f", "--frequency", type=float, default=143.05e6, help="Centre frequency. Default is GRAVES (143.05 MHz)")
    ap.add_argument("-g", "--gain", type=str, default=str(SDR_GAIN), help="SDR tuner gain (0-50, auto). Default is 50")
    ap.add_argument("-s", "--snr_threshold", type=float, default=45, help="SNR threshold. Default is 45 (~16 dB)")
    ap.add_argument("-r", "--raw", action='store_true', help="Store raw sample data")
    ap.add_argument("-n", "--noaudio", action='store_true', help="Disable saving of audio data")
    ap.add_argument("-d", "--decimate", action='store_true', help="Decimate data for spectrogram before saving")
    ap.add_argument("-c", "--capturetodated", action='store_true', help="Store captures to dated directories e.g. ~/radar_data/Archive/20220621")
    ap.add_argument("-w", "--waterfall", action='store_true', help="Display waterfall graph")
    ap.add_argument("-v", "--verbose", action='store_true', help="Verbose output")
    ap.add_argument("--detectionband", nargs=2, type=int, default=DETECTION_FREQUENCY_BAND, help="Frequency band for detection in Hz. Default is " + str(DETECTION_FREQUENCY_BAND) + " e.g. -120 120")
    ap.add_argument("--noiseband", nargs=2, type=int, default=NOISE_CALCULATION_BAND, help="Frequency band for noise calculation in Hz. Default is " + str(NOISE_CALCULATION_BAND) + " e.g. -500 500")
    args = vars(ap.parse_args())

    centre_freq = args['frequency']
    sdr_gain = args['gain']
    snr_threshold = args['snr_threshold']
    save_raw_samples = args['raw']
    no_audio = args['noaudio']
    decimate_before_saving = args['decimate']
    capturetodated = args['capturetodated']
    display_waterfall = args['waterfall']
    verbose = args['verbose']
    detection_frequency_band = args['detectionband']
    noise_calculation_band = args['noiseband']

    # Set up the logging
    # logging.basicConfig(filename=LOG_FILE, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)

    print("Detection frequency:", centre_freq)
    print("SNR threshold:", snr_threshold)

    # Make the data directories
    make_directories()

    # Deque for samples data for saving on trigger
    timed_sample_deque = deque(maxlen=SAMPLES_LENGTH)

    # Create the queue for the samples for analysis
    sample_queue = Queue(maxsize=10)

    # Create the queue for the waterfall display
    waterfall_queue = mpQueue(maxsize=1)

    # Create the SDR instance
    sdr = RtlSdr()

    # Start the sample analyser
    sample_analyser = SampleAnalyser(centre_freq)
    sample_analyser.start()

    # Start the waterfall display
    if  display_waterfall :
        p = Waterfall(centre_freq + FREQUENCY_OFFSET, SAMPLE_RATE, waterfall_queue)
        p.start()

    # Start the sample collection
    asyncio.run(streaming())
