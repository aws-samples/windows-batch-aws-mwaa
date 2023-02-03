#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import logging
import time
import datetime
from typing import Dict

import boto3

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.ecs import EcsRunTaskOperator
from airflow.models.param import Param
from airflow.utils.dates import days_ago

# ---------------------------------- Helper Functions

def get_cluster_name(cluster_resource_tag: str) -> str:
    ecs_client = boto3.client("ecs")
    response_clusters = ecs_client.list_clusters()
    for cluster in response_clusters["clusterArns"]:
        response_tags = ecs_client.list_tags_for_resource(resourceArn=cluster)
        for tag in response_tags["tags"]:
            if tag["key"] == cluster_resource_tag and tag["value"] == "true":
                return ecs_client.describe_clusters(clusters=[cluster])["clusters"][0][
                    "clusterName"
                ]


def get_asg_name(cluster_resource_tag: str) -> str:
    autoscaling_client = boto3.client("autoscaling")
    response = autoscaling_client.describe_auto_scaling_groups()

    for group in response["AutoScalingGroups"]:
        for tag in group["Tags"]:
            if tag["Key"] == cluster_resource_tag and tag["Value"] == "true":
                return group["AutoScalingGroupName"]


def get_task_definition_properties(cluster_resource_tag: str) -> Dict:
    ecs_client = boto3.client("ecs")
    response_list = ecs_client.list_task_definitions()
    for task in response_list["taskDefinitionArns"]:
        response = ecs_client.list_tags_for_resource(resourceArn=task)
        for tag in response["tags"]:
            if tag["key"] == cluster_resource_tag and tag["value"] == "true":
                task_definition = ecs_client.describe_task_definition(
                    taskDefinition=task
                )
                return {
                    "taskDefinitionArn": task,
                    "taskCpu": task_definition["taskDefinition"]["cpu"],
                    "taskMemory": task_definition["taskDefinition"]["memory"],
                }


def get_task_definition_arn(cluster_resource_tag: str) -> str:
    ecs_client = boto3.client("ecs")
    response_list = ecs_client.list_task_definitions()
    for task in response_list["taskDefinitionArns"]:
        response = ecs_client.list_tags_for_resource(resourceArn=task)
        for tag in response["tags"]:
            if tag["key"] == cluster_resource_tag and tag["value"] == "true":
                return str(task)


def get_asg_resource_properties(cluster_resource_tag: str) -> Dict:
    cpus = 0
    mem = 0
    asg_name = get_asg_name(cluster_resource_tag)
    autoscaling_client = boto3.client("autoscaling")
    ec2_client = boto3.client("ec2")
    asg_response = autoscaling_client.describe_auto_scaling_groups(
        AutoScalingGroupNames=[asg_name]
    )
    instance_ids = []
    for i in asg_response["AutoScalingGroups"]:
        for k in i["Instances"]:
            instance_ids.append(k["InstanceId"])
    ec2_response = ec2_client.describe_instances(
        InstanceIds=instance_ids,
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}],
    )
    for reservations in ec2_response["Reservations"]:
        for instances in reservations["Instances"]:
            type = instances["InstanceType"]
            response = ec2_client.describe_instance_types(InstanceTypes=[type])
            for instance_types in response["InstanceTypes"]:
                cpus += instance_types["VCpuInfo"]["DefaultVCpus"]
                mem += instance_types["MemoryInfo"]["SizeInMiB"]
    return {"clusterCpu": str(cpus * 1024), "clusterMemory": str(mem)}


def wait_for_container_instances(cluster_resource_tag, desired_count, timeout=300):
    ecs_client = boto3.client("ecs")
    start_time = time.time()
    instances_online = False
    while not instances_online:
        response = ecs_client.list_container_instances(
            cluster=get_cluster_name(cluster_resource_tag), status="ACTIVE"
        )
        print(
            f'{len(response["containerInstanceArns"])} container instances are active and registered with the cluster'
        )
        if len(response["containerInstanceArns"]) == desired_count:
            instances_online = True
            print(
                f"{desired_count} container instances are active and registered with the cluster"
            )
            break
        elif (time.time() - start_time) > timeout:
            raise TimeoutError(
                f"Timeout of {timeout} seconds exceeded while waiting for instances to be active and registered with the cluster"
            )
        else:
            time.sleep(30)


