#!/bin/bash

# shell script to create images from a detection

here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

source $HOME/vMeteorRadio/bin/activate
source $here/config.ini

pushd $LOGDIR/../Captures

if [ ! -f $1 ] ; then 
    echo "file not available"
else
    python $SRCDIR/analyse_detection.py -s -n -3 $1
fi 
popd