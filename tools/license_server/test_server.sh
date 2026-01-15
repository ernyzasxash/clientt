#!/bin/bash
# Test the license server endpoints locally

BASE_URL="${1:-http://localhost:5000}"
ADMIN_TOKEN="${2:-change-me}"

echo "Testing License Server"
echo "====================="
echo "Base URL: $BASE_URL"
echo ""

# Test with valid key
echo "1. Testing /check with valid key (TEST-KEY-123456):"
curl -v "$BASE_URL/check?key=TEST-KEY-123456"
echo -e "\n"

# Test with invalid key
echo "2. Testing /check with invalid key:"
curl -v "$BASE_URL/check?key=WRONG-KEY"
echo -e "\n"

# Test admin list (requires token)
echo "3. Testing /admin/list:"
curl -v -H "X-Admin-Token: $ADMIN_TOKEN" "$BASE_URL/admin/list"
echo -e "\n"

# Test admin add
echo "4. Testing /admin/add:"
curl -v -X POST -H "Content-Type: application/json" -H "X-Admin-Token: $ADMIN_TOKEN" \
  -d '{"key":"NEW-TEST-KEY"}' "$BASE_URL/admin/add"
echo -e "\n"

# List again
echo "5. Listing keys after add:"
curl -v -H "X-Admin-Token: $ADMIN_TOKEN" "$BASE_URL/admin/list"
echo -e "\n"
