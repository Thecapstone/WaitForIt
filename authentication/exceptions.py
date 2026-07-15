class NoSessionFingerprintError(Exception):
    """Error raised when a users session fingerprint is not a match or missing"""

    def __init__(self, fingerprint: str, message: str = "No active session found"):
        self.fingerprint = fingerprint
        super().__init__(message)

    def __str__(self):
        return f"No active session found for fingerprint: {self.fingerprint}"
