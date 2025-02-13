#!/bin/bash

load=$1
options=$2
workers=$3

if [ -z "$1" ]; then # check arg1
    load=10
fi

if [ -z "$2" ]; then # check arg2
    options=""
fi

if [ -z "$3" ]; then # check arg3
    workers=1
fi

chaosd attack stress cpu --load=${load} --options=${workers} --workers=${workers} 