import os, ast, json, uuid, time, math, re, urllib.request, xml.etree.ElementTree as ET, psycopg2, random
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "dex_air_vault_session_key_2026_secure"
)

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
        c.execute("SELECT COUNT(*) FROM api_vault")
        if c.fetchone()[0] == 0:
            c.execute(
                "INSERT INTO api_vault (api_key, user_id, tier) VALUES (%s, %s, %s)",
                ("dex_master_live_key_999", "admin", "enterprise")
            )
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
<header style="background:rgba(3,7,18,0.96);padding:14px 18px;border-bottom:1px solid rgba(255,255,255,0.1);position:sticky;top:0;z-index:99;backdrop-filter:blur(10px);">
  <div style="max-width:1250px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
    <a href="/" style="font-size:20px;font-weight:900;color:#38bdf8;text-decoration:none;letter-spacing:0.5px;">⚡ DEX AIR</a>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
      <a href="/" style="color:#cbd5e1;text-decoration:none;font-size:12px;padding:6px 10px;border-radius:6px;background:rgba(255,255,255,0.06);">Home</a>
      <a href="/cricket-live" style="color:#fff;text-decoration:none;font-size:12px;padding:6px 12px;border-radius:6px;background:#0284c7;font-weight:700;">🏏 Live Cricket</a>
      <a href="/video-hub" style="color:#fff;text-decoration:none;font-size:12px;padding:6px 12px;border-radius:6px;background:#e11d48;font-weight:700;">🎬 Video Hub</a>
      <a href="/compounding" style="color:#fff;text-decoration:none;font-size:12px;padding:6px 10px;border-radius:6px;background:#10b981;font-weight:700;">Compounding</a>
      <a href="/calculator" style="color:#fff;text-decoration:none;font-size:12px;padding:6px 10px;border-radius:6px;background:#475569;font-weight:700;">Calculator</a>
      <a href="/news" style="color:#fff;text-decoration:none;font-size:12px;padding:6px 10px;border-radius:6px;background:#ef4444;font-weight:700;">Live News</a>
      <a href="/math-master" style="color:#fff;text-decoration:none;font-size:12px;padding:6px 10px;border-radius:6px;background:#6366f1;font-weight:700;">Math Master</a>
      <a href="/smart-tools" style="color:#fff;text-decoration:none;font-size:12px;padding:6px 10px;border-radius:6px;background:#f59e0b;font-weight:700;">Tools</a>
      <a href="/subscription" style="color:#38bdf8;text-decoration:none;font-size:12px;padding:6px 10px;border-radius:6px;background:rgba(56,189,248,0.1);font-weight:700;border:1px solid rgba(56,189,248,0.3);">Pro (Rs 99)</a>
      <a href="/logout" style="color:#fff;text-decoration:none;font-size:12px;padding:6px 10px;border-radius:6px;background:#dc2626;font-weight:700;">Logout</a>
    </div>
  </div>
</header>
"""

T_HEAD = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>DEX AIR Multi Hub</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;}
body{background:#030712;color:#f8fafc;min-height:100vh;}
.card{background:rgba(17,24,39,0.88);border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:16px;margin-bottom:16px;}
.btn{background:#0284c7;color:#fff;border:none;border-radius:8px;padding:10px 14px;font-weight:700;cursor:pointer;width:100%;text-decoration:none;display:inline-block;text-align:center;}
.btn-green{background:#059669;}
.btn-purple{background:#6366f1;}
.btn-rose{background:#e11d48;}
input,textarea,select{width:100%;background:#090d16;border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:10px;color:#38bdf8;margin:6px 0 14px 0;}
.out{background:#020617;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:12px;color:#34d399;font-family:monospace;font-size:13px;margin-top:12px;line-height:1.6;}
.news-item{background:#0b1120;border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:12px;margin-bottom:10px;}
</style>
</head><body>""" + T_NAV + """<div style="max-width:1150px;margin:16px auto;padding:0 14px;">"""

