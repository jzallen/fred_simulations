#!/bin/bash
# Install cfn-guard binary for CloudFormation policy validation
#
# Usage: ./install-cfn-guard.sh [version]
# Example: ./install-cfn-guard.sh 3.0.0
#
# cfn-guard is AWS's policy-as-code tool for validating CloudFormation templates
# GitHub: https://github.com/aws-cloudformation/cloudformation-guard
# License: Apache 2.0 (FOSS)

set -e

VERSION="${1:-3.0.0}"
INSTALL_DIR="${2:-/usr/local/bin}"

echo "Installing cfn-guard v${VERSION}..."

# Detect platform
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
    Linux*)
        case "$ARCH" in
            x86_64) PLATFORM="linux-x86_64" ;;
            aarch64) PLATFORM="linux-aarch64" ;;
            *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
        esac
        ;;
    Darwin*)
        case "$ARCH" in
            x86_64) PLATFORM="macos-x86_64" ;;
            arm64) PLATFORM="macos-arm64" ;;
            *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
        esac
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

# Download URL
URL="https://github.com/aws-cloudformation/cloudformation-guard/releases/download/${VERSION}/cfn-guard-v${VERSION}-${PLATFORM}.tar.gz"

echo "Downloading from: $URL"
echo "Installing to: $INSTALL_DIR"

# Create temp directory
TMP_DIR="$(mktemp -d)"
trap "rm -rf $TMP_DIR" EXIT

# Download and extract
cd "$TMP_DIR"
curl -LO "$URL"
tar -xzf "cfn-guard-v${VERSION}-${PLATFORM}.tar.gz"

# Install binary
if [ -w "$INSTALL_DIR" ]; then
    mv cfn-guard "$INSTALL_DIR/"
    echo "✓ Installed cfn-guard to $INSTALL_DIR/cfn-guard"
else
    echo "Note: $INSTALL_DIR requires sudo access"
    sudo mv cfn-guard "$INSTALL_DIR/"
    echo "✓ Installed cfn-guard to $INSTALL_DIR/cfn-guard (sudo)"
fi

# Verify installation
if command -v cfn-guard >/dev/null 2>&1; then
    echo "✓ Installation successful!"
    cfn-guard --version
else
    echo "Warning: cfn-guard not found in PATH"
    echo "You may need to add $INSTALL_DIR to your PATH"
    echo ""
    echo "Add to ~/.bashrc or ~/.zshrc:"
    echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
fi

echo ""
echo "Next steps:"
echo "  1. Verify: cfn-guard --version"
echo "  2. Test: cfn-guard validate --data <template> --rules <rules>"
echo "  3. See: guard_rules/README.md for usage examples"
