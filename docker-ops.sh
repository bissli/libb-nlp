#!/bin/bash

# Load environment variables
set -a
source .env
set +a

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -b, --build          Build Docker image locally only"
    echo "  -p, --push           Build and push to ECR"
    echo "  -d, --deploy         Build, push, and deploy to ECS"
    echo "  -h, --help           Show this help message"
    echo
    echo "Examples:"
    echo "  $0 -b                # Build locally only"
    echo "  $0 -p                # Build and push to ECR"
    echo "  $0 -d                # Full build, push, and deploy"
    exit 1
}

# Function to check deployment status
check_deployment_status() {
    local deployment_status
    deployment_status=$(aws ecs describe-services \
        --cluster "${APP_NAME}-cl" \
        --services "${APP_NAME}-svc" \
        --query 'services[0].deployments[0].rolloutState' \
        --output text)
    echo "$deployment_status"
}

# Function to build Docker image
build_image() {
    echo "Building image..."
    docker compose build
    if [ $? -ne 0 ]; then
        echo "Error: Failed to build image"
        exit 1
    fi
    echo "Successfully built image"
}

# Function to push to ECR
push_to_ecr() {
    # Check if required variables are set
    if [ -z "$AWS_ACCOUNT_ID" ] || [ -z "$AWS_REGION" ] || [ -z "$ECR_REPOSITORY" ]; then
        echo "Error: Required environment variables are not set"
        echo "Please ensure AWS_ACCOUNT_ID, AWS_REGION, and ECR_REPOSITORY are set in .env"
        exit 1
    fi

    # Create ECR repository if it doesn't exist
    echo "Checking ECR repository..."
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

    # Push the image
    echo "Pushing image to ECR..."
    docker compose push

    if [ $? -ne 0 ]; then
        echo "Error: Failed to push image"
        exit 1
    fi
    echo "Successfully pushed image to ECR"
}

# Function to deploy and monitor
deploy_to_ecs() {
    if [ -z "$APP_NAME" ]; then
        echo "Error: APP_NAME environment variable is not set"
        exit 1
    fi

    # Update ECS service to force new deployment
    echo "Initiating deployment..."
    aws ecs update-service \
        --cluster "${APP_NAME}-cl" \
        --service "${APP_NAME}-svc" \
        --force-new-deployment

    if [ $? -ne 0 ]; then
        echo "Error: Failed to initiate deployment"
        exit 1
    fi

    # Monitor deployment status
    echo "Monitoring deployment status..."
    while true; do
        status=$(check_deployment_status)
        echo "Current deployment status: $status"

        if [ "$status" = "COMPLETED" ]; then
            echo "Deployment completed successfully!"
            break
        elif [ "$status" = "FAILED" ]; then
            echo "Deployment failed. Check ECS console for details."
            exit 1
        fi

        echo "Waiting 30 seconds before next check..."
        sleep 30
    done

    # Get the ALB DNS name
    alb_dns=$(aws cloudformation describe-stacks \
        --stack-name "${APP_NAME}" \
        --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNSName`].OutputValue' \
        --output text)

    echo "Application is accessible at: http://${alb_dns}"
    echo "Health check endpoint: http://${alb_dns}/health"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -b|--build)
            BUILD=true
            shift
            ;;
        -p|--push)
            BUILD=true
            PUSH=true
            shift
            ;;
        -d|--deploy)
            BUILD=true
            PUSH=true
            DEPLOY=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            usage
            ;;
    esac
done

# If no arguments provided, show usage
if [ -z "$BUILD" ] && [ -z "$PUSH" ] && [ -z "$DEPLOY" ]; then
    usage
fi

# Execute requested operations
if [ "$BUILD" = true ]; then
    build_image
fi

if [ "$PUSH" = true ]; then
    push_to_ecr
fi

if [ "$DEPLOY" = true ]; then
    deploy_to_ecs
fi
