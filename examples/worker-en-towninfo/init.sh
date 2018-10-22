#!/bin/sh

export HOST=$(hostname -I | grep -Po '10.0.[\d.]+')

while true; do python run.py; done
