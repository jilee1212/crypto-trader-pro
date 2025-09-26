#!/bin/bash

# Deployment script for Vultr server
# Usage: ./deploy_to_vultr.sh

echo "🚀 Deploying Crypto Trader Pro to Vultr Server..."

# Server connection details (replace with your actual server info)
SERVER_USER="root"
SERVER_HOST="nosignup.kr"  # Replace with your Vultr server IP
PROJECT_DIR="/root/crypto-trader-pro"

echo "📡 Connecting to Vultr server at $SERVER_HOST..."

# SSH into Vultr server and update the code
ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST << 'ENDSSH'

echo "🔄 Updating project on Vultr server..."

# Navigate to project directory
cd /root/crypto-trader-pro

# Stop existing services
echo "⏹️ Stopping existing services..."
pkill -f "uvicorn"
pkill -f "npm run"

# Pull latest changes from GitHub
echo "📥 Pulling latest changes from GitHub..."
git pull origin main

# Backend deployment
echo "🖥️ Setting up backend..."
cd backend

# Update Python dependencies
pip install -r requirements.txt

# Start backend server (detached)
echo "🚀 Starting backend server..."
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &

cd ..

# Frontend deployment
echo "📱 Setting up frontend..."
cd frontend

# Install npm dependencies
npm install

# Build frontend for production
npm run build

# Start frontend server (detached)
echo "🚀 Starting frontend server..."
nohup npm run preview --port 5173 --host 0.0.0.0 > frontend.log 2>&1 &

cd ..

echo "✅ Deployment completed!"
echo "🌐 Backend API: http://nosignup.kr:8000"
echo "📱 Frontend App: http://nosignup.kr:5173"
echo "📚 API Docs: http://nosignup.kr:8000/docs"

# Show running processes
echo "📊 Running processes:"
ps aux | grep -E "(uvicorn|npm)" | grep -v grep

ENDSSH

echo "🎉 Vultr server deployment completed!"
echo ""
echo "🔗 Access your application:"
echo "   Frontend: http://nosignup.kr:5173"
echo "   Backend API: http://nosignup.kr:8000"
echo "   API Documentation: http://nosignup.kr:8000/docs"
echo ""
echo "📋 To check server status:"
echo "   ssh root@nosignup.kr"
echo "   ps aux | grep -E '(uvicorn|npm)'"