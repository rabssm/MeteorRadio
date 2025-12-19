#!/bin/bash

# copyright Mark McIntyre, 2023-

# install meteorradio as a service

here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd $here

[ ! -d ~/.config/systemd/user/ ] && mkdir -p ~/.config/systemd/user/
cp meteorradio.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable meteorradio
 systemctl --user start meteorradio
