#!/usr/bin/env python
"""
Simple utility to generate a valid bearer token for testing the Epistemix API.

Usage:
    python generate_token.py <user_id>

Example:
    python generate_token.py 123

This will output a bearer token that can be used with curl or other tools:
    curl -H "Offline-Token: Bearer ..." http://localhost:5000/jobs
"""

import sys

from epistemix_api.models.user import UserToken


def main():
    if len(sys.argv) <= 2:
        print("Usage: python generate_token.py <user_id> <scopes_hash>")
        print("Example: python generate_token.py 123 abc123")
        sys.exit(1)

    try:
        user_id = int(sys.argv[1])
    except ValueError:
        print(f"Error: user_id must be an integer, got '{sys.argv[1]}'")
        sys.exit(1)

    if user_id <= 0:
        print("Error: user_id must be positive")
        sys.exit(1)

    scopes_hash = sys.argv[2] if len(sys.argv) > 2 else ""

    # Generate the token
    token = UserToken.generate_bearer_token(user_id, scopes_hash)

    print(f"Generated bearer token for user_id {user_id}:")
    print(token)
    print()
    print("You can use this token with curl:")
    print(f'curl -H "Offline-Token: {token}" http://localhost:5000/jobs')


if __name__ == "__main__":
    main()
