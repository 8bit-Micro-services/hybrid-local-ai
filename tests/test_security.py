import base64
import hashlib
import hmac

from app.core.security import RateLimiter, verify_line_signature


def test_line_signature_is_verified_without_timing_leak():
    body = b'{"events":[]}'
    secret = "test-secret"
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    signature = base64.b64encode(digest).decode()

    assert verify_line_signature(body, signature, secret)
    assert not verify_line_signature(body, "wrong", secret)
    assert not verify_line_signature(body, signature, "wrong-secret")


def test_rate_limiter_rejects_after_limit():
    limiter = RateLimiter(limit=2, window_seconds=60)

    assert limiter.allow("user", now=100)
    assert limiter.allow("user", now=101)
    assert not limiter.allow("user", now=102)
    assert limiter.allow("user", now=161)
