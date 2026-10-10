"""Dependency-free API abuse protection for desktop and single-instance deployments.

Cloud deployments must also enforce distributed limits at the edge (for example,
Cloud Armor or an API gateway). This limiter provides defence in depth and keeps
the local desktop API protected without requiring an external cache. Verified
users receive independent endpoint budgets so a shared serverless proxy address
cannot exhaust every customer's allowance; anonymous and invalid-credential
traffic remains IP-scoped.
"""
from __future__ import annotations

import os
import hashlib
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
HEALTH_PATHS = {"/", "/health/live", "/health/ready"}


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int
    client_ip: str
    category: str


class IpRateLimiter:
    """Fixed-window budgets by endpoint risk and verified caller."""

    def __init__(self) -> None:
        self.window_seconds = max(10, int(os.getenv("ASSISTANT_RATE_LIMIT_WINDOW_SECONDS", "60")))
        self.read_limit = max(10, int(os.getenv("ASSISTANT_RATE_LIMIT_READS", "180")))
        self.write_limit = max(5, int(os.getenv("ASSISTANT_RATE_LIMIT_WRITES", "60")))
        legacy_auth_limit = os.getenv("ASSISTANT_RATE_LIMIT_AUTH", "20")
        self.login_limit = max(3, int(os.getenv("ASSISTANT_RATE_LIMIT_LOGIN", legacy_auth_limit)))
        self.signup_limit = max(3, int(os.getenv("ASSISTANT_RATE_LIMIT_SIGNUP", "8")))
        self.anonymous_limit = max(3, int(os.getenv("ASSISTANT_RATE_LIMIT_MISSING_LOGIN", "30")))
        self.ai_limit = max(3, int(os.getenv("ASSISTANT_RATE_LIMIT_AI", "30")))
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def client_ip(self, request) -> str:
        if os.getenv("ASSISTANT_TRUST_PROXY", "false").strip().lower() in {"1", "true", "yes"}:
            forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
            if forwarded:
                return forwarded[:64]
        return (request.client.host if request.client else "unknown")[:64]

    @staticmethod
    def _has_bearer_token(request) -> bool:
        authorization = request.headers.get("authorization", "").strip()
        return authorization.lower().startswith("bearer ") and bool(authorization[7:].strip())

    def category(self, request) -> str:
        path = request.url.path.rstrip("/").lower() or "/"
        method = request.method.upper()

        if path in HEALTH_PATHS:
            return "health"
        if any(part in path for part in ("/sign-up", "/signup", "/register")):
            return "signup"
        if (
            path.startswith(("/login", "/auth"))
            or path.startswith("/settings/auth/")
            or path == "/settings/auth"
        ):
            return "login"
        auth_required = os.getenv("ASSISTANT_AUTH_REQUIRED", "false").strip().lower() in {"1", "true", "yes"}
        if auth_required and not self._has_bearer_token(request):
            return "missing-login"
        # Read-only metadata and preflights do not execute model inference.
        # Keep expensive GET inference endpoints in the AI budget.
        if method in {"OPTIONS", "GET", "HEAD"}:
            return "read"
        if path.startswith(("/api/conversations", "/api/calls")):
            return "ai"
        return "write" if method not in SAFE_METHODS else "read"

    def limit_for(self, category: str) -> int:
        return {
            "health": self.read_limit,
            "login": self.login_limit,
            "signup": self.signup_limit,
            "missing-login": self.anonymous_limit,
            "ai": self.ai_limit,
            "write": self.write_limit,
            "read": self.read_limit,
        }[category]

    def check(self, request, *, identity=None, force_ip=False, category_override=None) -> RateLimitDecision:
        category = category_override or self.category(request)
        limit = self.limit_for(category)
        ip = self.client_ip(request)
        if category == "health":
            return RateLimitDecision(True, limit, limit, 0, ip, category)

        subject = getattr(identity, "subject", None) if identity is not None else None
        if subject and not force_ip:
            subject_key = hashlib.sha256(str(subject).encode("utf-8")).hexdigest()[:24]
            bucket_owner = f"subject:{subject_key}"
        else:
            bucket_owner = f"ip:{ip}"
        bucket = f"{bucket_owner}:{category}"
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            events = self._requests[bucket]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, int(self.window_seconds - (now - events[0])))
                return RateLimitDecision(False, limit, 0, retry_after, ip, category)
            events.append(now)
            remaining = max(0, limit - len(events))
            if len(self._requests) > 20_000:
                stale = [key for key, values in self._requests.items() if not values or values[-1] <= cutoff]
                for key in stale[:5_000]:
                    self._requests.pop(key, None)
        return RateLimitDecision(True, limit, remaining, 0, ip, category)
