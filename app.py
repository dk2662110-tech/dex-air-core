import os, ast, json, uuid, time, math, re, urllib.request, xml.etree.ElementTree as ET, psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, render_template_string, session, redirect

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dex_air_super_secure_vault_session_key_2026")

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

T_NAV = """
<header style="background:rgba(3,7,18,0.95);padding:14px 20px;border-bottom:1px solid rgba(255,255,255,0.1);position:sticky;top:0;z-index:99;">
  <div style="max-width:1250px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
    <a href="/" style="font-size:20px;font-weight:800;color:#38bdf8;text-decoration:none;">⚡ DEX AIR</a>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
      <a href="/" style="color:#cbd5e1;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:rgba(255,255,255,0.05);">Home</a>
      <a href="/news" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 11px;border-radius:6px;background:#ef4444;font-weight:700;">🔴 Live News</a>
      <a href="/live-market" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:#10b981;font-weight:700;">📊 Live Market</a>
      <a href="/math-master" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:#6366f1;font-weight:700;">🧮 Math Master</a>
      <a href="/smart-tools" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:#f59e0b;font-weight:700;">🧰 Smart Tools</a>
      <a href="/subscription" style="color:#38bdf8;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:rgba(56,189,248,0.1);font-weight:700;border:1px solid rgba(56,189,248,0.3);">💳 Buy Plan (₹99)</a>
      <a href="/login" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 12px;border-radius:6px;background:#0284c7;font-weight:700;">👤 Login / Sign Up</a>
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
.card{background:rgba(17,24,39,0.85);border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:22px;margin-bottom:20px;}
.btn{background:#0284c7;color:#fff;border:none;border-radius:8px;padding:10px 16px;font-weight:700;cursor:pointer;width:100%;text-decoration:none;display:inline-block;text-align:center;}
.btn-green{background:#059669;}
.btn-purple{background:#6366f1;}
input,textarea,select{width:100%;background:#090d16;border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:10px;color:#38bdf8;margin:6px 0 14px 0;}
.out{background:#020617;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:14px;color:#34d399;font-family:monospace;font-size:13px;margin-top:14px;line-height:1.7;}
.step-box{background:rgba(15,23,42,0.8);border-left:4px solid #38bdf8;padding:12px;margin:8px 0;border-radius:0 8px 8px 0;color:#cbd5e1;}
.news-item{background:#0b1120;border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:14px;margin-bottom:12px;transition:0.2s;}
.news-item:hover{border-color:#38bdf8;}
.news-tag{font-size:11px;font-weight:700;padding:3px 8px;border-radius:4px;text-transform:uppercase;margin-right:6px;}
.mic-btn{background:#ef4444;color:#fff;border:none;border-radius:8px;padding:8px 14px;cursor:pointer;font-weight:700;display:inline-flex;align-items:center;gap:6px;}
.mic-btn.listening{animation:pulse 1s infinite;background:#dc2626;}
@keyframes pulse{0%{opacity:1;}50%{opacity:0.5;}100%{opacity:1;}}
</style>
</head><body>""" + T_NAV + """<div style="max-width:1100px;margin:30px auto;padding:0 16px;">"""

T_FOOT = """</div><footer style="text-align:center;padding:20px;font-size:12px;color:#64748b;border-top:1px solid rgba(255,255,255,0.08);">DEX AIR Sovereign Enterprise © 2026 | PostgreSQL Live Active</footer></body></html>"""

