class ConnectionException(Exception):
    """
    Exception raised for errors when connecting MQTT client.

    Attributes:
        message (str): The error message describing the exception.
    """

    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message


class DecodingException(Exception):
    """
    Exception raised for errors in the decoding process.

    This exception is raised when a message is received on the wrong topic
    or when there is an issue with decoding the message.

    Attributes:
        message (str): The error message describing the exception.
    """

    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message