def update_scaling_group(
    cluster_resource_tag: str, desired_capacity: int, timeout: int = 180
) -> None:
    group_name = get_asg_name(cluster_resource_tag)
    desired_capacity = desired_capacity

    autoscaling_client = boto3.client("autoscaling")
    response = autoscaling_client.update_auto_scaling_group(
        AutoScalingGroupName=group_name, DesiredCapacity=desired_capacity
    )
    response = autoscaling_client.describe_auto_scaling_groups(
        AutoScalingGroupNames=[group_name]
    )

    desired_capacity = response["AutoScalingGroups"][0]["DesiredCapacity"]
    current_capacity = len(response["AutoScalingGroups"][0]["Instances"])

    while desired_capacity != current_capacity:
        response = autoscaling_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[group_name]
        )
        desired_capacity = response["AutoScalingGroups"][0]["DesiredCapacity"]
        current_capacity = len(response["AutoScalingGroups"][0]["Instances"])

        time.sleep(30)

    print(
        f"Successfully reached desired capacity of {desired_capacity} for group {group_name}."
    )


def scale_cluster_capacity(**kwargs: Dict) -> None:
    cluster_resource_tag = kwargs["cluster_resource_tag"]
    capacity = int(kwargs["desired_capacity"])
    timeout_asg = int(kwargs["timeout_asg"])
    timeout_ecs = int(kwargs["timeout_ecs"])
    print("Scale to desired capacity ", capacity)
    update_scaling_group(cluster_resource_tag, capacity, timeout_asg)
    print(
        "Finished with Auto Scaling Group update, waiting for ECS Control plane consistency"
    )
    wait_for_container_instances(
        cluster_resource_tag=cluster_resource_tag,
        desired_count=capacity,
        timeout=timeout_ecs,
    )
    task_definition_properties = get_task_definition_properties(cluster_resource_tag)
    asg_resource_properties = get_asg_resource_properties(cluster_resource_tag)
    simulate_tasks_concurrency = max(
        1,
        int(
            min(
                int(asg_resource_properties["clusterCpu"])
                / int(task_definition_properties["taskCpu"]),
                int(asg_resource_properties["clusterMemory"])
                / int(task_definition_properties["taskMemory"]),
            )
        ),
    )
    print("Setting simulation task concurrency to", simulate_tasks_concurrency)
    Variable.set("simulate_tasks_concurrency", str(simulate_tasks_concurrency))


