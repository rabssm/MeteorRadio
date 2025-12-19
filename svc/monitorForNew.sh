#!/bin/bash

# shell script to monitor for new detections

here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

source $HOME/vMeteorRadio/bin/activate
source $here/config.ini

cd $LOGDIR/../Captures

watchmedo shell-command --patterns='*.npz' --recursive --command '$SRCDIR../srv/createImages.sh "${watch_src_path}"' .