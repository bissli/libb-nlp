# Libb-NLP API

A comprehensive Python API for Natural Language Processing tasks, providing intelligent text processing capabilities with both CPU and GPU acceleration support.

## Features

- Text Processing
  - Intelligent text splitting using SpaCy or semantic similarity
  - PDF text extraction with formatting preservation
  - Configurable chunk sizes and overlap
  - Visualization of similarity patterns

- AI Integration
  - OpenAI GPT models integration
  - Anthropic Claude models support
  - OpenRouter API compatibility
  - Unified API for multiple LLM providers

- Hardware Optimization
  - GPU acceleration support
  - CPU-only fallback option
  - Automatic hardware detection
  - Resource usage monitoring

## Installation

The library supports both CPU-only and GPU-accelerated installations. Choose the appropriate installation method based on your system:

### Prerequisites

- Python 3.10 or higher
- CUDA toolkit 12.1+ (for GPU support)

### Installation Steps

1. Clone the repository:
```bash
git clone https://github.com/bissli/libb-nlp
cd libb-nlp
```

2. Run the installation script:
```bash
# Install
pixi install

# For Prod
pixi install.py -e prod
```

## Usage

### SpaCy-based Splitting

```python
from lnlp import TextSplitterSpacy

splitter = TextSplitterSpacy()
chunks = splitter.split_text(
    text,
    chunk_size=4000,    # Maximum chunk size
    chunk_overlap=200   # Overlap between chunks
)
```

### Similarity-based Splitting

```python
from lnlp import TextSplitterSimilarity

splitter = TextSplitterSimilarity()
chunks = splitter.split_text(text)

# Optional: Visualize similarity patterns
splitter.plot_similarities(text)
```

## Using as a Dependency

There are two ways to use this library in your project:

### Option 1: Direct Python Package Dependency

Add to your project's `pyproject.toml`:
```toml
[project]
dependencies = [
    "libb-nlp @ git+https://github.com/bissli/libb-nlp.git",
    "torch",
    "torchvision"
]
```

Note: The torch and torchvision packages will be installed from PyPI. For GPU support,
ensure you have CUDA toolkit installed on your system.

### Option 2: Running with Docker

#### Local Development with Docker Compose

1. Build and run the container locally:
```bash
# CPU-only version
docker compose up

# GPU version (requires NVIDIA Docker runtime)
docker compose up
```

2. Test the API:
```bash
# Check health and GPU status
curl http://localhost:8000/health

# Split text using spaCy
curl -X POST http://localhost:8000/split/spacy \
  -H "Content-Type: application/json" \
  -d '{"text": "Your text here", "chunk_size": 4000, "chunk_overlap": 200}'

# Split text using similarity
curl -X POST http://localhost:8000/split/similarity \
  -H "Content-Type: application/json" \
  -d '{"text": "Your text here"}'
```

#### Updating Docker Environment

After initial setup, to update the Docker environment (e.g., after dependency changes):

1. Rebuild the container with no cache:
```bash
# CPU-only version
docker compose build --no-cache

# GPU version
docker compose build --no-cache
```

2. Remove old containers and volumes:
```bash
docker compose down -v
```

3. Start the updated environment:
```bash
docker compose up
```

Note: If you only changed application code (not dependencies), you can simply rebuild without the --no-cache flag:
```bash
docker compose build && docker compose up
```

## Required IAM Roles and Permissions

Before deploying, ensure you have the correct IAM roles and permissions set up:

### Deployment Role
To deploy using CloudFormation, you need a role with these managed policies:
- AmazonEC2ContainerRegistryPullOnly
- AmazonEC2FullAccess
- AmazonECS_FullAccess
- AWSCloudFormationFullAccess
- ElasticLoadBalancingFullAccess

Plus a custom pass role policy (e.g., "CloudFormationPassRole"):
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": "arn:aws:iam::123456789:role/ecsInstanceRole"
        }
    ]
}
```

### EC2 Instance Role
The EC2 instances require a role (e.g., "ecsInstanceRole") with these managed policies:
- AmazonEC2ContainerRegistryPullOnly
- AmazonEC2ContainerRegistryReadOnly
- AmazonEC2ContainerServiceforEC2Role
- CloudWatchAgentServerPolicy

Additionally, you need to attach a custom policy for CloudWatch Logs access:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:CreateLogGroup",
                "logs:PutLogEvents"
            ],
            "Resource": [
                "arn:aws:logs:us-east-1:123456789:log-group:/ecs/libb-nlp",
                "arn:aws:logs:us-east-1:123456789:log-group:/ecs/libb-nlp:*"
            ]
        }
    ]
}
```

Make sure to:
1. Create these roles before deployment
2. Update the CloudFormation parameters with the correct role names
3. Ensure the PassRole policy has the correct ARN for your account

