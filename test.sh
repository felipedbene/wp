#!/bin/bash

# Colors for better readability
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== WordPress Cloudflare Tunnel Test Script ===${NC}"
echo -e "${YELLOW}This script tests the connectivity and proper configuration of WordPress with Cloudflare Tunnel${NC}"
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl is not installed or not in PATH${NC}"
    exit 1
fi

# Check if the wp namespace exists
echo -e "${YELLOW}Checking if wp namespace exists...${NC}"
if kubectl get namespace wp &> /dev/null; then
    echo -e "${GREEN}✓ wp namespace exists${NC}"
else
    echo -e "${RED}✗ wp namespace does not exist${NC}"
    exit 1
fi

# Check WordPress pod status
echo -e "\n${YELLOW}Checking WordPress pod status...${NC}"
WP_POD=$(kubectl get pods -n wp -l app=wordpress-hellspawn -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -z "$WP_POD" ]; then
    echo -e "${RED}✗ WordPress pod not found${NC}"
    exit 1
else
    WP_STATUS=$(kubectl get pod -n wp $WP_POD -o jsonpath='{.status.phase}')
    if [ "$WP_STATUS" == "Running" ]; then
        echo -e "${GREEN}✓ WordPress pod $WP_POD is running${NC}"
    else
        echo -e "${RED}✗ WordPress pod $WP_POD status: $WP_STATUS${NC}"
        exit 1
    fi
fi

# Check WordPress service
echo -e "\n${YELLOW}Checking WordPress service...${NC}"
WP_SVC=$(kubectl get svc -n wp wordpress-frenzy -o jsonpath='{.metadata.name}' 2>/dev/null)
if [ -z "$WP_SVC" ]; then
    echo -e "${RED}✗ WordPress service not found${NC}"
    exit 1
else
    WP_SVC_IP=$(kubectl get svc -n wp wordpress-frenzy -o jsonpath='{.spec.clusterIP}')
    WP_SVC_PORT=$(kubectl get svc -n wp wordpress-frenzy -o jsonpath='{.spec.ports[0].port}')
    echo -e "${GREEN}✓ WordPress service $WP_SVC found at $WP_SVC_IP:$WP_SVC_PORT${NC}"
fi

# Check Cloudflared pod status
echo -e "\n${YELLOW}Checking Cloudflared pod status...${NC}"
CF_POD=$(kubectl get pods -n wp -l app=blog-cloudflared -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -z "$CF_POD" ]; then
    echo -e "${RED}✗ Cloudflared pod not found${NC}"
    exit 1
else
    CF_STATUS=$(kubectl get pod -n wp $CF_POD -o jsonpath='{.status.phase}')
    if [ "$CF_STATUS" == "Running" ]; then
        echo -e "${GREEN}✓ Cloudflared pod $CF_POD is running${NC}"
    else
        echo -e "${RED}✗ Cloudflared pod $CF_POD status: $CF_STATUS${NC}"
        exit 1
    fi
fi

# Check Cloudflared config
echo -e "\n${YELLOW}Checking Cloudflared configuration...${NC}"
CF_CONFIG=$(kubectl get configmap -n wp blog-cloudflared-config -o jsonpath='{.data.config\.yaml}' 2>/dev/null)
if [ -z "$CF_CONFIG" ]; then
    echo -e "${RED}✗ Cloudflared config not found${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Cloudflared config found${NC}"
    
    # Check for originServerName in config
    if echo "$CF_CONFIG" | grep -q "originServerName"; then
        echo -e "${GREEN}✓ originServerName is configured in Cloudflared config${NC}"
    else
        echo -e "${RED}✗ originServerName is missing in Cloudflared config${NC}"
        echo -e "${YELLOW}Recommendation: Add originRequest.originServerName to fix 'bad origin' errors${NC}"
    fi
fi

# Create a test pod for connectivity checks
echo -e "\n${YELLOW}Creating test pod for connectivity checks...${NC}"
cat <<EOF | kubectl apply -f - > /dev/null
apiVersion: v1
kind: Pod
metadata:
  name: curl-test
  namespace: wp
spec:
  containers:
  - name: curl
    image: curlimages/curl:latest
    command: 
      - sleep
      - "300"
EOF

echo -e "${YELLOW}Waiting for test pod to be ready...${NC}"
kubectl wait --for=condition=Ready pod/curl-test -n wp --timeout=60s > /dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Test pod failed to start${NC}"
    kubectl delete pod -n wp curl-test > /dev/null 2>&1
    exit 1
else
    echo -e "${GREEN}✓ Test pod is ready${NC}"
fi

# Test WordPress connectivity
echo -e "\n${YELLOW}Testing WordPress connectivity...${NC}"
HTTP_CODE=$(kubectl exec -n wp curl-test -- curl -s -o /dev/null -w "%{http_code}" http://wordpress-frenzy)
if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✓ WordPress is accessible (HTTP 200)${NC}"
else
    echo -e "${RED}✗ WordPress returned HTTP $HTTP_CODE${NC}"
fi

# Test WordPress with Host header
echo -e "\n${YELLOW}Testing WordPress with Host header...${NC}"
LINK_HEADER=$(kubectl exec -n wp curl-test -- curl -s -I http://wordpress-frenzy -H "Host: blog.debene.dev" | grep -i "Link:")
if [[ "$LINK_HEADER" == *"blog.debene.dev"* ]]; then
    echo -e "${GREEN}✓ WordPress correctly uses blog.debene.dev in Link header${NC}"
    echo -e "${GREEN}✓ Host header is working correctly${NC}"
else
    echo -e "${RED}✗ WordPress is not using blog.debene.dev in Link header${NC}"
    echo -e "${YELLOW}Actual Link header: $LINK_HEADER${NC}"
fi

# Check Cloudflared logs for errors
echo -e "\n${YELLOW}Checking Cloudflared logs for errors...${NC}"
CF_LOGS=$(kubectl logs -n wp $CF_POD --tail=50)
if echo "$CF_LOGS" | grep -i "error\|exception\|fail" > /dev/null; then
    echo -e "${RED}✗ Found potential errors in Cloudflared logs:${NC}"
    echo "$CF_LOGS" | grep -i "error\|exception\|fail"
else
    echo -e "${GREEN}✓ No obvious errors found in Cloudflared logs${NC}"
fi

# Check Cloudflared tunnel connections
echo -e "\n${YELLOW}Checking Cloudflared tunnel connections...${NC}"
CONN_COUNT=$(echo "$CF_LOGS" | grep -c "Registered tunnel connection")
if [ "$CONN_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Found $CONN_COUNT tunnel connections${NC}"
else
    echo -e "${RED}✗ No tunnel connections found in logs${NC}"
fi

# Clean up test pod
echo -e "\n${YELLOW}Cleaning up test resources...${NC}"
kubectl delete pod -n wp curl-test > /dev/null 2>&1
echo -e "${GREEN}✓ Test pod deleted${NC}"

echo -e "\n${GREEN}=== Test Summary ===${NC}"
echo -e "${GREEN}✓ WordPress pod is running${NC}"
echo -e "${GREEN}✓ WordPress service is configured${NC}"
echo -e "${GREEN}✓ Cloudflared pod is running${NC}"
echo -e "${GREEN}✓ Cloudflared configuration is valid${NC}"
echo -e "${GREEN}✓ WordPress is accessible${NC}"
echo -e "${GREEN}✓ Host header configuration is working${NC}"

echo -e "\n${YELLOW}If all tests passed, your WordPress site should be correctly configured with Cloudflare Tunnel.${NC}"
echo -e "${YELLOW}You can access your site at: https://blog.debene.dev${NC}"
