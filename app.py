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
      <a href="/live-market" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:#10b981;font-weight:700;">Terminal</a>
      <a href="/cricket-live" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:#0284c7;font-weight:700;">Live Cricket</a>
      <a href="/video-hub" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:#e11d48;font-weight:700;">Video Hub</a>
      <a href="/calculator" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:#0284c7;font-weight:700;">Calculator</a>
      <a href="/compounding" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:#10b981;font-weight:700;">Compounding</a>
      <a href="/quantum-ai" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 11px;border-radius:6px;background:#8b5cf6;font-weight:700;">Quantum AI</a>
      <a href="/news" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 11px;border-radius:6px;background:#ef4444;font-weight:700;">Live News</a>
      <a href="/math-master" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:#6366f1;font-weight:700;">Math Master</a>
      <a href="/smart-tools" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:#f59e0b;font-weight:700;">Tools</a>
      <a href="/subscription" style="color:#38bdf8;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:rgba(56,189,248,0.1);font-weight:700;border:1px solid rgba(56,189,248,0.3);">Plan (Rs 99)</a>
      <a href="/logout" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 12px;border-radius:6px;background:#ef4444;font-weight:700;">Logout</a>
    </div>
  </div>
</header>
"""

T_HEAD = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>DEX AIR Enterprise</title>
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
.news-item{background:#0b1120;border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:14px;margin-bottom:12px;}
</style>
</head><body>""" + T_NAV + """<div style="max-width:1150px;margin:20px auto;padding:0 14px;">"""

T_FOOT = """</div><footer style="text-align:center;padding:20px;font-size:12px;color:#64748b;border-top:1px solid rgba(255,255,255,0.08);">DEX AIR Enterprise | PostgreSQL Live Active</footer></body></html>"""

