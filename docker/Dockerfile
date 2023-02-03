# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Refer to Microsoft EULA regarding the base image (https://learn.microsoft.com/en-us/virtualization/windowscontainers/images-eula).
FROM mcr.microsoft.com/windows/server:ltsc2022

ARG OCTAVE_VERSION

RUN powershell.exe -Command \
  Install-PackageProvider -Name NuGet -Force; \
  Install-Module -Name AWS.Tools.S3 -Scope AllUsers -Force; \
  mkdir "C:/workdir"

WORKDIR "C:/workdir"

COPY "octave-${OCTAVE_VERSION}-w64" "C:/octave"
COPY "bootstrap.ps1" "simulate.m" "simulate.ps1" "aggregate.m" "aggregate.ps1"  "C:/workdir/"

ENTRYPOINT ["powershell.exe"]