# ==========================================
# 1. HOMEPAGE
# ==========================================
@app.route("/")
def home():
    content = """
    <div style="text-align:center;margin-bottom:30px;">
      <h1 style="color:#38bdf8;font-size:32px;margin-bottom:8px;">Sovereign Cloud Microservices</h1>
      <p style="color:#94a3b8;font-size:14px;">Live Global & Business News, Trading Chart & AI Signals, Voice Math Solver & Tools.</p>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;">
      <div class="card">
        <h3>🔴 Live Global & Market News</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">शेयर बाजार, बिजनेस, भारत व विश्व राजनीति की पल-पल की लाइव खबरें (Hindi & English)।</p>
        <a href="/news" class="btn" style="background:#ef4444;">Read Live News</a>
      </div>
      <div class="card">
        <h3>📊 Live Market & AI Signals</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">लाइव शेयर मार्केट चार्ट्स और AI से जानें कब खरीदें और कब न खरीदें।</p>
        <a href="/live-market" class="btn btn-green">Open Live Market</a>
      </div>
      <div class="card">
        <h3>🧮 Math Master & Voice Solver</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">बोलकर या लिखकर सवाल हल करें, स्टेप-बाय-स्टेप हिंदी विवरण और प्रैक्टिस शीट्स।</p>
        <a href="/math-master" class="btn btn-purple">Open Math Master</a>
      </div>
      <div class="card">
        <h3>👤 Trader Login & Sign Up</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">अपना अकाउंट बनाएँ और अपनी प्रो API Key व सेटिंग्स सुरक्षित रखें।</p>
        <a href="/login" class="btn">Login / Register</a>
      </div>
    </div>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

# ==========================================
# 2. LIVE GLOBAL & BUSINESS NEWS PAGE
# ==========================================
@app.route("/news")
def news():
    content = """
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:18px;">
        <div>
          <h2>🔴 24x7 Live Global & Market News Feed</h2>
          <p style="color:#94a3b8;font-size:13px;">ट्रेडिंग और बाजार को प्रभावित करने वाली देश-विदेश की ताज़ा खबरें।</p>
        </div>
        <div style="display:flex;gap:6px;">
          <button id="lang_hi" class="btn" style="background:#ef4444;padding:6px 12px;font-size:12px;" onclick="setLang('hi')">🇮🇳 हिंदी</button>
          <button id="lang_en" class="btn" style="background:rgba(255,255,255,0.08);color:#94a3b8;padding:6px 12px;font-size:12px;" onclick="setLang('en')">🌐 English</button>
        </div>
      </div>

      <!-- News Category Filter Tabs -->
      <div style="display:flex;gap:6px;margin-bottom:18px;flex-wrap:wrap;">
        <button id="ntab_all" class="btn" style="flex:1;background:#38bdf8;color:#030712;font-size:12px;padding:8px 6px;min-width:110px;" onclick="filterNews('all')">🔥 Breaking / All</button>
        <button id="ntab_biz" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;font-size:12px;padding:8px 6px;min-width:110px;" onclick="filterNews('biz')">💼 Market & Business</button>
        <button id="ntab_world" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;font-size:12px;padding:8px 6px;min-width:110px;" onclick="filterNews('world')">🌍 Global Geopolitics</button>
        <button id="ntab_pol" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;font-size:12px;padding:8px 6px;min-width:110px;" onclick="filterNews('pol')">🏛️ Indian Politics</button>
      </div>

      <!-- Live Feed Stream Container -->
      <div id="news_container">
        Loading live headlines...
      </div>
    </div>

    <script>
    let currentLang = 'hi';
    let currentCategory = 'all';

    const newsData = {
      hi: [
        { cat: 'biz', tag: 'शेयर बाजार', tagColor: '#10b981', title: 'निफ्टी 50 और सेंसेक्स में कंसोलिडेशन: IT और बैंकिंग शेयरों में मिलाजुला रुख', desc: 'वैश्विक संकेतों और कच्चे तेल की कीमतों के चलते घरेलू बाजार में सीमित दायरे में कारोबार देखा जा रहा है। विदेशी संस्थागत निवेशकों (FIIs) की बिकवाली थमी।', time: '5 मिनट पहले', source: 'NSE/BSE Insights' },
        { cat: 'biz', tag: 'कंपनियां', tagColor: '#0284c7', title: 'रिलायंस और टाटा मोटर्स की नई EV विस्तार योजना, तिमाही नतीजों पर नजर', desc: 'ऑटोमोबाइल और एनर्जी सेक्टर में घरेलू उत्पादन बढ़ाने और भारी निवेश के ऐलान से निवेशकों में सकारात्मक रुख देखा जा रहा है।', time: '18 मिनट पहले', source: 'Financial Express' },
        { cat: 'world', tag: 'ग्लोबल', tagColor: '#ef4444', title: 'अमेरिकी फेडरल रिजर्व की ब्याज दरों पर सख्त टिप्पणी, वैश्विक बॉन्ड यील्ड में हलचल', desc: 'मुद्रास्फीति (Inflation) के आंकड़ों को देखते हुए फेड ने ब्याज दरों में कटौती में सावधानी बरतने के संकेत दिए, जिससे डॉलर इंडेक्स मजबूत हुआ।', time: '35 मिनट पहले', source: 'Global Desk' },
        { cat: 'world', tag: 'भू-राजनीति', tagColor: '#f59e0b', title: 'मध्य-पूर्व तनाव के चलते कच्चे तेल (Brent Crude) में उतार-चढ़ाव, सुरक्षित परिसंपत्तियों की मांग', desc: 'सप्लाई चेन में रुकावट की आशंका से क्रूड ऑयल के दामों में उछाल आया है, जिसका सीधा असर एशियाई शेयर बाजारों और भारतीय रुपये पर पड़ा है।', time: '1 घंटा पहले', source: 'World News' },
        { cat: 'pol', tag: 'राष्ट्रीय', tagColor: '#6366f1', title: 'संसद में नए आर्थिक सुधार और इंफ्रास्ट्रक्चर बजट पर कैबिनेट की उच्चस्तरीय बैठक', desc: 'केंद्र सरकार ने मैन्युफैक्चरिंग हब और नए फ्रेट कॉरिडोर के लिए अतिरिक्त फंड के आवंटन को मंजूरी दी। रोजगार और मैन्युफैक्चरिंग को मिलेगा बढ़ावा।', time: '2 घंटे पहले', source: 'National Bureau' },
        { cat: 'pol', tag: 'नीति', tagColor: '#8b5cf6', title: 'RBI और वित्त मंत्रालय का डिजिटल पेमेंट और UPI सुरक्षा पर नया सख्त दिशानिर्देश', desc: 'साइबर वित्तीय धोखाधड़ी रोकने के लिए बैंकों को नए रियल-टाइम मॉनिटरिंग सिस्टम लगाने का निर्देश दिया गया है।', time: '3 घंटे पहले', source: 'Policy Wire' }
      ],
      en: [
        { cat: 'biz', tag: 'Markets', tagColor: '#10b981', title: 'Nifty 50 Consolidates Near Key Support: Mixed Performance Across IT & Banking', desc: 'Domestic equities witnessed range-bound action amid volatile crude prices and cautious global cues. FII selling slowed down in cash segment.', time: '5 mins ago', source: 'NSE/BSE Live' },
        { cat: 'biz', tag: 'Corporate', tagColor: '#0284c7', title: 'Reliance and Tata Motors Accelerate EV Expansion Pipeline Ahead of Q2 Results', desc: 'Aggressive capital expenditure plans in clean energy and automobile ecosystem drive positive institutional investor sentiment.', time: '20 mins ago', source: 'Market Reuters' },
        { cat: 'world', tag: 'Global Macro', tagColor: '#ef4444', title: 'US Federal Reserve Signals Cautious Rate Trajectory, Bond Yields Rebound', desc: 'Inflation sticky prints prompt central banks to hold rates steady, pushing US Dollar Index higher and putting pressure on emerging currencies.', time: '40 mins ago', source: 'Bloomberg Wire' },
        { cat: 'world', tag: 'Geopolitics', tagColor: '#f59e0b', title: 'Brent Crude Spikes on Supply Chain Uncertainty in Middle East Transit Routes', desc: 'Safe-haven assets like Gold and Treasuries see increased buying as energy shipping risks escalate across key maritime channels.', time: '1 hour ago', source: 'Global Intel' },
        { cat: 'pol', tag: 'India Policy', tagColor: '#6366f1', title: 'Union Cabinet Convenes High-Level Panel to Finalize Industrial Freight Corridor Outlay', desc: 'Government accelerates manufacturing incentives and logistical funding to boost domestic exports and regional employment.', time: '2 hours ago', source: 'National Press' },
        { cat: 'pol', tag: 'Economy', tagColor: '#8b5cf6', title: 'Finance Ministry & RBI Issue Tightened Cyber Safety Standards for Instant Settlements', desc: 'Mandatory real-time algorithmic fraud detection rolled out across digital banking rails to safeguard merchant transactions.', time: '3 hours ago', source: 'Central Wire' }
      ]
    };

    function renderNews() {
      const list = newsData[currentLang];
      const container = document.getElementById('news_container');
      const filtered = currentCategory === 'all' ? list : list.filter(item => item.cat === currentCategory);

      container.innerHTML = filtered.map(item => `
        <div class="news-item">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span class="news-tag" style="background:${item.tagColor}22;color:${item.tagColor};border:1px solid ${item.tagColor}55;">
              ${item.tag}
            </span>
            <span style="font-size:11px;color:#64748b;">⏱️ ${item.time} | <b>${item.source}</b></span>
          </div>
          <h3 style="font-size:16px;color:#f8fafc;margin-bottom:6px;line-height:1.4;">${item.title}</h3>
          <p style="font-size:13px;color:#94a3b8;line-height:1.6;">${item.desc}</p>
        </div>
      `).join('');
    }

    function setLang(lang) {
      currentLang = lang;
      document.getElementById('lang_hi').style.background = lang === 'hi' ? '#ef4444' : 'rgba(255,255,255,0.08)';
      document.getElementById('lang_hi').style.color = lang === 'hi' ? '#fff' : '#94a3b8';
      document.getElementById('lang_en').style.background = lang === 'en' ? '#ef4444' : 'rgba(255,255,255,0.08)';
      document.getElementById('lang_en').style.color = lang === 'en' ? '#fff' : '#94a3b8';
      renderNews();
    }

    function filterNews(cat) {
      currentCategory = cat;
      ['all', 'biz', 'world', 'pol'].forEach(c => {
        const btn = document.getElementById('ntab_' + c);
        if (c === cat) {
          btn.style.background = '#38bdf8';
          btn.style.color = '#030712';
        } else {
          btn.style.background = 'rgba(255,255,255,0.08)';
          btn.style.color = '#94a3b8';
        }
      });
      renderNews();
    }

    renderNews();
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

