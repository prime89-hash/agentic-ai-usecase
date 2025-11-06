# Deployment Guide - Agentic AI Financial Document Processing

## Overview
This guide provides step-by-step instructions for deploying the Agentic AI Financial Document Processing platform to any AWS account.

## Prerequisites

### Required Tools
- **AWS CLI** v2.0+ configured with appropriate permissions
- **Terraform** v1.0+ 
- **Python** 3.9+
- **Git** for version control
- **zip** utility for packaging

### AWS Permissions Required
The deploying user/role needs the following AWS permissions:
- IAM: Create/manage roles and policies
- Lambda: Create/manage functions and layers
- API Gateway: Create/manage REST APIs
- S3: Create/manage buckets
- DynamoDB: Create/manage tables
- CloudWatch: Create/manage logs and dashboards
- KMS: Create/manage encryption keys
- SNS: Create/manage topics
- Textract: Service access
- Bedrock: Model access

### AWS Service Limits
Ensure your AWS account has sufficient limits for:
- Lambda concurrent executions (recommended: 1000+)
- API Gateway requests per second (recommended: 10,000+)
- DynamoDB read/write capacity units
- S3 storage and requests

## Quick Start Deployment

### 1. Clone Repository
```bash
git clone <repository-url>
cd agentic-ai-usecase
```

### 2. Configure AWS Credentials
```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and region
```

### 3. Customize Configuration (Optional)
```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Edit terraform.tfvars with your specific settings
```

### 4. Deploy Infrastructure
```bash
cd src
./deploy.sh
```

The deployment script will:
- Build Lambda packages
- Deploy infrastructure with Terraform
- Configure monitoring and alerting
- Provide deployment summary with endpoints

## Manual Deployment Steps

If you prefer manual deployment or need to customize the process:

### Step 1: Prepare Lambda Packages
```bash
# Build common layer
cd src/layers
pip install -r requirements.txt -t python/
zip -r common-layer.zip python/

# Build Lambda functions
cd ../functions
for func in upload-handler supervisor-agent validator-agent extractor-agent compliance-agent qa-agent status-handler; do
    cd $func
    zip -r ../$func.zip .
    cd ..
done
```

### Step 2: Deploy with Terraform
```bash
cd terraform

# Initialize Terraform
terraform init

# Review deployment plan
terraform plan -var="environment=production"

# Deploy infrastructure
terraform apply -var="environment=production"
```

### Step 3: Verify Deployment
```bash
# Get API endpoint
API_ENDPOINT=$(terraform output -raw api_endpoint)

# Test API health
curl $API_ENDPOINT/v1/health

# Run comprehensive tests
cd ../test
python test_api.py $API_ENDPOINT
```

## Configuration Options

### Environment Variables
Key environment variables that can be customized:

| Variable | Description | Default |
|----------|-------------|---------|
| `aws_region` | AWS deployment region | us-east-1 |
| `environment` | Environment name | production |
| `lambda_memory_size` | Lambda memory in MB | 1024 |
| `lambda_timeout` | Lambda timeout in seconds | 900 |
| `api_throttle_rate` | API requests per second | 1000 |
| `document_retention_days` | Document retention period | 2555 (7 years) |
| `notification_email` | Admin notification email | admin@company.com |

### Multi-Environment Deployment
To deploy multiple environments (dev, staging, production):

```bash
# Development environment
terraform apply -var="environment=dev" -var="lambda_memory_size=512"

# Staging environment  
terraform apply -var="environment=staging" -var="api_throttle_rate=500"

# Production environment
terraform apply -var="environment=production" -var="enable_waf=true"
```

## Security Configuration

### 1. Enable WAF (Recommended for Production)
```bash
terraform apply -var="enable_waf=true"
```

### 2. Configure Custom Domain with SSL
```bash
# Add to terraform.tfvars
custom_domain_name = "api.yourcompany.com"
certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012"
```

### 3. Set Up VPC Endpoints (Optional)
For enhanced security, deploy Lambda functions in VPC with VPC endpoints for AWS services.

### 4. Configure Authentication
The platform supports multiple authentication methods:
- **API Keys**: For simple client authentication
- **IAM Roles**: For AWS service-to-service communication
- **JWT Tokens**: For user-based authentication (requires custom implementation)

## Monitoring and Alerting

### CloudWatch Dashboards
The deployment creates a comprehensive dashboard showing:
- API Gateway metrics (requests, latency, errors)
- Lambda metrics (invocations, duration, errors)
- DynamoDB metrics (read/write capacity, throttles)
- Custom business metrics (documents processed, compliance checks)

