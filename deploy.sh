#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_prerequisites() {
    print_status "Checking prerequisites..."
    
    command -v aws >/dev/null 2>&1 || { print_error "AWS CLI not installed"; exit 1; }
    command -v terraform >/dev/null 2>&1 || { print_error "Terraform not installed"; exit 1; }
    aws sts get-caller-identity >/dev/null 2>&1 || { print_error "AWS credentials not configured"; exit 1; }
    
    print_status "Prerequisites check passed!"
}

deploy_terraform() {
    print_status "Deploying Terraform infrastructure..."
    
    cd terraform
    terraform init
    terraform plan -out=tfplan
    terraform apply tfplan
    
    BUCKET_NAME=$(terraform output -raw s3_bucket_name)
    print_status "Infrastructure deployed! S3 Bucket: $BUCKET_NAME"
    cd ..
}

verify_deployment() {
    print_status "Verifying deployment..."
    
    cd terraform
    BUCKET_NAME=$(terraform output -raw s3_bucket_name 2>/dev/null) || { 
        print_error "Cannot get bucket name. Deploy infrastructure first."; 
        cd ..; exit 1; 
    }
    cd ..
    
    # Verify code upload
    if aws s3 ls s3://$BUCKET_NAME/code/migration-accelerator-graviton.zip >/dev/null 2>&1; then
        print_status "✓ Code uploaded to S3"
    else
        print_error "✗ Code not found in S3"
        exit 1
    fi
    
    # Verify EventBridge configuration (now managed by Terraform)
    CONFIG=$(aws s3api get-bucket-notification-configuration --bucket "$BUCKET_NAME" 2>/dev/null)
    if echo "$CONFIG" | grep -q "EventBridgeConfiguration" || [ -z "$CONFIG" ] || echo "$CONFIG" | grep -q "GetBucketNotificationConfiguration"; then
        print_status "✓ EventBridge notifications enabled"
    else
        print_warning "✗ EventBridge notifications not enabled"
    fi
}

show_usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy              Deploy AWS Batch infrastructure (default)"
    echo "  verify              Verify deployment configuration"
    echo "  destroy             Destroy infrastructure"
    echo "  status              Show deployment status"
    echo "  test                Show usage instructions"
    echo "  trigger             Manually trigger Lambda with test event"
    echo "  monitor             Monitor Batch job logs"
    echo ""
    echo "Features: AWS Batch orchestration, auto-scaling, Spot instance support"
}

