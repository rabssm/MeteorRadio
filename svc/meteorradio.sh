#!/bin/bash

# copyright Mark McIntyre, 2023-

here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd $here
source $HOME/vMeteorRadio/bin/activate
source $here/config.ini
logfile=$LOGDIR/meteor_radar-$(date +%Y%m%d-%H%M%S).log 
$HOME/vMeteorRadio/bin/python $SRCDIR/meteor_radar.py -c $VERBOSE -s $SNR -g $GAIN > $logfile
