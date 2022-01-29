# Raspberry Pi Radio Detection of Meteors


## Requirements
This guide assumes basic knowledge of electronics, the Unix environment, and some experience with the Raspberry Pi platform itself.

### Hardware

#### Software Radio
A Realtek Semiconductor Corp. RTL2838 DVB-T.  The USB dongle is plugged into a Raspberry Pi 3/4 (1-2GB memory) running Raspbian Linux.

#### Antenna
Recommended HB9-2 HB9CV 2 ELEMENT ANTENNA for the GRAVES frequency 143.05 MHz.

#### RPi control box
A Raspberry Pi 3B or 4, with one available USB port. Power supply. 8GB or larger SD Card.
Recommend that the latest version of Raspbian is installed. At the time of writing, this is Raspbian Buster.

A wifi or wired ethernet connection to the internet is required to maintain the NTP time.


### Software

Python acquisition software which reads the raw data from the USB dongle and does a FFT on each sample block as it's received, then analyses the FFT data to check for a peak in SNR at a frequency +/- 120 Hz of the target frequency (GRAVES 143.05 MHz). After the detection trigger, the software stores the sample data for the next 10s, converts the data to the frequency domain and stores the data in the form of a numpy npz file. There is a tool to visualise and analyse the resultant npz file using matplotlib. Each detection file is a little less than 700 kB in size.

Observation data is produced in the directories:
```
~/radar_data/       Detection FFT data files and audio files
    Logs/           Log files logging each detection in a variety of formats (see available formats below)

    Archive/        Directory for archiving detections of interest
    Captures/       Directory for keeping detections of interest
    Junk/           Directory for detections which are of no interest

```

The default frequency for radio meteor detection is the frequency of the GRAVES transmitter 143.05 MHz.

The data acquisition software uses the pyrtlsdr package for reading the USB data from the RTL SDR dongle. Also needs python-matplotlib and numpy for the FFT routines. The analysis software imports matplotlib and scipy.

In terms of resource usage, the acquisition software uses a fairly constant 60% of one CPU core of the Pi4, and about 90% of a single core on a Pi3b. When a detection is made, a separate python MultiProcess is started to perform the FFT on the 10s of stored sample data, and then store the data in the numpy npz format. This process uses 100% of a CPU core for about 10s.
It is recommended that when running using a Pi3b, the --decimate option is used, as this significantly improves performance of the FFT routines for storing the detections.

It will be necessary to experiment with the -s <SNR> option to determine the optimum SNR detection threshold for the specific antenna/receiving equipment. If there are too many false positives, then the SNR threshold should be increased.

#### Additional Software Modules
The following additional modules are required to run the software.
These can be installed with the commands:
```
sudo apt install rtl-sdr python-numpy python-setuptools python-pip libusb-dev python-matplotlib
pip install pyrtlsdr scipy
```

The pandas package is needed to create the monthly detection counts graphs:
```
pip install pandas
```

Playing of audio and conversion of the raw data files to audio .wav files by the analysis software requires the sox package:
```
sudo apt install sox
```

## Software Configuration File

Create a file named .radar_config in the top level home directory (e.g. ~/.radar_config) containing the following lines:
```
stationID: Mylocation
longitude: -1.999
latitude: 50.999
elevation: 24
ID_NUM: 17
foff: -60
TxSource: GRAVES
TimeSync: NTP
country: UK
region: Myregion
```

## Log Output Data
Information about each meteor detection is logged to files in the ~/radar_data/Logs directory in the following formats.

### RMOB CSV Format for UKMON (Daily file)
Filename: RYYYYMMDD_Location.csv  e.g. R20220127_Location.csv

Data format:

Ver,Y,M,D,h,m,s,Bri,Dur,freq,ID,Long,Lat,Alt,Tz
RMOB,2022,01,27,12,28,19.899,30.55,0.55,-40.77,Location,-1.99,50.99,24.0,0

### CSV Format for Radio Meteor Detection Collaboration Project (Monthly file)
Filename: YYYY-MM.csv  e.g. 2022-01.csv

Data format:

user_ID,date,time,signal,noise,frequency,durationc,durations,lat,long,source,timesync,snratio,doppler_estimate
17,2022-01-01,00:34:34.961687,-6.799,-31.262,2010,0,0.35,50.99,-1.99,GRAVES,NTP,24.46,10

Data provided for https://radiometeordetection.org/

## Running the software

To get help, run the command:
```
python meteor_radar.py -h
```

To start the software in verbose mode with a detection threshold SNR of 45, run the command:
```
python meteor_radar.py -v -s 45
```

To analyze the resultant FFT data in the .npz files in the output directory ~/radar_data :
```
python analyse_detection.py ~/radar_data
```

Example meteor detection as displayed by analyse_detection.py :
![alt text](https://github.com/rabssm/MeteorRadio/blob/main/doc/sample.png)


To make the software run automatically on every boot, add the command to crontab using the command:
```
crontab -e
```

Then add the following line at the end of the crontab (e.g.) :
```
@reboot sleep 60 && python -u /home/pi/source/MeteorRadar/src/meteor_radar.py -s 45
```

