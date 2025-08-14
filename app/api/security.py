# app/api/security.py
from functools import wraps
from urllib.parse import urlparse
from flask import request, current_app, jsonify, make_response

def _normalize_domains(raw):
    """
    Returns a set of normalized domains/origins:
    - Accepts bare domains (example.com) or full origins (https://example.com)
    - Stored lowercase, trimmed
    """
    items = [d.strip().lower() for d in raw or [] if d and d.strip()]
    return set(items)

def _host_from_origin(origin):
    if not origin:
        return None
    try:
        parsed = urlparse(origin)
        # If a bare domain was sent in Origin (unlikely), fall back
        return parsed.hostname or origin.lower()
    except Exception:
        return origin.lower()

def _domain_allowed(origin, allowed_domains):
    """
    Allows if:
      - origin is a full origin in the allow-list, OR
      - the origin's host exactly matches an allowed bare domain, OR
      - the origin's host is a subdomain of an allowed bare domain.
    """
    if not origin:
        return False

    o = origin.lower()
    host = _host_from_origin(origin)

    if o in allowed_domains:  # full origin match
        return True

    for d in allowed_domains:
        # bare-domain match or subdomain match
        if "://" not in d:
            if host == d or host.endswith(f".{d}"):
                return True
    return False

def _apply_cors(resp, origin, app):
    allowed = app.config.get("ALLOWED_DOMAINS_SET", set())
    custom_header = app.config.get("CUSTOM_AUTH_HEADER", "X-RFP-Customer")
    api_key_header = app.config.get("API_KEY_HEADER", "X-API-Key")

    if origin and _domain_allowed(origin, allowed):
        # Echo back the allowed Origin
        resp.headers["Access-Control-Allow-Origin"] = origin
    else:
        # For denied/unknown origins, do not reflect arbitrary origins
        resp.headers["Access-Control-Allow-Origin"] = "null"

    resp.headers["Vary"] = "Origin"
    resp.headers["Access-Control-Allow-Headers"] = f"{custom_header}, {api_key_header}, Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    resp.headers["Access-Control-Max-Age"] = "3600"
    return resp

def secure_endpoint():
    """
    Decorator to guard an endpoint with the policy:
      1) If Origin is allowed AND CUSTOM_AUTH_HEADER present -> authorized
      2) Else if CUSTOM_AUTH_HEADER present AND API_KEY_HEADER matches a key in .env -> authorized
      3) Otherwise -> denied

    Always adds CORS headers and logs decision using current_app.logger.
    """
    def decorator(view_fn):
        @wraps(view_fn)
        def wrapped(*args, **kwargs):
            app = current_app

            # Pull config prepared at startup
            allowed = app.config.get("ALLOWED_DOMAINS_SET", set())
            custom_header = app.config.get("CUSTOM_AUTH_HEADER", "X-RFP-Customer")
            api_key_header = app.config.get("API_KEY_HEADER", "X-API-Key")
            valid_keys = set(app.config.get("API_KEYS_LIST", []))

            # Extract request bits
            origin = request.headers.get("Origin") or request.headers.get("Referer")
            custom_header_val = request.headers.get(custom_header)
            api_key_val = request.headers.get(api_key_header)

            # Preflight support
            if request.method == "OPTIONS":
                resp = make_response("", 204)
                _apply_cors(resp, origin, app)
                app.logger.info(
                    "CORS preflight for %s %s origin=%s",
                    request.method, request.path, origin
                )
                return resp

            # Decision matrix
            granted = False
            reason = "denied"

            if origin and _domain_allowed(origin, allowed) and custom_header_val:
                granted = True
                reason = "allowed-origin + custom-header"
            elif custom_header_val and api_key_val and api_key_val in valid_keys:
                granted = True
                reason = "api-key + custom-header (origin not allowed)"

            # Log the decision using your configured logger
            app.logger.info(
                "Auth %s for %s %s | origin=%s custom_header_present=%s api_key_present=%s reason=%s",
                "GRANTED" if granted else "DENIED",
                request.method, request.path,
                origin, bool(custom_header_val), bool(api_key_val), reason
            )

            if not granted:
                resp = jsonify({"error": "Unauthorized"}), 403
            else:
                resp = view_fn(*args, **kwargs)

            # Make a response object (handles tuple or Response)
            resp = make_response(resp)
            _apply_cors(resp, origin, app)
            return resp
        return wrapped
    return decorator
