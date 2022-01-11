import datetime
import os
import signal
import argparse
import re
import glob


class Observation():

    def __init__(self, filename, observation_line, observation_time, instrument=None) :
        self.filename = filename
        self.instrument = instrument
        self.observation_line = observation_line
        self.observation_time = observation_time



def read_dates(filename) :
    global observation_list

    with open(filename) as fin :
        for line in fin:
            try:
                # split_line = line.split(', ')
                split_line = re.split(r'[;,\s]\s*', line)
                # print(split_line)

                # Check for UFO R05B25 format file
                if (split_line[0] == 'R05B25') :
                    instrument = split_line[6]
                    date_time_str = split_line[8] + '-' + split_line[9] + '-' + split_line[10] + ' ' + split_line[11] + ':' + split_line[12] + ':' + split_line[13]
                    date_from_file = datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S.%f')
                    observation_list.append(Observation(filename, line, date_from_file, instrument))
                    # print(date_from_file)

                # Check for UFO R91 format file
                elif (split_line[0] == 'R91') :
                    instrument = split_line[17]
                    date_time_str = split_line[1] + '-' + split_line[2] + '-' + split_line[3] + ' ' + split_line[4] + ':' + split_line[5] + ':' + split_line[6]
                    date_from_file = datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S.%f')
                    observation_list.append(Observation(filename, line, date_from_file, instrument))
                    # print(date_from_file)

                # Check for Radar RMOB format file
                elif (split_line[0] == 'RMOB') :
                    instrument = split_line[10] + "_RMOB"
                    date_time_str = split_line[1] + '-' + split_line[2] + '-' + split_line[3] + ' ' + split_line[4] + ':' + split_line[5] + ':' + split_line[6]
                    try: date_from_file = datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S.%f')
                    except ValueError:
                        date_from_file = datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')

                    observation_list.append(Observation(filename, line, date_from_file, instrument))
                    # print(date_from_file)

                # RADAR dates from radar .log files
                else:
                    instrument = "Ringwood_Radar"
                    date_time_str = split_line[0] + ' ' + split_line[1]
                    date_from_file = datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S.%f')
                    observation_list.append(Observation(filename, line, date_from_file, instrument))
                    # print(date_from_file)


            except Exception as e:
                # print(e)
                pass

    return



# Main program
if __name__ == "__main__":

    # construct the argument parser and parse the arguments
    ap = argparse.ArgumentParser(epilog="Example usage: python match_radar_visual.py ~/Desktop/Meteors/csv/2021/*2021*.csv ~/radar_data/Logs/2021-0*.log")
    ap.add_argument("files", type=str, nargs='+', help="Radar log and UFO csv files to analyse for matches.")
    ap.add_argument("-t", "--time", type=float, default=4.0, help="Max time difference between observations")
    ap.add_argument("-v", "--verbose", type=bool, default=False, help="Verbose")

    args = vars(ap.parse_args())

    files_for_matching = args['files']
    max_time_diff = args['time']
    verbose = args['verbose']
    # print(files_for_matching)

    observation_list = []
    previous_observation = None

    # Loop through the files and get observation times
    for file_for_matching in files_for_matching :
        read_dates(file_for_matching)

    # Sort all observations in time order
    observation_list.sort(key=lambda x: x.observation_time)

    for i, observation in enumerate(observation_list) :
        # If the observation is from the same instrument as the previous observation ignore it
        if (observation.instrument == observation_list[i-1].instrument) :
            previous_observation = None
            continue

        # Check the time difference between observations
        calculated_time_diff = (observation.observation_time-observation_list[i-1].observation_time).total_seconds()
        if abs(calculated_time_diff) < max_time_diff :
            if previous_observation is None : print()
            print(observation_list[i-1].observation_time, observation_list[i-1].instrument, "----->", observation.observation_time, observation.instrument, " Time_diff:", calculated_time_diff)
            if verbose:
                print("   Details:", observation_list[i-1].observation_line.strip('\n'))
                print("   Details:", observation.observation_line.strip('\n'))
            previous_observation = observation_list[i-1]
            # print(observation_list[i-1].observation_time, observation_list[i-1].instrument, "----->")
            # print(observation.observation_time, observation.instrument)
            # print()
        else : previous_observation = None

    #for observation in observation_list :
    #    print(observation.observation_time)
