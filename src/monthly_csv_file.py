import os
import glob
import datetime
import argparse
import re

DATA_DIR =  os.path.expanduser('~/radar_data/')
LOG_DIR = DATA_DIR + 'Logs/'
ID = "17"
GRAVES_FREQ="143050000"
RXLAT="50.86"
RXLONG="-1.78"
TXSOURCE="Graves"
TIMESYNC="NTP"
FOFF=-60

def read_data(filename) :
    global csv_output

    with open(filename) as fin :
        for line in fin:
            split_line = re.split(r'[ ]+', line)
            # print(split_line)
            date = datetime.datetime.strptime(split_line[0], '%d/%m/%Y').strftime('%Y-%m-%d')
            time = split_line[1]
            noise = split_line[3]
            signal = split_line[5]
            duration = split_line[7]
            frequency = split_line[9]
            max_snr = split_line[11]
            doppler_estimate = int((float(frequency)*1e6) - float(GRAVES_FREQ) - FOFF)
            offset_frequency = int(2000 + (float(frequency)*1e6) - float(GRAVES_FREQ) - FOFF)

            # print(ID, date, time, signal, noise, offset_frequency, '0', duration, RXLAT, RXLONG, TXSOURCE, TIMESYNC, max_snr, doppler_estimate, sep=',')
            output_line = "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" % (ID, date, time, signal, noise, offset_frequency, '0', duration, RXLAT, RXLONG, TXSOURCE, TIMESYNC, max_snr, doppler_estimate)
            # print(output_line)
            csv_output.append(output_line)



if __name__ == "__main__":

    # construct the argument parser and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-m", "--month", type=int, default=datetime.datetime.now().month, help="Month of report")
    ap.add_argument("-y", "--year", type=int, default=datetime.datetime.now().year, help="Year of report")
    args = vars(ap.parse_args())

    month = args['month']
    year = args['year']

    print("Formatting data for", year, month)
    list_of_files = sorted(glob.glob(LOG_DIR + '*-' + '%02d' % month + '-*.stats'))
    # print(list_of_files)

    # Read in the data from the stats files into csv_output
    csv_output = []
    for stats_file in list_of_files :
        read_data(stats_file)

    # Create the csv file
    filename = str(year) + '-' + '%02d' % month + ".csv"
    print("Writing to file:", LOG_DIR + filename)
    csv_file = open(LOG_DIR + filename, "w")

    # Write the header line and then the csv data lines
    csv_file.write("user_ID,date,time,signal,noise,frequency,durationc,durations,lat,long,source,timesync,snratio,doppler_estimate\n")
    for csv_line in csv_output :
        csv_file.write(csv_line)
    csv_file.close()