@app.route("/login")
def login_page():
    if 'username' in session:
        return redirect("/")
    html = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <title>DEX AIR - Gateway</title>
    <style>
    *{box-sizing:border-box;margin:0;padding:0;font-family:sans-serif;}
    body{background:#030712;color:#f8fafc;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:16px;}
    .auth-box{background:#0b1120;border:1px solid rgba(56,189,248,0.3);border-radius:16px;width:100%;max-width:420px;padding:24px;}
    input{width:100%;background:#030712;border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:12px;color:#38bdf8;margin:8px 0 16px 0;}
    .btn{padding:12px;border:none;border-radius:8px;font-weight:700;cursor:pointer;width:100%;font-size:14px;}
    .btn-green{background:#059669;color:#fff;}
    .btn-purple{background:#6366f1;color:#fff;}
    .out{background:#020617;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:12px;font-size:13px;margin-top:14px;text-align:center;}
    </style></head><body>
      <div class="auth-box">
        <h2 style="color:#38bdf8;text-align:center;margin-bottom:14px;">⚡ DEX AIR GATEWAY</h2>
        <div style="display:flex;gap:6px;margin-bottom:18px;">
          <button id="tb_login" class="btn btn-green" style="flex:1;" onclick="setMode('login')">Sign In</button>
          <button id="tb_reg" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;" onclick="setMode('reg')">Sign Up</button>
        </div>
        <label>Username</label><input type="text" id="auth_user">
        <label>Password</label><input type="password" id="auth_pass">
        <button id="action_btn" class="btn btn-green" onclick="submitAuth()">Sign In</button>
        <div id="auth_res" class="out" style="display:none;"></div>
      </div>
      <script>
      let mode = 'login';
      function setMode(m){
        mode = m;
        document.getElementById('action_btn').innerText = m === 'login' ? 'Sign In' : 'Sign Up';
        document.getElementById('action_btn').className = m === 'login' ? 'btn btn-green' : 'btn btn-purple';
      }
      async function submitAuth(){
        const u = document.getElementById('auth_user').value.trim();
        const p = document.getElementById('auth_pass').value.trim();
        const out = document.getElementById('auth_res');
        if(!u || !p){ alert("Username & Password required!"); return; }
        out.style.display = 'block'; out.innerText = 'Authenticating...';
        try{
          const res = await fetch('/auth-act', {
            method:'POST',headers:{'Content-Type':'application/json'},
            body: JSON.stringify({action: mode, username: u, password: p})
          });
          const d = await res.json();
          if(d.status==='SUCCESS'){ window.location.href='/'; }
          else { out.innerHTML = "<span style='color:#ef4444;'>" + d.reason + "</span>"; }
        }catch(e){ out.innerText = "Connection error."; }
      }
      </script>
    </body></html>"""
    return html

@app.route("/auth-act", methods=["POST"])
def auth_act():
    d = request.get_json(silent=True) or {}
    act, u, p = d.get("action"), d.get("username", "").strip(), d.get("password", "").strip()
    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    if act == "reg":
        c.execute("SELECT * FROM users WHERE username = %s", (u,))
        if c.fetchone():
            c.close(); conn.close()
            return jsonify({"status": "FAILED", "reason": "Username already exists!"})
        c.execute("INSERT INTO users (username, password, tier) VALUES (%s, %s, %s)", (u, p, "starter"))
        conn.commit()
        session["username"] = u
        c.close(); conn.close()
        return jsonify({"status": "SUCCESS"})
    else:
        c.execute("SELECT * FROM users WHERE username = %s AND password = %s", (u, p))
        row = c.fetchone()
        c.close(); conn.close()
        if row:
            session["username"] = u
            return jsonify({"status": "SUCCESS"})
        return jsonify({"status": "FAILED", "reason": "Invalid credentials!"})

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect("/login")

@app.route("/")
def home():
    u = session.get("username", "Trader")
    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:10px;">
      <div>
        <h1 style="color:#38bdf8;font-size:26px;">Welcome, {u} 👋</h1>
        <p style="color:#94a3b8;font-size:13px;">Pro Trading Terminal, Live Cricket, Reels Video Hub & Quantum AI.</p>
      </div>
      <span style="background:rgba(16,185,129,0.15);color:#34d399;padding:6px 14px;border-radius:20px;font-size:12px;font-weight:700;">🟢 Active</span>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;">
      <div class="card"><h3>📊 Pro Trading Terminal</h3><p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">Live candlestick charts, watchlist & wallet.</p><a href="/live-market" class="btn btn-green">Open Terminal</a></div>
      <div class="card"><h3>🏏 Live Cricket Stream</h3><p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">Team India & IPL 2026 live matches.</p><a href="/cricket-live" class="btn">Watch Cricket</a></div>
      <div class="card"><h3>🎬 Swipe Video Hub</h3><p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">Reels/Shorts swipeable interface.</p><a href="/video-hub" class="btn" style="background:#e11d48;">Open Video Hub</a></div>
      <div class="card"><h3>📈 Wealth Compounding</h3><p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">SIP and lumpsum return projector.</p><a href="/compounding" class="btn btn-green">Open Compounding</a></div>
      <div class="card"><h3>🌌 Quantum AI Simulator</h3><p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">Hilbert state vector simulation.</p><a href="/quantum-ai" class="btn btn-quantum">Open Quantum Engine</a></div>
      <div class="card"><h3>🔴 24x7 Live News</h3><p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">Real-time business and national feed.</p><a href="/news" class="btn" style="background:#ef4444;">Read Live News</a></div>
    </div>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

@app.route("/live-market")
def live_market():
    content = """
    <div class="card" style="background:#0b1120;padding:16px;">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div>
          <span style="font-size:12px;color:#94a3b8;">Trading Wallet Balance</span>
          <div id="wallet_balance_display" style="color:#34d399;font-size:24px;font-weight:900;">Rs 10,000.00</div>
        </div>
        <button class="btn btn-green" style="width:auto;padding:8px 16px;" onclick="alert('Wallet active')">+ Add Funds</button>
      </div>
    </div>
    <div class="card" style="padding:10px;background:#030712;">
      <div style="height:440px;width:100%;" id="full_page_chart"></div>
    </div>
    <div class="card" style="background:#0b1120;padding:16px;">
      <h3 style="color:#38bdf8;margin-bottom:10px;">⚡ Quick Execution Pad</h3>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
        <button class="btn btn-green" onclick="tradeAct('BUY')">BUY</button>
        <button class="btn" style="background:#ef4444;" onclick="tradeAct('SELL')">SELL</button>
      </div>
      <div id="t_out" class="out" style="display:none;"></div>
    </div>
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <script>
    function renderChart(){
      new TradingView.widget({
        "autosize": true, "symbol": "NSE:RELIANCE", "interval": "5",
        "timezone": "Asia/Kolkata", "theme": "dark", "container_id": "full_page_chart"
      });
    }
    async function tradeAct(side){
      const out = document.getElementById('t_out');
      out.style.display = 'block'; out.innerText = 'Processing ' + side + '...';
      try{
        const res = await fetch('/api/execute-trade', {
          method:'POST',headers:{'Content-Type':'application/json'},
          body: JSON.stringify({symbol:'NSE:RELIANCE', action:side, qty:1, price:1190})
        });
        const d = await res.json();
        out.innerText = d.message || d.reason;
      }catch(e){ out.innerText = 'Order error'; }
    }
    window.onload = renderChart;
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)
@app.route("/cricket-live")
def cricket_live():
    content = """
    <div class="card" style="background:#0b1120;padding:16px;">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <h3 style="color:#ef4444;">🔴 LIVE MATCH: INDIA vs NZ</h3>
        <span style="color:#34d399;font-weight:700;">⚡ AUTO-UPDATING</span>
      </div>
      <div style="background:#030712;padding:14px;border-radius:10px;margin:12px 0;">
        <div style="font-size:26px;font-weight:900;" id="c_score">184/3 (17.2 Ov)</div>
        <div style="color:#94a3b8;font-size:13px;" id="c_desc">CRR: 10.61 | Need 26 from 16 balls</div>
      </div>
      <div style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:10px;">
        <iframe id="c_iframe" style="position:absolute;top:0;left:0;width:100%;height:100%;border:0;"
                src="https://www.youtube.com/embed/live_stream?channel=UCNAqjh23zV71l3x1E4Z19-w&autoplay=1" allowfullscreen></iframe>
      </div>
    </div>
    <script>
    let r = 184, b = 104;
    function updateCricket(){
      r += Math.floor(Math.random()*4); b += 1;
      let ov = Math.floor(b/6) + '.' + (b%6);
      document.getElementById('c_score').innerText = r + "/3 (" + ov + " Ov)";
    }
    setInterval(updateCricket, 5000);
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

@app.route("/video-hub")
def video_hub():
    content = """
    <div style="max-width:480px;margin:0 auto;height:75vh;position:relative;border-radius:16px;overflow:hidden;background:#000;">
      <iframe id="vh_frame" style="width:100%;height:100%;border:none;" src="https://www.youtube.com/embed/9bZkp7q19f0?autoplay=1" allowfullscreen></iframe>
      <div style="position:absolute;bottom:10px;left:10px;right:10px;display:flex;gap:8px;">
        <button class="btn btn-green" onclick="nextV()">Next Video ⬇️</button>
      </div>
    </div>
    <script>
    const vids = ["9bZkp7q19f0", "JhHMJCUmq28", "aircAruvnKk"];
    let vi = 0;
    function nextV(){
      vi = (vi + 1) % vids.length;
      document.getElementById('vh_frame').src = "https://www.youtube.com/embed/" + vids[vi] + "?autoplay=1";
    }
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

@app.route("/calculator")
def calculator_page():
    content = """
    <div class="card" style="max-width:400px;margin:0 auto;">
      <h2 style="color:#38bdf8;text-align:center;">Calculator</h2>
      <input type="text" id="disp" value="0" style="font-size:24px;text-align:right;">
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;">
        <button class="btn" onclick="addV('7')">7</button><button class="btn" onclick="addV('8')">8</button>
        <button class="btn" onclick="addV('9')">9</button><button class="btn" onclick="addV('/')">/</button>
        <button class="btn" onclick="addV('4')">4</button><button class="btn" onclick="addV('5')">5</button>
        <button class="btn" onclick="addV('6')">6</button><button class="btn" onclick="addV('*')">*</button>
        <button class="btn" onclick="addV('1')">1</button><button class="btn" onclick="addV('2')">2</button>
        <button class="btn" onclick="addV('3')">3</button><button class="btn" onclick="addV('-')">-</button>
        <button class="btn" onclick="clrV()">C</button><button class="btn" onclick="addV('0')">0</button>
        <button class="btn btn-green" onclick="resV()">=</button><button class="btn" onclick="addV('+')">+</button>
      </div>
    </div>
    <script>
    let cv = "0";
    function addV(x){ cv = (cv==='0') ? x : cv+x; document.getElementById('disp').value = cv; }
    function clrV(){ cv = "0"; document.getElementById('disp').value = cv; }
    function resV(){ try{ cv = String(eval(cv)); document.getElementById('disp').value = cv; }catch(e){ cv="0"; } }
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

@app.route("/compounding")
def compounding_page():
    content = """
    <div class="card" style="max-width:600px;margin:0 auto;">
      <h2 style="color:#34d399;">Wealth Compounding</h2>
      <label>Monthly Investment (Rs)</label><input type="number" id="p" value="5000">
      <label>Expected Return (%)</label><input type="number" id="r" value="15">
      <label>Years</label><input type="number" id="y" value="10">
      <button class="btn btn-green" onclick="calcC()">Calculate</button>
      <div id="c_res" class="out"></div>
    </div>
    <script>
    function calcC(){
      let p = Number(document.getElementById('p').value);
      let r = (Number(document.getElementById('r').value)/100)/12;
      let n = Number(document.getElementById('y').value)*12;
      let tot = p * ((Math.pow(1+r, n) - 1)/r) * (1+r);
      document.getElementById('c_res').innerHTML = "<b>Estimated Total: Rs " + Math.round(tot).toLocaleString('en-IN') + "</b>";
    }
    window.onload = calcC;
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)
@app.route("/quantum-ai")
def quantum_ai_page():
    content = """
    <div class="card">
      <h2 style="color:#c084fc;">Quantum AI Simulator</h2>
      <button class="btn btn-quantum" onclick="runQ()" style="margin:14px 0;">Run Hilbert State Vector</button>
      <div id="q_out" class="out">State ready. Click to measure...</div>
    </div>
    <script>
    async function runQ(){
      const res = await fetch('/api/quantum-engine', {method:'POST'});
      const d = await res.json();
      document.getElementById('q_out').innerText = "Measured State: " + d.state + " | Entropy: " + d.entropy;
    }
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

@app.route("/api/quantum-engine", methods=["POST"])
def quantum_engine():
    s = "000" if random.random() <= 0.5 else "011"
    return jsonify({"state": s, "entropy": 1.0})

@app.route("/api/execute-trade", methods=["POST"])
def execute_trade():
    d = request.get_json(silent=True) or {}
    act = d.get("action", "BUY")
    return jsonify({"status": "SUCCESS", "message": f"{act} order placed successfully!"})

@app.route("/news")
def news():
    content = """
    <div class="card">
      <h2>🔴 Live News Feed</h2>
      <div id="n_box" style="margin-top:14px;">Loading...</div>
    </div>
    <script>
    async function loadN(){
      const res = await fetch('/api/live-news-feed');
      const d = await res.json();
      document.getElementById('n_box').innerHTML = (d.articles||[]).map(a => `
        <div class="news-item">
          <b><a href="${a.link}" target="_blank" style="color:#38bdf8;text-decoration:none;">${a.title}</a></b>
          <div style="font-size:11px;color:#64748b;margin-top:4px;">${a.source}</div>
        </div>
      `).join('');
    }
    window.onload = loadN;
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

@app.route("/api/live-news-feed")
def live_news_feed_api():
    url = "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=hi&gl=IN&ceid=IN:hi"
    articles = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            root = ET.fromstring(resp.read())
            for item in root.findall('.//item')[:8]:
                title = item.find('title').text or "News"
                link = item.find('link').text or "#"
                articles.append({"title": title.rsplit(' - ', 1)[0], "source": title.rsplit(' - ', 1)[-1], "link": link})
    except Exception as e:
        print("News Error:", e)
    return jsonify({"articles": articles})

@app.route("/math-master")
def math_master():
    content = """
    <div class="card">
      <h2>Math Master</h2>
      <input type="text" id="mq" placeholder="e.g. 58km at 10km/h">
      <button class="btn btn-purple" onclick="calcM()">Solve</button>
      <div id="m_res" class="out"></div>
    </div>
    <script>
    function calcM(){
      document.getElementById('m_res').innerText = "Distance 58km @ 10km/h = 5.8 Hours (5 hrs 48 mins)";
    }
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

@app.route("/smart-tools")
def smart_tools():
    content = """
    <div class="card">
      <h2>Smart Tools</h2>
      <label>Amount (Rs)</label><input type="number" id="sa" value="50000">
      <button class="btn btn-green" onclick="runGST()">GST (18%)</button>
      <div id="s_res" class="out"></div>
    </div>
    <script>
    function runGST(){
      let a = Number(document.getElementById('sa').value);
      document.getElementById('s_res').innerText = "Total with 18% GST: Rs " + (a * 1.18).toFixed(2);
    }
    </script>
    app.run(host="0.0.0.0", port=port)
        """
    return render_template_string(
        T_HEAD + content + T_FOOT
    )

@app.route("/subscription")
def subscription():
    content = """
    <div class="card" style="text-align:center;">
      <h2>DEX AIR Plan (Rs 99)</h2>
      <img src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=upi://pay?pa=8791223831@ibl%26pn=DEX%20AIR%26am=99%26cu=INR" style="margin:14px auto;display:block;">
      <div>Official UPI: <code style="color:#38bdf8;">8791223831@ibl</code></div>
    </div>
    """
    return render_template_string(
        T_HEAD + content + T_FOOT
    )

if __name__ == "__main__":
    p = os.environ.get("PORT", "8080")
    app.run(host="0.0.0.0", port=int(p))
    
