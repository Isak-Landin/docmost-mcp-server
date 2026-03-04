# docmost-fetcher/api/errors.py
from __future__ import annotations

# docmost-fetcher/api/errors.py
from dataclasses import dataclass
from typing import Any, Dict, Tuple, Optional

Result = Tuple[bool, Dict[str, Any]]

@dataclass
class ApiError(Exception):
    code: str
    message: str
    value: Any = None
    http_status: int = 400

    def to_dict(self) -> Dict[str, Any]:
        return {"error": self.code, "message": self.message, "value": self.value}

def default_http_status(code: str) -> int:
    if code == INVALID_INPUT:
        return 400
    if code == NOT_FOUND:
        return 404
    if code in (DB_ERROR, UNEXPECTED_ERROR):
        return 500
    return 400

def must(res: Result) -> Any:
    """
    Use inside routes (or higher-level wrappers).
    If ok -> returns payload.
    If err -> raises ApiError with same error/message/value.
    """
    ok_flag, d = res
    if ok_flag:
        return d["payload"]

    code = d.get("error", UNEXPECTED_ERROR)
    msg = d.get("message", ERROR_MESSAGES.get(code, "Unknown error."))
    val = d.get("value", None)
    raise ApiError(code=code, message=msg, value=val, http_status=default_http_status(code))

# Stable error codes (docmost-fetcher internal contract)
INVALID_INPUT = "invalid_input"
NOT_FOUND = "not_found"
DB_ERROR = "db_error"
UNEXPECTED_ERROR = "unexpected_error"

ERROR_MESSAGES: Dict[str, str] = {
    INVALID_INPUT: "Invalid input.",
    NOT_FOUND: "Resource not found.",
    DB_ERROR: "Database error.",
    UNEXPECTED_ERROR: "Unexpected error took place during runtime. This could mean that an inter.",
}

def ok(payload: Any) -> Tuple[bool, Dict[str, Any]]:
    # Success: payload only (per your rule)
    return True, {"payload": payload}

def err(code: str, value: Any = None, message: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
    # Failure: error + message + value only (per your rule)
    if message is None:
        message = ERROR_MESSAGES.get(code, "Unknown error.")
    return False, {"error": code, "message": message, "value": value}