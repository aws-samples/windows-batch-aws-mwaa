#!/usr/bin/env bash

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Script to delete the infrastructure

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

if [[ ! -f "$SCRIPT_DIR/.config" ]]; then
	echo "No Config found, exiting." && exit -1
fi

source $SCRIPT_DIR/.config

echo "Deleting the CloudFormation stack $ECS_STACK_NAME"
aws cloudformation delete-stack \
	--stack-name $ECS_STACK_NAME

echo "Deleting the CloudFormation stack $MWAA_STACK_NAME"
aws cloudformation delete-stack \
	--stack-name $MWAA_STACK_NAME

echo "Removing Bucket $ECS_BUCKET_NAME"
aws s3 rb s3://$ECS_BUCKET_NAME --force

echo "Removing Bucket $MWAA_BUCKET_NAME"
aws s3 rb s3://$MWAA_BUCKET_NAME --force

rm  "$SCRIPT_DIR/.config"