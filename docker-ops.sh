#!/bin/bash
set -euo pipefail

# Script configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"

# Required environment variables
readonly REQUIRED_VARS=(
    "OPENROUTER_API_KEY"
    "AWS_ACCOUNT_ID"
    "AWS_REGION"
    "ECR_REPOSITORY"
    "APP_NAME"
)

# Helper functions
log_info() {
    echo "[INFO] $1"
}

log_warn() {
    echo "[WARN] $1" >&2
}

log_error() {
    echo "[ERROR] $1" >&2
}


# Load environment variables (.env takes precedence)
load_environment() {
    # Set TZ from system timezone
    if [ -f /etc/timezone ]; then
        export TZ=$(cat /etc/timezone)
    elif [ -f /etc/localtime ] && command -v readlink >/dev/null; then
        # Try to extract timezone from localtime symlink
        LOCALTIME_LINK=$(readlink -f /etc/localtime)
        if [[ $LOCALTIME_LINK =~ zoneinfo/(.+)$ ]]; then
            export TZ=${BASH_REMATCH[1]}
        else
            export TZ="UTC"
            log_warn "Could not determine system timezone, defaulting to UTC"
        fi
    else
        export TZ="UTC"
        log_warn "Could not determine system timezone, defaulting to UTC"
    fi
    log_info "Using timezone: $TZ"

    if [ -f .env ]; then
        # Store current environment
        declare -A orig_env
        for var in "${REQUIRED_VARS[@]}"; do
            if [ -n "${!var:-}" ]; then
                orig_env[$var]="${!var}"
            fi
        done

        # Load .env file
        set -a
        source .env
        set +a

        # Restore any variables not in .env
        for var in "${REQUIRED_VARS[@]}"; do
            if [ -z "${!var:-}" ] && [ -n "${orig_env[$var]:-}" ]; then
                declare "$var=${orig_env[$var]}"
            fi
        done
    else
        log_warn "No .env file found, using environment variables only"
    fi
}

# Initialize environment
load_environment

show_usage() {
    cat << EOF
Usage: ${SCRIPT_NAME} [OPTIONS]

Options:
    -b, --build          Build Docker image locally only
    -p, --push           Build and push to ECR
    -d, --deploy         Build, push, and deploy to ECS
    -h, --help           Show this help message

Examples:
    ${SCRIPT_NAME} -b    # Build locally only
    ${SCRIPT_NAME} -p    # Build and push to ECR
    ${SCRIPT_NAME} -d    # Full build, push, and deploy
EOF
    exit 1
}

check_deployment_status() {
    aws ecs describe-services \
        --cluster "${APP_NAME}-cl" \
        --services "${APP_NAME}-svc" \
        --query 'services[0].deployments[0].rolloutState' \
        --output text
}

build_image() {
    log_info "Building Docker image..."

    if ! docker compose build; then
        log_error "Failed to build image"
        exit 1
    fi

    log_info "Successfully built image"
}

push_to_ecr() {
    local required_aws_vars=("AWS_ACCOUNT_ID" "AWS_REGION" "ECR_REPOSITORY")
    for var in "${required_aws_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log_error "Missing required variable: $var"
            exit 1
        fi
    done

    log_info "Checking ECR repository..."
    aws ecr describe-repositories --repository-names "${ECR_REPOSITORY}" 2>/dev/null || \
        aws ecr create-repository --repository-name "${ECR_REPOSITORY}"

    log_info "Logging in to ECR..."
    if ! aws ecr get-login-password --region "${AWS_REGION}" | \
         docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"; then
        log_error "Failed to login to ECR"
        exit 1
    fi

    log_info "Pushing image to ECR..."
    if ! docker compose push; then
        log_error "Failed to push image"
        exit 1
    fi

    log_info "Successfully pushed image to ECR"
}

deploy_to_ecs() {
    if [ -z "${APP_NAME:-}" ]; then
        log_error "APP_NAME environment variable is not set"
        exit 1
    fi

    log_info "Initiating deployment..."
    if ! aws ecs update-service \
            --cluster "${APP_NAME}-cl" \
            --service "${APP_NAME}-svc" \
            --force-new-deployment; then
        log_error "Failed to initiate deployment"
        exit 1
    fi

    log_info "Monitoring deployment status..."
    while true; do
        local status
        status=$(check_deployment_status)
        log_info "Current deployment status: $status"

        case "$status" in
            "COMPLETED")
                log_info "Deployment completed successfully!"
                break
                ;;
            "FAILED")
                log_error "Deployment failed. Check ECS console for details."
                exit 1
                ;;
            *)
                log_info "Waiting 30 seconds before next check..."
                sleep 30
                ;;
        esac
    done

    local alb_dns
    alb_dns=$(aws cloudformation describe-stacks \
        --stack-name "${APP_NAME}" \
        --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNSName`].OutputValue' \
        --output text)

    log_info "Application is accessible at: http://${alb_dns}"
    log_info "Health check endpoint: http://${alb_dns}/health"
}

main() {
    local BUILD=false
    local PUSH=false
    local DEPLOY=false

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
                show_usage
                ;;
            *)
                show_usage
                ;;
        esac
    done

    # If no arguments provided, show usage
    if ! $BUILD && ! $PUSH && ! $DEPLOY; then
        show_usage
    fi

    # Execute requested operations
    $BUILD && build_image
    $PUSH && push_to_ecr
    $DEPLOY && deploy_to_ecs
}

# Execute main function
main "$@"
