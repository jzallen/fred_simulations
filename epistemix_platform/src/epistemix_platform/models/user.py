"""
User authentication model for the Epistemix API.
Contains bearer token parsing and validation.
"""

import base64
import binascii
import json
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class UserToken:
    """
    User token model that handles bearer token parsing and validation.

    Extracts user_id and scopes_hash from a base64-encoded bearer token.
    """

    # TODO: There's nothing in the epx client code that suggests scopes_hash exists,
    # but the idea is that you could look up scopes by user_id, hash them, then compare
    # against the scopes_hash in the token.
    user_id: int
    scopes_hash: str  # placeholder for future scope handling
    raw_token: str

    @classmethod
    def generate_bearer_token(cls, user_id: int, scopes_hash: str = None) -> str:
        """
        Generate a bearer token string from a user_id.

        This is a convenience method for generating valid bearer tokens,
        particularly useful for testing and CLI integration.

        Args:
            user_id: The user ID to encode in the token
            scopes_hash: Optional scopes hash (defaults to a placeholder value)

        Returns:
            A properly formatted bearer token string (e.g., "Bearer <base64-token>")

        Example:
            >>> token = UserToken.generate_bearer_token(123)
            >>> print(token)
            Bearer eyJ1c2VyX2lkIjogMTIzLCAic2NvcGVzX2hhc2giOiAiZGVmYXVsdF9zY29wZXNfaGFzaCJ9
        """
        # TODO: Implement proper scopes hash logic based on user permissions
        if scopes_hash is None:
            scopes_hash = "default_scopes_hash"

        token_data = {"user_id": user_id, "scopes_hash": scopes_hash}

        token_json = json.dumps(token_data)
        token_bytes = token_json.encode("utf-8")
        token_b64 = base64.b64encode(token_bytes).decode("utf-8")

        return f"Bearer {token_b64}"

    @classmethod
    def from_bearer_token(cls, bearer_token: str) -> "UserToken":
        """
        Create a UserToken from a bearer token string.

        Args:
            bearer_token: The full bearer token string (e.g., "Bearer <base64-token>")

        Returns:
            UserToken instance with parsed user_id and scopes_hash

        Raises:
            ValueError: If token format is invalid or decoding fails
        """
        if not bearer_token:
            raise ValueError("Bearer token cannot be empty")

        if not bearer_token.startswith("Bearer "):
            raise ValueError("Invalid bearer token format. Expected 'Bearer <token>'")

        bearer_keyword, token = bearer_token.strip().split(" ", 1)

        try:
            # Base64 decode the token
            decoded_bytes = base64.b64decode(token)
            decoded_str = decoded_bytes.decode("utf-8")

            # Parse the JSON
            token_data = json.loads(decoded_str)

            # Validate required keys
            if "user_id" not in token_data:
                raise ValueError("Token missing required 'user_id' field")
            if "scopes_hash" not in token_data:
                raise ValueError("Token missing required 'scopes_hash' field")

            # Create and return UserToken instance
            return cls(
                user_id=int(token_data["user_id"]),
                scopes_hash=token_data["scopes_hash"],
                raw_token=bearer_token,
            )

        except (binascii.Error, UnicodeDecodeError) as e:
            raise ValueError(f"Failed to decode base64 token: {e}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse token JSON: {e}") from e
        except (ValueError, TypeError) as e:
            if "invalid literal for int()" in str(e):
                raise ValueError("Token contains invalid user_id or scopes_hash values") from e
            raise

    def to_dict(self) -> dict[str, Any]:
        """Convert the token to a dictionary representation."""
        return {"user_id": self.user_id, "scopes_hash": self.scopes_hash}

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"UserToken(user_id={self.user_id}, scopes_hash={self.scopes_hash})"
