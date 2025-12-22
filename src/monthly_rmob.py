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
    ap.add_argument("log_file_directory", type=str, nargs='?', default=LOG_DIR, help="Directory containing the log files")
    ap.add_argument("-m", "--month", type=int, default=datetime.datetime.now().month, help="Month of graph")
    ap.add_argument("-y", "--year", type=int, default=datetime.datetime.now().year, help="Year of graph")
    ap.add_argument("-o", "--observer", type=str, default="Observer", help="Observer's name")
    ap.add_argument("-d", "--directory", type=str, default=LOG_DIR, help="Directory to output RMOB files. Default is " + LOG_DIR)
    ap.add_argument("-f", "--footer", type=str, default=None, help="Footer file for appending to end of RMOB <observer_name>_mmyyyrmob.TXT file")

    args = vars(ap.parse_args())

    log_dir = args['log_file_directory']
    month = args['month']
    year = args['year']
    observer_name = args['observer']
    output_dir = args['directory'] + '/'
    footer_file_name = args['footer']

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
                # if line_words[0] == 'observer' : observer_name = line_words[1] 
    except Exception as e :
        print(e)

    print("Getting data for", year, month, "from", log_dir)
    list_of_files = sorted(glob.glob(log_dir + 'R' + str(year) + '%02d' % month + '*.csv'))
    filenames = list_of_files
    # print(filenames)

    frames = []

    # Collect the data from the RMOB .csv files
    for filename in filenames :
        df = pd.read_csv(filename)
        frames.append(df)

    result = pd.concat(frames)

    # Get dates and hours from data frames
    days = result['D']
    hours = result['h']
    months = result['M']
    years = result['Y']

    data = result.groupby(["D", "h"]).size().unstack(fill_value=0).stack()
    pd.set_option("display.max_rows", None, "display.max_columns", None)

    year = np.unique(years.to_numpy())[0]

    months = np.unique(months.to_numpy())
    month_string = ""
    for month in months : month_string += (datetime.date(1900, month, 1).strftime('%B') + " ")

    days = np.unique(days.to_numpy())
    hours = np.unique(hours.to_numpy())

    data_for_mesh = data.to_numpy()
    data_for_mesh = np.reshape(data_for_mesh, (len(days), len(hours)))
    # print(data_for_mesh)


    ###############################################
    # Output in RMOB-YYMM.DAT 3 column format yyyymmddhh,hh,meteor-count
    filename_date = datetime.date(year,month,1)
    filename = "RMOB-" + filename_date.strftime("%y%m") + ".DAT"
    print("Writing to file:", output_dir + filename)
    file = open(output_dir + filename, 'w')
    
    for day in days :
        for hour in hours :
            try: 
                file.write("%02d%02d%02d%02d,%02d,%d\n" % (year, month, day, hour, hour, data_for_mesh[day-days[0],hour]))
                # print("%02d%02d%02d%02d,%02d,%d" % (year, month, day, hour, hour, data_for_mesh[day-1,hour]))
            except Exception : pass
    file.close()


    ###############################################
    # Output in RMOB <observer_name>_052022rmob.TXT
    filename = observer_name + "_" + filename_date.strftime("%m%Y") + "rmob.TXT"
    print("Writing to file:", output_dir + filename)
    file = open(output_dir + filename, 'w')

    # Create the top line of the file
    top_line = filename_date.strftime("%b").lower() + "|"
    for hour in range(0, 24): top_line += (" %02dh|" % (hour))
    file.write(top_line + "\n")

    # Find missing days from missing log files
    missing_days = set(range(1, monthrange(year, month)[1])) - set(days)
    print("Missing days", missing_days)

    # Output the meteor counts
    for index in range(1,32) :
        out_line = " %02d|" %(index)
        for hour in range(0, 24) :
            # If there are missing days, or no data on some days, set "???""
            if index in missing_days or index > monthrange(year, month)[1] : out_line += "??? |"
            elif datetime.datetime(year, month, index, hour) > datetime.datetime.now() : out_line += "??? |"

            else:
                try: 
                    meteor_count = data_for_mesh[index-days[0], hour]
                    out_line += " %-3d|" %(meteor_count)
                except:
                    out_line += "??? |"

        out_line += "\n"
        file.write(out_line)

    # Append the text in the footer file if one exists
    if footer_file_name is not None :
        try:
            footer_file = open(footer_file_name, 'r')
            for line in footer_file :
                file.write(line)
            footer_file.close()
        except Exception as e : print(e)


    file.close()
