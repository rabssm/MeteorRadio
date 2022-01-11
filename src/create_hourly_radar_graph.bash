#!/usr/bin/env bash

rm -f ~/html/Radio_Meteor_Detections*`date "+%m" --date='2 months ago'`.png

pushd ~/html/ && nice python ~/source/MeteorRadar/src/monthly_graph.py -s -m `date "+%m"` && popd

# pushd ~/html/ && nice python ~/source/MeteorRadar/src/monthly_graph.py -s -m `date "+%m" --date='last month'` && popd

# Create last months graph only on the 1st day of each month
if [ `date '+%d'` == 01 ]
then
    pushd ~/html/ && nice python ~/source/MeteorRadar/src/monthly_graph.py -s -m `date "+%m" --date='last month'` && popd
fi
