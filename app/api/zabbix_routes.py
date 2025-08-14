# api/zabbix_routes.py
import os
import uuid
import requests
from flask import Blueprint, jsonify, current_app, request
from app.api.security import secure_endpoint

zabbix_api_bp = Blueprint('zabbix_api', __name__)

def _zbx_url() -> str:
    base = (os.getenv("ZABBIX_API_URL") or "").rstrip("/")
    if not base:
        raise RuntimeError("ZABBIX_API_URL is not set")
    return base if base.endswith("api_jsonrpc.php") else f"{base}/api_jsonrpc.php"

def _zbx_token() -> str:
    token = os.getenv("ZABBIX_API_TOKEN") or ""
    if not token:
        raise RuntimeError("ZABBIX_API_TOKEN is not set")
    return token

def _zbx_call(method: str, params: dict) -> dict:
    url = _zbx_url()
    token = _zbx_token()
    rpc_id = uuid.uuid4().hex

    payload = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": rpc_id}
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json-rpc",
    }

    current_app.logger.info("Zabbix request start: %s id=%s", method, rpc_id)
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        current_app.logger.warning("Zabbix API error: %s id=%s err=%s", method, rpc_id, data["error"])
    else:
        current_app.logger.info("Zabbix request ok: %s id=%s", method, rpc_id)
    return data


@zabbix_api_bp.route('/hosts', methods=['GET', 'OPTIONS'])
@secure_endpoint()
def hosts():
    """
    List Zabbix hosts (with inventory)
    ---
    tags:
      - Zabbix
    security:
      - CustomHeader: []
        ApiKeyHeader: []
    parameters:
      - in: query
        name: with_interfaces
        schema:
          type: boolean
          default: true
        description: Include host interfaces in the response (selectInterfaces).
      - in: query
        name: fields
        schema:
          type: string
        description: Comma-separated host fields to return (default is hostid,host,name).
      - in: query
        name: limit
        schema:
          type: integer
          minimum: 1
          maximum: 10000
        description: Maximum number of hosts to return.
      - in: query
        name: with_inventory
        schema:
          type: boolean
          default: true
        description: Include host inventory in the response (selectInventory).
      - in: query
        name: inventory_fields
        schema:
          type: string
        description: "Comma-separated inventory fields to return, if omitted and with_inventory true, returns all."
    responses:
      200:
        description: Hosts successfully retrieved
        content:
          application/json:
            example:
              status: ok
              result:
                - hostid: "10084"
                  host: "Zabbix server"
                  name: "Zabbix server"
                  interfaces:
                    - interfaceid: "1"
                      ip: "127.0.0.1"
                      dns: ""
                  inventory:
                    type: "Server"
                    os: "Ubuntu 22.04"
                    serialno_a: "XYZ123"
      400:
        description: Bad request (invalid parameters or missing configuration)
        content:
          application/json:
            example:
              status: error
              error:
                message: "Invalid query parameter: limit"
      502:
        description: Zabbix backend error or transport failure
        content:
          application/json:
            example:
              status: error
              error:
                message: "Not authorized."
                code: -32602
      500:
        description: Internal server error
        content:
          application/json:
            example:
              status: error
              error:
                message: "Internal server error"
    """
    current_app.logger.info("Zabbix /hosts endpoint hit")

    try:
        # Query params
        with_interfaces = str(request.args.get("with_interfaces", "true")).lower() != "false"
        with_inventory = str(request.args.get("with_inventory", "true")).lower() != "false"
        fields_arg = request.args.get("fields", "")
        inv_fields_arg = request.args.get("inventory_fields", "")
        limit_arg = request.args.get("limit")

        # Base host fields
        output_fields = ["hostid", "host", "name"]
        if fields_arg:
            output_fields = [f.strip() for f in fields_arg.split(",") if f.strip()]

        params = {"output": output_fields}

        if with_interfaces:
            params["selectInterfaces"] = ["interfaceid", "ip"]

        if with_inventory:
            if inv_fields_arg.strip():
                inv_fields = [f.strip() for f in inv_fields_arg.split(",") if f.strip()]
                params["selectInventory"] = inv_fields
            else:
                # Return full inventory when no subset is requested
                params["selectInventory"] = "extend"

        if limit_arg:
            try:
                limit_val = int(limit_arg)
                if limit_val <= 0:
                    raise ValueError
                params["limit"] = limit_val
            except ValueError:
                current_app.logger.warning("Invalid 'limit' param: %r", limit_arg)
                return jsonify({"status": "error", "error": {"message": "Invalid query parameter: limit"}}), 400

        # Call Zabbix
        data = _zbx_call("host.get", params)

        if "error" in data:
            return jsonify({"status": "error", "error": data["error"]}), 502

        return jsonify({"status": "ok", "result": data.get("result", [])}), 200

    except requests.HTTPError as http_err:
        current_app.logger.exception("Transport error calling Zabbix")
        return jsonify({"status": "error", "error": {"message": str(http_err)}}), 502
    except RuntimeError as cfg_err:
        current_app.logger.error("Zabbix config error: %s", cfg_err)
        return jsonify({"status": "error", "error": {"message": str(cfg_err)}}), 400
    except Exception:
        current_app.logger.exception("Unhandled error in /api/zabbix/hosts")
        return jsonify({"status": "error", "error": {"message": "Internal server error"}}), 500