def generate_params(**kwargs: Dict) -> Dict:
    num_tasks = int(kwargs["num_tasks"])
    num_frames = int(kwargs["num_frames"])
    frame_size = int(kwargs["frame_size"])
    EbN0dB = kwargs["EbN0dB"]
    EbN0dB = EbN0dB.strip("][").split(", ")
    EbN0dB = [float(e) for e in EbN0dB]
    s3_bucket = str(kwargs["s3_bucket"])
    s3_prefix_task_results = str(kwargs["s3_prefix_task_results"])
    cluster_container_name = str(kwargs["cluster_container_name"])
    tasks_per_snr = num_tasks // len(EbN0dB)
    simulate_tasks = []
    for i in range(num_tasks):
        snr_index = min(i // tasks_per_snr, len(EbN0dB) - 1)
        simulate_tasks.append(
            {
                "containerOverrides": [
                    {
                        "name": str(cluster_container_name),
                        "command": [
                            "C:/workdir/simulate.ps1",
                            str(num_frames),
                            str(frame_size),
                            str(EbN0dB[snr_index]),
                            str(snr_index),
                            str(i),
                            str(s3_bucket),
                            str(s3_prefix_task_results),
                        ],
                    },
                ],
            }
        )
    return simulate_tasks


# ---------------------------------- Airflow DAG

CLUSTER_RESOURCE_TAG_DEFAULT = "windows-batch-blog"

with DAG(
    dag_id="windows-batch-compute-dag",
    description="Scale an ECS cluster of MS Windows hosts",
    schedule_interval=None,
    start_date=days_ago(1),
    tags=[""],
    default_args={"retries": 3, "retry_delay": datetime.timedelta(seconds=60)},
    catchup=False,
    params={
        "num_tasks": Param(200, type="integer"),
        "num_frames": Param(300000, type="integer"),
        "frame_size": Param(4096, type="integer"),
        "EbN0dB": Param([0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 11.0, 12.0], type="array"),
        "s3_bucket": Param("CHANGE_TO_YOUR_BUCKET_NAME", type="string"),
        "s3_prefix_task_results": Param("sim/task_results", type="string"),
        "s3_prefix_aggregate_results": Param("sim/aggregate_results", type="string"),
        "cluster_container_name": Param("WindowsBatchContainer", type="string"),
        "cluster_scale_out_size": Param(6, type="integer"),
        "cluster_scale_in_size": Param(0, type="integer"),
        "cluster_scale_asg_timeout": Param(180, type="integer"),
        "cluster_scale_ecs_timeout": Param(600, type="integer"),
    },
) as dag:
    # Airflow Task to aggregate simulation results
    aggregate_task = EcsRunTaskOperator(
        dag=dag,
        task_id="aggregate",
        cluster=get_cluster_name(
            str(
                Variable.get(
                    "cluster_resource_tag", default_var=CLUSTER_RESOURCE_TAG_DEFAULT
                )
            )
        ),
        task_definition=get_task_definition_arn(
            str(
                Variable.get(
                    "cluster_resource_tag", default_var=CLUSTER_RESOURCE_TAG_DEFAULT
                )
            )
        ),
        aws_conn_id="aws_ecs",
        overrides={
            "containerOverrides": [
                {
                    "name": "{{ params.cluster_container_name }}",
                    "command": [
                        "C:/workdir/aggregate.ps1",
                        "{{ params.num_tasks }}",
                        "{{ params.s3_bucket }}",
                        "{{ params.s3_prefix_task_results }}",
                        "{{ params.s3_prefix_aggregate_results }}",
                    ],
                },
            ],
        },
    )
    # Airflow Task to parse and prepare parameters for simulation
    generate_params_task = PythonOperator(
        task_id="generate_params",
        python_callable=generate_params,
        op_kwargs={
            "num_tasks": "{{ params.num_tasks }}",
            "num_frames": "{{ params.num_frames }}",
            "frame_size": "{{ params.frame_size }}",
            "EbN0dB": "{{ params.EbN0dB }}",
            "s3_bucket": "{{ params.s3_bucket }}",
            "s3_prefix_task_results": "{{ params.s3_prefix_task_results }}",
            "cluster_container_name": "{{ params.cluster_container_name }}",
        },
        dag=dag,
    )
    # Airflow Task to run the actual payload simulation parallelized
    simulate_task = EcsRunTaskOperator.partial(
        dag=dag,
        task_id="simulate",
        cluster=get_cluster_name(
            str(
                Variable.get(
                    "cluster_resource_tag", default_var=CLUSTER_RESOURCE_TAG_DEFAULT
                )
            )
        ),
        task_definition=get_task_definition_arn(
            str(
                Variable.get(
                    "cluster_resource_tag", default_var=CLUSTER_RESOURCE_TAG_DEFAULT
                )
            )
        ),
        aws_conn_id="aws_ecs",
        max_active_tis_per_dag=int(
            Variable.get("simulate_tasks_concurrency", default_var=2)
        ),
    ).expand(overrides=generate_params_task.output)
    # Airflow Task to scale the ECS cluster out before simulation
    scale_out_task = PythonOperator(
        task_id="scale_out",
        python_callable=scale_cluster_capacity,
        op_kwargs={
            "cluster_resource_tag": str(
                Variable.get(
                    "cluster_resource_tag", default_var=CLUSTER_RESOURCE_TAG_DEFAULT
                )
            ),
            "desired_capacity": "{{ params.cluster_scale_out_size }}",
            "timeout_asg": "{{ params.cluster_scale_asg_timeout }}",
            "timeout_ecs": "{{ params.cluster_scale_ecs_timeout }}",
        },
        dag=dag,
    )
    # Airflow Task to scale the ECS cluster in after simulation
    scale_in_task = PythonOperator(
        task_id="scale_in",
        python_callable=scale_cluster_capacity,
        op_kwargs={
            "cluster_resource_tag": str(
                Variable.get(
                    "cluster_resource_tag", default_var=CLUSTER_RESOURCE_TAG_DEFAULT
                )
            ),
            "desired_capacity": "{{ params.cluster_scale_in_size }}",
            "timeout_asg": "{{ params.cluster_scale_asg_timeout }}",
            "timeout_ecs": "{{ params.cluster_scale_ecs_timeout }}",
        },
        dag=dag,
    )
    # Define DAG Task dependencies
    simulate_task.set_upstream(generate_params_task)
    simulate_task.set_upstream(scale_out_task)
    aggregate_task.set_upstream(simulate_task)
    scale_in_task.set_upstream(aggregate_task)