#!/usr/bin/env bash

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Script to deploy infrastructure

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

if [[ ! -f "$SCRIPT_DIR/.config" ]]; then
	cat > $SCRIPT_DIR/.config <<-EOF
	export ECS_STACK_NAME="ecs-stack"
	export MWAA_STACK_NAME="mwaa-stack"
	export ECS_BUCKET_NAME="ecs-bucket-`openssl rand -hex 8`"
	export MWAA_BUCKET_NAME="mwaa-bucket-`openssl rand -hex 8`"
	EOF

	source $SCRIPT_DIR/.config

	REGION=$(aws ec2 describe-availability-zones --output text --query 'AvailabilityZones[0].[RegionName]')
	echo "Creating ECS Bucket for Simulation Results ($ECS_BUCKET_NAME)"
	aws s3api create-bucket --bucket $ECS_BUCKET_NAME --create-bucket-configuration "LocationConstraint=$REGION"
	aws s3api put-public-access-block \
    --bucket $ECS_BUCKET_NAME \
    --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

	echo "Creating MWAA Bucket for DAGs ($MWAA_BUCKET_NAME)"
	aws s3api create-bucket --bucket $MWAA_BUCKET_NAME --create-bucket-configuration "LocationConstraint=$REGION"
	aws s3api put-public-access-block \
		--bucket $MWAA_BUCKET_NAME \
		--public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
fi

source $SCRIPT_DIR/.config

echo "Uploading dag files to MWAA Bucket"
find "$SCRIPT_DIR/dags" -iname '*.py' -exec aws s3 cp {} s3://${MWAA_BUCKET_NAME}/dags/ \;

echo "Deploying Stack \"$ECS_STACK_NAME\" ..."
aws cloudformation deploy \
		--stack-name $ECS_STACK_NAME \
		--template-file "$SCRIPT_DIR/cloudformation/ecs.yaml" \
		--capabilities "CAPABILITY_IAM" "CAPABILITY_NAMED_IAM" \
		--parameter-overrides \
				"EcsBucketName=$ECS_BUCKET_NAME"

echo "Deploying Stack \"$MWAA_STACK_NAME\" ..."
aws cloudformation deploy \
		--stack-name $MWAA_STACK_NAME \
		--template-file "$SCRIPT_DIR/cloudformation/mwaa.yaml" \
		--capabilities "CAPABILITY_IAM" "CAPABILITY_NAMED_IAM" \
		--parameter-overrides \
				"AirflowBucketName=${MWAA_BUCKET_NAME}"

echo "Airflow WebUI URL:"
AirflowWebServerDns=$(aws cloudformation describe-stacks \
		--stack-name $MWAA_STACK_NAME \
		--output text \
		--query "Stacks[0].Outputs[?OutputKey=='MwaaWebserverUrl'].OutputValue")
echo "https://$AirflowWebServerDns"
