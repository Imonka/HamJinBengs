"""Domain errors. Services raise these; main.py turns them into JSON responses ({"error": ...})."""


class AppError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def payload(self) -> dict:
        return {"error": self.message}


class BadRequest(AppError):
    status_code = 400


class Unauthorized(AppError):
    status_code = 401


class Forbidden(AppError):
    status_code = 403


class NotFound(AppError):
    status_code = 404


class Conflict(AppError):
    status_code = 409


class TooManyAttempts(AppError):
    status_code = 429


class RuleViolation(Conflict):
    """A change breaks one or more scheduling rules (hard constraints)."""

    def __init__(self, message: str, violations: list[str]):
        super().__init__(message)
        self.violations = violations

    def payload(self) -> dict:
        return {"error": self.message, "violations": self.violations}
