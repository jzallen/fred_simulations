"""
User domain model for the Epistemix API.
Contains the core business logic and rules for user entities.
"""

import base64
import binascii
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class UserRole(Enum):
    """Enumeration of possible user roles."""

    USER = "user"
    ADMIN = "admin"
    RESEARCHER = "researcher"
    ANALYST = "analyst"


class UserStatus(Enum):
    """Enumeration of possible user statuses."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


@dataclass
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


@dataclass
class User:
    """
    User domain entity representing a user in the Epistemix system.

    This is a core business entity that encapsulates the essential
    properties and behaviors of a user.
    """

    # Required fields
    id: int

    # Optional fields with defaults
    username: str | None = None
    email: str | None = None
    role: UserRole = UserRole.USER
    status: UserStatus = UserStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_login: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization validation and setup."""
        self._validate()

    def _validate(self):
        """Validate the user entity according to business rules."""
        if self.id <= 0:
            raise ValueError("User ID must be positive")

        if self.email and not self._is_valid_email(self.email):
            raise ValueError("Invalid email format")

        if self.username and len(self.username.strip()) == 0:
            raise ValueError("Username cannot be empty")

    def _is_valid_email(self, email: str) -> bool:
        """Validate email format using a simple regex."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    def update_status(self, new_status: UserStatus) -> None:
        """Update the user status with business logic validation."""
        if not self._is_valid_status_transition(self.status, new_status):
            raise ValueError(
                f"Invalid status transition from {self.status.value} to {new_status.value}"
            )

        self.status = new_status
        self._touch_updated_at()

    def _is_valid_status_transition(self, from_status: UserStatus, to_status: UserStatus) -> bool:
        """Validate if a status transition is allowed according to business rules."""
        # Define valid transitions
        valid_transitions = {
            UserStatus.PENDING: [UserStatus.ACTIVE, UserStatus.INACTIVE],
            UserStatus.ACTIVE: [UserStatus.INACTIVE, UserStatus.SUSPENDED],
            UserStatus.INACTIVE: [UserStatus.ACTIVE, UserStatus.SUSPENDED],
            UserStatus.SUSPENDED: [UserStatus.ACTIVE, UserStatus.INACTIVE],
        }

        return to_status in valid_transitions.get(from_status, [])

    def update_role(self, new_role: UserRole) -> None:
        """Update the user role."""
        self.role = new_role
        self._touch_updated_at()

    def record_login(self) -> None:
        """Record a user login timestamp."""
        self.last_login = datetime.utcnow()
        self._touch_updated_at()

    def _touch_updated_at(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()

    def is_active(self) -> bool:
        """Check if the user is in an active state."""
        return self.status == UserStatus.ACTIVE

    def can_create_jobs(self) -> bool:
        """Check if the user can create jobs based on their role and status."""
        return self.is_active() and self.role in {
            UserRole.USER,
            UserRole.RESEARCHER,
            UserRole.ANALYST,
            UserRole.ADMIN,
        }

    def can_manage_users(self) -> bool:
        """Check if the user can manage other users."""
        return self.is_active() and self.role == UserRole.ADMIN

    def to_dict(self) -> dict[str, Any]:
        """Convert the user to a dictionary representation."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "status": self.status.value,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
            "lastLogin": self.last_login.isoformat() if self.last_login else None,
            "metadata": self.metadata,
        }

    @classmethod
    def create_new(
        cls, user_id: int, username: str = None, email: str = None, role: UserRole = UserRole.USER
    ) -> "User":
        """
        Factory method to create a new user with proper initialization.

        Args:
            user_id: Unique identifier for the user
            username: Optional username
            email: Optional email address
            role: User role (defaults to USER)

        Returns:
            A new User instance with ACTIVE status
        """
        user = cls(id=user_id, username=username, email=email, role=role, status=UserStatus.ACTIVE)

        return user

    def __eq__(self, other) -> bool:
        """Check equality based on user ID."""
        if not isinstance(other, User):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on user ID."""
        return hash(self.id)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"User(id={self.id}, username={self.username}, role={self.role.value}, "
            f"status={self.status.value})"
        )
