import re
import pandas as pd
import argparse
from matplotlib import pyplot as plt
import numpy as np
import datetime
import os
import glob
from calendar import monthrange

DATA_DIR = os.path.expanduser('~/radar_data')
LOG_DIR = DATA_DIR + 'Logs/'
CONFIG_FILE = os.path.expanduser('~/.radar_config')

# Main program
if __name__ == "__main__":

    ap = argparse.ArgumentParser()
    ap.add_argument("files", type=str, nargs='*', default="", help="RMOB csv file(s) to read")
    ap.add_argument("-s", "--saveimage", action='store_true', help="Save image only")
    ap.add_argument("-l", "--limit", type=int, default=0, help="Limit on graph z axis")
    ap.add_argument("-m", "--month", type=int, default=datetime.datetime.now().month, help="Month of graph")
    ap.add_argument("-y", "--year", type=int, default=datetime.datetime.now().year, help="Year of graph")


    args = vars(ap.parse_args())

    filenames = args['files']
    save_image = args['saveimage']
    graph_zlimit = args['limit']
    month = args['month']
    year = args['year']

    config_file_name = CONFIG_FILE
    country = ""
    region = ""
    tx_source = ""
    try:
        with open(config_file_name) as fp:
            for cnt, line in enumerate(fp):
                line_words = (re.split("[: \n]+", line))
                if line_words[0] == 'country' : country = line_words[1]
                if line_words[0] == 'region' : region = line_words[1]
                if line_words[0] == 'TxSource' : tx_source = line_words[1] 
    except Exception as e:
        print(e)

    print("Graphing data for", year, month)
    list_of_files = sorted(glob.glob(LOG_DIR ~ 'R' + str(year) + '%02d' % month + '*.csv'))
    if filenames == "" : filenames = list_of_files
    # print(filenames)


    frames = []
    # date_parser = pd.to_datetime

    # Collect the data from the RMOB .csv files
    for filename in filenames :
        # df = pd.read_csv(filename, parse_dates={ 'datetime': ['Y', 'M', 'D', 'h', 'm', 's']})
        df = pd.read_csv(filename)
        # df = pd.read_csv(filename, parse_dates={ 'year': ['Y'], 'month': ['M'], 'day': ['D'], 'hour': ['h'], 'minute': ['m'], 'seconds': ['s']})
        #print(df['h'].value_counts())
        #print(df['D'].value_counts())

        frames.append(df)

    result = pd.concat(frames)
    # print(result)

    # Get dates and hours from data frames
    days = result['D']
    hours = result['h']
    months = result['M']
    years = result['Y']

    data = result.groupby(["D", "h"]).size().unstack(fill_value=0).stack()
    pd.set_option("display.max_rows", None, "display.max_columns", None)
    # print(data)

    year = np.unique(years.to_numpy())[0]

    months = np.unique(months.to_numpy())
    month_string = ""
    for month in months : month_string += (datetime.date(1900, month, 1).strftime('%B') + " ")

    days = np.unique(days.to_numpy())
    # print(days)
    hours = np.unique(hours.to_numpy())


    data_for_mesh = data.to_numpy()
    data_for_mesh = np.reshape(data_for_mesh, (len(days), len(hours)))

    # Find missing days from missing log files
    missing_days = set(range(1, monthrange(year, month)[1])) - set(days)
    print("Missing days", missing_days)

    zeros_row = np.zeros((1, 24))
    print(zeros_row.shape)
    # data_for_mesh = np.insert(data_for_mesh, 3, zeros_row, 0)

    print(data_for_mesh, data_for_mesh.shape)



    # Set the z-max for the colormesh plot based on 3 standard deviations above the mean
    data_mean = np.mean(data_for_mesh)
    data_std = np.std(data_for_mesh)
    if graph_zlimit == 0 : data_vmax = data_mean + (3 * data_std)
    else : data_vmax = graph_zlimit


    x_range = np.arange(days[0], days[0] + len(days) + 1)
    y_range = np.arange(hours[0], hours[0] + len(hours) + 1)

    print(x_range, y_range)

    fig = plt.figure(figsize=(12,9))
    ax = fig.add_subplot(111)
    ax.set_facecolor('0.0')
    ax.set_title('Radio Meteor Detections ' + str(days[0]) + "-" + str(days[-1]) + " " + str(month_string) + str(year) + " (" + tx_source + " -> " + region + " " + country + ")\n", fontsize=16)
    qmesh = ax.pcolormesh(x_range, y_range, data_for_mesh.transpose(), cmap='gnuplot', vmin=0, vmax=data_vmax)  # jet and terrain look good too
    colour_bar = fig.colorbar(qmesh,ax=ax)
    colour_bar.set_label("Hourly Meteor Count")
    # ax.axis('tight')
    ax.set_xlabel("Day of month")
    ax.set_ylabel("Hour of day (UT)")
    plt.gca().invert_yaxis()
    plt.xticks(np.arange(1, monthrange(year, month)[1]+1))

    # Loop over data dimensions and create text annotations.
    for i in range(len(days)):
        for j in range(len(hours)):
            text = ax.text(i+days[0]+0.2, j+0.8, data_for_mesh[i, j], ha="left", va="bottom", color="black", fontsize=8)

    # Limit values
    # data_for_mesh[data_for_mesh > 60] = 60

    if save_image :
        image_filename = 'Radio Meteor Detections ' + str(year) + "-" + '%02d' % month
        plt.savefig(image_filename.replace(" ", "_"))
    else:
        plt.show()

    day_data = result['D'].value_counts().sort_index()
    # day_data = np.unique(day_data.to_numpy())
    #fig = plt.figure(figsize=(12,9))
    #ax = fig.add_subplot(111)
    #qmesh = ax.pcolormesh(np.arange(6), np.arange(2), day_data, cmap='gnuplot')