### Alerting Configuration
Default alarms are created for:
- Lambda function errors (threshold: 5 errors in 10 minutes)
- API Gateway 4XX errors (threshold: 10 errors in 5 minutes)
- DynamoDB throttling (threshold: any throttles)

### Log Aggregation
All logs are centralized in CloudWatch with:
- 14-day retention for cost optimization
- Structured logging for easy searching
- Error tracking and alerting

## Cost Optimization

### 1. Right-Size Lambda Functions
Monitor Lambda duration and memory usage to optimize:
```bash
# Check Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=your-function-name \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Average,Maximum
```

### 2. Optimize DynamoDB Capacity
Use on-demand billing for variable workloads or provisioned capacity for predictable workloads.

### 3. S3 Lifecycle Policies
The deployment includes intelligent tiering:
- Standard → Standard-IA (30 days)
- Standard-IA → Glacier (90 days)
- Glacier → Deep Archive (365 days)

### 4. Monitor Costs
```bash
# Get monthly costs by service
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-02-01 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

## Troubleshooting

### Common Issues

#### 1. Lambda Function Timeouts
**Symptoms**: Functions timing out during document processing
**Solutions**:
- Increase Lambda timeout (max 15 minutes)
- Optimize document processing logic
- Use asynchronous processing for large documents

#### 2. API Gateway Throttling
**Symptoms**: 429 Too Many Requests errors
**Solutions**:
- Increase throttling limits
- Implement client-side retry logic
- Use usage plans for different client tiers

#### 3. DynamoDB Throttling
**Symptoms**: ProvisionedThroughputExceededException
**Solutions**:
- Enable auto-scaling
- Switch to on-demand billing
- Optimize query patterns

#### 4. Bedrock Access Issues
**Symptoms**: Access denied errors when calling Bedrock
**Solutions**:
- Ensure Bedrock service is available in your region
- Request access to required foundation models
- Check IAM permissions for Bedrock

### Debugging Commands

```bash
# View Lambda logs
aws logs tail /aws/lambda/function-name --follow

# Check API Gateway logs
aws logs describe-log-groups --log-group-name-prefix API-Gateway-Execution-Logs

# Monitor DynamoDB metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=your-table-name

# Check S3 bucket policies
aws s3api get-bucket-policy --bucket your-bucket-name
```

## Backup and Disaster Recovery

### 1. Automated Backups
The deployment includes:
- DynamoDB point-in-time recovery (enabled)
- S3 versioning (enabled)
- Lambda function versioning
- Infrastructure as Code (Terraform state)

### 2. Cross-Region Replication
For disaster recovery, consider:
```bash
# Deploy to secondary region
terraform apply -var="aws_region=us-west-2" -var="environment=dr"
```

### 3. Backup Procedures
```bash
# Export DynamoDB table
aws dynamodb scan --table-name your-table --output json > backup.json

# Backup S3 bucket
aws s3 sync s3://source-bucket s3://backup-bucket

# Export Terraform state
terraform state pull > terraform-state-backup.json
```

## Scaling Considerations

### Horizontal Scaling
The platform automatically scales through:
- Lambda concurrent execution scaling
- DynamoDB auto-scaling
- API Gateway automatic scaling

### Performance Optimization
For high-volume deployments:
1. **Use provisioned concurrency** for Lambda functions
2. **Implement caching** with ElastiCache
3. **Use CloudFront** for global distribution
4. **Optimize Bedrock model selection** based on use case

### Multi-Tenant Scaling
The platform supports multi-tenancy through:
- Tenant isolation in S3 key prefixes
- Tenant-specific DynamoDB partitions
- Usage tracking per tenant
- Configurable rate limiting per tenant

## Support and Maintenance

### Regular Maintenance Tasks
1. **Monitor costs** and optimize resource usage
2. **Update Lambda runtimes** and dependencies
3. **Review security configurations** and access patterns
4. **Backup critical data** and test recovery procedures
5. **Update documentation** and runbooks

### Getting Support
- **Documentation**: Comprehensive guides in `/docs` directory
- **Monitoring**: CloudWatch dashboards and alarms
- **Logging**: Centralized logs in CloudWatch
- **Community**: GitHub issues and discussions

### Version Updates
To update the platform:
1. Review changelog and breaking changes
2. Test updates in development environment
3. Deploy to staging for validation
4. Deploy to production during maintenance window
5. Monitor system health post-deployment
