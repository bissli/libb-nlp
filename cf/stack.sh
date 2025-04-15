#!/bin/bash

# Function to display usage
usage() {
    echo "Usage: $0 <command> [options]"
    echo "Commands:"
    echo "  create    - Create a new stack"
    echo "  update    - Update existing stack"
    echo "  delete    - Delete the stack"
    echo "  status    - Check stack status"
    exit 1
}

# Check if command is provided
if [ $# -lt 1 ]; then
    usage
fi

STACK_NAME="libb-nlp"
TEMPLATE_FILE="cf/cf-libb-nlp.yml"

case "$1" in
    create)
        echo "Creating stack ${STACK_NAME}..."
        aws cloudformation create-stack \
            --stack-name ${STACK_NAME} \
            --template-body file://${TEMPLATE_FILE} \
            --capabilities CAPABILITY_NAMED_IAM \
            --parameters \
                ParameterKey=ApplicationName,ParameterValue=${STACK_NAME} \
                ParameterKey=VpcId,ParameterValue=${AWS_VPC_ID} \
                ParameterKey=PrivateSubnet1Id,ParameterValue=${AWS_PRIVATE_1} \
                ParameterKey=PrivateSubnet2Id,ParameterValue=${AWS_PRIVATE_2} \
                ParameterKey=EcrRepository,ParameterValue=${STACK_NAME} \
                ParameterKey=Region,ParameterValue=us-east-1 \
                ParameterKey=ImageTag,ParameterValue=latest \
                ParameterKey=TaskExecutionRole,ParameterValue=${TASK_EXECUTION_ROLE_ARN} \
                ParameterKey=TaskRole,ParameterValue=${TASK_ROLE_ARN}
        ;;

    update)
        echo "Updating stack ${STACK_NAME}..."
        aws cloudformation update-stack \
            --stack-name ${STACK_NAME} \
            --template-body file://${TEMPLATE_FILE} \
            --capabilities CAPABILITY_NAMED_IAM \
            --parameters \
                ParameterKey=ApplicationName,UsePreviousValue=true \
                ParameterKey=VpcId,UsePreviousValue=true \
                ParameterKey=PrivateSubnet1Id,UsePreviousValue=true \
                ParameterKey=PrivateSubnet2Id,UsePreviousValue=true \
                ParameterKey=EcrRepository,UsePreviousValue=true \
                ParameterKey=ImageTag,UsePreviousValue=true \
                ParameterKey=Region,UsePreviousValue=true \
                ParameterKey=TaskExecutionRole,UsePreviousValue=true \
                ParameterKey=TaskRole,UsePreviousValue=true
        ;;

    delete)
        echo "Deleting stack ${STACK_NAME}..."
        aws cloudformation delete-stack --stack-name ${STACK_NAME}
        ;;

    status)
        echo "Checking stack status..."
        aws cloudformation describe-stacks \
            --stack-name ${STACK_NAME} \
            --query 'Stacks[0].StackStatus' \
            --output text
        ;;

    *)
        usage
        ;;
esac

echo "You can check the stack status in the AWS CloudFormation console"