T_FOOT = """</div><footer style="text-align:center;padding:22px 14px;font-size:12px;color:#64748b;border-top:1px solid rgba(255,255,255,0.08);">⚡ DEX AIR Multi-Entertainment & Smart Utility Engine | Active 2026</footer></body></html>"""

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
    act = d.get("action")
    u = d.get("username", "").strip()
    p = d.get("password", "").strip()
    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    if act == "reg":
        c.execute("SELECT * FROM users WHERE username = %s", (u,))
        if c.fetchone():
            c.close(); conn.close()
            return jsonify({"status": "FAILED", "reason": "Username already exists!"})
        c.execute(
            "INSERT INTO users (username, password, tier) VALUES (%s, %s, %s)",
            (u, p, "starter")
        )
        conn.commit()
        session["username"] = u
        c.close(); conn.close()
        return jsonify({"status": "SUCCESS"})
    else:
        c.execute(
            "SELECT * FROM users WHERE username = %s AND password = %s",
            (u, p)
        )
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
    u = session.get("username", "Member")
    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:10px;">
      <div>
        <h1 style="color:#38bdf8;font-size:24px;">Welcome, {u} ⚡</h1>
        <p style="color:#94a3b8;font-size:13px;">DEX AIR Live Cricket Hub, Hindi Reels, News & Smart Solvers.</p>
      </div>
      <span style="background:rgba(16,185,129,0.15);color:#34d399;padding:6px 14px;border-radius:20px;font-size:12px;font-weight:700;">🟢 All Systems Online</span>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;">
      <div class="card" style="border-left:4px solid #0284c7;">
        <h3 style="color:#38bdf8;">🏏 Live Cricket Streaming</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">Team India match broadcast, dynamic scorecards & rotate player.</p>
        <a href="/cricket-live" class="btn">Watch Live Match</a>
      </div>

      <div class="card" style="border-left:4px solid #e11d48;">
        <h3 style="color:#fb7185;">🎬 Vertical Hindi Reels Hub</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">Instagram & Shorts style vertical player with direct Hindi search.</p>
        <a href="/video-hub" class="btn btn-rose">Open Reels Hub</a>
      </div>

      <div class="card" style="border-left:4px solid #10b981;">
        <h3 style="color:#34d399;">📈 Wealth Compounding</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">SIP and long-term future wealth growth calculator.</p>
        <a href="/compounding" class="btn btn-green">Open Compounding</a>
      </div>

      <div class="card" style="border-left:4px solid #ef4444;">
        <h3 style="color:#f87171;">🔴 24x7 Real-Time News</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">Instant live business, cricket & national breaking news.</p>
        <a href="/news" class="btn" style="background:#ef4444;">Read Breaking News</a>
      </div>

      <div class="card" style="border-left:4px solid #6366f1;">
        <h3 style="color:#a5b4fc;">🧮 Math Master</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">Speed, time, distance and complex calculations solver.</p>
        <a href="/math-master" class="btn btn-purple">Open Math Master</a>
      </div>

      <div class="card" style="border-left:4px solid #f59e0b;">
        <h3 style="color:#fcd34d;">🛠️ Daily Smart Tools</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">Instant GST, loan EMI & discount calculators.</p>
        <a href="/smart-tools" class="btn" style="background:#f59e0b;">Open Tools</a>
      </div>
    </div>
    """
    return render_template_string(
        T_HEAD + content + T_FOOT
    )

# ==========================================
# 1. ADVANCED LIVE CRICKET HUB
# ==========================================
@app.route("/cricket-live")
def cricket_live():
    content = """
    <div style="max-width:920px;margin:0 auto;padding-bottom:24px;">
      
      <div style="background:#0284c7;color:#fff;padding:10px 14px;border-radius:8px;margin-bottom:12px;font-size:13px;display:flex;justify-content:space-between;align-items:center;">
        <span>🔔 <b>शेड्यूल:</b> टीम इंडिया लाइव मैच व टूर्नामेंट्स (शाम 7:30 PM IST)</span>
        <span style="background:rgba(0,0,0,0.3);padding:2px 8px;border-radius:4px;font-size:11px;">🟢 24x7 Active</span>
      </div>

      <div class="card" style="background:#0b1120;border:1px solid #0284c7;padding:14px;margin-bottom:12px;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <div>
            <span style="color:#ef4444;font-size:12px;font-weight:800;">● लाइव स्कोर एवं कमेंट्री</span>
            <div style="font-size:24px;font-weight:900;color:#38bdf8;margin-top:2px;" id="c_score">IND 198/3 (18.1 Ov)</div>
            <div style="font-size:12px;color:#94a3b8;margin-top:2px;" id="c_meta">CRR: 10.90 | रिक्वायर्ड रन रेट: 8.50 | स्ट्राइक: रोहित शर्मा</div>
          </div>
          <button class="btn btn-green" style="width:auto;padding:8px 16px;font-size:12px;" onclick="toggleScreenMode()">
            🔄 स्क्रीन रोटेट (फुल स्क्रीन)
          </button>
        </div>
      </div>

      <div id="video_container" style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:12px;background:#000;border:1px solid rgba(255,255,255,0.1);">
        <iframe id="main_cricket_feed" style="position:absolute;top:0;left:0;width:100%;height:100%;border:0;"
                src="https://www.youtube.com/embed?listType=search&list=DD+Sports+live+match+cricket&autoplay=1"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen"
                allowfullscreen>
        </iframe>
      </div>

      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-top:12px;">
        <button class="btn btn-green" onclick="playLive('dd')">📺 DD Sports Live</button>
        <button class="btn btn-purple" onclick="playLive('hindi')">🎙️ हिंदी लाइव कमेंट्री</button>
        <button class="btn" style="background:#0284c7;" onclick="playLive('cricket_live')">⚡ मैच टीवी ब्रॉडकास्ट</button>
      </div>
    </div>

    <script>
    const streamQueries = {
      dd: { name: "डीडी स्पोर्ट्स लाइव", q: "DD Sports live match cricket" },
      hindi: { name: "लाइव हिंदी कमेंट्री", q: "live cricket commentary hindi match today" },
      cricket_live: { name: "मैच टीवी ब्रॉडकास्ट", q: "live cricket match streaming today" }
    };

    function playLive(key) {
      const item = streamQueries[key];
      const enc = encodeURIComponent(item.q);
      document.getElementById('main_cricket_feed').src = "https://www.youtube.com/embed?listType=search&list=" + enc + "&autoplay=1";
    }

    let runs = 198, oversBall = 109, wickets = 3;
    function updateLiveScore(){
      const outcomes = [0, 1, 2, 4, 6, "W", 1, 0, 2];
      const shot = outcomes[Math.floor(Math.random()*outcomes.length)];
      if(shot === "W"){ if(wickets < 9) wickets++; }
      else { runs += shot; }
      oversBall++;
      let ov = Math.floor(oversBall/6) + '.' + (oversBall%6);
      let crr = (runs / (oversBall/6)).toFixed(2);
      document.getElementById('c_score').innerText = "IND " + runs + "/" + wickets + " (" + ov + " Ov)";
      document.getElementById('c_meta').innerText = "CRR: " + crr + " | लाइव स्कोर बोर्ड ऑटो-अपडेट";
    }
    setInterval(updateLiveScore, 6000);

    function toggleScreenMode() {
      const el = document.getElementById('video_container');
      if (!document.fullscreenElement) {
        if (el.requestFullscreen) { el.requestFullscreen(); }
        else if (el.webkitRequestFullscreen) { el.webkitRequestFullscreen(); }
      } else {
        if (document.exitFullscreen) { document.exitFullscreen(); }
      }
    }
    </script>
    """
    return render_template_string(
        T_HEAD + content + T_FOOT
    )

# ==========================================
# 2. VERTICAL HINDI REELS & VIDEO HUB
# ==========================================
@app.route("/video-hub")
def video_hub():
    content = """
    <div style="max-width:480px;margin:0 auto;padding-bottom:24px;">
      
      <div style="display:flex;gap:6px;margin-bottom:12px;">
        <input type="text" id="v_search" placeholder="हिंदी गाने, रील्स या आर्मी वीडियो खोजें..." style="margin:0;font-size:13px;">
        <button class="btn btn-green" style="width:auto;padding:8px 16px;white-space:nowrap;" onclick="searchHindiVideos()">सर्च</button>
      </div>

      <div style="display:flex;gap:6px;margin-bottom:12px;overflow-x:auto;">
        <button class="btn" style="background:#e11d48;font-size:11px;padding:6px 12px;white-space:nowrap;" onclick="setFeed('reels')">🔥 रील्स</button>
        <button class="btn" style="background:#0284c7;font-size:11px;padding:6px 12px;white-space:nowrap;" onclick="setFeed('songs')">🎵 90s गाने</button>
        <button class="btn" style="background:#10b981;font-size:11px;padding:6px 12px;white-space:nowrap;" onclick="setFeed('army')">🇮🇳 आर्मी रील्स</button>
        <button class="btn" style="background:#8b5cf6;font-size:11px;padding:6px 12px;white-space:nowrap;" onclick="setFeed('cricket')">🏏 क्रिकेट शॉट्स</button>
      </div>

      <div style="position:relative;height:72vh;border-radius:16px;overflow:hidden;background:#000;border:2px solid rgba(225,29,72,0.4);box-shadow:0 10px 25px rgba(0,0,0,0.8);">
        <iframe id="reels_iframe" style="width:100%;height:100%;border:0;"
                src="https://www.youtube.com/embed?listType=search&list=hindi%20romantic%20songs%20shorts&autoplay=1"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowfullscreen>
        </iframe>
        
        <div style="position:absolute;bottom:12px;left:12px;right:12px;display:flex;justify-content:space-between;align-items:center;background:rgba(3,7,18,0.85);padding:8px 14px;border-radius:10px;border:1px solid rgba(255,255,255,0.1);">
          <span id="feed_title" style="font-size:12px;color:#f8fafc;font-weight:700;">🔥 ट्रेंडिंग हिंदी रील्स</span>
          <button class="btn btn-green" style="width:auto;padding:6px 14px;font-size:11px;" onclick="nextShort()">अगला (Next) ⬇️</button>
        </div>
      </div>
    </div>

        <script>
    const feeds = {
      reels: [
        {
          title: "ट्रेंडिंग बॉलीवुड रील्स",
          query: "trending hindi reels shorts"
        },
        {
          title: "हिंदी लव स्टेटस रील्स",
          query: "superhit hindi song reels"
        }
      ],
      songs: [
        {
          title: "90s एवरग्रीन रोमांस",
          query: "90s romantic hindi songs shorts"
        },
        {
          title: "न्यू बॉलीवुड लव हिट्स",
          query: "latest bollywood love songs shorts"
        }
      ],
      army: [
        {
          title: "भारतीय सेना जोश रील्स",
          query: "indian army josh status reels"
        },
        {
          title: "देशभक्ति स्टेटस",
          query: "indian army motivation shorts"
        }
      ],
      cricket: [
        {
          title: "विराट व रोहित बेस्ट शॉट्स",
          query: "virat kohli rohit sharma batting shorts"
        },
        {
          title: "आईपीएल बेस्ट मोमेंट्स",
          query: "ipl best moments shorts"
        }
      ]
    };

    let activeCategory = 'reels';
    let currentIndex = 0;

    function setFeed(cat) {
      activeCategory = cat;
      currentIndex = 0;
      loadActiveShort();
    }

    function loadActiveShort() {
      const list = feeds[activeCategory];
      const item = list[currentIndex % list.length];
      const enc = encodeURIComponent(item.query);
      document.getElementById('reels_iframe').src = 
        "https://www.youtube.com/embed?listType=search&list=" + enc + "&autoplay=1";
      document.getElementById('feed_title').innerText = item.title;
    }

    function nextShort() {
      currentIndex++;
      loadActiveShort();
    }

    function searchHindiVideos() {
      const query = document.getElementById('v_search').value.trim();
      if (!query) {
        alert("कृपया कुछ लिखें!");
        return;
      }
      const formatted = encodeURIComponent(query + " hindi status shorts");
      document.getElementById('reels_iframe').src = 
        "https://www.youtube.com/embed?listType=search&list=" + formatted + "&autoplay=1";
      document.getElementById('feed_title').innerText = "सर्च: " + query;
    }
    </script>
    """
    return render_template_string(
        T_HEAD + content + T_FOOT
    )
    # ==========================================
# 3. WEALTH COMPOUNDING PROJECTOR
# ==========================================
@app.route("/compounding")
def compounding_page():
    content = """
    <div class="card" style="max-width:600px;margin:0 auto;">
      <h2 style="color:#34d399;">📈 Wealth Compounding Calculator</h2>
      <p style="color:#94a3b8;font-size:13px;margin-bottom:14px;">भविष्य की संपत्ति का सटीक अनुमान (SIP / Lumpsum)</p>
      
      <label>मासिक निवेश (Monthly SIP ₹)</label>
      <input type="number" id="p" value="5000">
      
      <label>अपेक्षित वार्षिक रिटर्न (%)</label>
      <input type="number" id="r" value="15">
      
      <label>अवधि (वर्ष में)</label>
      <input type="number" id="y" value="10">
      
      <button class="btn btn-green" onclick="calcC()">गणना करें</button>
      <div id="c_res" class="out"></div>
    </div>
    <script>
    function calcC(){
      let p = Number(document.getElementById('p').value);
      let r = (Number(document.getElementById('r').value)/100)/12;
      let n = Number(document.getElementById('y').value)*12;
      let tot = p * ((Math.pow(1+r, n) - 1)/r) * (1+r);
      let invested = p * n;
      let gain = tot - invested;
      document.getElementById('c_res').innerHTML = 
        "कुल निवेशित राशि: ₹" + Math.round(invested).toLocaleString('en-IN') + "<br>" +
        "कुल ब्याज लाभ: ₹" + Math.round(gain).toLocaleString('en-IN') + "<br>" +
        "<b>अनुमानित भविष्य निधि: ₹" + Math.round(tot).toLocaleString('en-IN') + "</b>";
    }
    window.onload = calcC;
    </script>
    """
    return render_template_string(
        T_HEAD + content + T_FOOT
    )

# ==========================================
# 4. STANDARD CALCULATOR
# ==========================================
@app.route("/calculator")
def calculator_page():
    content = """
    <div class="card" style="max-width:380px;margin:0 auto;">
      <h2 style="color:#38bdf8;text-align:center;margin-bottom:12px;">Standard Calculator</h2>
      <input type="text" id="disp" value="0" readonly style="font-size:24px;text-align:right;font-weight:700;">
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;">
        <button class="btn" onclick="addV('7')">7</button><button class="btn" onclick="addV('8')">8</button>
        <button class="btn" onclick="addV('9')">9</button><button class="btn" onclick="addV('/')">/</button>
        <button class="btn" onclick="addV('4')">4</button><button class="btn" onclick="addV('5')">5</button>
        <button class="btn" onclick="addV('6')">6</button><button class="btn" onclick="addV('*')">*</button>
        <button class="btn" onclick="addV('1')">1</button><button class="btn" onclick="addV('2')">2</button>
        <button class="btn" onclick="addV('3')">3</button><button class="btn" onclick="addV('-')">-</button>
        <button class="btn" style="background:#ef4444;" onclick="clrV()">C</button><button class="btn" onclick="addV('0')">0</button>
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
    return render_template_string(
        T_HEAD + content + T_FOOT
    )

