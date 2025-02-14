#!/bin/bash

# Load environment variables
set -a
source .env
set +a

# Check if required variables are set
if [ -z "$AWS_ACCOUNT_ID" ] || [ -z "$AWS_REGION" ] || [ -z "$ECR_REPOSITORY" ]; then
    echo "Error: Required environment variables are not set"
    exit 1
fi

# Create ECR repository if it doesn't exist
aws ecr describe-repositories --repository-names ${ECR_REPOSITORY} 2>/dev/null || \
aws ecr create-repository --repository-name ${ECR_REPOSITORY}

# Login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

if [ $? -ne 0 ]; then
    echo "Error: Failed to login to ECR"
    exit 1
fi

# Build the image
echo "Building image..."
docker compose build

if [ $? -ne 0 ]; then
    echo "Error: Failed to build image"
    exit 1
fi

# Push the image
echo "Pushing image to ECR..."
docker compose push

if [ $? -ne 0 ]; then
    echo "Error: Failed to push image"
    exit 1
fi

echo "Successfully built and pushed image to ECR"
