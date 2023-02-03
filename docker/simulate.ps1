# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Powershell script to wrap simulation octave script and interact with S3.

if ($args.count -ne 7){
    Write-Error "Usage: simulate.ps1 <frame_size> <num_frames> <EbN0dB> <snr_index> <rand_seed> <s3_bucket> <s3_prefix>" 
    exit 1
}
$frame_size=$args[0]
$num_frames=$args[1]
$EbN0dB=$args[2]
$snr_index=$args[3]
$rand_seed=$args[4]
$s3_bucket=$args[5]
$s3_prefix=$args[6] 

$file_prefix="sim_results_"

# Initialize
& "C:/workdir/bootstrap.ps1"

# Run Simulation, creates a file locally with results
cd "C:/workdir/"
C:/octave/mingw64/bin/octave-cli.exe "C:/workdir/simulate.m" $frame_size $num_frames $EbN0dB $snr_index $rand_seed

# Upload results file to S3
Write-S3Object -BucketName $s3_bucket -File "${file_prefix}${rand_seed}.mat" -Key "${s3_prefix}/${file_prefix}${rand_seed}.mat"
