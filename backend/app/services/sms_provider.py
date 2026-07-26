from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SmsSendResult:
    success: bool
    external_message_id: str | None = None
    error: str | None = None


class SmsProvider(Protocol):
    name: str

    def send_sms(self, *, phone: str, text: str) -> SmsSendResult:
        ...


class DummySmsProvider:
    name = "dummy"

    def send_sms(self, *, phone: str, text: str) -> SmsSendResult:
        # Deterministic mock provider for development and tests.
        if not phone.strip():
            return SmsSendResult(success=False, error="Phone is empty")
        if not text.strip():
            return SmsSendResult(success=False, error="Text is empty")
        external_id = f"dummy-{abs(hash((phone, text)))}"
        return SmsSendResult(success=True, external_message_id=external_id)
