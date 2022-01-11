#!/usr/bin/env bash

# grep "Radar detection triggered.*$(date +%Y-%m-%d)" /var/log/user.log* | sed 's/^.*Radar detection triggered at //g' > /home/pi/radar_data/Logs/"$(date +%Y-%m-%d)".log

grep -a "Rad.* detection stats log .*$(date --date='yesterday' +%d\/%m\/%Y)" /var/log/user.log* | sed 's/^.*Rad.* detection stats log //g' > /home/pi/radar_data/Logs/"$(date --date='yesterday' +%Y-%m-%d)".stats
grep -a "Rad.* detection stats log .*$(date +%d\/%m\/%Y)" /var/log/user.log* | sed 's/^.*Rad.* detection stats log //g' > /home/pi/radar_data/Logs/"$(date +%Y-%m-%d)".stats

# awk '{sep="," ; print $1,sep,$2,sep,20*log($4)/log(10),sep,20*log($8)/log(10),sep,20*log($8)/log(10)-20*log($4)/log(10)}' ~/radar_data/Logs/"$(date +%Y-%m-%d)".log > /tmp/"$(date +%Y-%m-%d)".csv
# awk '{sep=","; graves=143050000; name="Richard Bassom"; rxlat="50.86"; rxlong="-1.78"; txsource="Graves"; timesync="NTP"; foff=-60; print name,sep,$1,sep,$2,sep,$6,sep,$4,sep,foff,sep,0,sep,$8,sep,rxlat,sep,rxlong,sep,txsource,sep,timesync,sep,$12,sep,($10*1e6)-graves-foff}' ~/radar_data/Logs/*.stats

# Create the monthly stats log csv files for last month and this month, and convert to xls. Note $12>15 restricts output SNR to >15 dB
awk '{sep=","; graves=143050000; name="Richard Bassom"; rxlat="50.86"; rxlong="-1.78"; txsource="Graves"; timesync="NTP"; foff=-60; print name,sep,$1,sep,$2,sep,$6,sep,$4,sep,2000+($10*1e6)-graves-foff,sep,0,sep,$8,sep,rxlat,sep,rxlong,sep,txsource,sep,timesync,sep,$12,sep,($10*1e6)-graves-foff}' ~/radar_data/Logs/"$(date --date='last month' +%Y-%m)"*.stats > /tmp/"$(date --date='last month' +%Y-%m)".csv
ssconvert /tmp/"$(date --date='last month' +%Y-%m)".csv ~/Desktop/"$(date --date='last month' +%Y-%m)".xls
rm /tmp/"$(date --date='last month' +%Y-%m)".csv

awk '{sep=","; graves=143050000; name="Richard Bassom"; rxlat="50.86"; rxlong="-1.78"; txsource="Graves"; timesync="NTP"; foff=-60; print name,sep,$1,sep,$2,sep,$6,sep,$4,sep,2000+($10*1e6)-graves-foff,sep,0,sep,$8,sep,rxlat,sep,rxlong,sep,txsource,sep,timesync,sep,$12,sep,($10*1e6)-graves-foff}' ~/radar_data/Logs/"$(date --date='this month' +%Y-%m)"*.stats > /tmp/"$(date --date='this month' +%Y-%m)".csv
ssconvert /tmp/"$(date --date='this month' +%Y-%m)".csv ~/Desktop/"$(date --date='this month' +%Y-%m)".xls
rm /tmp/"$(date --date='this month' +%Y-%m)".csv

# awk '$12>15 {sep=","; graves=143050000; name="Richard Bassom"; rxlat="50.86"; rxlong="-1.78"; txsource="Graves"; timesync="NTP"; foff=-60; print name,sep,$1,sep,$2,sep,$6,sep,$4,sep,foff,sep,0,sep,$8,sep,rxlat,sep,rxlong,sep,txsource,sep,timesync,sep,$12,sep,($10*1e6)-graves-foff}' ~/radar_data/Logs/"$(date +%Y-%m-%d)".stats
# awk '$12>15 {sep=","; graves=143050000; name="Richard Bassom"; rxlat="50.86"; rxlong="-1.78"; txsource="Graves"; timesync="NTP"; foff=-60; print name,sep,$1,sep,$2,sep,$6,sep,$4,sep,foff,sep,0,sep,$8,sep,rxlat,sep,rxlong,sep,txsource,sep,timesync,sep,$12,sep,($10*1e6)-graves-foff}' ~/radar_data/Logs/"$(date +%Y-%m-%d)".stats > /tmp/"$(date +%Y-%m-%d)".csv
# ssconvert /tmp/"$(date +%Y-%m-%d)".csv ~/Desktop/"$(date +%Y-%m-%d)".xls
