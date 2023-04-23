# Disclaimer
This sample relies on a pre-build Docker Image stored in a [public ECR repository](https://gallery.ecr.aws/o1d7m8a4/windows-batch-aws-mwaa). Consequently, all steps decribed below are optional and can be used to recreate this image. More generally, this also provides a step-by-step tutorial on building and testing your own Windows Container Images that interact with AWS Services  

# Prerequisites
To build and run your own container image, perform the following steps:
1. When deploying the [ECS CloudFormation template](/cloudformation/ecs.yaml)
    - specify the `RdpIp` (check e.g. https://ipinfo.io/)
    - specify an SSH Key for the `KeyName` parameter
    - explicitly change the `EcsContainerImageUrl` parameter to an empty string
2. Create ECR respository you can push your container to
    ```shell
    aws ecr create-repository --repository-name 'windows-octave'
    ```
This results in opening up RDP access to the container instances and configure the cluster to use the container repository you create in the next step.

The next section describes how you can build a container and push it to this repository.

# Create Container Image

## Get Access to the ECS Windows Container Instance
After you deployed the ECS stack but prior to running any simulations, you can [use
the SSH Key you specified to decode the RDP password](https://aws.amazon.com/premiumsupport/knowledge-center/retrieve-windows-admin-password/) in order to gain RDP access to the initial Container Instance of the cluster.
RDP is restricted to be accessed only from the `RdpIp` specified via the cluster instance security group.

## Build on the Windows Container Instance and push to remote ECR repository
Clone the repository and start powershell in the `docker` directory.
```powershell
# Configure
$accountId = (Get-STSCallerIdentity).Account
$region = (Get-EC2InstanceMetadata -Category Region).SystemName
$ecrRepo = "windows-octave"
$tag = "latest"
$appName = "octave"

# Download GnuOctave and extract it
$octaveVersion = "7.3.0"
wget "https://ftpmirror.gnu.org/octave/windows/octave-$octaveVersion-w64.zip" -UseBasicParsing -OutFile "./octave.zip"
Expand-Archive -Path "./octave.zip" -DestinationPath "./"

# Build
docker build -t $appName --build-arg OCTAVE_VERSION=$octaveVersion .

# Test locally. Make sure you create an S3 bucket and configure credentials for the container to access it
$S3_BUCKET="ecs-task-results-debug-bucket"
$Env:AWS_REGION="us-east-2"
$Env:AWS_ACCESS_KEY_ID="AS..."
$Env:AWS_SECRET_ACCESS_KEY="4LUL...r"
$Env:AWS_SESSION_TOKEN="IQ.."
docker run -it -e AWS_REGION -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN  `
    octave C:/workdir/simulate.ps1 100 100 0 0 0 ${S3_BUCKET} octave_sim/task_results
docker run -it -e AWS_REGION -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN  `
    octave C:/workdir/simulate.ps1 100 100 5 1 1 $S3_BUCKET octave_sim/task_results
docker run -it -e AWS_REGION -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN  `
    octave C:/workdir/simulate.ps1 100 100 9 2 2 $S3_BUCKET octave_sim/task_results
docker run -it -e AWS_REGION -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN  `
    octave C:/workdir/aggregate.ps1 3 $S3_BUCKET octave_sim/task_results octave_sim/aggregated_results

# Push to remote ECR respository
(Get-ECRLoginCommand).Password | docker login --username AWS --password-stdin "$accountId.dkr.ecr.$region.amazonaws.com"
docker tag ${appName} "$accountId.dkr.ecr.$region.amazonaws.com/${ecrRepo}:$tag"
docker push "$accountId.dkr.ecr.$region.amazonaws.com/${ecrRepo}:$tag"

# Or alternatively, to public ECR
$PUBLIC_ECR_REPO="public.ecr.aws/o1d7m8a4/windows-batch-aws-mwaa"
$PUBLIC_ECR_PASSWORD="ey.." # To obtain this, run "aws ecr-public get-login-password"
echo $PUBLIC_ECR_PASSWORD | docker login --username AWS --password-stdin "public.ecr.aws"
docker tag ${appName} "${PUBLIC_ECR_REPO}:${octaveVersion}"
docker push "${PUBLIC_ECR_REPO}:${octaveVersion}"
docker tag ${appName} "${PUBLIC_ECR_REPO}:${tag}"
docker push "${PUBLIC_ECR_REPO}:${tag}"
```
