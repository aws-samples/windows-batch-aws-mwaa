% Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
% SPDX-License-Identifier: MIT-0

% Run a Bit Error Rate Simulation
% Further Reading:
% https://en.wikipedia.org/wiki/Bit_error_rate
% https://en.wikipedia.org/wiki/Additive_white_Gaussian_noise
% https://en.wikipedia.org/wiki/Eb/N0

% Parse Input
args = argv();

if length(args) ~= 5
  printf('Usage: simulate.m frame_size num_frames EbN0dB rand_seed');
  exit(1);
end

frame_size = str2num(args{1});
num_frames = str2num(args{2});
EbN0dB = str2num(args{3});
snr_index = str2num(args{4});
rand_seed = str2num(args{5});
file_prefix='sim_results_';

% Seed Random Number Generator
randn('seed',rand_seed);
rand('seed',rand_seed)

% Simulate BPSK transmission over AWGN channel
EbN0 = 10.^(EbN0dB/10);
N0 = 1./EbN0;
sigma = sqrt(N0/2);

BitErrors=0;
NumBits=0;

for nn=1:num_frames
  txBits = msg = randi([0 1],frame_size,1); 
  s = 1 - 2 * txBits; 
  r = s + sigma * randn(frame_size,1); 
  s_hat = sign(r);
  rxBits = (1-s_hat)/2;
  BitErrors = BitErrors + sum(rxBits ~= txBits);
  NumBits = NumBits + frame_size;
end

printf( 'Bit Errors: %d\n', BitErrors);

printf( 'Saving results to file.\n');
save([file_prefix, num2str(rand_seed), '.mat'], 'NumBits', 'BitErrors', 'EbN0dB', 'rand_seed', 'snr_index');