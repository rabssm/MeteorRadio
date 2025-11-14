# Raspberry Pi Radio Meteor Detector


## Requirements
This guide assumes basic knowledge of electronics, the Unix environment, and some experience with the Raspberry Pi platform itself.

### Hardware

#### Software Radio
A Realtek Semiconductor Corp. RTL2832U DVB-T.  The USB dongle is plugged into a Raspberry Pi 3/4 (1-2GB memory) running Raspbian Linux. To check that your USB dongle will work, see the section below regarding the 'rtl_test' command.

#### Antenna
Recommended HB9-2 HB9CV 2 ELEMENT ANTENNA for the GRAVES frequency 143.05 MHz.

#### RPi control box
A Raspberry Pi 3B or 4, with one available USB port. Power supply. 8GB or larger SD Card.
Recommended OS is Raspbian Bookworm.

A wifi or wired ethernet connection to the internet is required to maintain the NTP time.

## Software
### Acquisition and Detection Software
The software uses Python3.
The acquisition software reads the raw data from the USB radio and does a fast fourier transform (FFT) on each sample block as it is received. The FFT of each sample block is then analysed to check for a peak signal above the SNR threshold at a frequency +/- 120 Hz of the target frequency (GRAVES 143.05 MHz).
After each detection trigger, the software stores the raw sample data for the next 10 seconds as an SMP file. If the --fft option is used, the detection data is stored in 2 files, the raw audio data in the form of a raw audio file, and the FFT data in the form of an SPG numpy npz file.

#### Observation Data
Observation data is produced in the directories:
```
~/radar_data/       Detection FFT data files and audio files
    Logs/           Log files logging each detection in a variety of formats (see available formats below)
    Archive/        Directory for archiving detections of interest
    Captures/       Directory for keeping detections of interest
    Junk/           Directory for detections which are of no interest

```
##### Raw Observation Data
Raw observation data is acquired by default. This produces files containing the raw I/Q sample data from the SDR in the form of a numpy npz file with the name format:

```
SMP_FFFFFFFFF_YYYYMMDD_HHMMSS_%%%%%%.npz
e.g.
SMP_143050000_20220622_152435_196974.npz
```

These raw observation detection files are about 3.1 MB in size. They contain all of the information required for a detailed analysis of the meteor detection for example for high resolution head echo analysis.

##### FFT Output filename format
FFT observation data is required when the --fft command line option is used.
```
Audio file:     AUD_FFFFFFFFF_YYYYMMDD_HHMMSS_%%%%%%.raw
FFT file:       SPG_FFFFFFFFF_YYYYMMDD_HHMMSS_%%%%%%.npz

where:
FFFFFFFFF               is the centre frequency in Hz
YYYYMMDD_HHMMSS_%%%%%%  is the date and time of the start of the observation to microsecond resolution

e.g.
AUD_143050000_20220206_132454_941629.raw
SPG_143050000_20220206_132454_941629.npz
```

Audio and FFT detection files are about 800 kB in size.

#### Radio Tuning
The software tunes the USB software radio to a central frequency 2 kHz below the required frequency. This is so that a meteor detection yields an approximately 2 kHz audible tone on the upper sideband. The default frequency for radio meteor detection is the frequency of the GRAVES transmitter 143.05 MHz. The required frequency can be changed using the -f option.


#### Resource Usage and Performance
The acquisition software uses about 50% of one CPU core of the Pi4, and about 90% of one core on a Pi3b. When a detection is made, a separate python MultiProcess is started to perform the FFT on the 10 seconds of stored sample data, and then store the data in the numpy npz format. This process uses 100% of a CPU core for about 10s.
It is recommended that when running using a Pi3b, the --decimate option is used, as this significantly improves performance of the FFT routines for storing the detections.

Note. It may be necessary to experiment with the -s 'SNR' option to determine the optimum SNR detection threshold for the specific antenna/receiving equipment. The default SNR is set to 45 (~16dB). If there are too many false positives, then the SNR threshold should be increased.

### Analysis Software
The analyse_detection.py matplotlib tool can be used to visualise and analyse the resultant detection SPC or SMP npz files. This tool imports matplotlib and scipy.

### Installation
The software uses the pyrtlsdr package for reading the USB data from the RTL SDR dongle. It also needs python-matplotlib and numpy for the FFT routines.
The required python modules can be installed with the installation commands below, and has been tested on Raspbian Bookworm:
```
# Clone this repository
git clone https://github.com/rabssm/MeteorRadio.git

# Install required apt packages
sudo apt update && sudo apt install rtl-sdr libopenblas-dev

# Create a virtual environmemt in which to install and run the software
python -m venv ~/vMeteorRadio
source ~/vMeteorRadio/bin/activate
cd MeteorRadio
pip install -r requirements.txt
```