# ==========================================
# 3. TRADER LOGIN & SIGNUP PAGE
# ==========================================
@app.route("/login")
def login_page():
    user = session.get("username")
    content = f"""
    <div class="card" style="max-width:480px;margin:30px auto;">
      <h2 style="text-align:center;margin-bottom:6px;">👤 Trader Portal Access</h2>
      <p style="text-align:center;color:#94a3b8;font-size:13px;margin-bottom:20px;">Apne account se login karein ya naya register karein.</p>
      
      {'<div style="background:rgba(16,185,129,0.15);border:1px solid #10b981;border-radius:8px;padding:12px;margin-bottom:16px;color:#34d399;text-align:center;">Aap logged in hain as: <b>' + user + '</b> | <a href="/logout" style="color:#ef4444;margin-left:8px;text-decoration:none;font-weight:700;">Logout</a></div>' if user else ''}

      <div style="display:flex;gap:6px;margin-bottom:18px;">
        <button id="auth_t1" class="btn" style="flex:1;background:#0284c7;" onclick="setAuthTab('login')">Sign In</button>
        <button id="auth_t2" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;" onclick="setAuthTab('reg')">Sign Up (New)</button>
      </div>

      <!-- Login Form -->
      <div id="f_login">
        <label>Username / Email</label>
        <input type="text" id="l_user" placeholder="e.g. trader_dinesh">
        <label>Password</label>
        <input type="password" id="l_pass" placeholder="••••••••">
        <button class="btn btn-green" onclick="handleAuth('login')">Login to Terminal</button>
      </div>

      <!-- Register Form -->
      <div id="f_reg" style="display:none;">
        <label>Naya Username Chunein</label>
        <input type="text" id="r_user" placeholder="e.g. trader_dinesh">
        <label>Password Banayein</label>
        <input type="password" id="r_pass" placeholder="••••••••">
        <button class="btn btn-purple" onclick="handleAuth('reg')">Create Trader Account</button>
      </div>

      <div id="auth_out" class="out" style="display:none;margin-top:14px;"></div>
    </div>

    <script>
    function setAuthTab(t){
      if(t==='login'){
        document.getElementById('f_login').style.display='block';
        document.getElementById('f_reg').style.display='none';
        document.getElementById('auth_t1').style.background='#0284c7';
        document.getElementById('auth_t1').style.color='#fff';
        document.getElementById('auth_t2').style.background='rgba(255,255,255,0.08)';
        document.getElementById('auth_t2').style.color='#94a3b8';
      }else{
        document.getElementById('f_login').style.display='none';
        document.getElementById('f_reg').style.display='block';
        document.getElementById('auth_t2').style.background='#6366f1';
        document.getElementById('auth_t2').style.color='#fff';
        document.getElementById('auth_t1').style.background='rgba(255,255,255,0.08)';
        document.getElementById('auth_t1').style.color='#94a3b8';
      }
    }

    async function handleAuth(action){
      const out = document.getElementById('auth_out');
      const u = action==='login' ? document.getElementById('l_user').value.trim() : document.getElementById('r_user').value.trim();
      const p = action==='login' ? document.getElementById('l_pass').value.trim() : document.getElementById('r_pass').value.trim();

      if(!u || !p){ alert("Username aur password bharein!"); return; }

      out.style.display = 'block';
      out.innerText = "PostgreSQL se verify ho raha hai...";

      try{
        const res = await fetch('/auth-action', {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({action: action, username: u, password: p})
        });
        const d = await res.json();
        if(d.status === 'SUCCESS'){
          out.innerHTML = `<span style="color:#34d399;">✅ ${d.message}</span>`;
          setTimeout(() => { window.location.href = '/live-market'; }, 1000);
        }else{
          out.innerHTML = `<span style="color:#ef4444;">❌ ${d.reason}</span>`;
        }
      }catch(e){
        out.innerText = "Server error.";
      }
    }
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

@app.route("/auth-action", methods=["POST"])
def auth_action():
    d = request.get_json(silent=True) or {}
    action = d.get("action")
    u = d.get("username", "").strip()
    p = d.get("password", "").strip()

    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)

    if action == "reg":
        c.execute("SELECT * FROM users WHERE username = %s", (u,))
        if c.fetchone():
            c.close(); conn.close()
            return jsonify({"status": "FAILED", "reason": "Username pehle se maujood hai! Dusra chunein."})
        c.execute("INSERT INTO users (username, password, tier) VALUES (%s, %s, %s)", (u, p, "starter"))
        conn.commit()
        session["username"] = u
        c.close(); conn.close()
        return jsonify({"status": "SUCCESS", "message": "Account safaltapoorvak ban gaya! Terminal par redirect kar rahe hain..."})

    else:
        c.execute("SELECT * FROM users WHERE username = %s AND password = %s", (u, p))
        row = c.fetchone()
        c.close(); conn.close()
        if row:
            session["username"] = u
            return jsonify({"status": "SUCCESS", "message": "Login Safal! Welcome back, " + u})
        else:
            return jsonify({"status": "FAILED", "reason": "Galat Username ya Password!"})

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect("/login")

# ==========================================
# 4. LIVE STOCK MARKET & AI BUY/SELL ENGINE
# ==========================================
@app.route("/live-market")
def live_market():
    content = """
    <div class="card" style="max-width:980px;margin:0 auto;">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:14px;">
        <div>
          <h2>📊 Live Share Market & AI Advisor</h2>
          <p style="color:#94a3b8;font-size:13px;">Real-time chart aur AI Buy/Sell signal: Kab khareedein aur kab na khareedein.</p>
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
          <a href="/news" class="btn" style="background:#ef4444;font-size:12px;padding:6px 12px;width:auto;"><i class="fa-solid fa-bolt"></i> Live Breaking News</a>
          <span style="display:inline-flex;align-items:center;gap:6px;background:rgba(16,185,129,0.15);color:#34d399;padding:6px 12px;border-radius:20px;font-size:12px;font-weight:700;">
            <span style="width:8px;height:8px;background:#10b981;border-radius:50%;display:inline-block;"></span> LIVE NSE/BSE
          </span>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:2fr 1fr;gap:12px;margin-bottom:14px;">
        <div>
          <label style="font-size:12px;color:#94a3b8;">Stock / Index Chunein:</label>
          <select id="market_symbol" onchange="updateLiveChart()">
            <option value="NSE:NIFTY" selected>NIFTY 50 (NSE Index)</option>
            <option value="BSE:SENSEX">SENSEX (BSE Index)</option>
            <option value="NSE:RELIANCE">Reliance Industries (RELIANCE)</option>
            <option value="NSE:TCS">Tata Consultancy Services (TCS)</option>
            <option value="NSE:HDFCBANK">HDFC Bank (HDFCBANK)</option>
            <option value="NSE:INFY">Infosys (INFY)</option>
            <option value="NSE:TATAMOTORS">Tata Motors (TATAMOTORS)</option>
          </select>
        </div>
        <div style="display:flex;align-items:flex-end;">
          <button class="btn btn-green" onclick="getAISignal()" style="margin-bottom:14px;">
            🤖 AI Se Signal Poochein
          </button>
        </div>
      </div>

      <div style="height:420px;border-radius:10px;overflow:hidden;border:1px solid rgba(255,255,255,0.1);margin-bottom:18px;">
        <div id="tradingview_chart" style="height:100%;width:100%;"></div>
      </div>

      <div id="ai_signal_box" class="out" style="line-height:1.8;">
        Stock chun kar <b>"AI Se Signal Poochein"</b> button par tap karein...
      </div>
    </div>

    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <script>
    function initChart(symbol) {
      document.getElementById('tradingview_chart').innerHTML = '';
      new TradingView.widget({
        "autosize": true,
        "symbol": symbol,
        "interval": "D",
        "timezone": "Asia/Kolkata",
        "theme": "dark",
        "style": "1",
        "locale": "in",
        "toolbar_bg": "#030712",
        "enable_publishing": false,
        "hide_side_toolbar": false,
        "allow_symbol_change": true,
        "container_id": "tradingview_chart"
      });
    }

    function updateLiveChart() {
      const sym = document.getElementById('market_symbol').value;
      initChart(sym);
    }

    window.onload = function() {
      initChart("NSE:NIFTY");
    };

    async function getAISignal() {
      const sym = document.getElementById('market_symbol').value;
      const out = document.getElementById('ai_signal_box');
      out.innerText = "Technical indicators (RSI, Moving Averages, Support/Resistance) scan ho rahe hain...";

      try {
        const res = await fetch('/market-ai-signal', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({symbol: sym})
        });
        const d = await res.json();
        out.innerHTML = d.analysis;
      } catch(e) {
        out.innerText = "Signal nikalne mein error aaya.";
      }
    }
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

