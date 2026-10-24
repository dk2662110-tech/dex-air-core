import http.server
import json
import time
import math
import statistics
import ast
import os
import sqlite3
import secrets

DB_FILE = "dex_air_vault.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                key TEXT PRIMARY KEY,
                user_id TEXT,
                plan TEXT,
                created_at REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT,
                func_name TEXT,
                latency_us REAL,
                status TEXT,
                timestamp REAL
            )
        """)
        cursor.execute("INSERT OR IGNORE INTO api_keys VALUES (?, ?, ?, ?)", 
                       ("dex_live_client_alpha", "AlphaCorp", "Pro", time.time()))
        conn.commit()

init_db()

def verify_key(key: str) -> bool:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM api_keys WHERE key = ?", (key,))
        return cursor.fetchone() is not None

def record_usage(key: str, func_name: str, latency: float, status: str):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usage_logs (key, func_name, latency_us, status, timestamp) VALUES (?, ?, ?, ?, ?)",
            (key, func_name, latency, status, time.time())
        )
        conn.commit()

class HardenedASTSandbox:
    ALLOWED_NODE_TYPES = {
        ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return,
        ast.Assign, ast.Name, ast.Constant, ast.BinOp, ast.UnaryOp,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub,
        ast.Call, ast.Load, ast.Store, ast.If, ast.Compare, 
        ast.Lt, ast.Gt, ast.LtE, ast.GtE, ast.Eq, ast.Attribute, ast.Expr,
        ast.List, ast.Tuple, ast.Dict
    }

    def compile_and_verify(self, source_code: str):
        tree = ast.parse(source_code)
        for node in ast.walk(tree):
            if type(node) not in self.ALLOWED_NODE_TYPES:
                raise PermissionError(f"Disallowed syntax '{type(node).__name__}'")
            if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
                raise PermissionError(f"Dunder attribute '{node.attr}' blocked")
        return compile(tree, filename="<sandbox>", mode="exec")

    def safe_execute(self, compiled_code, func_name: str, args: tuple):
        safe_builtins = {"min": min, "max": max, "abs": abs, "sum": sum, "len": len, "round": round}
        safe_env = {"__builtins__": safe_builtins, "math": math, "statistics": statistics}
        exec(compiled_code, safe_env)
        return safe_env[func_name](*args)

sandbox = HardenedASTSandbox()

THREATS = ["ignore all previous instructions", "bypass system prompt", "jailbreak"]

def scan_prompt(prompt_text: str) -> dict:
    cleaned = prompt_text.lower()
    for t in THREATS:
        if t in cleaned:
            return {"safe": False, "threat": t, "verdict": "BLOCKED"}
    return {"safe": True, "threat": None, "verdict": "CLEAN"}

class ProductionGatewayHandler(http.server.BaseHTTPRequestHandler):
    def _send(self, code: int, data: dict, content_type="application/json"):
        out = json.dumps(data, indent=2).encode() if content_type == "application/json" else data.encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(out)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
        self.wfile.write(out)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        if self.path in ["/", "/status"]:
            self._send(200, {
                "system": "DEX AIR Sovereign Enterprise Suite",
                "version": "v302.0_CLOUD_LIVE",
                "status": "ONLINE",
                "endpoints": ["/execute", "/guardrail", "/checkout"]
            })
        else:
            self._send(404, {"error": "Not found"})

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length).decode()) if length > 0 else {}

        if self.path == "/execute":
            key = self.headers.get("X-API-Key")
            if not key or not verify_key(key):
                self._send(401, {"verdict": "UNAUTHORIZED", "reason": "Missing or invalid X-API-Key"})
                return

            t0 = time.perf_counter()
            try:
                compiled = sandbox.compile_and_verify(body["code"])
                res = sandbox.safe_execute(compiled, body["func_name"], tuple(body.get("args", [])))
                lat_us = round((time.perf_counter() - t0) * 1_000_000.0, 2)
                record_usage(key, body["func_name"], lat_us, "SUCCESS")
                self._send(200, {"verdict": "SUCCESS", "result": res, "latency_us": lat_us, "logged": True})
            except PermissionError as pe:
                record_usage(key, body.get("func_name", "unknown"), 0.0, "BLOCKED")
                self._send(403, {"verdict": "BLOCKED", "reason": str(pe)})
            except Exception as e:
                self._send(400, {"verdict": "ERROR", "reason": str(e)})

        elif self.path == "/guardrail":
            res = scan_prompt(body.get("prompt", ""))
            status = 200 if res["safe"] else 403
            self._send(status, res)

        elif self.path == "/checkout":
            user_id = body.get("user_id", "Client")
            new_key = f"dex_{secrets.token_hex(12)}"
            with sqlite3.connect(DB_FILE) as conn:
                conn.cursor().execute("INSERT INTO api_keys VALUES (?, ?, ?, ?)", (new_key, user_id, "Paid", time.time()))
                conn.commit()
            self._send(201, {"status": "ISSUED", "issued_key": new_key, "user": user_id})
        else:
            self._send(404, {"error": "Not found"})

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    server = http.server.HTTPServer(('0.0.0.0', port), ProductionGatewayHandler)
    print(f"🚀 DEX AIR Sovereign Gateway listening on 0.0.0.0:{port}", flush=True)
    server.serve_forever()
      