To ensure that the RTL SDR dongle will work on your system, run the rtl_test program. Check that this detects your device and runs correctly.
```
rtl_test
```

Playing of audio and conversion of the raw data files to audio .wav files by the analysis software requires the sox package:
```
sudo apt install -y sox
```

The chrony package is recommended to be installed to maintain the NTP time synchronisation. This is optional, but use of chrony should ensure that timings of observations are accurate to within 1ms
```
sudo apt install -y chrony
```

## Software Configuration File
Create a file named .radar_config in the top level home directory (e.g. ~/.radar_config) containing the following lines:
```
stationID: Mylocation ; Geographical location of the receiver
longitude: -1.999     ; Geographical longitude of the receiver
latitude: 50.999      ; Geographical latitude of the receiver
elevation: 24         ; Altitude above sea level of the receiver in metres
ID_NUM: 17            ; ID number used for Radio Meteor Detection Collaboration Project
foff: -60             ; Measured frequency offset of the receiver in Hz
TxSource: GRAVES      ; Name of the tranmitter
TimeSync: NTP         ; Time synchronisation method
country: UK           ; Country
region: Myregion      ; Region within country
```

## Log Output Data
Information about each meteor detection is logged to files in the ~/radar_data/Logs directory in the following formats.

### RMOB CSV Format for UK Meteor Analysis group (Daily file)
Filename: RYYYYMMDD_Location.csv  e.g. R20220127_Location.csv

Data format:
```
Ver,Y,M,D,h,m,s,Bri,Dur,freq,ID,Long,Lat,Alt,Tz
RMOB,2022,01,27,12,28,19.899,30.55,0.55,-40.77,Location,-1.99,50.99,24.0,0
```

Data provided in RMOB csv format to UK Meteor Analysis group.

### CSV Format for Radio Meteor Detection Collaboration Project (Monthly file)
Filename: YYYY-MM.csv  e.g. 2022-01.csv

Data format:
```
user_ID,date,time,signal,noise,frequency,durationc,durations,lat,long,source,timesync,snratio,doppler_estimate
17,2022-01-01,00:34:34.961687,-6.799,-31.262,2010,0,0.35,50.99,-1.99,GRAVES,NTP,24.46,10
```

Data provided for https://radiometeordetection.org/

### Software tool for generating monthly colorgramme output file for RMOB.ORG https://www.rmob.org/
A python script is provided to produce output data to allow use by the RMOB colorgramme software to produce an RMOB colorgramme for upload to RMOB.

```
python monthly_rmob.py -y 2022 -m 10 -o Observer
```

## Running the acquisition software

To get help using the acquisition software, run the command:
```
~/vMeteorRadio/bin/python meteor_radar.py -h
```

To start the acquisition software in verbose mode with a detection threshold SNR of 45, run the command:
```
~/vMeteorRadio/bin/python meteor_radar.py -v -s 45
```

To analyze the meteor detection FFT data in the .npz files in the output directory ~/radar_data :
```
python analyse_detection.py ~/radar_data
```

The raw sample audio files have a sample rate of 37.5k. They can be converted to .wav files using sox or played :
```
sox -r 37.5k -b 16 -e signed-integer -c 1 <audio_file.raw> <audio_file.wav>

# Play a raw audio file applying a 1500-3000 Hz bandpass filter
play -r 37.5k -b 16 -e signed-integer -c 1 <raw_audio_file> sinc 1500-3000
```


Below is an example of a meteor detection spectrogram as displayed by analyse_detection.py. In this example, the head echo can be clearly seen in the line moving across the plot from the right towards the centre. This line gives an indication of the radial velocity and deceleration of the meteor from the Doppler frequency shift.
The later vertical component of the plot is the radio echo from the plasma trail. This echo from the plasma trail can also show Doppler frequency shifts.

![alt text](https://github.com/rabssm/MeteorRadio/blob/main/doc/sample.png)

To make the software run automatically on every boot, add the command to crontab using the command:
```
crontab -e
```

Then add the following line at the end of the crontab (e.g.) :
```
@reboot sleep 60 && ~/vMeteorRadio/bin/python -u ~/source/MeteorRadio/src/meteor_radar.py -s 40 -g 50
```

