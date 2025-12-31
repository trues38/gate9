#!/bin/bash

##############################################
# SSH Tunnel to VPS Neo4j
# Allows local access to remote Neo4j database
##############################################

VPS_HOST="root@141.164.35.214"
LOCAL_PORT="7687"
REMOTE_PORT="7687"

echo "=========================================="
echo "Creating SSH Tunnel to VPS Neo4j"
echo "=========================================="
echo ""
echo "Local:  localhost:${LOCAL_PORT}"
echo "Remote: ${VPS_HOST}:${REMOTE_PORT}"
echo ""
echo "Press Ctrl+C to close tunnel"
echo "=========================================="
echo ""

# Create SSH tunnel
# -L: Local port forwarding
# -N: Don't execute remote command
# -f: Run in background (optional, remove for foreground)
ssh -L ${LOCAL_PORT}:localhost:${REMOTE_PORT} ${VPS_HOST} -N

# Keep tunnel open
echo "Tunnel closed."
