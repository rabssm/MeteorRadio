#!/bin/bash

# Script to create graphs and data files for my website

here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

source $HOME/vMeteorRadio/bin/activate
source $here/config.ini

pushd $LOGDIR
python $SRCDIR/monthly_graph.py -s -m $(date +%m)
[ $(date '+%d') == 01 ] && python $SRCDIR/monthly_graph.py -s -m $(date +%m --date='last month')
