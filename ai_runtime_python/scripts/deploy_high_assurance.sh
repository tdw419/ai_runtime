#!/bin/bash

# High-Assurance AI Daemon Deployment Script
set -e

echo "🚀 Deploying High-Assurance AI System Daemon..."

# Check if running as root (for system deployment)
if [ "$EUID" -eq 0 ]; then
    echo "✓ Running with appropriate privileges"
else
    echo "⚠️  Not running as root - some features may require elevated privileges"
fi

# Create necessary directories
echo "📁 Creating directory structure..."
mkdir -p logs knowledge backups

# Install py-spy for performance profiling (if not present)
if ! command -v py-spy &> /dev/null; then
    echo "📊 Installing py-spy for performance profiling..."
    if command -v cargo &> /dev/null; then
        cargo install py-spy
    else
        echo "⚠️  Cargo not available - install Rust to get py-spy"
        echo "   Alternatively: curl -L https://github.com/benfred/py-spy/releases/download/v0.3.14/py-spy-v0.3.14-x86_64-unknown-linux-gnu.tar.gz | tar xz"
    fi
fi

# Validate configuration
echo "🔧 Validating configuration..."
python -c "
import yaml, sys
try:
    with open('config/system.yaml', 'r') as f:
        config = yaml.safe_load(f)
    print('✓ Configuration valid')
    
    # Check critical security settings
    security = config.get('security', {})
    if security.get('require_llm_validation'):
        print('✓ LLM validation enabled')
    else:
        print('⚠️  LLM validation disabled - consider enabling for production')
        
except Exception as e:
    print(f'✗ Configuration error: {e}')
    sys.exit(1)
"

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Test critical components
echo "🧪 Testing critical components..."
python scripts/test_safe_fixes.py
python scripts/test_basic_code_analysis.py

# Setup systemd service (if root)
if [ "$EUID" -eq 0 ]; then
    echo "🔧 Installing systemd service..."
    cat > /etc/systemd/system/ai-daemon.service << EOF
[Unit]
Description=High-Assurance AI System Daemon
After=network.target

[Service]
Type=exec
User=$SUDO_USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python -m core.daemon
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable ai-daemon
    echo "✓ Systemd service installed and enabled"
fi

echo "🎉 High-Assurance AI Daemon deployment complete!"
echo ""
echo "Next steps:"
echo "1. Review config/system.yaml for your environment"
echo "2. Start the daemon: ./scripts/start.sh"
echo "3. Monitor logs: tail -f logs/structured_daemon.log"
echo "4. Check security findings: tail -f logs/security_findings.jsonl"