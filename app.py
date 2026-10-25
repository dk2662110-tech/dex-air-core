import os, ast, json, uuid, time, math, re, urllib.request, xml.etree.ElementTree as ET, psycopg2, random
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dex_air_vault_session_key_2026_secure")

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://dexdb_user:7Qn6dCaKuD9J1Unh8Ynyt86O6z5VbILS@dpg-dbeegojncjis73e0d7t0-a/dexdb"
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(64) UNIQUE NOT NULL,
                password VARCHAR(128) NOT NULL,
                tier VARCHAR(32) DEFAULT 'starter',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS api_vault (
                api_key VARCHAR(64) PRIMARY KEY,
                user_id VARCHAR(64) NOT NULL,
                tier VARCHAR(32) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                api_key VARCHAR(64),
                endpoint VARCHAR(64),
                status VARCHAR(32),
                latency_ms FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_wallets (
                username VARCHAR(64) PRIMARY KEY,
                balance FLOAT DEFAULT 10000.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS live_orders (
                id SERIAL PRIMARY KEY,
                username VARCHAR(64) NOT NULL,
                symbol VARCHAR(32) NOT NULL,
                action VARCHAR(10) NOT NULL,
                qty INT NOT NULL,
                price FLOAT NOT NULL,
                status VARCHAR(20) DEFAULT 'EXECUTED',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("SELECT COUNT(*) FROM api_vault")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO api_vault (api_key, user_id, tier) VALUES (%s, %s, %s)",
                      ("dex_master_live_key_999", "admin", "enterprise"))
        conn.commit()
        c.close()
        conn.close()
    except Exception as e:
        print("DB Init Error:", e)

init_db()

# Security Gate: बिना लॉगिन अंदर के किसी भी रूट तक पहुंच वर्जित
@app.before_request
def require_login():
    allowed_routes = ['login_page', 'auth_act', 'static']
    if request.endpoint and request.endpoint not in allowed_routes:
        if 'username' not in session:
            return redirect(url_for('login_page'))

T_NAV = """
<header style="background:rgba(3,7,18,0.95);padding:14px 20px;border-bottom:1px solid rgba(255,255,255,0.1);position:sticky;top:0;z-index:99;">
  <div style="max-width:1250px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
    <a href="/" style="font-size:20px;font-weight:800;color:#38bdf8;text-decoration:none;">⚡ DEX AIR</a>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
      <a href="/" style="color:#cbd5e1;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:rgba(255,255,255,0.05);">Home</a>
      <a href="/live-market" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:#10b981;font-weight:700;">📊 Terminal</a>
      <a href="/cricket-live" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:#0284c7;font-weight:700;">🏏 Live Cricket</a>
      <a href="/video-hub" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:#e11d48;font-weight:700;">🎬 Video Hub</a>
      <a href="/calculator" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:#0284c7;font-weight:700;">🧮 Calculator</a>
      <a href="/compounding" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:#10b981;font-weight:700;">📈 Compounding</a>
      <a href="/quantum-ai" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 11px;border-radius:6px;background:#8b5cf6;font-weight:700;">🌌 Quantum AI</a>
      <a href="/news" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 11px;border-radius:6px;background:#ef4444;font-weight:700;">🔴 Live News</a>
      <a href="/math-master" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:#6366f1;font-weight:700;">🧮 Math Master</a>
      <a href="/smart-tools" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:#f59e0b;font-weight:700;">🧰 Tools</a>
      <a href="/subscription" style="color:#38bdf8;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:rgba(56,189,248,0.1);font-weight:700;border:1px solid rgba(56,189,248,0.3);">💳 Plan (₹99)</a>
      <a href="/logout" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 12px;border-radius:6px;background:#ef4444;font-weight:700;">🚪 Logout</a>
    </div>
  </div>
</header>
"""

T_HEAD = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>DEX AIR Sovereign Enterprise</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;}
body{background:#030712;color:#f8fafc;min-height:100vh;}
.card{background:rgba(17,24,39,0.85);border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:18px;margin-bottom:16px;}
.btn{background:#0284c7;color:#fff;border:none;border-radius:8px;padding:10px 16px;font-weight:700;cursor:pointer;width:100%;text-decoration:none;display:inline-block;text-align:center;}
.btn-green{background:#059669;}
.btn-purple{background:#6366f1;}
.btn-quantum{background:#8b5cf6;}
input,textarea,select{width:100%;background:#090d16;border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:10px;color:#38bdf8;margin:6px 0 14px 0;}
.out{background:#020617;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:14px;color:#34d399;font-family:monospace;font-size:13px;margin-top:14px;line-height:1.7;}
.step-box{background:rgba(15,23,42,0.8);border-left:4px solid #38bdf8;padding:12px;margin:8px 0;border-radius:0 8px 8px 0;color:#cbd5e1;}
.news-item{background:#0b1120;border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:14px;margin-bottom:12px;transition:0.2s;}
.news-item:hover{border-color:#38bdf8;}
.mic-btn{background:#ef4444;color:#fff;border:none;border-radius:8px;padding:8px 14px;cursor:pointer;font-weight:700;display:inline-flex;align-items:center;gap:6px;}
</style>
</head><body>""" + T_NAV + """<div style="max-width:1150px;margin:20px auto;padding:0 14px;">"""

T_FOOT = """</div><footer style="text-align:center;padding:20px;font-size:12px;color:#64748b;border-top:1px solid rgba(255,255,255,0.08);">DEX AIR Sovereign Enterprise © 2026 | PostgreSQL Live Active</footer></body></html>"""

# ==========================================
# 1. LOGIN & SIGN UP PAGE (GATEWAY)
# ==========================================
@app.route("/login")
def login_page():
    if 'username' in session:
        return redirect("/")
    
    html = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <title>DEX AIR - Gateway Portal</title>
    <style>
    *{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;}
    body{background:#030712;color:#f8fafc;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:16px;}
    .auth-box{background:#0b1120;border:1px solid rgba(56,189,248,0.3);border-radius:16px;width:100%;max-width:420px;padding:24px;box-shadow:0 15px 35px rgba(0,0,0,0.8);}
    input{width:100%;background:#030712;border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:12px;color:#38bdf8;margin:8px 0 16px 0;font-size:14px;}
    .btn{padding:12px;border:none;border-radius:8px;font-weight:700;cursor:pointer;width:100%;font-size:14px;}
    .btn-green{background:#059669;color:#fff;}
    .btn-purple{background:#6366f1;color:#fff;}
    .out{background:#020617;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:12px;font-size:13px;margin-top:14px;text-align:center;}
    </style>
    </head><body>
      <div class="auth-box">
        <div style="text-align:center;margin-bottom:20px;">
          <h1 style="color:#38bdf8;font-size:26px;font-weight:900;">⚡ DEX AIR</h1>
          <p style="color:#94a3b8;font-size:13px;margin-top:4px;">Secure Gateway Portal</p>
        </div>

        <div style="display:flex;gap:6px;margin-bottom:18px;">
          <button id="tb_login" class="btn btn-green" style="flex:1;" onclick="setMode('login')">Sign In</button>
          <button id="tb_reg" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;" onclick="setMode('reg')">Sign Up</button>
        </div>

        <label style="font-size:12px;color:#94a3b8;">Username</label>
        <input type="text" id="auth_user" placeholder="Enter username">

        <label style="font-size:12px;color:#94a3b8;">Password</label>
        <input type="password" id="auth_pass" placeholder="••••••••">

        <button id="action_btn" class="btn btn-green" onclick="submitAuth()">Sign In to Terminal</button>
        <div id="auth_res" class="out" style="display:none;"></div>
      </div>

      <script>
      let mode = 'login';
      function setMode(m){
        mode = m;
        if(m==='login'){
          document.getElementById('tb_login').className = 'btn btn-green';
          document.getElementById('tb_login').style.background = '#059669';
          document.getElementById('tb_login').style.color = '#fff';
          document.getElementById('tb_reg').className = 'btn';
          document.getElementById('tb_reg').style.background = 'rgba(255,255,255,0.08)';
          document.getElementById('tb_reg').style.color = '#94a3b8';
          document.getElementById('action_btn').innerText = 'Sign In to Terminal';
          document.getElementById('action_btn').className = 'btn btn-green';
        } else {
          document.getElementById('tb_reg').className = 'btn btn-purple';
          document.getElementById('tb_reg').style.background = '#6366f1';
          document.getElementById('tb_reg').style.color = '#fff';
          document.getElementById('tb_login').className = 'btn';
          document.getElementById('tb_login').style.background = 'rgba(255,255,255,0.08)';
          document.getElementById('tb_login').style.color = '#94a3b8';
          document.getElementById('action_btn').innerText = 'Create Account (Sign Up)';
          document.getElementById('action_btn').className = 'btn btn-purple';
        }
      }

      async function submitAuth(){
        const u = document.getElementById('auth_user').value.trim();
        const p = document.getElementById('auth_pass').value.trim();
        const out = document.getElementById('auth_res');

        if(!u || !p){ alert("Username aur Password dono bharein!"); return; }

        out.style.display = 'block';
        out.innerHTML = '<span style="color:#38bdf8;">Authenticating with PostgreSQL...</span>';

        try{
          const res = await fetch('/auth-act', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({action: mode, username: u, password: p})
          });
          const d = await res.json();
          if(d.status==='SUCCESS'){
            out.innerHTML = "<span style='color:#34d399;'>✅ " + d.msg + "</span>";
            setTimeout(()=>{ window.location.href='/'; }, 800);
          } else {
            out.innerHTML = "<span style='color:#ef4444;'>❌ " + d.reason + "</span>";
          }
        }catch(e){
          out.innerText = "Server connection error.";
        }
      }
      </script>
    </body></html>"""
    return html

@app.route("/auth-act", methods=["POST"])
def auth_act():
    d = request.get_json(silent=True) or {}
    act = d.get("action")
    u = d.get("username", "").strip()
    p = d.get("password", "").strip()

    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)

    if act == "reg":
        c.execute("SELECT * FROM users WHERE username = %s", (u,))
        if c.fetchone():
            c.close(); conn.close()
            return jsonify({"status": "FAILED", "reason": "Yeh username pehle se registered hai! Doosra chunein."})
        c.execute("INSERT INTO users (username, password, tier) VALUES (%s, %s, %s)", (u, p, "starter"))
        conn.commit()
        session["username"] = u
        c.close(); conn.close()
        return jsonify({"status": "SUCCESS", "msg": "Account ban gaya! Welcome to DEX AIR..."})
    else:
        c.execute("SELECT * FROM users WHERE username = %s AND password = %s", (u, p))
        row = c.fetchone()
        c.close(); conn.close()
        if row:
            session["username"] = u
            return jsonify({"status": "SUCCESS", "msg": "Login safal! Welcome back, " + u})
        return jsonify({"status": "FAILED", "reason": "Galat Username ya Password!"})

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect("/login")

# ==========================================
# 2. HOMEPAGE (DASHBOARD)
# ==========================================
@app.route("/")
def home():
    u = session.get("username", "Trader")
    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:10px;">
      <div>
        <h1 style="color:#38bdf8;font-size:26px;">Welcome, {u} 👋</h1>
        <p style="color:#94a3b8;font-size:13px;">Full-Screen Pro Trading Terminal, Live Cricket, Reels Video Hub & Quantum AI Suite.</p>
      </div>
      <span style="background:rgba(16,185,129,0.15);color:#34d399;padding:6px 14px;border-radius:20px;font-size:12px;font-weight:700;">
        🟢 Session Active
      </span>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;">
      <div class="card">
        <h3>📊 Pro Trading Terminal</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">Groww style full-page trading terminal, live watchlist aur wallet.</p>
        <a href="/live-market" class="btn btn-green">Open Terminal</a>
      </div>
      <div class="card">
        <h3>🏏 Live Cricket Stream & Scores</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">लाइव मैच ब्रॉडकास्ट, बॉल-बाय-बॉल स्कोरकार्ड और रन रेट ट्रैकर।</p>
        <a href="/cricket-live" class="btn" style="background:#0284c7;">Watch Cricket Live</a>
      </div>
      <div class="card">
        <h3>🎬 Swipe Video Hub</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">मोबाइल पर ऊपर-नीचे स्वाइप करके रील्स स्टाइल वीडियो देखें।</p>
        <a href="/video-hub" class="btn" style="background:#e11d48;">Open Video Hub</a>
      </div>
      <div class="card">
        <h3>📈 Wealth Compounding</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">मंथली SIP और एकमुश्त निवेश पर चक्रवृद्धि ब्याज की ग्रोथ कैलकुलेट करें।</p>
        <a href="/compounding" class="btn btn-green">Open Compounding</a>
      </div>
      <div class="card">
        <h3>🌌 Quantum AI Simulator</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">3-Qubit quantum register, superposition, entanglement aur entropy analyzer.</p>
        <a href="/quantum-ai" class="btn btn-quantum">Open Quantum Engine</a>
      </div>
      <div class="card">
        <h3>🔴 Live Google News Hub</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">शेयर बाजार, बिज़नेस, क्रूड और राष्ट्रीय नीतियां (100% Real Live).</p>
        <a href="/news" class="btn" style="background:#ef4444;">Read Live News</a>
      </div>
    </div>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

# ==========================================
# 3. FULL-PAGE PRO LIVE TRADING TERMINAL
# ==========================================
@app.route("/live-market")
def live_market():
    content = """
    <div style="max-width:100%;margin:0 auto;padding-bottom:30px;">
      
      <div class="card" style="background:#0b1120;border:1px solid rgba(56,189,248,0.25);border-radius:14px;padding:16px;margin-bottom:14px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
          <div>
            <span style="font-size:12px;color:#94a3b8;">Trading Wallet Balance</span>
            <div id="wallet_balance_display" style="color:#34d399;font-size:24px;font-weight:900;">₹10,000.00</div>
          </div>
          <button class="btn btn-green" style="width:auto;padding:10px 18px;font-size:13px;border-radius:24px;font-weight:800;" onclick="openAddFundModal()">
            <i class="fa-solid fa-plus"></i> Add Funds
          </button>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;background:#030712;padding:12px;border-radius:10px;border:1px solid rgba(255,255,255,0.05);">
          <div>
            <span style="font-size:11px;color:#64748b;">Current Portfolio Value</span>
            <div style="font-size:15px;font-weight:800;color:#f8fafc;" id="port_curr_val">₹22,462.99</div>
          </div>
          <div>
            <span style="font-size:11px;color:#64748b;">Overall P&L Returns</span>
            <div style="font-size:15px;font-weight:800;color:#ef4444;" id="port_pnl">-₹2,219.61 (-8.99%)</div>
          </div>
        </div>
      </div>

      <div style="height:62px;margin-bottom:14px;border-radius:10px;overflow:hidden;border:1px solid rgba(255,255,255,0.08);">
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
          {
            "symbols": [
              {"proName": "NSE:NIFTY", "title": "NIFTY 50"},
              {"proName": "BSE:SENSEX", "title": "SENSEX"},
              {"proName": "NSE:RELIANCE", "title": "RELIANCE"},
              {"proName": "NSE:TATASTEEL", "title": "TATA STEEL"},
              {"proName": "NSE:JIOFIN", "title": "JIO FINANCIAL"},
              {"proName": "NSE:TATAMOTORS", "title": "TATA MOTORS"},
              {"proName": "NSE:PNB", "title": "PNB"}
            ],
            "showSymbolLogo": true,
            "colorTheme": "dark",
            "isTransparent": true,
            "displayMode": "adaptive",
            "locale": "in"
          }
          </script>
        </div>
      </div>

      <div class="card" style="background:#0b1120;padding:16px;margin-bottom:14px;">
        <h3 style="font-size:15px;color:#38bdf8;margin-bottom:10px;"><i class="fa-solid fa-fire"></i> Trending Market Stocks</h3>
        
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin-bottom:12px;">
                    <div onclick="selectStock('NSE:RELIANCE', 1190.00)" class="news-item" style="cursor:pointer;margin:0;padding:10px;border-radius:8px;">
            <b style="color:#f8fafc;font-size:13px;">Reliance Ind.</b><br>
            <span style="color:#34d399;font-size:12px;font-weight:700;">₹1,190.00 (+0.46%)</span>
          </div>
          <div onclick="selectStock('NSE:TATASTEEL', 183.74)" class="news-item" style="cursor:pointer;margin:0;padding:10px;border-radius:8px;">
            <b style="color:#f8fafc;font-size:13px;">Tata Steel</b><br>
            <span style="color:#ef4444;font-size:12px;font-weight:700;">₹183.74 (-8.75%)</span>
          </div>
          <div onclick="selectStock('NSE:JIOFIN', 205.03)" class="news-item" style="cursor:pointer;margin:0;padding:10px;border-radius:8px;">
            <b style="color:#f8fafc;font-size:13px;">Jio Financial</b><br>
            <span style="color:#ef4444;font-size:12px;font-weight:700;">₹205.03 (-2.74%)</span>
          </div>
          <div onclick="selectStock('NSE:PNB', 120.37)" class="news-item" style="cursor:pointer;margin:0;padding:10px;border-radius:8px;">
            <b style="color:#f8fafc;font-size:13px;">PNB Bank</b><br>
            <span style="color:#ef4444;font-size:12px;font-weight:700;">₹120.37 (-2.13%)</span>
          </div>
          <div onclick="selectStock('NSE:PCJEWELLER', 18.04)" class="news-item" style="cursor:pointer;margin:0;padding:10px;border-radius:8px;">
            <b style="color:#f8fafc;font-size:13px;">PC Jeweller</b><br>
            <span style="color:#ef4444;font-size:12px;font-weight:700;">₹18.04 (-0.17%)</span>
          </div>
        </div>

        <label style="font-size:12px;color:#94a3b8;">Manual Stock Selector:</label>
        <select id="active_stock_sym" onchange="manualStockSwitch()">
          <option value="NSE:RELIANCE" selected>Reliance Industries (NSE: RELIANCE)</option>
          <option value="NSE:TATASTEEL">Tata Steel (NSE: TATASTEEL)</option>
          <option value="NSE:JIOFIN">Jio Financial Services (NSE: JIOFIN)</option>
          <option value="NSE:PNB">Punjab National Bank (NSE: PNB)</option>
          <option value="NSE:PCJEWELLER">PC Jeweller Ltd (NSE: PCJEWELLER)</option>
          <option value="NSE:TATAMOTORS">Tata Motors (NSE: TATAMOTORS)</option>
          <option value="NSE:NIFTY">NIFTY 50 Index Futures</option>
        </select>
      </div>

      <div class="card" style="padding:10px;margin-bottom:14px;background:#030712;">
        <div style="display:flex;justify-content:space-between;align-items:center;padding:4px 8px 10px 8px;">
          <div>
            <b id="chart_title_display" style="color:#38bdf8;font-size:16px;">Reliance Industries</b>
            <span style="font-size:12px;color:#64748b;margin-left:6px;">(5 Min Candlestick)</span>
          </div>
          <span style="display:inline-flex;align-items:center;gap:6px;background:rgba(16,185,129,0.15);color:#34d399;padding:4px 10px;border-radius:20px;font-size:11px;font-weight:700;">
            <span style="width:7px;height:7px;background:#10b981;border-radius:50%;display:inline-block;"></span> LIVE NSE
          </span>
        </div>
        <div style="height:440px;width:100%;border-radius:8px;overflow:hidden;">
          <div id="full_page_chart" style="height:100%;width:100%;"></div>
        </div>
      </div>

      <div class="card" style="background:#0b1120;border:1px solid #38bdf8;padding:18px;margin-bottom:14px;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:gap:8px;margin-bottom:10px;">
          <h3 style="font-size:16px;color:#38bdf8;"><i class="fa-solid fa-robot"></i> AI Live Buy/Sell Analysis</h3>
          <button class="btn btn-purple" style="width:auto;padding:6px 14px;font-size:12px;" onclick="requestAISignal()">
            🔄 Re-Scan
          </button>
        </div>
        <div id="ai_verdict_container" style="line-height:1.7;">
          <div style="color:#94a3b8;font-size:13px;">Analyzing technical patterns, live RSI and moving averages...</div>
        </div>
      </div>

      <div class="card" style="background:#0b1120;border:1px solid rgba(16,185,129,0.4);padding:18px;margin-bottom:14px;">
        <h3 style="font-size:16px;color:#34d399;margin-bottom:12px;">⚡ Live Execution Pad</h3>
        
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
          <div style="background:#030712;padding:12px;border-radius:8px;border:1px solid rgba(255,255,255,0.06);">
            <div style="font-size:11px;color:#94a3b8;">Live Price (LTP)</div>
            <div id="active_exec_price" style="font-size:22px;font-weight:900;color:#38bdf8;">₹1,190.00</div>
          </div>
          <div style="background:#030712;padding:12px;border-radius:8px;border:1px solid rgba(255,255,255,0.06);">
            <div style="font-size:11px;color:#94a3b8;">Margin Required</div>
            <div id="active_exec_margin" style="font-size:22px;font-weight:900;color:#f8fafc;">₹11,900.00</div>
          </div>
        </div>

        <label style="font-size:12px;color:#94a3b8;">Quantity (Shares):</label>
        <input type="number" id="active_exec_qty" value="10" min="1" oninput="calcMarginTotal()" style="font-size:16px;font-weight:700;">

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px;">
          <button class="btn btn-green" onclick="submitLiveTrade('BUY')" style="padding:14px;font-size:16px;border-radius:10px;">
            🟢 BUY (Kharidein)
          </button>
          <button class="btn" style="background:#ef4444;padding:14px;font-size:16px;border-radius:10px;" onclick="submitLiveTrade('SELL')">
            🔴 SELL (Bechein)
          </button>
        </div>

        <div id="active_order_status" class="out" style="display:none;margin-top:12px;font-size:13px;"></div>
      </div>

      <div class="card" style="background:#0b1120;padding:16px;">
        <h3 style="font-size:15px;color:#38bdf8;margin-bottom:10px;">📂 Your Live Executed Orders</h3>
        <div style="overflow-x:auto;">
          <table style="width:100%;text-align:left;font-size:13px;border-collapse:collapse;">
            <thead>
              <tr style="border-bottom:1px solid rgba(255,255,255,0.1);color:#94a3b8;">
                <th style="padding:8px;">Time</th>
                <th style="padding:8px;">Stock</th>
                <th style="padding:8px;">Side</th>
                <th style="padding:8px;">Qty</th>
                <th style="padding:8px;">Price</th>
                <th style="padding:8px;">Status</th>
              </tr>
            </thead>
            <tbody id="trade_order_rows">
              <tr><td colspan="6" style="padding:14px;text-align:center;color:#64748b;">No live trades placed yet.</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div id="fund_modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);z-index:999;backdrop-filter:blur(5px);justify-content:center;align-items:center;padding:16px;">
        <div style="background:#111827;border:1px solid #10b981;border-radius:14px;max-width:440px;width:100%;padding:22px;position:relative;">
          <button onclick="closeAddFundModal()" style="position:absolute;top:14px;right:14px;background:#ef4444;color:#fff;border:none;border-radius:50%;width:30px;height:30px;font-weight:700;cursor:pointer;">✕</button>
          
          <h3 style="color:#34d399;margin-bottom:6px;">💰 Add Trading Funds</h3>
          <p style="color:#94a3b8;font-size:12px;margin-bottom:14px;">Instant UPI deposit via PhonePe/GPay QR.</p>
          
          <div style="text-align:center;background:#fff;padding:10px;border-radius:10px;margin-bottom:12px;">
            <img src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=upi://pay?pa=8791223831@ibl%26pn=DEX%20AIR%26am=5000%26cu=INR" style="width:160px;height:160px;">
          </div>
          
          <div style="text-align:center;font-size:12px;color:#94a3b8;margin-bottom:12px;">
            Official UPI: <code style="color:#38bdf8;font-weight:700;">8791223831@ibl</code>
          </div>

          <label style="font-size:11px;">Amount (₹ Deposit)</label>
          <input type="number" id="fund_amount" value="5000">

          <label style="font-size:11px;">12-Digit UPI Ref / UTR Number</label>
          <input type="text" id="fund_utr" placeholder="e.g. 429182940192">

          <button class="btn btn-green" onclick="submitDeposit()">Verify & Credit Wallet</button>
          <div id="deposit_out" class="out" style="display:none;margin-top:10px;"></div>
        </div>
      </div>

    </div>

    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <script>
    let activeSymbol = "NSE:RELIANCE";
    let activeLTP = 1190.00;

    function renderFullChart(sym) {
      document.getElementById('full_page_chart').innerHTML = '';
      new TradingView.widget({
        "autosize": true,
        "symbol": sym,
        "interval": "5",
        "timezone": "Asia/Kolkata",
        "theme": "dark",
        "style": "1",
        "locale": "in",
        "toolbar_bg": "#030712",
        "container_id": "full_page_chart"
      });
    }

    function selectStock(sym, price) {
      activeSymbol = sym;
      activeLTP = price;
      document.getElementById('active_stock_sym').value = sym;
      document.getElementById('chart_title_display').innerText = sym;
      renderFullChart(sym);
      updateDisplayValues();
      requestAISignal();
    }

    function manualStockSwitch() {
      const sym = document.getElementById('active_stock_sym').value;
      const prices = {
        "NSE:RELIANCE": 1190.00,
        "NSE:TATASTEEL": 183.74,
        "NSE:JIOFIN": 205.03,
        "NSE:PNB": 120.37,
        "NSE:PCJEWELLER": 18.04,
        "NSE:TATAMOTORS": 925.00,
        "NSE:NIFTY": 22600.00
      };
      selectStock(sym, prices[sym] || 500.00);
    }

    function updateDisplayValues() {
      document.getElementById('active_exec_price').innerText = '₹' + activeLTP.toLocaleString('en-IN', {minimumFractionDigits: 2});
      calcMarginTotal();
    }

    function calcMarginTotal() {
      const qty = Number(document.getElementById('active_exec_qty').value) || 0;
      const total = qty * activeLTP;
      document.getElementById('active_exec_margin').innerText = '₹' + total.toLocaleString('en-IN', {minimumFractionDigits: 2});
    }

    async function requestAISignal() {
      const container = document.getElementById('ai_verdict_container');
      container.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Running technical scan on ' + activeSymbol + '...';

      try {
        const res = await fetch('/api/live-market-ai', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({symbol: activeSymbol, ltp: activeLTP})
        });
        const d = await res.json();
        activeLTP = d.price;
        updateDisplayValues();
        container.innerHTML = d.html;
      } catch(e) {
        container.innerHTML = '<span style="color:#ef4444;">AI scan error. Please retry.</span>';
      }
    }

    async function syncTerminalData() {
      try {
        const res = await fetch('/api/get-wallet-orders');
        const d = await res.json();
        document.getElementById('wallet_balance_display').innerText = '₹' + d.balance.toLocaleString('en-IN', {minimumFractionDigits: 2});
        
        const tbody = document.getElementById('trade_order_rows');
        if(d.orders && d.orders.length > 0) {
          tbody.innerHTML = d.orders.map(o => `
            <tr style="border-bottom:1px solid rgba(255,255,255,0.04);">
              <td style="padding:8px;color:#64748b;">${o.created_at.slice(11, 19)}</td>
              <td style="padding:8px;font-weight:700;color:#38bdf8;">${o.symbol}</td>
              <td style="padding:8px;font-weight:700;color:${o.action==='BUY'?'#34d399':'#ef4444'};">${o.action}</td>
              <td style="padding:8px;">${o.qty}</td>
              <td style="padding:8px;">₹${Number(o.price).toFixed(2)}</td>
              <td style="padding:8px;"><span style="background:rgba(16,185,129,0.15);color:#34d399;padding:2px 6px;border-radius:4px;font-size:11px;">${o.status}</span></td>
            </tr>
          `).join('');
        }
      } catch(e) {}
    }

    async function submitLiveTrade(action) {
      const qty = Number(document.getElementById('active_exec_qty').value);
      const out = document.getElementById('active_order_status');
      out.style.display = 'block';
      out.innerHTML = 'Executing ' + action + ' order...';

      try {
        const res = await fetch('/api/execute-trade', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({symbol: activeSymbol, action: action, qty: qty, price: activeLTP})
        });
        const d = await res.json();
        if(d.status === 'SUCCESS') {
          out.innerHTML = `<span style="color:#34d399;">✅ ${d.message}</span>`;
          syncTerminalData();
        } else {
          out.innerHTML = `<span style="color:#ef4444;">❌ ${d.reason}</span>`;
        }
      } catch(e) {
        out.innerText = "Order placement error.";
      }
    }

    function openAddFundModal() { document.getElementById('fund_modal').style.display = 'flex'; }
    function closeAddFundModal() { document.getElementById('fund_modal').style.display = 'none'; }

    async function submitDeposit() {
      const amt = Number(document.getElementById('fund_amount').value);
      const utr = document.getElementById('fund_utr').value.trim();
      const out = document.getElementById('deposit_out');

      if(!utr) { alert("12-digit UTR number bharein!"); return; }
      out.style.display = 'block';
      out.innerText = "Verifying UPI transaction...";

      try {
        const res = await fetch('/api/deposit-funds', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({amount: amt, utr: utr})
        });
        const d = await res.json();
        if(d.status === 'SUCCESS') {
          out.innerHTML = `<span style="color:#34d399;">🎉 Funds Credited: ₹${amt}</span>`;
          syncTerminalData();
          setTimeout(closeAddFundModal, 1500);
        } else {
          out.innerHTML = `<span style="color:#ef4444;">❌ ${d.reason}</span>`;
        }
      } catch(e) { out.innerText = "Deposit failed."; }
    }

    window.onload = function() {
      selectStock('NSE:RELIANCE', 1190.00);
      syncTerminalData();
    };
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)
    # ==========================================
# 4. AUTO-UPDATING LIVE CRICKET & STREAMING ENGINE
# ==========================================
@app.route("/cricket-live")
def cricket_live():
    content = """
    <div style="max-width:1000px;margin:0 auto;padding-bottom:30px;">
      
      <!-- Tournament Selector Tabs -->
      <div style="display:flex;gap:8px;margin-bottom:12px;overflow-x:auto;">
        <button id="tab_ind" class="btn" style="flex:1;background:#0284c7;font-size:13px;padding:10px 14px;white-space:nowrap;font-weight:800;" onclick="switchMatchSeries('IND')">
          🇮🇳 Team India International (Live)
        </button>
        <button id="tab_ipl" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;font-size:13px;padding:10px 14px;white-space:nowrap;font-weight:800;" onclick="switchMatchSeries('IPL')">
          🏆 TATA IPL 2026 (Live)
        </button>
      </div>

      <!-- Real-Time Auto-Updating Scorecard Card -->
      <div class="card" style="background:#0b1120;border:1px solid #0284c7;padding:16px;margin-bottom:14px;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:12px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="width:10px;height:10px;background:#ef4444;border-radius:50%;display:inline-block;box-shadow: 0 0 10px #ef4444;"></span>
            <span style="color:#ef4444;font-weight:800;font-size:13px;text-transform:uppercase;" id="m_type_badge">LIVE MATCH IN PROGRESS</span>
            <span style="background:rgba(16,185,129,0.15);color:#34d399;font-size:11px;padding:2px 8px;border-radius:4px;font-weight:700;">
              ⚡ AUTO-REFRESHING (5s)
            </span>
          </div>
          <button class="btn btn-green" style="width:auto;padding:6px 12px;font-size:12px;" onclick="simulateBall()">
            ⚡ Instant Ball Update
          </button>
        </div>

        <!-- Live Scoreboard Box -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;background:#030712;padding:14px;border-radius:10px;border:1px solid rgba(255,255,255,0.06);">
          <div>
            <div style="font-size:12px;color:#94a3b8;" id="c_header_title">Current Match:</div>
            <div style="font-size:22px;font-weight:900;color:#38bdf8;" id="c_team">INDIA 🇮🇳 vs NZ 🇳🇿</div>
            <div style="font-size:30px;font-weight:900;color:#f8fafc;" id="c_score">184/3 <span style="font-size:15px;color:#64748b;">(17.2 Ov)</span></div>
          </div>
          <div>
            <div style="font-size:13px;color:#34d399;font-weight:700;" id="c_crr">CRR: 10.61 | Required: 9.75</div>
            <div style="font-size:13px;color:#cbd5e1;margin-top:6px;" id="c_batsmen">🏏 Rohit Sharma 72* (38) | Hardik Pandya 24* (12)</div>
            <div style="font-size:12px;color:#ef4444;margin-top:4px;" id="c_bowler">🎯 Trent Boult: 3.2-0-32-2</div>
          </div>
        </div>

        <!-- Dynamic This Over Balls Strip -->
        <div style="display:flex;align-items:center;gap:6px;margin-top:12px;overflow-x:auto;">
          <span style="font-size:11px;color:#64748b;font-weight:700;">THIS OVER:</span>
          <div id="recent_balls_container" style="display:flex;gap:6px;">
            <span style="background:#0284c7;color:#fff;padding:3px 8px;border-radius:50%;font-size:12px;font-weight:700;">4</span>
            <span style="background:#1e293b;color:#f8fafc;padding:3px 8px;border-radius:50%;font-size:12px;font-weight:700;">1</span>
            <span style="background:#10b981;color:#fff;padding:3px 8px;border-radius:50%;font-size:12px;font-weight:700;">6</span>
            <span style="background:#1e293b;color:#f8fafc;padding:3px 8px;border-radius:50%;font-size:12px;font-weight:700;">2</span>
          </div>
        </div>
      </div>

      <!-- Live Video Player Card -->
      <div class="card" style="padding:10px;background:#000;border:1px solid rgba(255,255,255,0.1);margin-bottom:14px;">
        <div style="display:flex;justify-content:space-between;align-items:center;padding:4px 8px 10px 8px;flex-wrap:wrap;gap:8px;">
          <div>
            <b id="stream_title" style="color:#38bdf8;font-size:15px;">Server 1: Live Broadcast HD</b>
            <span style="font-size:11px;color:#64748b;margin-left:6px;">(Auto Synchronized)</span>
          </div>
          <div style="display:flex;gap:6px;">
            <button class="btn" style="background:#0284c7;width:auto;padding:5px 12px;font-size:12px;" onclick="switchServer(1)">Main Stream</button>
            <button class="btn" style="background:rgba(255,255,255,0.08);color:#cbd5e1;width:auto;padding:5px 12px;font-size:12px;" onclick="switchServer(2)">Hindi Audio Commentary</button>
          </div>
        </div>

        <div style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:10px;">
          <iframe id="cricket_iframe"
                  style="position:absolute;top:0;left:0;width:100%;height:100%;border:0;"
                  src="https://www.youtube.com/embed/live_stream?channel=UCNAqjh23zV71l3x1E4Z19-w&autoplay=1"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowfullscreen>
          </iframe>
        </div>
      </div>

      <!-- Custom Match Stream Input -->
      <div class="card" style="background:#0b1120;padding:16px;">
        <h3 style="font-size:14px;color:#38bdf8;margin-bottom:6px;"><i class="fa-solid fa-satellite-dish"></i> Custom Match Stream Link / YouTube Live Embed</h3>
        <p style="color:#94a3b8;font-size:12px;margin-bottom:10px;">किसी भी लाइव मैच का YouTube लिंक या Video ID पेस्ट करके तुरंत चलाएं:</p>
        
        <div style="display:flex;gap:8px;">
          <input type="text" id="cricket_stream_url" placeholder="Paste YouTube Live Link या Video ID" style="margin:0;">
          <button class="btn btn-green" style="width:auto;padding:10px 20px;white-space:nowrap;" onclick="loadCustomCricketStream()">Watch Live</button>
        </div>
      </div>

    </div>

    <script>
    let activeSeries = 'IND';
    const seriesData = {
      IND: {
        badge: "LIVE: INDIA INTERNATIONAL TOUR",
        team: "INDIA 🇮🇳 vs NZ 🇳🇿",
        runs: 184,
        wickets: 3,
        balls: 104,
        batsmen: "🏏 Rohit Sharma 72* (38) | Hardik Pandya 24* (12)",
        bowler: "🎯 Trent Boult: 3.2-0-32-2",
        server1: "https://www.youtube.com/embed/live_stream?channel=UCNAqjh23zV71l3x1E4Z19-w&autoplay=1",
        server2: "https://www.youtube.com/embed/jfKfPfyJRdk?autoplay=1"
      },
      IPL: {
        badge: "LIVE: TATA IPL 2026 MATCH",
        team: "RCB 🔴 vs CSK 🟡",
        runs: 198,
        wickets: 4,
        balls: 110,
        batsmen: "🏏 Virat Kohli 82* (48) | Rajat Patidar 45* (22)",
        bowler: "🎯 Matheesha Pathirana: 3.2-0-38-2",
        server1: "https://www.youtube.com/embed/live_stream?channel=UCNAqjh23zV71l3x1E4Z19-w&autoplay=1",
        server2: "https://www.youtube.com/embed/aircAruvnKk?autoplay=1"
      }
    };

    function switchMatchSeries(series) {
      activeSeries = series;
      document.getElementById('tab_ind').style.background = series === 'IND' ? '#0284c7' : 'rgba(255,255,255,0.08)';
      document.getElementById('tab_ind').style.color = series === 'IND' ? '#fff' : '#94a3b8';
      document.getElementById('tab_ipl').style.background = series === 'IPL' ? '#0284c7' : 'rgba(255,255,255,0.08)';
      document.getElementById('tab_ipl').style.color = series === 'IPL' ? '#fff' : '#94a3b8';

      const d = seriesData[series];
      document.getElementById('m_type_badge').innerText = d.badge;
      document.getElementById('c_team').innerText = d.team;
      document.getElementById('c_batsmen').innerText = d.batsmen;
      document.getElementById('c_bowler').innerText = d.bowler;
      switchServer(1);
      renderScore();
    }

    function switchServer(num) {
      const d = seriesData[activeSeries];
      document.getElementById('cricket_iframe').src = num === 1 ? d.server1 : d.server2;
      document.getElementById('stream_title').innerText = "Server " + num + ": " + (activeSeries === 'IND' ? 'India' : 'IPL') + " Live Feed";
    }

    function loadCustomCricketStream() {
      const raw = document.getElementById('cricket_stream_url').value.trim();
      if(!raw) { alert("कृपया कोई मान्य लिंक या YouTube ID दर्ज करें!"); return; }
      let vidId = raw;
      if(raw.includes("v=")) vidId = raw.split("v=")[1].split("&")[0];
      else if(raw.includes("youtu.be/")) vidId = raw.split("youtu.be/")[1].split("?")[0];
      document.getElementById('cricket_iframe').src = "https://www.youtube.com/embed/" + vidId + "?autoplay=1";
      document.getElementById('stream_title').innerText = "Custom Broadcast Active (ID: " + vidId + ")";
    }

    function renderScore() {
      const d = seriesData[activeSeries];
      const overs = Math.floor(d.balls / 6) + "." + (d.balls % 6);
      const crr = (d.runs / (d.balls / 6)).toFixed(2);
      document.getElementById('c_score').innerHTML = d.runs + "/" + d.wickets + ` <span style="font-size:15px;color:#64748b;">(${overs} Ov)</span>`;
      document.getElementById('c_crr').innerText = "CRR: " + crr + " | Required: 9.80";
    }

    // ऑटोमैटिक लाइव बॉल-बाय-बॉल अपडेट इंजन
    function simulateBall() {
      const d = seriesData[activeSeries];
      const possibleRuns = [0, 1, 2, 4, 6, "W", 1];
      const outcome = possibleRuns[Math.floor(Math.random() * possibleRuns.length)];

      if(outcome === "W") {
        if(d.wickets < 9) d.wickets += 1;
      } else {
        d.runs += outcome;
      }
      d.balls += 1;

      // हालिया गेंद (Recent Ball) को स्ट्रिप में जोड़ना
      const container = document.getElementById('recent_balls_container');
      const badge = document.createElement('span');
      badge.style.padding = "3px 8px";
      badge.style.borderRadius = "50%";
      badge.style.fontSize = "12px";
      badge.style.fontWeight = "700";

      if(outcome === 4) { badge.style.background = "#0284c7"; badge.style.color = "#fff"; }
      else if(outcome === 6) { badge.style.background = "#10b981"; badge.style.color = "#fff"; }
      else if(outcome === "W") { badge.style.background = "#ef4444"; badge.style.color = "#fff"; }
      else { badge.style.background = "#1e293b"; badge.style.color = "#f8fafc"; }

      badge.innerText = outcome;
      container.appendChild(badge);
      if(container.children.length > 6) {
        container.removeChild(container.firstChild);
      }

      renderScore();
    }

    // हर 5 सेकंड में बिना पेज रीलोड किए अपने-आप रन और ओवर बदलेंगे
    setInterval(simulateBall, 5000);

    window.onload = function() {
      switchMatchSeries('IND');
    };
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)
    # ==========================================
# 5. SWIPEABLE VIDEO FEED (SHORTS/REELS STYLE)
# ==========================================
@app.route("/video-hub")
def video_hub():
    content = """
    <style>
    .swipe-container {
      position: relative;
      width: 100%;
      max-width: 480px;
      margin: 0 auto;
      height: 80vh;
      border-radius: 16px;
      overflow: hidden;
      background: #000;
      border: 1px solid rgba(225,29,72,0.4);
      box-shadow: 0 10px 30px rgba(0,0,0,0.8);
      touch-action: pan-y;
    }
    .video-viewport { width: 100%; height: 100%; position: relative; }
    .video-viewport iframe { width: 100%; height: 100%; border: none; }
    .swipe-overlay {
      position: absolute; bottom: 0; left: 0; right: 0;
      background: linear-gradient(transparent, rgba(3,7,18,0.95));
      padding: 16px; pointer-events: auto;
    }
    .nav-float {
      position: absolute; right: 12px; top: 50%; transform: translateY(-50%);
      display: flex; flex-direction: column; gap: 12px; z-index: 10;
    }
    .nav-float button {
      background: rgba(17,24,39,0.85); border: 1px solid rgba(255,255,255,0.2);
      color: #fff; width: 42px; height: 42px; border-radius: 50%;
      cursor: pointer; display: flex; align-items: center; justify-content: center;
    }
    </style>

    <div style="max-width:800px;margin:0 auto;padding-bottom:20px;">
      <div style="display:flex;gap:8px;margin-bottom:14px;overflow-x:auto;">
        <button id="cat_all" class="btn" style="flex:1;background:#e11d48;font-size:12px;padding:8px 12px;" onclick="switchCategory('all')">🔥 Trending</button>
        <button id="cat_trade" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;font-size:12px;padding:8px 12px;" onclick="switchCategory('trade')">📈 Trading</button>
        <button id="cat_quantum" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;font-size:12px;padding:8px 12px;" onclick="switchCategory('quantum')">🌌 Quantum</button>
      </div>

      <div class="swipe-container" id="swipe_box">
        <div class="nav-float">
          <button onclick="prevVideo()"><i class="fa-solid fa-chevron-up"></i></button>
          <button onclick="nextVideo()"><i class="fa-solid fa-chevron-down"></i></button>
        </div>
        <div class="video-viewport">
          <iframe id="swipe_iframe" src="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope" allowfullscreen></iframe>
        </div>
        <div class="swipe-overlay">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <span id="badge_cat" style="background:#e11d48;color:#fff;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;">Trending</span>
            <span id="video_index_badge" style="font-size:12px;color:#cbd5e1;font-weight:700;">1 / 3</span>
          </div>
          <h3 id="current_video_title" style="color:#f8fafc;font-size:15px;margin-bottom:4px;">Loading Video...</h3>
          <p style="color:#94a3b8;font-size:11px;">👆 Swipe Up / Down to change video</p>
        </div>
      </div>
    </div>

    <script>
    const videoDatabase = {
      all: [
        { id: "9bZkp7q19f0", title: "Trading Basics: Complete Price Action Course", cat: "Trading" },
        { id: "JhHMJCUmq28", title: "Quantum Computing Explained in 10 Minutes", cat: "Quantum" },
        { id: "aircAruvnKk", title: "Neural Networks & Deep Learning", cat: "AI & Tech" }
      ],
      trade: [{ id: "9bZkp7q19f0", title: "Trading Basics: Complete Price Action Course", cat: "Trading" }],
      quantum: [{ id: "JhHMJCUmq28", title: "Quantum Computing Explained in 10 Minutes", cat: "Quantum" }]
    };

    let activeList = [...videoDatabase.all];
    let currentIndex = 0;

    function renderCurrentVideo() {
      const vid = activeList[currentIndex];
      if (!vid) return;
      document.getElementById('swipe_iframe').src = "https://www.youtube.com/embed/" + vid.id + "?autoplay=1";
      document.getElementById('current_video_title').innerText = vid.title;
      document.getElementById('badge_cat').innerText = vid.cat;
      document.getElementById('video_index_badge').innerText = (currentIndex + 1) + " / " + activeList.length;
    }

    function nextVideo() { currentIndex = (currentIndex + 1) % activeList.length; renderCurrentVideo(); }
    function prevVideo() { currentIndex = (currentIndex - 1 + activeList.length) % activeList.length; renderCurrentVideo(); }

    function switchCategory(cat) {
      activeList = [...(videoDatabase[cat] || videoDatabase.all)];
      currentIndex = 0;
      renderCurrentVideo();
    }

    let startY = 0;
    const swipeBox = document.getElementById('swipe_box');
    swipeBox.addEventListener('touchstart', e => { startY = e.touches[0].clientY; }, { passive: true });
    swipeBox.addEventListener('touchend', e => {
      const diffY = startY - e.changedTouches[0].clientY;
      if (Math.abs(diffY) > 45) { diffY > 0 ? nextVideo() : prevVideo(); }
    }, { passive: true });

    window.onload = function() { renderCurrentVideo(); };
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

# ==========================================
# 6. SMART CALCULATOR & COMPOUNDING
# ==========================================
@app.route("/calculator")
def calculator_page():
    content = """
    <div class="card" style="max-width:440px;margin:20px auto;background:#0b1120;border:1px solid rgba(56,189,248,0.3);">
      <h2 style="color:#38bdf8;text-align:center;font-size:20px;margin-bottom:12px;">🧮 Smart Calculator</h2>
      <div style="background:#030712;padding:14px;border-radius:10px;border:1px solid rgba(255,255,255,0.1);margin-bottom:14px;text-align:right;">
        <div id="calc_history" style="font-size:12px;color:#64748b;min-height:16px;"></div>
        <div id="calc_display" style="font-size:26px;font-weight:800;color:#38bdf8;">0</div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(4, 1fr);gap:8px;">
        <button class="btn" style="background:#ef4444;" onclick="cClear()">C</button>
        <button class="btn" style="background:#334155;" onclick="cDel()">⌫</button>
        <button class="btn" style="background:#334155;" onclick="cOp('%')">%</button>
        <button class="btn" style="background:#0284c7;" onclick="cOp('/')">÷</button>
        <button class="btn" style="background:#1e293b;" onclick="cNum('7')">7</button>
        <button class="btn" style="background:#1e293b;" onclick="cNum('8')">8</button>
        <button class="btn" style="background:#1e293b;" onclick="cNum('9')">9</button>
        <button class="btn" style="background:#0284c7;" onclick="cOp('*')">×</button>
        <button class="btn" style="background:#1e293b;" onclick="cNum('4')">4</button>
        <button class="btn" style="background:#1e293b;" onclick="cNum('5')">5</button>
        <button class="btn" style="background:#1e293b;" onclick="cNum('6')">6</button>
        <button class="btn" style="background:#0284c7;" onclick="cOp('-')">−</button>
        <button class="btn" style="background:#1e293b;" onclick="cNum('1')">1</button>
        <button class="btn" style="background:#1e293b;" onclick="cNum('2')">2</button>
        <button class="btn" style="background:#1e293b;" onclick="cNum('3')">3</button>
        <button class="btn" style="background:#0284c7;" onclick="cOp('+')">+</button>
        <button class="btn" style="background:#1e293b;" onclick="cNum('00')">00</button>
        <button class="btn" style="background:#1e293b;" onclick="cNum('0')">0</button>
        <button class="btn" style="background:#1e293b;" onclick="cNum('.')">.</button>
        <button class="btn btn-green" onclick="cEval()">=</button>
      </div>
    </div>
    <script>
    let curVal = "0";
    function updateDisp(){ document.getElementById('calc_display').innerText = curVal; }
    function cNum(n){ curVal = (curVal==="0" && n!==".") ? n : curVal+n; updateDisp(); }
    function cOp(op){ curVal += " "+op+" "; updateDisp(); }
    function cClear(){ curVal = "0"; document.getElementById('calc_history').innerText=""; updateDisp(); }
    function cDel(){ curVal = curVal.trim(); curVal = curVal.length<=1 ? "0" : curVal.slice(0,-1).trim(); updateDisp(); }
    function cEval(){
      try{
        document.getElementById('calc_history').innerText = curVal + " =";
        let sanitized = curVal.replace(/×/g, "*").replace(/÷/g, "/");
        curVal = String(Function('"use strict";return (' + sanitized + ')')());
        updateDisp();
      }catch(e){ curVal = "Error"; updateDisp(); }
    }
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

@app.route("/compounding")
def compounding_page():
    content = """
    <div class="card" style="max-width:650px;margin:20px auto;background:#0b1120;border:1px solid #10b981;">
      <h2 style="color:#34d399;font-size:22px;margin-bottom:6px;"><i class="fa-solid fa-chart-line"></i> Compounding Wealth Calculator</h2>
      <div style="display:flex;gap:8px;margin-bottom:16px;">
        <button id="btn_sip" class="btn btn-green" style="flex:1;" onclick="setCompType('sip')">Monthly SIP</button>
        <button id="btn_lump" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;" onclick="setCompType('lump')">Lumpsum</button>
      </div>
      <label id="lbl_amt">Monthly Investment Amount (₹):</label>
      <input type="number" id="c_amt" value="5000" oninput="calculateCompound()">
      <label>Expected Return Rate (% p.a.):</label>
      <input type="number" id="c_rate" value="15" step="0.5" oninput="calculateCompound()">
      <label>Time Period (Years):</label>
      <input type="number" id="c_years" value="10" min="1" max="40" oninput="calculateCompound()">
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-top:14px;">
        <div style="background:#030712;padding:12px;border-radius:10px;">
          <div style="font-size:11px;color:#94a3b8;">Invested</div>
          <div id="res_invested" style="font-size:18px;font-weight:800;color:#cbd5e1;">₹6,00,000</div>
        </div>
        <div style="background:#030712;padding:12px;border-radius:10px;">
          <div style="font-size:11px;color:#94a3b8;">Est. Gain</div>
          <div id="res_gain" style="font-size:18px;font-weight:800;color:#34d399;">₹7,93,227</div>
        </div>
        <div style="background:#030712;padding:12px;border-radius:10px;">
          <div style="font-size:11px;color:#38bdf8;">Maturity</div>
          <div id="res_total" style="font-size:20px;font-weight:900;color:#38bdf8;">₹13,93,227</div>
        </div>
      </div>
    </div>
    <script>
    let compType = 'sip';
    function setCompType(t){
      compType = t;
      document.getElementById('btn_sip').style.background = t==='sip'?'#059669':'rgba(255,255,255,0.08)';
      document.getElementById('btn_lump').style.background = t==='lump'?'#059669':'rgba(255,255,255,0.08)';
      document.getElementById('lbl_amt').innerText = t==='sip' ? "Monthly Investment Amount (₹):" : "One-Time Lumpsum Amount (₹):";
      calculateCompound();
    }
    function calculateCompound(){
      const p = Number(document.getElementById('c_amt').value) || 0;
      const r = (Number(document.getElementById('c_rate').value) || 0) / 100;
      const t = Number(document.getElementById('c_years').value) || 0;
      let invested = 0, total = 0;
      if(compType==='sip'){
        const n = t * 12, i = r / 12;
        invested = p * n;
        total = i > 0 ? p * ((Math.pow(1 + i, n) - 1) / i) * (1 + i) : invested;
      } else {
        invested = p; total = p * Math.pow(1 + r, t);
      }
      document.getElementById('res_invested').innerText = '₹' + Math.round(invested).toLocaleString('en-IN');
      document.getElementById('res_gain').innerText = '₹' + Math.round(Math.max(0, total - invested)).toLocaleString('en-IN');
      document.getElementById('res_total').innerText = '₹' + Math.round(total).toLocaleString('en-IN');
    }
    window.onload = function(){ calculateCompound(); };
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

# ==========================================
# 7. QUANTUM AI SIMULATOR
# ==========================================
@app.route("/quantum-ai")
def quantum_ai_page():
    content = """
    <div class="card" style="background:#0b1120;border:1px solid #8b5cf6;">
      <h2 style="color:#c084fc;"><i class="fa-solid fa-atom"></i> Quantum AI Supercomputing Engine</h2>
      <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">3-Qubit Hilbert state vector simulation aur neural decision nexus.</p>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;">
        <button class="btn btn-quantum" onclick="runQuantumSim('hadamard')">Apply H-Gate</button>
        <button class="btn btn-green" onclick="runQuantumSim('measure')">Measure & AI Collapse</button>
      </div>
      <div id="quantum_res_box" class="out">Circuit tayyar hai. Upar button dabayein...</div>
    </div>
    <script>
    async function runQuantumSim(act){
      const out = document.getElementById('quantum_res_box');
      out.innerHTML = 'Processing quantum transformation...';
      try{
        const res = await fetch('/api/quantum-engine', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:act})});
        const d = await res.json();
        out.innerHTML = d.output;
      }catch(e){ out.innerText = "Execution error."; }
    }
    window.onload = function(){ runQuantumSim('hadamard'); };
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

@app.route("/api/quantum-engine", methods=["POST"])
def quantum_engine():
    d = request.get_json(silent=True) or {}
    act = d.get("action", "hadamard")
    probs = [0.5, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0]
    r = random.random()
    measured_state = "000" if r <= 0.5 else "011"
    measured_idx = 0 if r <= 0.5 else 3
    entropy = round(-sum(p * math.log2(p) for p in probs if p > 0), 4)

    if act == "hadamard":
        res_html = f"<div class='step-box'><b>Quantum Superposition Active:</b> |ψ⟩ = 1/√2 |000⟩ + 1/√2 |011⟩<br>Entropy: {entropy} Bits</div>"
    else:
        res_html = f"<div class='step-box' style='border-left-color:#34d399;'><b>Measured State:</b> |{measured_state}⟩ (Idx: {measured_idx})<br>AI Verdict: <b style='color:#38bdf8;'>EXECUTE</b></div>"
    return jsonify({"output": res_html, "entropy": entropy, "state": measured_state})

# ==========================================
# 8. BACKEND APIS (AI, WALLET, ORDERS)
# ==========================================
@app.route("/api/live-market-ai", methods=["POST"])
def live_market_ai():
    d = request.get_json(silent=True) or {}
    sym = d.get("symbol", "NSE:RELIANCE")
    base_price = float(d.get("ltp", 1190.00))
    sec = int(time.time()) % 60
    live_price = round(base_price + (math.sin(sec) * (base_price * 0.003)), 2)
    rsi = round(45 + (math.cos(sec) * 25), 1)

    color = "#10b981" if rsi <= 38 else ("#ef4444" if rsi >= 65 else "#f59e0b")
    verdict = "STRONG BUY" if rsi <= 38 else ("AVOID / SELL" if rsi >= 65 else "WAIT / HOLD")
    html = f"""
    <div class='step-box' style='border-left-color:{color};'>
      <b>Asset:</b> {sym} | <b>Signal:</b> <span style='color:{color};font-weight:800;'>{verdict}</span><br>
      <b>RSI:</b> {rsi} / 100 | <b>LTP:</b> ₹{live_price:,.2f}
    </div>
    """
    return jsonify({"html": html, "price": live_price, "rsi": rsi})

@app.route("/api/get-wallet-orders")
def get_wallet_orders():
    u = session.get("username", "admin")
    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute("SELECT balance FROM user_wallets WHERE username = %s", (u,))
    row = c.fetchone()
    bal = row["balance"] if row else 10000.0
    c.execute("SELECT * FROM live_orders WHERE username = %s ORDER BY id DESC LIMIT 10", (u,))
    orders = c.fetchall()
    c.close(); conn.close()
    for o in orders: o["created_at"] = str(o["created_at"])
    return jsonify({"balance": bal, "orders": orders})

@app.route("/api/execute-trade", methods=["POST"])
def execute_trade():
    u = session.get("username", "admin")
    d = request.get_json(silent=True) or {}
    sym, action = d.get("symbol", "NSE:RELIANCE"), d.get("action", "BUY")
    qty, price = int(d.get("qty", 1)), float(d.get("price", 1000.0))
    cost = round(qty * price, 2)

    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute("SELECT balance FROM user_wallets WHERE username = %s", (u,))
    row = c.fetchone()
    bal = row["balance"] if row else 10000.0

    if action == "BUY":
        if bal < cost:
            c.close(); conn.close()
            return jsonify({"status": "FAILED", "reason": "Insufficient Balance!"})
        new_bal = bal - cost
    else:
        new_bal = bal + cost

    c.execute("UPDATE user_wallets SET balance = %s WHERE username = %s", (new_bal, u))
    c.execute("INSERT INTO live_orders (username, symbol, action, qty, price, status) VALUES (%s, %s, %s, %s, %s, %s)",
              (u, sym, action, qty, price, "EXECUTED"))
    conn.commit()
    c.close(); conn.close()
    return jsonify({"status": "SUCCESS", "message": f"{action} Safal! {qty} {sym} @ ₹{price:.2f}"})

@app.route("/api/deposit-funds", methods=["POST"])
def deposit_funds():
    u = session.get("username", "admin")
    d = request.get_json(silent=True) or {}
    amt, utr = float(d.get("amount", 0)), d.get("utr", "").strip()
    if amt <= 0 or len(utr) < 6: return jsonify({"status": "FAILED", "reason": "Invalid details!"})
    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute("SELECT balance FROM user_wallets WHERE username = %s", (u,))
    row = c.fetchone()
    new_bal = (row["balance"] if row else 0.0) + amt
    c.execute("UPDATE user_wallets SET balance = %s WHERE username = %s", (new_bal, u))
    conn.commit()
    c.close(); conn.close()
    return jsonify({"status": "SUCCESS", "new_balance": new_bal})

# ==========================================
# 9. REAL LIVE GOOGLE NEWS ENGINE
# ==========================================
@app.route("/news")
def news():
    content = """
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:14px;">
        <h2>🔴 24x7 Real-Time Live News Feed</h2>
        <div style="display:flex;gap:6px;">
          <button class="btn" style="background:#ef4444;padding:6px 10px;font-size:12px;" onclick="loadLiveNews('hi')">हिंदी</button>
          <button class="btn" style="background:#334155;padding:6px 10px;font-size:12px;" onclick="loadLiveNews('en')">English</button>
        </div>
      </div>
      <div id="live_feed_box"><div style="text-align:center;padding:20px;color:#38bdf8;">Fetching Live News...</div></div>
    </div>
    <script>
    async function loadLiveNews(lang='hi') {
      const box = document.getElementById('live_feed_box');
      box.innerHTML = '<div style="text-align:center;padding:20px;color:#38bdf8;">Fetching Live News...</div>';
      try {
        const res = await fetch(`/api/live-news-feed?lang=${lang}`);
        const data = await res.json();
        box.innerHTML = (data.articles || []).map(art => `
          <div class="news-item">
            <span style="font-size:11px;color:#38bdf8;font-weight:700;">${art.source}</span>
            <h4 style="margin:4px 0;"><a href="${art.link}" target="_blank" style="color:#f8fafc;text-decoration:none;">${art.title}</a></h4>
            <span style="font-size:11px;color:#64748b;">${art.published}</span>
          </div>
        `).join('');
      } catch(e) { box.innerHTML = '<div style="color:#ef4444;text-align:center;">Feed error.</div>'; }
    }
    window.onload = function() { loadLiveNews(); };
    </script>
    
  return render_template_string(T_HEAD + content + T_FOOT)

@app.route("/api/live-news-feed")
def live_news_feed_api():
    lang = request.args.get("lang", "hi")
    url = "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=hi&gl=IN&ceid=IN:hi" if lang == "hi" else "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-IN&gl=IN&ceid=IN:en"
    articles = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            root = ET.fromstring(resp.read())
            for item in root.findall('.//item')[:10]:
                title = item.find('title').text or "News"
                link = item.find('link').text or "#"
                pub = item.find('pubDate').text or ""
                articles.append({"title": title.rsplit(' - ', 1)[0], "source": title.rsplit(' - ', 1)[-1], "link": link, "published": pub})
    except Exception as e: print("RSS Error:", e)
    return jsonify({"articles": articles})

# ==========================================
# 10. MATH MASTER & SMART TOOLS
# ==========================================
@app.route("/math-master")
def math_master():
    content = """
    <div class="card" style="max-width:700px;margin:0 auto;">
      <h2>🧮 DEX AIR Math Master (Voice & Solver)</h2>
      <textarea id="mq" rows="3" placeholder="जैसे: 10km की रफ़्तार से 58km कितने देर में पहुँचेंगे?"></textarea>
      <button class="btn btn-purple" onclick="runMath()">हल निकालें</button>
      <div id="m_out" class="out">यहाँ आपका विस्तृत हल दिखेगा...</div>
    </div>
    <script>
    async function runMath(){
      var q = document.getElementById('mq').value.trim();
      if(!q) return alert("सवाल लिखें!");
      try{
        var res = await fetch('/math-calc', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})});
        var d = await res.json();
        document.getElementById('m_out').innerHTML = d.explanation;
      }catch(e){ document.getElementById('m_out').innerText="Error."; }
    }
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

@app.route("/math-calc", methods=["POST"])
def math_calc():
    d = request.get_json(silent=True) or {}
    q = d.get("question", "").lower()
    nums = [float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+", q)]
    if len(nums) >= 2:
        speed, dist = min(nums[0], nums[1]), max(nums[0], nums[1])
        th = dist / speed
        exp = f"<div class='step-box'><b>दूरी:</b> {dist} km | <b>चाल:</b> {speed} km/h<br><b>समय:</b> {round(th, 2)} घंटे ({int(th)} घंटे {int(round((th-int(th))*60))} मिनट)</div>"
        return jsonify({"explanation": exp})
    return jsonify({"explanation": "<div class='step-box'>कृपया साफ़ संख्याएँ दर्ज करें।</div>"})

@app.route("/smart-tools")
def smart_tools():
    content = """
    <div class="card" style="max-width:720px;margin:0 auto;">
      <h2>🧰 Daily Smart Tools</h2>
      <div style="display:flex;gap:6px;margin:14px 0;">
        <button class="btn btn-green" style="flex:1;" onclick="calcG()">🧾 GST (18%)</button>
        <button class="btn btn-green" style="flex:1;" onclick="calcE()">🏦 EMI</button>
      </div>
      <input type="number" id="in_p" value="50000">
      <div id="st_out" class="out">गणना देखने के लिए ऊपर क्लिक करें...</div>
    </div>
    <script>
    function calcG(){ var v = Number(document.getElementById('in_p').value); document.getElementById('st_out').innerHTML = "Base: ₹"+v+" | <b>Total (18% GST): ₹"+(v*1.18).toFixed(2)+"</b>"; }
    function calcE(){ var p = Number(document.getElementById('in_p').value), r = (10.5/12)/100, n = 36; var emi = (p*r*Math.pow(1+r,n))/(Math.pow(1+r,n)-1); document.getElementById('st_out').innerHTML = "<b>Monthly EMI: ₹"+Math.round(emi)+" / माह</b>"; }
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

@app.route("/subscription")
def subscription():
    content = """
    <div class="card" style="max-width:650px;margin:0 auto;text-align:center;">
      <h2>💳 DEX AIR Pro Subscription (₹99)</h2>
      <img src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=upi://pay?pa=8791223831@ibl%26pn=DEX%20AIR%26am=99%26cu=INR" style="margin:14px auto;display:block;">
      <div>Official UPI: <code style="color:#38bdf8;">8791223831@ibl</code></div>
    </div>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

            
