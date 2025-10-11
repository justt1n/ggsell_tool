class APIError(Exception):
    pass


class QueueLimitExceededError(APIError):
    """Raised when the queue limit is exceeded."""
    pass