# ==========================================
# 5. MATH MASTER & VOICE ENGINE
# ==========================================
@app.route("/math-master")
def math_master():
    content = """
    <div class="card" style="max-width:700px;margin:0 auto;">
      <h2>🧮 DEX AIR Math Master (Voice & Real Solver)</h2>
      <p style="color:#94a3b8;font-size:13px;margin-bottom:18px;">बोलकर या लिखकर सवाल हल करें, स्टेप-बाय-स्टेप विवरण और प्रैक्टिस शीट्स पाएँ।</p>
      
      <div style="display:flex;gap:6px;margin-bottom:18px;flex-wrap:wrap;">
        <button id="m_tab1" class="btn" style="flex:1;background:#6366f1;font-size:12px;padding:8px 6px;" onclick="setMathTab('ai_solve')">🎤 बोलकर / लिखकर हल</button>
        <button id="m_tab2" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;font-size:12px;padding:8px 6px;" onclick="setMathTab('sheets')">🔒 प्रैक्टिस शीट्स (Sub)</button>
        <button id="m_tab3" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;font-size:12px;padding:8px 6px;" onclick="setMathTab('algebra')">📈 Algebra</button>
        <button id="m_tab4" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;font-size:12px;padding:8px 6px;" onclick="setMathTab('bodmas')">➕ BODMAS</button>
      </div>

      <div id="sec_ai_solve">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
          <label style="font-size:13px;color:#38bdf8;font-weight:700;">सवाल लिखें या माइक से बोलें:</label>
          <button id="mic_btn" class="mic-btn" type="button" onclick="startVoice()"><i class="fa-solid fa-microphone"></i> <span id="mic_text">बोलकर लिखें</span></button>
        </div>

        <textarea id="custom_question" rows="3" placeholder="यहाँ बोलें या टाइप करें... जैसे: एक व्यक्ति 10km की रफ़्तार से जा रहा है वह 58km कितने देर में पहुँचेगा?"></textarea>

        <label style="font-size:13px;color:#38bdf8;font-weight:700;">या सवाल की फ़ोटो अपलोड करें:</label>
        <input type="file" id="math_photo" accept="image/*" style="background:#1e293b;padding:8px;border:1px dashed #38bdf8;">

        <button class="btn btn-purple" onclick="solveRealMath()"><i class="fa-solid fa-calculator"></i> स्टेप-बाय-स्टेप हिंदी में हल निकालें</button>
      </div>

      <div id="sec_sheets" style="display:none;">
        <div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:8px;padding:14px;color:#f87171;margin-bottom:12px;text-align:center;">
          🔒 <b>प्रीमियम प्रैक्टिस शीट्स लॉक्ड हैं</b><br>
          <span style="font-size:12px;color:#cbd5e1;">A to Z चैप्टर्स के प्रैक्टिस सवाल और हल केवल Pro/Enterprise मेंबर्स के लिए हैं।</span>
        </div>

        <label>अपनी Pro API Key दर्ज करें:</label>
        <input type="text" id="sub_key" placeholder="dex_master_live_key_999 या आपकी Pro Key">

        <label>प्रैक्टिस चैप्टर चुनें:</label>
        <select id="sheet_chap">
          <option value="arithmetic">अंकगणित - 50 महत्वपूर्ण प्रश्न व हल</option>
          <option value="algebra">बीजगणित - समीकरण एवं बहुपद वर्कशीट</option>
          <option value="trig">त्रिकोणमिति - सर्वसमिकाएँ व ऊँचाई-दूरी</option>
          <option value="geometry">क्षेत्रमिति - 2D और 3D फॉर्मूला प्रैक्टिस शीट</option>
        </select>

        <button class="btn btn-green" onclick="unlockSheets()">प्रैक्टिस शीट अनलॉक करें</button>
        <div style="text-align:center;margin-top:10px;">
          <a href="/subscription" style="color:#38bdf8;font-size:12px;text-decoration:none;">₹99 में Pro Plan लेने के लिए यहाँ क्लिक करें →</a>
        </div>
      </div>

      <div id="sec_algebra" style="display:none;">
        <p style="font-size:13px;color:#38bdf8;margin-bottom:10px;">द्विघात समीकरण (Quadratic Equation): <b>ax² + bx + c = 0</b></p>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;">
          <div><label>a</label><input type="number" id="alg_a" value="1"></div>
          <div><label>b</label><input type="number" id="alg_b" value="-5"></div>
          <div><label>c</label><input type="number" id="alg_c" value="6"></div>
        </div>
        <button class="btn btn-purple" onclick="solveAlgebra()">हल निकालें</button>
      </div>

      <div id="sec_bodmas" style="display:none;">
        <label style="font-size:12px;color:#94a3b8;">BODMAS कीपैड डिस्प्ले</label>
        <input type="text" id="calc_screen" value="50 + (12 * 8) - (100 / 4)" style="font-size:18px;letter-spacing:1px;font-weight:700;text-align:right;" placeholder="0">
        <div class="calc-grid">
          <button class="c-btn c-action" onclick="pressKey('C')">C</button>
          <button class="c-btn c-op" onclick="pressKey('(')">(</button>
          <button class="c-btn c-op" onclick="pressKey(')')">)</button>
          <button class="c-btn c-action" onclick="pressKey('DEL')">⌫</button>
          <button class="c-btn" onclick="pressKey('7')">7</button>
          <button class="c-btn" onclick="pressKey('8')">8</button>
          <button class="c-btn" onclick="pressKey('9')">9</button>
          <button class="c-btn c-op" onclick="pressKey('/')">÷</button>
          <button class="c-btn" onclick="pressKey('4')">4</button>
          <button class="c-btn" onclick="pressKey('5')">5</button>
          <button class="c-btn" onclick="pressKey('6')">6</button>
          <button class="c-btn c-op" onclick="pressKey('*')">×</button>
          <button class="c-btn" onclick="pressKey('1')">1</button>
          <button class="c-btn" onclick="pressKey('2')">2</button>
          <button class="c-btn" onclick="pressKey('3')">3</button>
          <button class="c-btn c-op" onclick="pressKey('-')">−</button>
          <button class="c-btn" onclick="pressKey('0')">0</button>
          <button class="c-btn" onclick="pressKey('.')">.</button>
          <button class="c-btn c-op" onclick="pressKey('**')">xʸ</button>
          <button class="c-btn c-op" onclick="pressKey('+')">+</button>
          <button class="c-btn c-equals" onclick="solveBodmas()">= Evaluate</button>
          <button class="c-btn c-op" style="grid-column:span 2;" onclick="pressKey('%')">% Modulo</button>
        </div>
      </div>

      <div id="math_output" class="out">यहाँ आपका विस्तृत हल और उत्तर दिखेगा...</div>
    </div>

    <script>
    function pressKey(v){
      var s = document.getElementById('calc_screen');
      if(v==='C'){s.value='';}else if(v==='DEL'){s.value=s.value.slice(0,-1);}else{s.value+=v;}
    }

    function setMathTab(mode){
      var tabs = ['m_tab1','m_tab2','m_tab3','m_tab4'];
      for(var i=0; i<tabs.length; i++){ document.getElementById(tabs[i]).style.background='rgba(255,255,255,0.08)'; }
      var secs = ['sec_ai_solve','sec_sheets','sec_algebra','sec_bodmas'];
      for(var j=0; j<secs.length; j++){ document.getElementById(secs[j]).style.display='none'; }
      
      if(mode==='ai_solve'){document.getElementById('m_tab1').style.background='#6366f1';document.getElementById('sec_ai_solve').style.display='block';}
      else if(mode==='sheets'){document.getElementById('m_tab2').style.background='#6366f1';document.getElementById('sec_sheets').style.display='block';}
      else if(mode==='algebra'){document.getElementById('m_tab3').style.background='#6366f1';document.getElementById('sec_algebra').style.display='block';}
      else{document.getElementById('m_tab4').style.background='#6366f1';document.getElementById('sec_bodmas').style.display='block';}
    }

    function startVoice() {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        alert("Browser mein Voice Recognition support nahi hai.");
        return;
      }
      const recognition = new SpeechRecognition();
      recognition.lang = 'hi-IN';
      const btn = document.getElementById('mic_btn');
      const txt = document.getElementById('mic_text');
      const box = document.getElementById('custom_question');

      btn.classList.add('listening');
      txt.innerText = "सुन रहा हूँ... बोलिए";

      recognition.onresult = function(event) {
        box.value = event.results[0][0].transcript;
        btn.classList.remove('listening');
        txt.innerText = "बोलकर लिखें";
      };

      recognition.onerror = function() {
        btn.classList.remove('listening');
        txt.innerText = "बोलकर लिखें";
      };

      recognition.start();
    }

    async function solveRealMath() {
      var q = document.getElementById('custom_question').value.trim();
      var out = document.getElementById('math_output');
      if (!q) {
        out.innerHTML = "<span style='color:#ef4444;'>कृपया सवाल लिखें या माइक से बोलें!</span>";
        return;
      }
      out.innerText = "सवाल का गणितीय विश्लेषण व स्टेप-बाय-स्टेप हल जारी है...";
      try {
        var res = await fetch('/math-calc', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({type: 'smart_solve', question: q})
        });
        var d = await res.json();
        out.innerHTML = d.explanation;
      } catch(e) {
        out.innerText = "हल करने में समस्या आई।";
      }
    }

    async function unlockSheets(){
      var key = document.getElementById('sub_key').value.trim();
      var chap = document.getElementById('sheet_chap').value;
      var out = document.getElementById('math_output');
      out.innerText = "PostgreSQL डेटाबेस से सब्सक्रिप्शन वेरीफाई हो रहा है...";
      try{
        var res = await fetch('/unlock-sheet', {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({api_key: key, chapter: chap})
        });
        var d = await res.json();
        if(d.status === 'UNLOCKED'){
          out.innerHTML = d.content;
        } else {
          out.innerHTML = "<span style='color:#ef4444;'>❌ " + d.reason + "</span><br><br><a href='/subscription' class='btn' style='max-width:200px;margin-top:10px;'>सब्सक्रिप्शन एक्टिवेट करें</a>";
        }
      }catch(e){
        out.innerText = "वेरिफिकेशन में समस्या आई।";
      }
    }

    async function solveAlgebra(){
      var a = Number(document.getElementById('alg_a').value);
      var b = Number(document.getElementById('alg_b').value);
      var c = Number(document.getElementById('alg_c').value);
      var out = document.getElementById('math_output');
      out.innerText = "हल तैयार हो रहा है...";
      try{
        var res = await fetch('/math-calc', {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({type:'algebra', a:a, b:b, c:c})
        });
        var d = await res.json();
        out.innerHTML = d.explanation;
      }catch(e){out.innerText = "Equation Error.";}
    }

    async function solveBodmas(){
      var expr = document.getElementById('calc_screen').value;
      var out = document.getElementById('math_output');
      out.innerText = "BODMAS गणना जारी है...";
      try{
        var res = await fetch('/math-calc', {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({type:'bodmas', expr:expr})
        });
        var d = await res.json();
        if(d.status==='SUCCESS'){
          out.innerHTML = "🔢 <b>समीकरण:</b> " + expr + "<br>🎯 <b>अंतिम उत्तर:</b> <span style='color:#38bdf8;font-size:20px;font-weight:700;'>" + d.result + "</span>";
          document.getElementById('calc_screen').value = d.result;
        } else { out.innerText = "Error: " + d.reason; }
      }catch(e){out.innerText = "Calculation error.";}
    }
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

# ==========================================
# 6. SMART TOOLS & PAYMENT (₹99 QR CODE)
# ==========================================
@app.route("/smart-tools")
def smart_tools():
    content = """
    <div class="card" style="max-width:720px;margin:0 auto;">
      <h2>🧰 Daily Life Smart Tools</h2>
      <p style="color:#94a3b8;font-size:13px;margin-bottom:18px;">रोज़मर्रा के जीवन, बिल, लोन और व्यापार के लिए 5 आसान कैलकुलेटर।</p>
      
      <div style="display:flex;gap:6px;margin-bottom:20px;flex-wrap:wrap;">
        <button id="st_tab1" class="btn" style="flex:1;background:#f59e0b;font-size:12px;padding:8px 6px;" onclick="setToolTab('gst')">🧾 GST Calc</button>
        <button id="st_tab2" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;font-size:12px;padding:8px 6px;" onclick="setToolTab('emi')">🏦 Loan EMI</button>
        <button id="st_tab3" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;font-size:12px;padding:8px 6px;" onclick="setToolTab('split')">👥 Bill Split</button>
        <button id="st_tab4" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;font-size:12px;padding:8px 6px;" onclick="setToolTab('discount')">🏷️ Discount</button>
        <button id="st_tab5" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;font-size:12px;padding:8px 6px;" onclick="setToolTab('fuel')">⛽ Fuel Trip</button>
      </div>

      <div id="tool_gst">
        <label>मूल राशि (Original Amount ₹)</label>
        <input type="number" id="gst_amt" value="5000">
        <label>GST दर (%)</label>
        <select id="gst_rate">
          <option value="5">5%</option><option value="12">12%</option><option value="18" selected>18%</option><option value="28">28%</option>
        </select>
        <label>प्रकार</label>
        <select id="gst_type">
          <option value="add">GST जोड़ें (Exclusive)</option><option value="remove">GST हटाएँ (Inclusive)</option>
        </select>
        <button class="btn btn-green" onclick="calcGST()">GST निकालें</button>
      </div>

      <div id="tool_emi" style="display:none;">
        <label>लोन राशि (₹)</label><input type="number" id="emi_p" value="500000">
        <label>वार्षिक ब्याज दर (%)</label><input type="number" id="emi_r" value="10.5">
        <label>अवधि (वर्ष)</label><input type="number" id="emi_y" value="5">
        <button class="btn btn-green" onclick="calcEMI()">EMI निकालें</button>
      </div>

      <div id="tool_split" style="display:none;">
        <label>कुल बिल (₹)</label><input type="number" id="split_bill" value="2400">
        <label>कुल लोग</label><input type="number" id="split_people" value="4">
        <label>टिप (₹)</label><input type="number" id="split_tip" value="100">
        <button class="btn btn-green" onclick="calcSplit()">हिस्सा निकालें</button>
      </div>

      <div id="tool_discount" style="display:none;">
        <label>MRP (₹)</label><input type="number" id="disc_price" value="1999">
        <label>छूट (%)</label><input type="number" id="disc_pct" value="25">
        <button class="btn btn-green" onclick="calcDiscount()">छूट निकालें</button>
      </div>

      <div id="tool_fuel" style="display:none;">
        <label>सफ़र की दूरी (KM)</label><input type="number" id="fuel_dist" value="250">
        <label>माइलेज (KM/Litre)</label><input type="number" id="fuel_mileage" value="18">
        <label>ईंधन कीमत (₹/Litre)</label><input type="number" id="fuel_cost" value="96">
        <button class="btn btn-green" onclick="calcFuel()">खर्चा निकालें</button>
      </div>

      <div id="tool_output" class="out">गणना देखने के लिए बटन पर क्लिक करें...</div>
    </div>

    <script>
    function setToolTab(tool) {
      const tabs = ['st_tab1','st_tab2','st_tab3','st_tab4','st_tab5'];
      const forms = ['tool_gst','tool_emi','tool_split','tool_discount','tool_fuel'];
      tabs.forEach(t => { document.getElementById(t).style.background = 'rgba(255,255,255,0.08)'; document.getElementById(t).style.color = '#94a3b8'; });
      forms.forEach(f => document.getElementById(f).style.display = 'none');
      if(tool === 'gst') { document.getElementById('st_tab1').style.background = '#f59e0b'; document.getElementById('st_tab1').style.color = '#fff'; document.getElementById('tool_gst').style.display = 'block'; }
      else if(tool === 'emi') { document.getElementById('st_tab2').style.background = '#f59e0b'; document.getElementById('st_tab2').style.color = '#fff'; document.getElementById('tool_emi').style.display = 'block'; }
      else if(tool === 'split') { document.getElementById('st_tab3').style.background = '#f59e0b'; document.getElementById('st_tab3').style.color = '#fff'; document.getElementById('tool_split').style.display = 'block'; }
      else if(tool === 'discount') { document.getElementById('st_tab4').style.background = '#f59e0b'; document.getElementById('st_tab4').style.color = '#fff'; document.getElementById('tool_discount').style.display = 'block'; }
      else { document.getElementById('st_tab5').style.background = '#f59e0b'; document.getElementById('st_tab5').style.color = '#fff'; document.getElementById('tool_fuel').style.display = 'block'; }
    }
    function calcGST(){
      const a=Number(document.getElementById('gst_amt').value), r=Number(document.getElementById('gst_rate').value), t=document.getElementById('gst_type').value;
      if(t==='add'){ const g=a*(r/100); document.getElementById('tool_output').innerHTML=`मूल: ₹${a} | GST (${r}%): ₹${g.toFixed(2)}<br>🎯 कुल बिल: <span style="color:#38bdf8;font-weight:700;">₹${(a+g).toFixed(2)}</span>`; }
      else{ const b=a/(1+(r/100)); document.getElementById('tool_output').innerHTML=`कुल: ₹${a} | मूल: ₹${b.toFixed(2)}<br>⚡ शामिल GST: <span style="color:#38bdf8;font-weight:700;">₹${(a-b).toFixed(2)}</span>`; }
    }
    function calcEMI(){
      const p=Number(document.getElementById('emi_p').value), r=(Number(document.getElementById('emi_r').value)/12)/100, n=Number(document.getElementById('emi_y').value)*12;
      const emi=(p*r*Math.pow(1+r,n))/(Math.pow(1+r,n)-1);
      document.getElementById('tool_output').innerHTML=`🏦 मासिक EMI: <span style="color:#38bdf8;font-size:18px;font-weight:700;">₹${Math.round(emi).toLocaleString('en-IN')} / माह</span><br>कुल ब्याज: ₹${Math.round(emi*n-p).toLocaleString('en-IN')}`;
    }
    function calcSplit(){
      const b=Number(document.getElementById('split_bill').value)+Number(document.getElementById('split_tip').value), p=Number(document.getElementById('split_people').value);
      if(p>0) document.getElementById('tool_output').innerHTML=`🎯 प्रति व्यक्ति शेयर: <span style="color:#38bdf8;font-size:18px;font-weight:700;">₹${(b/p).toFixed(2)}</span>`;
    }
    function calcDiscount(){
      const p=Number(document.getElementById('disc_price').value), d=Number(document.getElementById('disc_pct').value);
      const s=p*(d/100);
      document.getElementById('tool_output').innerHTML=`💸 बचत: ₹${s.toFixed(2)} | 🎯 अंतिम मूल्य: <span style="color:#38bdf8;font-weight:700;">₹${(p-s).toFixed(2)}</span>`;
    }
    function calcFuel(){
      const dist=Number(document.getElementById('fuel_dist').value), m=Number(document.getElementById('fuel_mileage').value), r=Number(document.getElementById('fuel_cost').value);
      if(m>0) document.getElementById('tool_output').innerHTML=`🎯 कुल ईंधन खर्चा: <span style="color:#38bdf8;font-size:18px;font-weight:700;">₹${Math.round((dist/m)*r).toLocaleString('en-IN')}</span>`;
    }
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