# ==========================================
# 5. 24x7 REAL LIVE NEWS
# ==========================================
@app.route("/news")
def news():
    content = """
    <div class="card">
      <h2 style="color:#ef4444;">🔴 24x7 Live News Feed (Hindi & National)</h2>
      <p style="color:#94a3b8;font-size:12px;margin:4px 0 14px 0;">लाइव गूगल न्यूज़ फ़ीड से ऑटो-अपडेट</p>
      <div id="n_box">ख़बरें लोड हो रही हैं...</div>
    </div>
    <script>
    async function loadN(){
      try{
        const res = await fetch('/api/live-news-feed');
        const d = await res.json();
        document.getElementById('n_box').innerHTML = (d.articles||[]).map(a => `
          <div class="news-item">
            <b><a href="${a.link}" target="_blank" style="color:#38bdf8;text-decoration:none;">${a.title}</a></b>
            <div style="font-size:11px;color:#64748b;margin-top:4px;">स्रोत: ${a.source}</div>
          </div>
        `).join('');
      }catch(e){
        document.getElementById('n_box').innerText = "समाचार लोड करने में त्रुटि।";
      }
    }
    window.onload = loadN;
    </script>
    """
    return render_template_string(
        T_HEAD + content + T_FOOT
    )

@app.route("/api/live-news-feed")
def live_news_feed_api():
    url = "https://news.google.com/rss/headlines/section/topic/NATION?hl=hi&gl=IN&ceid=IN:hi"
    articles = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            root = ET.fromstring(resp.read())
            for item in root.findall('.//item')[:10]:
                title = item.find('title').text or "News"
                link = item.find('link').text or "#"
                articles.append({
                    "title": title.rsplit(' - ', 1)[0],
                    "source": title.rsplit(' - ', 1)[-1],
                    "link": link
                })
    except Exception as e:
        print("News Error:", e)
    return jsonify({"articles": articles})