show_test_instructions() {
    cd terraform 2>/dev/null || { print_error "Run deployment first"; exit 1; }
    BUCKET_NAME=$(terraform output -raw s3_bucket_name 2>/dev/null) || { 
        print_error "Cannot get bucket name. Deploy infrastructure first."; 
        exit 1; 
    }
    QUEUE_NAME=$(terraform output -raw batch_job_queue_name 2>/dev/null) || "graviton-validator-queue"
    DASHBOARD_URL=$(terraform output -raw dashboard_url 2>/dev/null) || "N/A"
    cd ..
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🚀 GRAVITON VALIDATOR - USAGE INSTRUCTIONS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📦 S3 Bucket: $BUCKET_NAME"
    echo "🔧 Batch Queue: $QUEUE_NAME"
    echo "📊 Dashboard: $DASHBOARD_URL"
    echo ""
    
    # Check EventBridge status (now managed by Terraform)
    if aws s3api get-bucket-notification-configuration --bucket "$BUCKET_NAME" 2>/dev/null | grep -q "EventBridgeConfiguration"; then
        echo "✅ EventBridge notifications: ENABLED"
    else
        echo "⚠️  EventBridge notifications: NOT ENABLED"
    fi
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📝 INDIVIDUAL MODE (One SBOM at a time):"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  aws s3 cp your-sbom.json s3://$BUCKET_NAME/input/individual/"
    echo ""
    echo "  ✅ Automatically triggers Batch job"
    echo "  ✅ Results: s3://$BUCKET_NAME/output/individual/your-sbom/"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📝 BATCH MODE (Multiple SBOMs per project):"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  # Step 1: Upload SBOMs (no trigger)"
    echo "  aws s3 cp app1.sbom.json s3://$BUCKET_NAME/input/batch/my-project/"
    echo "  aws s3 cp app2.sbom.json s3://$BUCKET_NAME/input/batch/my-project/"
    echo ""
    echo "  # Step 2: Create manifest (filenames only)"
    echo "  cat > batch-manifest.txt <<EOF"
    echo "app1.sbom.json"
    echo "app2.sbom.json"
    echo "EOF"
    echo ""
    echo "  # Step 3: Upload manifest (triggers ONE job)"
    echo "  aws s3 cp batch-manifest.txt s3://$BUCKET_NAME/input/batch/my-project/"
    echo ""
    echo "  ✅ Triggers single Batch job for entire project"
    echo "  ✅ Results: s3://$BUCKET_NAME/output/batch/my-project/"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔍 MONITORING:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  # Check Batch jobs"
    echo "  aws batch list-jobs --job-queue $QUEUE_NAME --job-status RUNNING"
    echo ""
    echo "  # View logs"
    echo "  aws logs tail /aws/batch/graviton-validator --follow"
    echo ""
    echo "  # Check results"
    echo "  aws s3 ls s3://$BUCKET_NAME/output/individual/"
    echo "  aws s3 ls s3://$BUCKET_NAME/output/batch/"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

case "${1:-deploy}" in
    "deploy")
        check_prerequisites
        deploy_terraform
        verify_deployment
        print_status "🎉 AWS Batch Infrastructure Deployed!"
        show_test_instructions
        ;;
    "terraform")
        check_prerequisites
        deploy_terraform
        ;;
    "verify")
        verify_deployment
        ;;
    "destroy")
        print_warning "Destroying infrastructure..."
        cd terraform 2>/dev/null || { print_error "No terraform directory found"; exit 1; }
        BUCKET_NAME=$(terraform output -raw s3_bucket_name 2>/dev/null)
        cd ..
        
        if [ ! -z "$BUCKET_NAME" ]; then
            print_warning "Emptying S3 bucket: $BUCKET_NAME"
            aws s3 rm s3://$BUCKET_NAME --recursive 2>/dev/null || true
        fi
        
        cd terraform && terraform destroy && cd ..
        print_status "Infrastructure destroyed!"
        ;;
    "status")
        cd terraform 2>/dev/null || { print_error "No terraform directory found"; exit 1; }
        QUEUE_NAME=$(terraform output -raw batch_job_queue_name 2>/dev/null)
        BUCKET_NAME=$(terraform output -raw s3_bucket_name 2>/dev/null)
        cd ..
        
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "📊 Deployment Status"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Batch Queue: $QUEUE_NAME"
        echo "S3 Bucket: $BUCKET_NAME"
        echo ""
        
        if [ ! -z "$QUEUE_NAME" ]; then
            echo "Recent Jobs:"
            aws batch list-jobs --job-queue "$QUEUE_NAME" --max-items 5 2>/dev/null || echo "No jobs found"
        fi
        ;;
    "test")
        show_test_instructions
        ;;
    "trigger")
        cd terraform 2>/dev/null || { print_error "No terraform directory found"; exit 1; }
        LAMBDA_NAME=$(terraform output -raw lambda_function_name 2>/dev/null)
        BUCKET_NAME=$(terraform output -raw s3_bucket_name 2>/dev/null)
        cd ..
        
        print_status "Manually triggering Lambda..."
        cat > /tmp/test-event.json <<EOF
{
  "detail": {
    "bucket": {
      "name": "$BUCKET_NAME"
    },
    "object": {
      "key": "input/individual/sample_syft_sbom.json"
    }
  }
}
EOF
        aws lambda invoke --function-name "$LAMBDA_NAME" --cli-binary-format raw-in-base64-out --payload file:///tmp/test-event.json /tmp/response.json
        cat /tmp/response.json
        echo ""
        ;;
    "monitor")
        cd terraform 2>/dev/null || { print_error "No terraform directory found"; exit 1; }
        QUEUE_NAME=$(terraform output -raw batch_job_queue_name 2>/dev/null)
        DASHBOARD_URL=$(terraform output -raw dashboard_url 2>/dev/null)
        cd ..
        
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "📊 Monitoring"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Batch Queue: $QUEUE_NAME"
        echo "Dashboard: $DASHBOARD_URL"
        echo ""
        echo "Monitoring Batch job logs (Ctrl+C to exit)..."
        aws logs tail /aws/batch/graviton-validator --follow
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        print_error "Unknown command: $1"
        show_usage
        exit 1
        ;;
esac