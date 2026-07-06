from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Verdict(str, Enum):
    STRONG_OK = "strong_ok"
    WEAK_OK = "weak_ok"
    SUSPECT_OK = "suspect_ok"
    CHALLENGE = "challenge"
    BLOCKED = "blocked"
    RATE_LIMITED = "rate_limited"
    AUTH_REQUIRED = "auth_required"
    NOT_FOUND = "not_found"
    UNSAFE_URL = "unsafe_url"
    UNKNOWN = "unknown"


TERMINAL_NONSUCCESS = {
    Verdict.AUTH_REQUIRED,
    Verdict.NOT_FOUND,
    Verdict.UNSAFE_URL,
}


@dataclass(slots=True)
class Attempt:
    phase: str
    executor: str
    url: str
    url_transform: str = "original"
    identity: str | None = None
    referer: str = ""
    status: int = 0
    body_size: int = 0
    verdict: Verdict = Verdict.UNKNOWN
    reasons: list[str] = field(default_factory=list)
    elapsed_ms: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["verdict"] = self.verdict.value
        return data


@dataclass(slots=True)
class FetchResult:
    ok: bool
    content: str = ""
    final_url: str = ""
    verdict: Verdict = Verdict.UNKNOWN
    summary: str = ""
    trace: list[Attempt] = field(default_factory=list)
    stop_reason: str = ""
    untried_routes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, *, include_content: bool = True, max_content_chars: int | None = None) -> dict[str, Any]:
        content = self.content if include_content else ""
        if max_content_chars is not None and len(content) > max_content_chars:
            content = content[:max_content_chars]
        return {
            "ok": self.ok,
            "content": content,
            "content_length": len(self.content),
            "final_url": self.final_url,
            "verdict": self.verdict.value,
            "summary": self.summary,
            "trace": [attempt.to_dict() for attempt in self.trace],
            "stop_reason": self.stop_reason,
            "untried_routes": list(self.untried_routes),
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class ValidationResult:
    verdict: Verdict
    reasons: list[str] = field(default_factory=list)
    body_size: int = 0
    status: int = 0
    matched_selectors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.verdict in {Verdict.STRONG_OK, Verdict.WEAK_OK}


@dataclass(slots=True)
class ResponseEnvelope:
    status_code: int
    text: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    content: bytes | None = None

    @property
    def body_size(self) -> int:
        if self.content is not None:
            return len(self.content)
        return len(self.text.encode("utf-8", "ignore"))
