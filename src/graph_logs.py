import csv
import argparse
import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# Class for containing observation data and times
class Observation():

    def __init__(self, observation_time) :
        self.time = observation_time


def read_observation_times(filename) :
    f = open(filename, 'r')
    reader = csv.reader(f)

    date_data = []
    observation_data = []

    for row in reader:
        date_from_file = None
        date_time_str = row[1] + '-' + row[2] + '-' + row[3] + ' ' + row[4] + ':' + row[5] + ':' + row[6]

        try: date_from_file = datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError: pass
        try: date_from_file = datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
        except ValueError: pass

        if date_from_file is not None:
            date_data.append(date_from_file)
            # observation_data.append(Observation(date_from_file))

    f.close()

    return date_data, observation_data


# Main program
if __name__ == "__main__":

    ap = argparse.ArgumentParser()
    ap.add_argument("files", type=str, nargs='+', help="RMOB csv file(s) to read")
    args = vars(ap.parse_args())

    filenames = args['files']

    date_data = []
    observation_data = []
    date_data_for_hourly_count = []

    # Collect the data from the RMOB .csv files
    for filename in filenames :
        date_data.extend(read_observation_times(filename)[0])
        # observation_data.extend(read_observation_times(filename)[1])


    ####################################
    # Plot the histogram of hourly counts
    fig, ax = plt.subplots()
    ax.set_title("Total Meteor Counts\n" + min(date_data).strftime('%Y-%m-%d') + " to " + max(date_data).strftime('%Y-%m-%d'))
    ax.set_xlabel("Time of Day")

    # Fix the date data for hourly counts
    for dt in date_data :
        dt = dt.replace(year=2000, month=1, day=1)
        date_data_for_hourly_count.append(dt)

    ax.hist(date_data_for_hourly_count, 24, rwidth=0.75)

    # Format the x axis date time
    hour_fmt = '%H'
    myFmt = mdates.DateFormatter(hour_fmt)
    ax.xaxis.set_major_formatter(myFmt)
    fig.autofmt_xdate()

    plt.pause(0.1)

    ####################################
    # Plot the histogram of daily counts
    fig, ax = plt.subplots()
    ax.set_title("Total Meteor Counts\n" + min(date_data).strftime('%Y-%m-%d') + " to " + max(date_data).strftime('%Y-%m-%d'))
    ax.set_xlabel("Date")

    # Get number of days
    num_days = (max(date_data) - min(date_data)).days

    ax.hist(date_data, bins=num_days, rwidth=0.75)

    # Format the x axis date time
    date_fmt = '%Y-%m-%d'
    myFmt = mdates.DateFormatter(date_fmt)
    ax.xaxis.set_major_formatter(myFmt)
    fig.autofmt_xdate()

    plt.show()


