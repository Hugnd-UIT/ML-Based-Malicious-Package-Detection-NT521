#!/bin/bash

sudo apt-get update
sudo apt-get install -y python3 python3-pip
sudo apt-get install -y bpfcc-tools linux-headers-$(uname -r)
sudo apt-get install -y linux-tools-$(uname -r)
bpftool --version
uname -r
sudo apt-get install -y bpftrace
bpftrace --version
pip3 install virtualenv --break-system-packages