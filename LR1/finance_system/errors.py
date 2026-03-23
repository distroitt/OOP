class FinanceSystemError(Exception):
    pass


class ValidationError(FinanceSystemError):
    pass


class AuthorizationError(FinanceSystemError):
    pass


class NotFoundError(FinanceSystemError):
    pass


class UndoError(FinanceSystemError):
    pass