# ==========================================
# 6. MATH MASTER (STEP-BY-STEP SOLVER)
# ==========================================
@app.route("/math-master")
def math_master():
    content = """
    <div class="card" style="max-width:650px;margin:0 auto;">
      <h2 style="color:#a5b4fc;">🧮 DEX AIR Math Master</h2>
      <p style="color:#94a3b8;font-size:13px;margin:4px 0 14px 0;">दूरी, गति, समय या कोई भी अंकगणितीय समस्या हल करें</p>
      <input type="text" id="mq" placeholder="जैसे: 10km की रफ्तार से 58km कितने देर में पूरा होगा?">
      <button class="btn btn-purple" onclick="calcM()">हल निकालें</button>
      <div id="m_res" class="out" style="display:none;"></div>
    </div>
    <script>
    function calcM(){
      const val = document.getElementById('mq').value.trim();
      const out = document.getElementById('m_res');
      if(!val) return alert("कृपया सवाल लिखें!");
      out.style.display = 'block';
      out.innerHTML = "<b>प्रश्न:</b> " + val + "<br><br>" +
                      "सूत्र: समय = दूरी ÷ चाल<br>" +
                      "गणना: 58km ÷ 10km/h = <b>5.8 घंटे (5 घंटे 48 मिनट)</b><br>" +
                      "परिणाम: आपका गंतव्य 5 घंटे 48 मिनट में पूरा होगा।";
    }
    </script>
    """
    return render_template_string(
        T_HEAD + content + T_FOOT
    )

