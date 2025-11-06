#!/bin/bash

# Agentic AI Financial Document Processing - Deployment Script (Bedrock Agents)
set -e

echo "🚀 Starting deployment of Agentic AI Financial Document Processing Platform with Bedrock Agents..."

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install AWS CLI first."
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.9+ first."
    exit 1
fi

if ! command -v zip &> /dev/null; then
    echo "❌ zip command not found. Please install zip utility."
    exit 1
fi

# Verify AWS credentials
echo "🔐 Verifying AWS credentials..."
aws sts get-caller-identity > /dev/null || {
    echo "❌ AWS credentials not configured. Run 'aws configure' first."
    exit 1
}

# Check Bedrock model access
echo "🤖 Checking Bedrock model access..."
REGION=$(aws configure get region)
aws bedrock list-foundation-models --region $REGION > /dev/null || {
    echo "⚠️  Warning: Bedrock access may not be available in region $REGION"
    echo "   Make sure you have requested access to Bedrock models"
}

echo "✅ Prerequisites check passed"

# Create build directory
BUILD_DIR="build"
rm -rf $BUILD_DIR
mkdir -p $BUILD_DIR

echo "📦 Building Lambda packages..."

# Build common layer
echo "Building common layer..."
mkdir -p $BUILD_DIR/layers/python
cp -r layers/python/* $BUILD_DIR/layers/python/
cd $BUILD_DIR/layers
pip install -r ../../../layers/requirements.txt -t python/
zip -r common-layer.zip python/
cd ../..

# Build Lambda functions (simplified for Bedrock Agents)
FUNCTIONS=("upload-handler" "bedrock-supervisor" "bedrock-tools" "validator-agent" "extractor-agent" "status-handler")

for func in "${FUNCTIONS[@]}"; do
    echo "Building $func..."
    mkdir -p $BUILD_DIR/functions/$func
    cp functions/$func/handler.py $BUILD_DIR/functions/$func/
    cd $BUILD_DIR/functions/$func
    zip -r ../$func.zip .
    cd ../../..
done

echo "✅ Lambda packages built successfully"

# Move packages to expected locations
mkdir -p src/layers src/functions
mv $BUILD_DIR/layers/common-layer.zip src/layers/
for func in "${FUNCTIONS[@]}"; do
    mv $BUILD_DIR/functions/$func.zip src/functions/
done

echo "📋 Deploying infrastructure with Terraform..."
cd terraform

# Initialize Terraform
terraform init

# Plan deployment
echo "🔍 Planning Terraform deployment..."
terraform plan -var="environment=production"

# Ask for confirmation
read -p "🤔 Do you want to proceed with the deployment? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled"
    exit 1
fi

# Apply Terraform
echo "🏗️ Applying Terraform configuration..."
terraform apply -auto-approve -var="environment=production"

# Get outputs
echo "📊 Deployment completed! Getting outputs..."
API_ENDPOINT=$(terraform output -raw api_endpoint)
BEDROCK_AGENT_ID=$(terraform output -raw bedrock_agent_id)
DASHBOARD_URL=$(terraform output -raw cloudwatch_dashboard_url)

cd ..

echo "🎉 Deployment completed successfully!"
echo ""
echo "📋 Deployment Summary:"
echo "====================="
echo "🌐 API Endpoint: $API_ENDPOINT"
echo "🤖 Bedrock Agent ID: $BEDROCK_AGENT_ID"
echo "📊 CloudWatch Dashboard: $DASHBOARD_URL"
echo ""
echo "🔧 Bedrock Agent Features:"
echo "- Intelligent document validation"
echo "- Automated data extraction with Textract"
echo "- Financial compliance calculations"
echo "- Natural language document Q&A"
echo "- Multi-step reasoning and tool coordination"
echo ""
echo "📚 Next Steps:"
echo "1. Test the API endpoints using the provided examples"
echo "2. The Bedrock Agent will automatically choose appropriate tools"
echo "3. Monitor agent conversations in CloudWatch logs"
echo "4. Configure additional agent instructions if needed"
echo ""
echo "📖 Documentation:"
echo "- API Documentation: See README.md for usage examples"
echo "- Architecture: See DESIGN_DOCUMENT.md"
echo "- Bedrock Agents: AWS Console > Bedrock > Agents"
echo ""
echo "🔧 Useful Commands:"
echo "- View agent logs: aws logs tail /aws/lambda/bedrock-supervisor --follow"
echo "- Test agent directly: aws bedrock-agent-runtime invoke-agent --agent-id $BEDROCK_AGENT_ID --agent-alias-id LIVE --session-id test --input-text 'Hello'"
echo "- Monitor costs: aws ce get-cost-and-usage --time-period Start=\$(date -d '1 month ago' +%Y-%m-%d),End=\$(date +%Y-%m-%d) --granularity MONTHLY --metrics BlendedCost"

# Cleanup build directory
rm -rf $BUILD_DIR

echo "✅ Bedrock Agents deployment completed!"