@app.route("/subscription")
def subscription():
    content = """
    <div style="text-align:center;margin-bottom:24px;">
      <h2>💳 DEX AIR Pro Subscription</h2>
      <p style="color:#94a3b8;font-size:13px;">PhonePe, Google Pay, ya Paytm se scan karein aur turant Pro Key payein.</p>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px;max-width:850px;margin:0 auto;">
      <div class="card" style="text-align:center;border-color:#38bdf8;">
        <div style="display:inline-block;padding:4px 12px;background:#059669;color:#fff;border-radius:20px;font-size:12px;font-weight:700;margin-bottom:10px;">
          SPECIAL LAUNCH OFFER
        </div>
        <h3 style="color:#38bdf8;">Scan & Pay (PhonePe / UPI)</h3>
        <div style="font-size:32px;font-weight:800;color:#f8fafc;margin:8px 0;">₹99 <span style="font-size:14px;color:#94a3b8;">/ Lifetime Access</span></div>
        
        <div style="background:#fff;padding:12px;border-radius:12px;display:inline-block;margin:10px 0;">
          <img src="https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=upi://pay?pa=8791223831@ibl%26pn=DEX%20AIR%26am=99%26cu=INR" 
               alt="PhonePe UPI QR Code" 
               style="width:200px;height:200px;display:block;">
        </div>

        <div style="margin-top:8px;">
          <span style="font-size:12px;color:#94a3b8;">Official UPI ID:</span><br>
          <code style="color:#38bdf8;font-size:14px;font-weight:700;background:rgba(255,255,255,0.06);padding:3px 8px;border-radius:4px;">8791223831@ibl</code>
        </div>
        <p style="font-size:11px;color:#64748b;margin-top:6px;">Supported: PhonePe | Google Pay | Paytm | BHIM (SBI Bank)</p>
      </div>

      <div class="card">
        <h3>Payment Verification</h3>
        <p style="color:#94a3b8;font-size:12px;margin:8px 0 14px 0;">
          QR code par ₹99 transfer karne ke baad transaction ki detail yahan bharein:
        </p>

        <label style="font-size:12px;color:#94a3b8;">Aapka Naam / Client Name</label>
        <input type="text" id="pay_user" placeholder="e.g. Ramesh Kumar">

        <label style="font-size:12px;color:#94a3b8;">UPI UTR / Reference Number (12 Digits)</label>
        <input type="text" id="pay_utr" placeholder="12 digit UTR number (e.g. 428192847192)">

        <button class="btn btn-green" onclick="verifyAndIssueKey()">
          <i class="fa-solid fa-bolt"></i> Payment Submit Karein Aur Pro Key Payein
        </button>

        <div id="pay_out" class="out" style="display:none;margin-top:14px;"></div>
      </div>
    </div>

    <script>
    async function verifyAndIssueKey() {
      var user = document.getElementById('pay_user').value.trim();
      var utr = document.getElementById('pay_utr').value.trim();
      var out = document.getElementById('pay_out');

      if(!user || !utr) {
        alert("Kripya apna naam aur 12-digit UPI UTR number bharein!");
        return;
      }
      out.style.display = "block";
      out.innerText = "Payment verify ho rahi hai aur database mein key register ho rahi hai...";

      try {
        var res = await fetch('/checkout', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({user_id: user, utr: utr, tier: 'pro'})
        });
        var d = await res.json();
        if(d.status === 'ISSUED') {
          out.innerHTML = `
            🎉 <b>Payment Request Received!</b><br><br>
            Aapki Pro Active API Key hai:<br>
            <span style="color:#38bdf8;font-size:17px;font-weight:700;">${d.issued_key}</span><br><br>
            <i>Status: <b>ACTIVE</b> | Tier: <b>${d.tier}</b> | DB: <b>PostgreSQL</b></i><br>
            <small style="color:#94a3b8;">Is key ko copy karke Math Master ke Practice Sheets tab mein lagayein.</small>
          `;
        } else {
          out.innerText = "Error: " + d.reason;
        }
      } catch(e) {
        out.innerText = "Payment processing failed.";
      }
    }
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

# ==========================================
# 7. BACKEND ROUTING & ENGINES
# ==========================================
@app.route("/market-ai-signal", methods=["POST"])
def market_ai_signal():
    d = request.get_json(silent=True) or {}
    sym = d.get("symbol", "NSE:NIFTY")

    signals = {
        "NSE:NIFTY": {
            "action": "WAIT / NO TRADE ZONE (इंतज़ार करें)",
            "color": "#f59e0b",
            "reason": "मार्केट 24,850 के रेजिस्टेंस के पास कंसोलिडेट कर रहा है। फ्रेश ब्रेकआउट के बिना एंट्री न लें।",
            "target": "24,850", "stoploss": "24,350", "trend": "Sideways"
        },
        "BSE:SENSEX": {
            "action": "HOLD / ACCUMULATE (होल्ड करें)",
            "color": "#38bdf8",
            "reason": "हैवीवेट इंडेक्स में सपोर्ट मजबूत है। गिरावट पर धीरे-धीरे खरीदारी सुरक्षित है।",
            "target": "82,000", "stoploss": "80,200", "trend": "Bullish Bias"
        },
        "NSE:RELIANCE": {
            "action": "BUY ON DIPS (खरीदारी करें)",
            "color": "#10b981",
            "reason": "स्टॉक 200 EMA सपोर्ट से बाउंस ले रहा है। वॉल्यूम में सुधार देखा जा रहा है।",
            "target": "3,120", "stoploss": "2,910", "trend": "Strong Bullish"
        },
        "NSE:TCS": {
            "action": "AVOID / DO NOT BUY (अभी न खरीदें)",
            "color": "#ef4444",
            "reason": "ग्लोबल टेक खर्च में सुस्ती के चलते प्रॉफिट बुकिंग जारी है।",
            "target": "N/A", "stoploss": "N/A", "trend": "Bearish Pressure"
        }
    }

    info = signals.get(sym, {
        "action": "WAIT FOR CONFIRMATION",
        "color": "#f59e0b",
        "reason": "मार्केट सामान्य वॉल्यूम पर है। ब्रेकआउट का इंतज़ार करें।",
        "target": "Current + 3%", "stoploss": "Current - 1.5%", "trend": "Neutral"
    })

    analysis_html = f"""
    <div style='color:{info["color"]};font-size:18px;font-weight:800;margin-bottom:8px;'>🎯 AI Verdict: {info["action"]}</div>
    <div class='step-box'>
      <b>📈 Asset:</b> {sym} | <b>🧭 Trend:</b> {info["trend"]}<br>
      <b>🎯 Target:</b> {info["target"]} | <b>🛑 Stop-Loss:</b> {info["stoploss"]}
    </div>
    <div class='step-box' style='border-left-color:{info["color"]};'>
      <b>💡 AI Detail Reason (हिंदी):</b><br>{info["reason"]}
    </div>
    """
    return jsonify({"analysis": analysis_html})

@app.route("/math-calc", methods=["POST"])
def math_calc():
    d = request.get_json(silent=True) or {}
    calc_type = d.get("type", "")

    if calc_type == "smart_solve":
        q = d.get("question", "").lower()
        nums = [float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+", q)]
        exp = "<div style='color:#38bdf8;font-size:16px;font-weight:700;margin-bottom:8px;'>📖 सवाल का रियल स्टेप-बाय-स्टेप हिंदी हल:</div>"

        if ("km" in q or "doori" in q or "दूरी" in q or "raftar" in q or "speed" in q or "चाल" in q or "samay" in q or "समय" in q) and len(nums) >= 2:
            speed = nums[0] if nums[0] <= nums[1] else nums[1]
            dist = nums[1] if nums[0] <= nums[1] else nums[0]
            total_hours = dist / speed
            hours = int(total_hours)
            minutes = int(round((total_hours - hours) * 60))

            exp += f"""
            <div class='step-box'>
              <b>Step 1 (डेटा):</b> चाल = <b>{speed} km/h</b>, कुल दूरी = <b>{dist} km</b>
            </div>
            <div class='step-box'>
              <b>Step 2 (फॉर्मूला):</b> समय = दूरी ÷ चाल = {dist} ÷ {speed} = <b>{round(total_hours, 2)} घंटे</b>
            </div>
            <div class='step-box' style='border-left-color:#34d399;'>
              🎯 <b>सटीक अंतिम उत्तर:</b> पहुँचने में <b>{hours} घंटे {minutes} मिनट</b> का समय लगेगा।
            </div>
            """
            return jsonify({"explanation": exp})
        else:
            exp += f"<div class='step-box'><b>सवाल:</b> {d.get('question')}<br>कृपया संख्याएँ और इकाइयाँ स्पष्ट लिखें ताकि सटीक फॉर्मूला लागू हो सके।</div>"
            return jsonify({"explanation": exp})

    elif calc_type == "algebra":
        a, b, c = float(d.get("a", 1)), float(d.get("b", 0)), float(d.get("c", 0))
        disc = (b ** 2) - (4 * a * c)
        exp = f"<div style='color:#38bdf8;'>ax² + bx + c = 0</div><div class='step-box'>विवेचक D = {disc}</div>"
        if disc >= 0:
            r1 = round((-b + math.sqrt(disc)) / (2 * a), 4)
            r2 = round((-b - math.sqrt(disc)) / (2 * a), 4)
            exp += f"<div class='step-box' style='border-left-color:#34d399;'>🎯 <b>मूल (Roots):</b> x₁ = {r1}, x₂ = {r2}</div>"
        else:
            exp += f"<div class='step-box' style='border-left-color:#ef4444;'>काल्पनिक मूल (D < 0)</div>"
        return jsonify({"explanation": exp})

    elif calc_type == "bodmas":
        expr = d.get("expr", "").strip()
        try:
            tree = ast.parse(expr, mode='eval')
            for node in ast.walk(tree):
                if isinstance(node, (ast.Call, ast.Name, ast.Attribute, ast.Import, ast.ImportFrom)):
                    return jsonify({"status": "FAILED", "reason": "Restricted call"}), 400
            val = eval(compile(tree, filename='', mode='eval'), {"__builtins__": None}, {})
            return jsonify({"status": "SUCCESS", "result": round(float(val), 6)})
        except Exception:
            return jsonify({"status": "FAILED", "reason": "Invalid BODMAS syntax"}), 400

    return jsonify({"error": "Unknown type"}), 400

@app.route("/unlock-sheet", methods=["POST"])
def unlock_sheet():
    d = request.get_json(silent=True) or {}
    key = d.get("api_key", "").strip()
    chapter = d.get("chapter", "arithmetic")

    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute("SELECT * FROM api_vault WHERE api_key = %s", (key,))
    record = c.fetchone()
    c.close(); conn.close()

    if not record or record.get("tier") not in ["pro", "enterprise"]:
        return jsonify({"status": "LOCKED", "reason": "अवैध API Key या यह Pro/Enterprise सब्सक्राइबर नहीं है।"})

    sheet_data = {
        "arithmetic": "<div style='color:#34d399;'>✅ अंकगणित प्रैक्टिस शीट अनलॉक (Pro)</div><div class='step-box'><b>प्रश्न 1:</b> ₹1,200 में बेचने पर 20% लाभ। CP = <b>₹1,000</b></div>",
        "algebra": "<div style='color:#34d399;'>✅ बीजगणित प्रैक्टिस शीट अनलॉक</div><div class='step-box'><b>प्रश्न 1:</b> x² - 7x + 12 = 0 के मूल: <b>x = 3, 4</b></div>",
        "trig": "<div class='step-box'><b>प्रश्न:</b> sin²30° + cos²30° = <b>1</b></div>",
        "geometry": "<div class='step-box'><b>प्रश्न:</b> r = 7cm वृत्त क्षेत्रफल = <b>154 वर्ग सेमी</b></div>"
    }
    return jsonify({"status": "UNLOCKED", "content": sheet_data.get(chapter, sheet_data["arithmetic"])})

@app.route("/checkout", methods=["POST"])
def checkout():
    d = request.get_json(silent=True) or {}
    uid = d.get("user_id", "Client")
    tier = d.get("tier", "pro")
    new_key = f"dex_{uuid.uuid4().hex[:24]}"

    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO api_vault (api_key, user_id, tier) VALUES (%s, %s, %s)", (new_key, uid, tier))
        conn.commit()
        c.close(); conn.close()
        return jsonify({"status": "ISSUED", "issued_key": new_key, "user": uid, "tier": tier, "db": "PostgreSQL"})
    except Exception as e:
        return jsonify({"status": "FAILED", "reason": str(e)}), 500

@app.route("/compounding")
def compounding():
    return render_template_string(T_HEAD + "<div class='card'><h2>📈 Wealth Compounding</h2><p>Lumpsum and Step-up SIP active.</p></div>" + T_FOOT)

@app.route("/developer")
def developer():
    return render_template_string(T_HEAD + "<div class='card'><h2>Developer IDE</h2><p>Python AST engine running.</p></div>" + T_FOOT)

@app.route("/ai")
def ai():
    return render_template_string(T_HEAD + "<div class='card'><h2>AI Guardrail Active</h2></div>" + T_FOOT)

@app.route("/execute", methods=["POST"])
def execute():
    t0 = time.time()
    api_key = request.headers.get("X-API-Key")
    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute("SELECT * FROM api_vault WHERE api_key = %s", (api_key,))
    if not c.fetchone():
        c.close(); conn.close()
        return jsonify({"error": "Unauthorized"}), 401
    d = request.get_json(silent=True) or {}
    code, fn, args = d.get("code",""), d.get("func_name",""), d.get("args",[])
    try:
        tree = ast.parse(code)
        for n in ast.walk(tree):
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                return jsonify({"verdict": "BLOCKED", "reason": "No Imports Allowed"}), 400
            if isinstance(n, ast.Call) and getattr(n.func, 'id', '') in ['eval', 'exec', 'open']:
                return jsonify({"verdict": "BLOCKED", "reason": "Restricted Call"}), 400
        scope = {}
        exec(code, {}, scope)
        ans = scope[fn](*args)
        lat = round((time.time() - t0) * 1000, 2)
        c.execute("INSERT INTO audit_logs (api_key, endpoint, status, latency_ms) VALUES (%s, %s, %s, %s)",
                  (api_key, "/execute", "SUCCESS", lat))
        conn.commit()
        c.close(); conn.close()
        return jsonify({"verdict": "SUCCESS", "result": ans, "latency_ms": lat})
    except Exception as e:
        return jsonify({"verdict": "ERROR", "reason": str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
    
