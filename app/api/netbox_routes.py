# api/netbox_routes.py
import os
import requests
from flask import Blueprint, jsonify, current_app, request
from app.api.security import secure_endpoint

netbox_api_bp = Blueprint("netbox_api", __name__)

def _nbx_url() -> str:
    """
    Resolve the NetBox base URL (e.g., http://192.168.1.101:8000), normalized without trailing slash.
    """
    base = (os.getenv("NETBOX_API_URL") or "").strip().rstrip("/")
    if not base:
        raise RuntimeError("NETBOX_API_URL is not set")
    # If user forgot scheme, default to http (common in lab networks)
    if not base.startswith(("http://", "https://")):
        base = f"http://{base}"
    return base

def _nbx_token() -> str:
    token = os.getenv("NETBOX_API_TOKEN") or ""
    if not token:
        raise RuntimeError("NETBOX_API_TOKEN is not set")
    return token

@netbox_api_bp.route("/sites", methods=["GET", "OPTIONS"])
@secure_endpoint()
def list_sites():
    """
    List NetBox sites
    ---
    tags:
      - NetBox
    security:
      - CustomHeader: []
        ApiKeyHeader: []
    parameters:
      - in: query
        name: q
        schema:
          type: string
        description: Optional search term. Passed through to NetBox as ?q=<term>.
      - in: query
        name: name
        schema:
          type: string
        description: Optional exact-name filter (NetBox filter param).
      - in: query
        name: slug
        schema:
          type: string
        description: Optional exact-slug filter (NetBox filter param).
      - in: query
        name: limit
        schema:
          type: integer
          minimum: 0
          maximum: 10000
          default: 0
        description: Max records to return. Default 0 returns all results (NetBox pagination).
      - in: query
        name: offset
        schema:
          type: integer
          minimum: 0
        description: Offset for pagination (ignored when limit=0).
    responses:
      200:
        description: Sites successfully retrieved
        content:
          application/json:
            example:
              status: ok
              result:
                count: 2
                results:
                  - id: 1
                    name: "Chicago-DC"
                    slug: "chicago-dc"
                    status: "active"
                    region: "Midwest"
                    tenant: "Internal"
                  - id: 2
                    name: "Dallas-Edge"
                    slug: "dallas-edge"
                    status: "planned"
                    region: "South"
                    tenant: null
      400:
        description: Bad request (invalid parameters or missing configuration)
        content:
          application/json:
            example:
              status: error
              error:
                message: "Invalid query parameter: limit"
      502:
        description: NetBox backend error or transport failure
        content:
          application/json:
            example:
              status: error
              error:
                message: "Bad gateway to NetBox"
      500:
        description: Internal server error
        content:
          application/json:
            example:
              status: error
              error:
                message: "Internal server error"
    """
    current_app.logger.info("NetBox /sites endpoint hit")

    try:
        base = _nbx_url()
        token = _nbx_token()

        # Query params
        q = request.args.get("q")
        name = request.args.get("name")
        slug = request.args.get("slug")
        limit_arg = request.args.get("limit", "0")
        offset_arg = request.args.get("offset")

        # Validate ints
        params = {}
        try:
            limit_val = int(limit_arg)
            if limit_val < 0:
                raise ValueError
            params["limit"] = limit_val
        except ValueError:
            current_app.logger.warning("Invalid 'limit' param: %r", limit_arg)
            return jsonify({"status": "error", "error": {"message": "Invalid query parameter: limit"}}), 400

        if offset_arg is not None:
            try:
                offset_val = int(offset_arg)
                if offset_val < 0:
                    raise ValueError
                params["offset"] = offset_val
            except ValueError:
                current_app.logger.warning("Invalid 'offset' param: %r", offset_arg)
                return jsonify({"status": "error", "error": {"message": "Invalid query parameter: offset"}}), 400

        # Filters (NetBox supports ?q, ?name, ?slug for dcim.sites)
        if q:
            params["q"] = q
        if name:
            params["name"] = name
        if slug:
            params["slug"] = slug

        url = f"{base}/api/dcim/sites/"
        headers = {
            "Authorization": f"Token {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        current_app.logger.info("NetBox request start: GET %s params=%s", url, {k: v for k, v in params.items() if v is not None})

        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Normalize a friendly, compact projection in 'results'
        results = []
        print(data)
        for item in (data.get("results") or []):
            results.append({
                "id": item.get("id"),
                "name": item.get("name"),
                "status": (item.get("status") or {}).get("label") if isinstance(item.get("status"), dict) else item.get("status"),
                "location": item.get("physical_address"),
                "lat": item.get("latitude"),
                "long": item.get("longitude"),
            })

        current_app.logger.info("NetBox request ok: %d sites returned", len(results))
        return jsonify({"status": "ok", "result": {"count": len(results), "results": results}}), 200

    except requests.HTTPError as http_err:
        current_app.logger.exception("Transport error calling NetBox")
        return jsonify({"status": "error", "error": {"message": str(http_err)}}), 502
    except RuntimeError as cfg_err:
        current_app.logger.error("NetBox config error: %s", cfg_err)
        return jsonify({"status": "error", "error": {"message": str(cfg_err)}}), 400
    except Exception:
        current_app.logger.exception("Unhandled error in /api/netbox/sites")
        return jsonify({"status": "error", "error": {"message": "Internal server error"}}), 500
