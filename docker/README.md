# Disclaimer
This sample relies on a pre-build Docker Image, so all steps decribed here are optional.

# Prerequisites
In case you want to experiment and reproduce building the Docker Image, perform the following steps:
1. When deploying the [ECS CloudFormation template](/cloudformation/ecs.yaml)
    - specify the `RdpIp` (check e.g. https://ipinfo.io/)
    - specify an SSH Key for the `KeyName` parameter
    - do not not specify the `EcsContainerImageUrl` parameter (leave it blank)
2. Create ECR respository you can push your container to
    ```shell
    aws ecr create-repository --repository-name 'windows-octave'
    ```
This results in opening up access to the container instance and configure the the cluster to use the container repository you create in the next step.

The next section describes how you can build a container and push it to this repository.

# Create Container

## Get Access to the ECS Windows Container Instance
After you deployed the ECS stack but prior to running any simulations, you can [use
the SSH Key you specified to decode the RDP password](https://aws.amazon.com/premiumsupport/knowledge-center/retrieve-windows-admin-password/) in order to gain RDP access to the initial Container Instance of the cluster.
RDP is restricted to be accessed only from the `RdpIp` specified via the cluster instance security group.

## Build on the Windows Container Instance and push to remote ECR repository
```powershell
# Configure
$accountId = (Get-STSCallerIdentity).Account
$region = (Get-EC2InstanceMetadata -Category Region).SystemName
$ecrRepo = "windows-octave"
$tag = "latest"
$appName = "octave"

# Download GnuOctave and extract it to
$octaveVersion = "7.3.0"
wget "https://ftpmirror.gnu.org/octave/windows/octave-$octaveVersion-w64.zip" -UseBasicParsing -OutFile "./octave.zip"
Expand-Archive -Path "./octave.zip" -DestinationPath "./"

# Build
docker build -t $appName --build-arg OCTAVE_VERSION=$octaveVersion .

# Test locally (you need permissions to the S3 bucket)
docker run -it octave C:/workdir/simulate.ps1 100 100 0 0 0 ecs-task-io-bucket octave_sim/task_results
docker run -it octave C:/workdir/simulate.ps1 100 100 5 1 1 ecs-task-io-bucket octave_sim/task_results
docker run -it octave C:/workdir/simulate.ps1 100 100 9 2 2 ecs-task-io-bucket octave_sim/task_results
docker run -it octave C:/workdir/aggregate.ps1 3 ecs-task-io-bucket octave_sim/task_results octave_sim/aggregated_results

# Push to remote ECR respository
(Get-ECRLoginCommand).Password | docker login --username AWS --password-stdin "$accountId.dkr.ecr.$region.amazonaws.com"
docker tag ${appName} "$accountId.dkr.ecr.$region.amazonaws.com/${ecrRepo}:$tag"
docker push "$accountId.dkr.ecr.$region.amazonaws.com/${ecrRepo}:$tag"
```