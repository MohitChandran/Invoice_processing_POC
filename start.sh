#!/bin/bash

# Quick Start Script for AI Travel Invoice Validator
# This script sets up and runs the application

set -e

echo "=========================================="
echo "AI Travel Invoice Validator - Quick Start"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python $PYTHON_VERSION detected"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Build vector store
echo "Building RAG vector store..."
if [ -f "src/agents/rules_rag/build_vectorstore.py" ]; then
    python src/agents/rules_rag/build_vectorstore.py
    echo "✓ Vector store built successfully"
else
    echo "⚠ Warning: build_vectorstore.py not found"
fi
echo ""

# Check Ollama connection
echo "Checking Ollama connection..."
OLLAMA_URL="http://192.168.10.200:11434"
if curl -s -f "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
    echo "✓ Ollama server is reachable"
else
    echo "⚠ Warning: Cannot connect to Ollama at $OLLAMA_URL"
    echo "  Make sure Ollama is running with gemma3:27b model"
fi
echo ""

# Create necessary directories
echo "Creating directories..."
mkdir -p logs
mkdir -p data/uploads/invoices
mkdir -p data/uploads/proposals
mkdir -p data/samples/invoices
mkdir -p data/samples/proposals
mkdir -p src/agents/rules_rag/vs
echo "✓ Directories created"
echo ""

# Start the server
echo "=========================================="
echo "Starting FastAPI server..."
echo "=========================================="
echo ""
echo "Server will be available at:"
echo "  • Main API: http://localhost:8000"
echo "  • Swagger UI: http://localhost:8000/docs"
echo "  • Health: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the application
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
