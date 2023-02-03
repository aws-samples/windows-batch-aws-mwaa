# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Powershell script to wrap simulation octave script and interact with S3.

if ($args.count -ne 4){
    Write-Error "Usage: aggregate.ps1 <num_tasks> <s3_bucket> <s3_task_result_prefix> <s3_aggregate_result_prefix>" 
    exit 1
}
$num_tasks=$args[0]
$s3_bucket=$args[1]
$s3_task_result_prefix=$args[2] 
$s3_aggregate_result_prefix=$args[3] 

$file_prefix="sim_results_"

# Initialize
& "C:/workdir/bootstrap.ps1"

# Download Results
cd "C:/workdir/"
Read-S3Object -BucketName $s3_bucket -KeyPrefix ${s3_task_result_prefix} -Folder "results"
C:/octave/mingw64/bin/octave-cli.exe "C:/workdir/aggregate.m" $num_tasks "results"
# Upload results file to S3
Write-S3Object -BucketName $s3_bucket -File "results.mat" -Key "${s3_aggregate_result_prefix}/results.mat"
Write-S3Object -BucketName $s3_bucket -File "results.png" -Key "${s3_aggregate_result_prefix}/results.png"
