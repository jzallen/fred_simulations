#!/bin/bash
# Run cfn-nag security scanner via Docker
#
# Usage: ./run-cfn-nag.sh <template-path>
# Example: ./run-cfn-nag.sh ../templates/s3/s3-upload-bucket.json
#
# cfn-nag scans CloudFormation templates for security anti-patterns (140+ built-in rules)
# Docker image: stelligent/cfn_nag (MIT License)

set -e

if [ -z "$1" ]; then
    echo "Error: Template path required"
    echo "Usage: $0 <template-path>"
    exit 1
fi

template_path="$1"

if [ ! -f "$template_path" ]; then
    echo "Error: Template file not found: $template_path"
    exit 1
fi

# Get absolute paths for Docker volume mounting
template_dir="$(cd "$(dirname "$template_path")" && pwd)"
template_file="$(basename "$template_path")"

echo "Running cfn-nag security scan on: $template_file"
echo "----------------------------------------"

# Run cfn-nag via Docker
# --rm: Remove container after run
# -v: Mount template directory as read-only
docker run --rm \
    -v "${template_dir}:/templates:ro" \
    stelligent/cfn_nag \
    "/templates/${template_file}"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "----------------------------------------"
    echo "✓ No security violations found"
else
    echo "----------------------------------------"
    echo "✗ Security violations detected (exit code: $exit_code)"
    echo ""
    echo "See above for details. To suppress specific findings, add metadata to template:"
    echo ""
    echo '  "Metadata": {'
    echo '    "cfn_nag": {'
    echo '      "rules_to_suppress": ['
    echo '        {'
    echo '          "id": "W51",'
    echo '          "reason": "Justification for suppression"'
    echo '        }'
    echo '      ]'
    echo '    }'
    echo '  }'
fi

exit $exit_code
