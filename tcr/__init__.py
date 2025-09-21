"""TCR (Test && Commit || Revert) - AI-constrained development pattern."""

__version__ = "0.1.0"

from .cli import (
    TCRConfig,
    TCRHandler,
    TCRRunner,
    list_sessions,
    stop_session,
    main,
    get_or_generate_session_id,
    get_log_file_path,
)

__all__ = [
    "TCRConfig",
    "TCRHandler",
    "TCRRunner",
    "list_sessions",
    "stop_session",
    "main",
    "get_or_generate_session_id",
    "get_log_file_path",
]