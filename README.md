# Libb-NLP Text Splitter

A Python library that provides intelligent text splitting capabilities using SpaCy or similarity-based approaches. Choose between CPU-only or GPU-accelerated implementations for optimal performance based on your hardware.

## Features

- SpaCy-based splitting with sentence boundary detection
- Semantic similarity-based splitting using sentence transformers
- Optional visualization of similarity patterns
- Configurable chunk sizes and overlap
- GPU acceleration support for faster processing
- CPU-only option for systems without GPU

## Installation

The library supports both CPU-only and GPU-accelerated installations. Choose the appropriate installation method based on your system:

### Prerequisites

- Python 3.9 or higher
- Poetry package manager
- CUDA toolkit 12.1+ (for GPU support)

### Installation Steps

1. Clone the repository:
```bash
git clone https://github.com/bissli/libb-nlp
cd libb-nlp
```

2. Choose your installation type:

```bash
# For CPU-only installation (recommended for most users)
poetry install -E cpu -E test --with cpu --sync

# For GPU-accelerated installation (requires CUDA toolkit)
poetry install -E gpu -E test --with gpu --sync

# For basic installation without torch (minimal dependencies)
poetry install
```

3. Verify installation:
```bash
poetry run python -c "from lnlp import TextSplitterSpacy, TextSplitterSimilarity"
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

### Option 1: Direct Poetry Dependency

Add to your project's `pyproject.toml`:
```toml
[tool.poetry.dependencies]
libb-nlp = { git = "https://github.com/bissli/libb-nlp.git" }

# For CPU-only version
torch = { source = "torch_cpu" }
torchvision = { source = "torch_cpu" }

# OR for GPU version
torch = { source = "torch_cuda" }
torchvision = { source = "torch_cuda" }
```

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

#### Deployment Steps

1. First, build and push the Docker image to ECR using the provided script:
```bash
# Set up environment variables in .env file:
AWS_ACCOUNT_ID=your_account_id
AWS_REGION=your_region
ECR_REPOSITORY=libb-nlp
IMAGE_TAG=latest

# Push to ECR
./push.sh
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
# 1. First update and push your Docker image
./push.sh

# 2. Force ECS to use the new image by updating the service
# Replace APP_NAME with your ApplicationName value from CloudFormation
aws ecs update-service \
  --cluster APP_NAME-cl \
  --service APP_NAME-svc \
  --force-new-deployment

# 3. Monitor the deployment status
aws ecs describe-services \
  --cluster APP_NAME-cl \
  --services APP_NAME-svc \
  --query 'services[0].deployments'
```

Note: You don't need to use CloudWatch for updating the image. The ECS
update-service command above will automatically deploy the new image.
CloudWatch is used for monitoring logs and metrics, not for deployments.

5. To tear down:
```bash
aws cloudformation delete-stack --stack-name libb-nlp
```

## Required IAM Roles and Permissions

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
