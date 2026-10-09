class ConnectionException(Exception):
    """Raised when MQTT client connection fails."""

    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message


class DecodingException(Exception):
    """Raised when message decoding fails.

    Occurs when a message is received on an unexpected topic or when decoding fails.
    """

    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message


class NoValueException(Exception):
    """Raised when an empty string is received instead of a typed value.

    Args:
        the_type: Expected type for the value.
    """

    def __init__(self, the_type: type):
        self.message = f"Empty message string received, waiting for {the_type}"

    def __str__(self):
        return self.message