### Resource Naming Convention
All resources created by CloudFormation will be prefixed with the ApplicationName parameter value:
- ECS Cluster: `<name>-cl`
- ECS Service: `<name>-svc`
- Load Balancer: `<name>-al`
- Target Group: `<name>-tg`
- Security Groups: `<name>-sg-alb`, `<name>-sg-ecs`
- Auto Scaling Group: `<name>-asg`
- Launch Template: `<name>-lt`
- CloudWatch Log Group: `/ecs/<name>`

### Deploying with CloudFormation

The application can be deployed to AWS using the included CloudFormation template. It supports GPU-accelerated deployment on ECS with proper networking and load balancing.

#### Prerequisites

1. AWS CLI installed and configured:
```bash
aws configure
```

2. Required local tools:
- Docker installed and running
- AWS CLI with configured credentials
- Existing VPC with private subnets
- ECR repository for the container image
- IAM roles and permissions configured as described above

#### Deployment Steps

1. First, build and push the Docker image to ECR using the provided script:
```bash
# Set up environment variables in .env file:
AWS_ACCOUNT_ID=your_account_id
AWS_REGION=your_region
ECR_REPOSITORY=libb-nlp
IMAGE_TAG=latest

# Build locally only
./docker-ops.sh -b

# Build and push to ECR
./docker-ops.sh -p

# Build, push and deploy
./docker-ops.sh -d
```

2. Deploy the CloudFormation stack:
```bash
aws cloudformation create-stack \
  --stack-name libb-nlp \
  --template-body file://cf-libb-nlp.yml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters \
    ParameterKey=ApplicationName,ParameterValue=libb-nlp \
    ParameterKey=VpcId,ParameterValue=vpc-xxxxx \
    ParameterKey=PrivateSubnet1Id,ParameterValue=subnet-xxxxx \
    ParameterKey=PrivateSubnet2Id,ParameterValue=subnet-xxxxx \
    ParameterKey=IamInstanceProfile,ParameterValue=your-instance-profile \
    ParameterKey=EcrRepository,ParameterValue=libb-nlp \
    ParameterKey=Region,ParameterValue=us-east-1 \
    ParameterKey=ImageTag,ParameterValue=latest
```

The CloudFormation template will create:
- ECS cluster with GPU-enabled instances
- Application Load Balancer in private subnets
- Security groups for ECS and ALB
- Auto Scaling Group for EC2 instances
- ECS Service and Task Definition
- CloudWatch Log Group

3. Monitor the deployment:
```bash
# Check stack status
aws cloudformation describe-stacks --stack-name libb-nlp

# Get the ALB DNS name
aws cloudformation describe-stacks \
  --stack-name libb-nlp \
  --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNSName`].OutputValue' \
  --output text
```

4. To update the deployment with a new Docker image:
```bash
# Deploy new version using docker-ops.sh
./docker-ops.sh -d

This will:
1. Build the new Docker image
2. Push it to ECR
3. Deploy to ECS
4. Monitor deployment status
5. Display the ALB DNS name when complete
```

Note: You don't need to use CloudWatch for updating the image. The ECS
update-service command above will automatically deploy the new image.
CloudWatch is used for monitoring logs and metrics, not for deployments.

5. To tear down:
```bash
aws cloudformation delete-stack --stack-name libb-nlp
```


## Performance Considerations

- GPU version is recommended for processing large volumes of text
- CPU version is suitable for most general use cases
- Memory usage scales with text size and model complexity

For detailed examples, benchmarks, and API documentation, visit our [GitHub repository](https://github.com/bissli/libb-nlp).

## Accessing Your Application

After deployment, your application will be accessible through the Application Load Balancer DNS name. The CloudFormation stack creates all necessary resources with consistent naming:

### Resource Naming Convention
All resources are prefixed with the ApplicationName parameter value:
- ECS Cluster: `<name>-cl`
- ECS Service: `<name>-svc`
- Load Balancer: `<name>-al`
- Target Group: `<name>-tg`
- Security Groups: `<name>-sg-alb`, `<name>-sg-ecs`
- Auto Scaling Group: `<name>-asg`
- Launch Template: `<name>-lt`
- CloudWatch Log Group: `/ecs/<name>`

### Endpoints
Once deployed, you can access these endpoints:
```bash
# Health check
http://<ALB_DNS_NAME>/health

# GPU status
http://<ALB_DNS_NAME>/gpu

# Text splitting endpoints
http://<ALB_DNS_NAME>/split/spacy
http://<ALB_DNS_NAME>/split/similarity
```

### Monitoring
The deployment includes:
- CloudWatch Log Group: `/ecs/<name>`
- Container Insights metrics
- ALB access logs and metrics
- GPU utilization metrics

For GPU-related task failures, SSH into the EC2 instance and check the ECS agent logs:
```bash
tail -n 100 /var/log/ecs/ecs-agent.log | grep -iE "error|AccessDenied"
```
