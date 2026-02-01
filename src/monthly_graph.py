import re
import pandas as pd
import argparse
from matplotlib import pyplot as plt
import numpy as np
import datetime
import os
import glob
from calendar import monthrange

DATA_DIR =  os.path.expanduser('~/radar_data/')
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
    except Exception as e :
        print(e)

    print("Graphing data for", year, month)
    list_of_files = sorted(glob.glob(LOG_DIR + 'R' + str(year) + '%02d' % month + '*.csv'))
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

    # ------------------------------------------------------------
    # Build a complete (day × hour) grid for the whole month
    # ------------------------------------------------------------

    days_in_month = monthrange(year, month)[1]
    all_days = np.arange(1, days_in_month + 1)
    all_hours = np.arange(0, 24)

    # Group data and reindex to include missing days/hours
    data = (
        result
        .groupby(["D", "h"])
        .size()
        .unstack(fill_value=0)
        .reindex(index=all_days, columns=all_hours, fill_value=0)
    )

    data_for_mesh = data.to_numpy()

    # ------------------------------------------------------------
    # Z-axis scaling
    # ------------------------------------------------------------

    data_mean = np.mean(data_for_mesh)
    data_std = np.std(data_for_mesh)

    if graph_zlimit == 0:
        data_vmax = data_mean + (3 * data_std)
    else:
        data_vmax = graph_zlimit

    # ------------------------------------------------------------
    # Plot
    # ------------------------------------------------------------

    x_range = np.arange(1, days_in_month + 2)   # +1 for pcolormesh edges
    y_range = np.arange(0, 25)                  # 24 hours + edge

    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111)
    ax.set_facecolor('0.0')

    ax.set_title(
        f"Radio Meteor Detections 1–{days_in_month} "
        f"{datetime.date(1900, month, 1).strftime('%B')} {year} "
        f"({tx_source} → {region} {country})\n",
        fontsize=16
    )

    qmesh = ax.pcolormesh(
        x_range,
        y_range,
        data_for_mesh.T,
        cmap='gnuplot',
        vmin=0,
        vmax=data_vmax
    )

    colour_bar = fig.colorbar(qmesh, ax=ax)
    colour_bar.set_label("Hourly Meteor Count")

    ax.set_xlabel("Day of month")
    ax.set_ylabel("Hour of day (UT)")
    ax.set_xticks(all_days)
    ax.set_yticks(all_hours)
    ax.invert_yaxis()

    # ------------------------------------------------------------
    # Cell annotations
    # ------------------------------------------------------------

    for day_idx, day in enumerate(all_days):
        for hour_idx, hour in enumerate(all_hours):
            value = data_for_mesh[day_idx, hour_idx]
            if value > 0:
                ax.text(
                    day + 0.1,
                    hour + 0.8,
                    value,
                    ha="left",
                    va="bottom",
                    fontsize=8,
                    color="black"
                )

    # ------------------------------------------------------------
    # Output
    # ------------------------------------------------------------

    if save_image:
        image_filename = f"Radio_Meteor_Detections_{year}_{month:02d}.png"
        plt.savefig(image_filename)
    else:
        plt.show()

    day_data = result['D'].value_counts().sort_index()
    # day_data = np.unique(day_data.to_numpy())
    #fig = plt.figure(figsize=(12,9))
    #ax = fig.add_subplot(111)
    #qmesh = ax.pcolormesh(np.arange(6), np.arange(2), day_data, cmap='gnuplot')
