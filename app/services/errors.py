"""Application-level errors raised by service use cases."""


class ApplicationError(Exception):
    """Base error that adapters can translate without leaking DB exceptions."""

    status_code = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class DataIntegrityError(ApplicationError):
    """A write violated a database-backed domain integrity rule."""

    status_code = 409
