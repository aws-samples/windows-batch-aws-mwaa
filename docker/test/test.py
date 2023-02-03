#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Test the Octave Scripts End-to-End

import os
import math

num_tasks =  10
num_frames = 100
frame_size = 1000
EbN0dB = [-2.0, 4.0, 10.0]

octave_bin = "/Applications/Octave-6.2.0.app/Contents/Resources/usr/bin/octave-octave-app@6.0.90"

# Change to directory of this script
abs_path = os.path.abspath(__file__)
dir_name = os.path.dirname(abs_path)
os.chdir(dir_name)


tasks_per_snr = num_tasks // len(EbN0dB)
for i in range(num_tasks):
    snr_index = min( i // tasks_per_snr, len(EbN0dB)-1 )
    os.system( octave_bin + " " + "../simulate.m" + " " + str(num_frames) + " " + str(frame_size) + " " + str(EbN0dB[snr_index]) + " " + str(snr_index) + " " + str(i) )


# Aggregate Simulation
os.system( octave_bin + " " + "../aggregate.m" + " " + str(num_tasks) + " .")
