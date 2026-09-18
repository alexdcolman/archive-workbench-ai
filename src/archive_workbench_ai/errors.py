from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PluginError(Exception):
    message: str
    exit_code: int
    code: str

    def __str__(self) -> str:
        return self.message


class InvalidRequestError(PluginError):
    def __init__(self, message: str):
        super().__init__(message, 2, "invalid_request")


class IncompatibleProtocolError(PluginError):
    def __init__(self, message: str):
        super().__init__(message, 3, "incompatible_protocol")


class InvalidInputError(PluginError):
    def __init__(self, message: str):
        super().__init__(message, 4, "invalid_input")


class RuntimeUnavailableError(PluginError):
    def __init__(self, message: str):
        super().__init__(message, 5, "runtime_unavailable")


class InferenceError(PluginError):
    def __init__(self, message: str):
        super().__init__(message, 7, "inference_error")
