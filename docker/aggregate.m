% Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
% SPDX-License-Identifier: MIT-0

% Aggregate bit errors into a joint file and create a Plot

% Parse Input
args = argv();
if length(args) ~= 2
  printf('Usage: aggregate.m num_tasks results_folder');
  exit(1);
end
file_prefix='sim_results_';
max_num_snr = 30;

num_tasks = str2num(args{1});
results_folder = args{2};
snr_vec = nan(max_num_snr, 1);
bit_error_vec = zeros(max_num_snr, 1);
num_bits_vec =  zeros(max_num_snr, 1);
tasks_per_snr_vec = zeros(max_num_snr, 1);

for tt=0:(num_tasks-1)
  load([ results_folder , '/', file_prefix, num2str(tt), '.mat' ]);
  if snr_index+1 > max_num_snr
    snr_vec = [snr_vec, nan(max_num_snr, 1)];
    bit_error_vec = [bit_error_vec, zeros(max_num_snr, 1)];
    num_bits_vec = [num_bits_vec, zeros(max_num_snr, 1)];
    tasks_per_snr_vec = [tasks_per_snr_vec, zeros(max_num_snr, 1)];
  end
  snr_vec(snr_index+1) = EbN0dB;
  bit_error_vec(snr_index+1) = bit_error_vec(snr_index+1) + BitErrors;
  num_bits_vec(snr_index+1) = num_bits_vec(snr_index+1) + NumBits;
  tasks_per_snr_vec(snr_index+1) = tasks_per_snr_vec(snr_index+1) +1;
end

bit_error_vec(isnan(snr_vec)) = [];
num_bits_vec(isnan(snr_vec)) = [];
tasks_per_snr_vec(isnan(snr_vec)) = [];
snr_vec(isnan(snr_vec)) = [];

ber_vec = bit_error_vec ./ num_bits_vec;

semilogy(snr_vec, ber_vec, '-o');
grid on;
title('Bit Error Rate as function on SNR');
xlabel ('Signal to Noise Ratio [dB]');
ylabel ('Bit Error Rate');
print('results.png', '-dpng');

save('results.mat', 'bit_error_vec', 'num_bits_vec', 'ber_vec', 'snr_vec', 'tasks_per_snr_vec');