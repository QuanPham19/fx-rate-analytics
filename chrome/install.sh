#!/bin/bash
set -eux
apt-get install -y wget
wget -qO /tmp/google-chrome-stable_current_amd64.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
dpkg -i /tmp/google-chrome-stable_current_amd64.deb
apt-get install -y -f
rm /tmp/google-chrome-stable_current_amd64.deb
apt-get clean
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*