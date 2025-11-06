# 📋 Deployment Checklist for Beginners

## Before You Start

### ✅ Prerequisites Checklist
- [ ] **AWS Account created** (free tier is fine)
- [ ] **Python 3.9+ installed** (`python --version`)
- [ ] **AWS CLI installed** (`aws --version`)
- [ ] **Terraform installed** (`terraform --version`)
- [ ] **Git installed** (`git --version`)

### ✅ AWS Setup Checklist
- [ ] **AWS credentials configured** (`aws configure`)
- [ ] **AWS CLI working** (`aws sts get-caller-identity`)
- [ ] **Bedrock access requested** (AWS Console > Bedrock > Model access)
- [ ] **Claude 3 Sonnet model enabled**

---

## Step-by-Step Deployment

### 📁 Step 1: Get the Code
```bash
# Create project directory
mkdir my-ai-project
cd my-ai-project

# Clone the repository
git clone <repository-url>
cd agentic-ai-usecase

# Verify you have all files
ls -la
```

**✅ Checkpoint**: You should see folders like `terraform/`, `src/`, `test/`

### 🔧 Step 2: Prepare Environment
```bash
# Check Python version (should be 3.9+)
python --version

# Check AWS connection
aws sts get-caller-identity

# Check Terraform
terraform --version
```

**✅ Checkpoint**: All commands should work without errors

### 🚀 Step 3: Deploy Infrastructure
```bash
# Navigate to source directory
cd src

# Make deploy script executable (Mac/Linux)
chmod +x deploy.sh

# Run deployment (takes 10-15 minutes)
./deploy.sh
```

**✅ Checkpoint**: Script should complete with "Deployment completed successfully!"

### 📝 Step 4: Save Important Information
After deployment, save these values:
- [ ] **API Endpoint**: `https://xxxxx.execute-api.us-east-1.amazonaws.com/production`
- [ ] **Bedrock Agent ID**: `XXXXXXXXXX`
- [ ] **CloudWatch Dashboard URL**: `https://console.aws.amazon.com/...`

---

## Testing Your Deployment

### 🧪 Quick Test
```bash
# Navigate to examples directory
cd ../examples

# Run simple test
python simple_test.py YOUR_API_ENDPOINT
```

**✅ Checkpoint**: Should see "✅ PASS" for most tests

### 🔍 Manual Verification

#### Check AWS Resources
1. **Go to AWS Console**
2. **Check these services exist**:
   - [ ] **S3**: 2 buckets created (documents, processed-data)
   - [ ] **Lambda**: 6 functions created
   - [ ] **DynamoDB**: 4 tables created
   - [ ] **API Gateway**: 1 API created
   - [ ] **Bedrock**: 1 agent created

#### Test API Endpoints
```bash
# Test basic connectivity
curl YOUR_API_ENDPOINT/v1/health

# Should return: {"status": "healthy"} or similar
```

---

## Common Issues & Solutions

### ❌ Issue: "AWS credentials not configured"
**Solution**:
```bash
aws configure
# Enter your Access Key ID, Secret Access Key, Region, and Output format
```

### ❌ Issue: "Bedrock access denied"
**Solution**:
1. Go to AWS Console > Bedrock
2. Click "Model access" in left menu
3. Click "Request model access"
4. Enable "Claude 3 Sonnet"
5. Wait for approval (usually instant)

### ❌ Issue: "Terraform apply failed"
**Solution**:
```bash
cd terraform
terraform destroy  # Clean up
terraform apply     # Try again
```

### ❌ Issue: "Lambda function timeout"
**Solution**:
1. Go to AWS Console > Lambda
2. Find your function
3. Increase timeout to 15 minutes
4. Increase memory to 1024 MB

### ❌ Issue: "API Gateway 403 Forbidden"
**Solution**:
- Check IAM permissions
- Verify API Gateway deployment
- Check CORS settings

---

## Monitoring & Maintenance

### 📊 Check System Health
1. **CloudWatch Dashboard**:
   - Go to saved dashboard URL
   - Monitor API requests, Lambda duration, errors

2. **CloudWatch Logs**:
   ```bash
   # View recent logs
   aws logs tail /aws/lambda/bedrock-supervisor --follow
   ```

### 💰 Monitor Costs
```bash
# Check current month costs
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost
```

### 🔄 Update System
```bash
# Pull latest changes
git pull

# Redeploy
cd src
./deploy.sh
```

---

## Success Criteria

### ✅ Deployment Successful If:
- [ ] All AWS resources created without errors
- [ ] API endpoint responds to requests
- [ ] Bedrock Agent can be invoked
- [ ] Simple test script passes all tests
- [ ] CloudWatch dashboard shows metrics

### ✅ System Working If:
- [ ] Can request upload URLs
- [ ] Can process documents with AI
- [ ] AI provides intelligent responses
- [ ] Financial calculations work
- [ ] No errors in CloudWatch logs

---

## Next Steps After Successful Deployment

### 🎯 Immediate Actions
1. **Test with real documents**:
   - Upload a PDF financial statement
   - Ask questions about the content
   - Request compliance calculations

2. **Explore the system**:
   - Check CloudWatch logs
   - Monitor API usage
   - Review Bedrock Agent conversations

### 🚀 Advanced Customization
1. **Modify AI instructions**:
   - Edit `terraform/bedrock_agents.tf`
   - Update agent instructions
   - Redeploy with `terraform apply`

2. **Add new capabilities**:
   - Create new tool functions
   - Add document types
   - Implement custom calculations

3. **Build a web interface**:
   - Create HTML/JavaScript frontend
   - Connect to your API
   - Add user authentication

---

## Getting Help

### 🆘 When You Need Support
1. **Check logs first**:
   ```bash
   aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/"
   aws logs tail /aws/lambda/function-name --follow
   ```

2. **Common resources**:
   - AWS Documentation
   - Stack Overflow
   - AWS Forums
   - GitHub Issues

3. **Debug commands**:
   ```bash
   # Check AWS services
   aws sts get-caller-identity
   aws lambda list-functions
   aws bedrock-agent list-agents
   
   # Check Terraform state
   cd terraform
   terraform show
   ```

### 📞 Emergency Cleanup
If something goes wrong and you need to start over:
```bash
cd terraform
terraform destroy  # Removes all AWS resources
# Then start deployment again
```

**⚠️ Warning**: This will delete all data and resources!

---

## Congratulations! 🎉

If you've completed this checklist successfully, you now have:
- A working AI document processing system
- Real-time financial analysis capabilities
- Scalable cloud infrastructure
- Production-ready monitoring

You're ready to process financial documents with AI! 🤖📊