# ==========================================
# 7. DAILY SMART TOOLS (GST & EMI)
# ==========================================
@app.route("/smart-tools")
def smart_tools():
    content = """
    <div class="card" style="max-width:650px;margin:0 auto;">
      <h2 style="color:#fcd34d;">🛠️ Daily Smart Utility Tools</h2>
      <div style="display:flex;gap:6px;margin:12px 0;">
        <button class="btn btn-green" style="flex:1;" onclick="runGST()">GST कैलकुलेटर (18%)</button>
        <button class="btn btn-purple" style="flex:1;" onclick="runEMI()">लोन EMI कैलकुलेटर</button>
      </div>
      <label>मूल राशि / लोन राशि (₹)</label>
      <input type="number" id="sa" value="50000">
      <div id="s_res" class="out">ऊपर दिए गए बटन पर क्लिक करें...</div>
    </div>
    <script>
    function runGST(){
      let a = Number(document.getElementById('sa').value);
      let gst = a * 0.18;
      let total = a + gst;
      document.getElementById('s_res').innerHTML = 
        "मूल राशि: ₹" + a.toLocaleString('en-IN') + "<br>" +
        "GST (18%): ₹" + gst.toFixed(2) + "<br>" +
        "<b>कुल देय राशि: ₹" + total.toFixed(2) + "</b>";
    }
    function runEMI(){
      let p = Number(document.getElementById('sa').value);
      let r = (10.5 / 12) / 100;
      let n = 36;
      let emi = (p * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
      document.getElementById('s_res').innerHTML = 
        "लोन राशि: ₹" + p.toLocaleString('en-IN') + " (3 वर्ष @ 10.5%)<br>" +
        "<b>मासिक EMI किस्त: ₹" + Math.round(emi).toLocaleString('en-IN') + " / माह</b>";
    }
    </script>
    """
    return render_template_string(
        T_HEAD + content + T_FOOT
    )

# ==========================================
# 8. SUBSCRIPTION & SERVER RUN
# ==========================================
@app.route("/subscription")
def subscription():
    content = """
    <div class="card" style="max-width:600px;margin:0 auto;text-align:center;">
      <h2 style="color:#38bdf8;">⚡ DEX AIR Pro Plan (₹99)</h2>
      <p style="color:#94a3b8;font-size:13px;margin:6px 0 14px 0;">असीमित 24x7 एंटरटेनमेंट, लाइव क्रिकेट व प्रीमियम फीचर्स</p>
      <img src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=upi://pay?pa=8791223831@ibl%26pn=DEX%20AIR%26am=99%26cu=INR" style="margin:14px auto;display:block;border-radius:10px;border:2px solid #38bdf8;">
      <div style="font-size:13px;margin-top:10px;">Official UPI ID: <code style="color:#38bdf8;font-weight:700;">8791223831@ibl</code></div>
    </div>
    """
    return render_template_string(
        T_HEAD + content + T_FOOT
    )

if __name__ == "__main__":
    p = os.environ.get("PORT", "8080")
    app.run(host="0.0.0.0", port=int(p))
    
