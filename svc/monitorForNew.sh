#!/bin/bash

# shell script to monitor for new detections

here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

source $here/config.ini

cd $LOGDIR
mkdir -p done
ls -1tr 20*.csv | tail -2 | while read i ; do 
    if [[ -f done/$i ]] ; then
        diff $i done/$i > /dev/null
        if [ $? == 1 ] ; then
            yr=${i:0:4}
            mth=${i:5:8}
            targname="s3://mjmm-rawradiodata/raw/event_log_${yr}${mth}"
            /usr/local/bin/aws s3 cp $i $targname
            cp $i done/
        fi
    else
        yr=${i:0:4}
        mth=${i:5:8}
        targname="s3://mjmm-rawradiodata/raw/event_log_${yr}${mth}"
        /usr/local/bin/aws s3 cp $i $targname
        cp $i done/
    fi 
done 
cd ../Captures
latestdir=$(ls -1trd 20* | tail -1)
ls -1tr $latestdir/SMP*.npz | tail -1 | while read i ; do 
    donelist=$LOGDIR/uploaded.txt
    if [ -f $donelist ] ; then
        grep $i $donelist > /dev/null
        if [ $? == 1 ] ; then 
            targname="s3://mjmm-rawradiodata/tmp/$(basename $i)"
            /usr/local/bin/aws s3 cp $i $targname
            echo $i >> $donelist
        fi 
    else
        echo $i    
    fi 
done 
source ~/source/tackley-tools/config.ini > /dev/null 2>&1

currdt=$(date +%Y-%m-%d,)
currhr=$(date +%Y-%m-%d,%H)
lastcsv=$(ls -1 $LOGDIR/20*.csv | tail -1)
dailyct=$(egrep "$currdt" $lastcsv | wc -l)
hourlyct=$(egrep "$currhr" $lastcsv | wc -l)
/usr/bin/mosquitto_pub -h $BROKER -u $USERNAME -P $PASSWORD -t meteorcams/radiopi/hourly -m $hourlyct
/usr/bin/mosquitto_pub -h $BROKER -u $USERNAME -P $PASSWORD -t meteorcams/radiopi/daily -m $dailyct
