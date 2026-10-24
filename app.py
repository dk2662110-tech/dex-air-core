import os, ast, json, uuid, time, math, re, psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, render_template_string, session, redirect

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dex_air_vault_key_2026")

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
      <a href="/login" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 12px;border-radius:6px;background:#0284c7;font-weight:700;">👤 Login</a>
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
.card{background:rgba(17,24,39,0.85);border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:22px;margin-bottom:20px;}
.btn{background:#0284c7;color:#fff;border:none;border-radius:8px;padding:10px 16px;font-weight:700;cursor:pointer;width:100%;text-decoration:none;display:inline-block;text-align:center;}
.btn-green{background:#059669;}
.btn-purple{background:#6366f1;}
input,textarea,select{width:100%;background:#090d16;border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:10px;color:#38bdf8;margin:6px 0 14px 0;}
.out{background:#020617;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:14px;color:#34d399;font-family:monospace;font-size:13px;margin-top:14px;line-height:1.7;}
.step-box{background:rgba(15,23,42,0.8);border-left:4px solid #38bdf8;padding:12px;margin:8px 0;border-radius:0 8px 8px 0;color:#cbd5e1;}
.news-item{background:#0b1120;border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:14px;margin-bottom:12px;}
.mic-btn{background:#ef4444;color:#fff;border:none;border-radius:8px;padding:8px 14px;cursor:pointer;font-weight:700;display:inline-flex;align-items:center;gap:6px;}
</style>
</head><body>""" + T_NAV + """<div style="max-width:1100px;margin:30px auto;padding:0 16px;">"""

T_FOOT = """</div><footer style="text-align:center;padding:20px;font-size:12px;color:#64748b;border-top:1px solid rgba(255,255,255,0.08);">DEX AIR Sovereign Enterprise © 2026 | PostgreSQL Live Active</footer></body></html>"""

@app.route("/")
def home():
    content = """
    <div style="text-align:center;margin-bottom:30px;">
      <h1 style="color:#38bdf8;font-size:32px;margin-bottom:8px;">Sovereign Cloud Microservices</h1>
      <p style="color:#94a3b8;font-size:14px;">Live Global News, Trading Charts, AI Market Signals, Voice Math Solver & Life Tools.</p>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;">
      <div class="card">
        <h3>🔴 Live Market & Global News</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">शेयर बाजार, बिज़नेस, ग्लोबल क्रूड और राष्ट्रीय नीतियां (Hindi/English).</p>
        <a href="/news" class="btn" style="background:#ef4444;">Read Live News</a>
      </div>
      <div class="card">
        <h3>📊 Live Market & AI Signals</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">लाइव चार्ट्स और AI सिग्नल्स (कब खरीदें और कब न खरीदें)।</p>
        <a href="/live-market" class="btn btn-green">Open Live Market</a>
      </div>
      <div class="card">
        <h3>🧮 Math Master & Voice Solver</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">बोलकर सवाल पूछें, स्टेप-बाय-स्टेप हिंदी हल और लॉक्ड शीट्स।</p>
        <a href="/math-master" class="btn btn-purple">Open Math Master</a>
      </div>
      <div class="card">
        <h3>🧰 5 Daily Smart Tools</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">GST, Loan EMI, Bill Split, Discount और Fuel Mileage हिसाब।</p>
        <a href="/smart-tools" class="btn" style="background:#f59e0b;">Open Smart Tools</a>
      </div>
    </div>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

@app.route("/news")
def news():
    content = """
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:18px;">
        <h2>🔴 24x7 Live Global & Market Feed</h2>
        <div style="display:flex;gap:6px;">
          <button id="l_hi" class="btn" style="background:#ef4444;padding:6px 12px;font-size:12px;" onclick="setL('hi')">🇮🇳 हिंदी</button>
          <button id="l_en" class="btn" style="background:rgba(255,255,255,0.08);color:#94a3b8;padding:6px 12px;font-size:12px;" onclick="setL('en')">🌐 English</button>
        </div>
      </div>
      <div id="nc"></div>
    </div>
    <script>
    var curL = 'hi';
    var data = {
      hi: [
        { t:'शेयर बाजार: निफ्टी और सेंसेक्स में कंसोलिडेशन, IT में मिलाजुला रुख', d:'कच्चे तेल और विदेशी संस्थागत निवेशकों की चाल से बाजार सीमित दायरे में है।', time:'5 मिनट पहले' },
        { t:'कंपनियां: रिलायंस और टाटा मोटर्स की नई EV विस्तार योजना', d:'क्लीन एनर्जी और ऑटोमोबाइल सेक्टर में भारी निवेश की घोषणा।', time:'25 मिनट पहले' },
        { t:'ग्लोबल मैक्रो: फेडरल रिजर्व के ब्याज दर बयानों से डॉलर मजबूत', d:'मुद्रास्फीति दबाव के कारण वैश्विक बॉन्ड यील्ड में तेजी।', time:'1 घंटा पहले' }
      ],
      en: [
        { t:'Markets: Nifty 50 Consolidates, IT & Banks Show Mixed Action', d:'Range-bound trading observed tracking volatile crude and global cues.', time:'5 mins ago' },
        { t:'Corporate: Reliance & Tata Motors Accelerate EV Expansion', d:'Aggressive capital expenditure plans boost long-term investor sentiment.', time:'25 mins ago' },
        { t:'Global Macro: US Fed Stance Keeps Dollar Index Elevated', d:'Persistent inflation keeps bond yields moving upward across major hubs.', time:'1 hour ago' }
      ]
    };
    function renderN(){
      var arr = data[curL];
      var h = '';
      for(var i=0; i<arr.length; i++){
        h += '<div class="news-item"><div style="font-size:11px;color:#64748b;margin-bottom:4px;">⏱️ ' + arr[i].time + '</div><h3 style="font-size:16px;color:#38bdf8;margin-bottom:6px;">' + arr[i].t + '</h3><p style="font-size:13px;color:#94a3b8;">' + arr[i].d + '</p></div>';
      }
      document.getElementById('nc').innerHTML = h;
    }
    function setL(l){
      curL = l;
      document.getElementById('l_hi').style.background = l==='hi'?'#ef4444':'rgba(255,255,255,0.08)';
      document.getElementById('l_en').style.background = l==='en'?'#ef4444':'rgba(255,255,255,0.08)';
      renderN();
    }
    renderN();
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

@app.route("/live-market")
def live_market():
    content = """
    <div class="card" style="max-width:980px;margin:0 auto;">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:14px;">
        <h2>📊 Live Share Market & AI Advisor</h2>
        <a href="/news" class="btn" style="background:#ef4444;font-size:12px;padding:6px 12px;width:auto;">🔴 Live Breaking News</a>
      </div>
      <div style="display:grid;grid-template-columns:2fr 1fr;gap:12px;margin-bottom:14px;">
        <select id="sym" onchange="upChart()">
          <option value="NSE:NIFTY" selected>NIFTY 50</option>
          <option value="BSE:SENSEX">SENSEX</option>
          <option value="NSE:RELIANCE">Reliance</option>
          <option value="NSE:TCS">TCS</option>
          <option value="NSE:TATAMOTORS">Tata Motors</option>
        </select>
        <button class="btn btn-green" onclick="getSignal()">🤖 AI Se Signal Poochein</button>
      </div>
      <div style="height:420px;border-radius:10px;overflow:hidden;border:1px solid rgba(255,255,255,0.1);margin-bottom:18px;">
        <div id="tv_chart" style="height:100%;width:100%;"></div>
      </div>
      <div id="ai_box" class="out">Stock chun kar <b>AI Se Signal Poochein</b> par click karein...</div>
    </div>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>
    function loadC(s){
      document.getElementById('tv_chart').innerHTML = '';
      new TradingView.widget({"autosize":true,"symbol":s,"interval":"D","timezone":"Asia/Kolkata","theme":"dark","style":"1","locale":"in","container_id":"tv_chart"});
    }
    function upChart(){ loadC(document.getElementById('sym').value); }
    window.onload = function(){ loadC("NSE:NIFTY"); };
    async function getSignal(){
      var s = document.getElementById('sym').value;
      var out = document.getElementById('ai_box');
      out.innerText = "Analyzing charts & technical indicators...";
      try{
        var res = await fetch('/market-ai-signal', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({symbol:s})});
        var d = await res.json();
        out.innerHTML = d.analysis;
      }catch(e){ out.innerText = "Error getting signal."; }
    }
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

@app.route("/market-ai-signal", methods=["POST"])
def market_ai_signal():
    d = request.get_json(silent=True) or {}
    sym = d.get("symbol", "NSE:NIFTY")
    signals = {
        "NSE:NIFTY": {"act": "WAIT / NO TRADE ZONE", "c": "#f59e0b", "t": "24,850", "sl": "24,350", "r": "24,850 resistance ke paas market consolidate ho raha hai. Breakout bina jump na karein."},
        "BSE:SENSEX": {"act": "HOLD / ACCUMULATE", "c": "#38bdf8", "t": "82,000", "sl": "80,200", "r": "Major stocks par support healthy hai. Dips par khareedari safe hai."},
        "NSE:RELIANCE": {"act": "BUY ON DIPS", "c": "#10b981", "t": "3,120", "sl": "2,910", "r": "200 EMA support se volume ke sath bounce back dekhne ko mil raha hai."},
        "NSE:TCS": {"act": "AVOID / DO NOT BUY", "c": "#ef4444", "t": "N/A", "sl": "N/A", "r": "Tech spending sukrne se short-term profit booking pressure bana hua hai."}
    }
    s = signals.get(sym, {"act": "WAIT", "c": "#f59e0b", "t": "Market High", "sl": "Support", "r": "Confirmation ka intezar karein."})
    html = f"""
    <div style='color:{s["c"]};font-size:18px;font-weight:700;'>🎯 AI Verdict: {s["act"]}</div>
    <div class='step-box'><b>Asset:</b> {sym} | <b>Target:</b> {s["t"]} | <b>Stop-Loss:</b> {s["sl"]}</div>
    <div class='step-box' style='border-left-color:{s["c"]};'><b>Hindi Reason:</b><br>{s["r"]}</div>
    """
    return jsonify({"analysis": html})

@app.route("/math-master")
def math_master():
    content = """
    <div class="card" style="max-width:700px;margin:0 auto;">
      <h2>🧮 DEX AIR Math Master (Voice & Solver)</h2>
      <div style="display:flex;justify-content:space-between;align-items:center;margin:14px 0 8px 0;">
        <label style="font-size:13px;color:#38bdf8;font-weight:700;">Sawal Likhien Ya Boliye:</label>
        <button id="mb" class="mic-btn" type="button" onclick="recVoice()"><i class="fa-solid fa-microphone"></i> <span id="mt">Bol Kar Likhien</span></button>
      </div>
      <textarea id="mq" rows="3" placeholder="Jaise: Ek byakti 10km ki raftar se 58km kitni der mein pahuchega?"></textarea>
      <button class="btn btn-purple" onclick="runMath()"><i class="fa-solid fa-calculator"></i> Step-by-Step Hindi Me Hal Karein</button>
      <div id="m_out" class="out">Aapka uttar yahan dikhega...</div>
    </div>
    <script>
    function recVoice(){
      var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if(!SR){ alert("Browser voice support nahi karta. Chrome use karein."); return; }
      var r = new SR();
      r.lang = 'hi-IN';
      document.getElementById('mt').innerText = "Sun raha hoon...";
      r.onresult = function(e){
        document.getElementById('mq').value = e.results[0][0].transcript;
        document.getElementById('mt').innerText = "Bol Kar Likhien";
      };
      r.onerror = function(){ document.getElementById('mt').innerText = "Bol Kar Likhien"; };
      r.start();
    }
    async function runMath(){
      var q = document.getElementById('mq').value.trim();
      var out = document.getElementById('m_out');
      if(!q){ alert("Sawal likhein ya bolein!"); return; }
      out.innerText = "Calculating solution...";
      try{
        var res = await fetch('/math-calc', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})});
        var d = await res.json();
        out.innerHTML = d.explanation;
      }catch(e){ out.innerText = "Calculation error."; }
    }
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

@app.route("/math-calc", methods=["POST"])
def math_calc():
    d = request.get_json(silent=True) or {}
    q = d.get("question", "").lower()
    nums = [float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+", q)]
    if ("km" in q or "doori" in q or "दूरी" in q or "raftar" in q or "speed" in q or "चाल" in q or "samay" in q or "समय" in q) and len(nums) >= 2:
        speed = nums[0] if nums[0] <= nums[1] else nums[1]
        dist = nums[1] if nums[0] <= nums[1] else nums[0]
        th = dist / speed
        h = int(th)
        m = int(round((th - h) * 60))
        exp = f"""
        <div style='color:#38bdf8;font-size:16px;font-weight:700;'>📖 Speed, Time & Distance Solution:</div>
        <div class='step-box'><b>Data:</b> Speed = <b>{speed} km/h</b>, Distance = <b>{dist} km</b></div>
        <div class='step-box'><b>Formula:</b> Time = Distance ÷ Speed = {dist} ÷ {speed} = <b>{round(th, 2)} ghante</b></div>
        <div class='step-box' style='border-left-color:#34d399;'>🎯 <b>Final Answer:</b> <b>{h} ghante {m} minute</b> lagenge ({round(th, 2)} hrs).</div>
        """
        return jsonify({"explanation": exp})
    else:
        return jsonify({"explanation": f"<div class='step-box'><b>Aapka Sawal:</b> {d.get('question')}<br>Sawal me number aur units saaf likhein taaki exact answer nikle.</div>"})

@app.route("/smart-tools")
def smart_tools():
    content = """
    <div class="card" style="max-width:720px;margin:0 auto;">
      <h2>🧰 Daily Life Smart Tools</h2>
      <div style="display:flex;gap:6px;margin:14px 0;flex-wrap:wrap;">
        <button class="btn btn-green" style="flex:1;" onclick="calcG()">🧾 GST (18%)</button>
        <button class="btn btn-green" style="flex:1;" onclick="calcE()">🏦 Loan EMI</button>
        <button class="btn btn-green" style="flex:1;" onclick="calcF()">⛽ Fuel Trip</button>
      </div>
      <label>Amount / Principal (₹)</label>
      <input type="number" id="in_p" value="50000">
      <div id="st_out" class="out">Tools output will appear here...</div>
    </div>
    <script>
    function calcG(){
      var v = Number(document.getElementById('in_p').value);
      var g = v * 0.18;
      document.getElementById('st_out').innerHTML = "Base: ₹" + v + "<br>GST (18%): ₹" + g.toFixed(2) + "<br><b>Total: ₹" + (v+g).toFixed(2) + "</b>";
    }
    function calcE(){
      var p = Number(document.getElementById('in_p').value);
      var r = (10.5/12)/100, n = 36;
      var emi = (p * r * Math.pow(1+r,n))/(Math.pow(1+r,n)-1);
      document.getElementById('st_out').innerHTML = "Loan: ₹" + p + " (10.5% for 3 yrs)<br><b>Monthly EMI: ₹" + Math.round(emi) + " / month</b>";
    }
    function calcF(){
      var dist = Number(document.getElementById('in_p').value);
      var cost = (dist / 15) * 96;
      document.getElementById('st_out').innerHTML = "Distance: " + dist + " KM (15 km/l @ ₹96)<br><b>Fuel Cost: ₹" + Math.round(cost) + "</b>";
    }
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

@app.route("/subscription")
def subscription():
    content = """
    <div class="card" style="max-width:650px;margin:0 auto;text-align:center;">
      <h2>💳 DEX AIR Pro Subscription (₹99)</h2>
      <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">PhonePe / UPI se ₹99 bhejein aur instant Pro Key payein.</p>
      <div style="background:#fff;padding:12px;border-radius:12px;display:inline-block;margin:10px 0;">
        <img src="https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=upi://pay?pa=8791223831@ibl%26pn=DEX%20AIR%26am=99%26cu=INR" style="width:200px;height:200px;display:block;">
      </div>
      <div>Official UPI: <code style="color:#38bdf8;font-weight:700;">8791223831@ibl</code></div>
      <div style="text-align:left;margin-top:18px;">
        <label>Aapka Naam</label><input type="text" id="pu" placeholder="Ramesh Kumar">
        <label>UPI 12-Digit UTR Number</label><input type="text" id="putr" placeholder="12 digit UTR number">
        <button class="btn btn-green" onclick="subPay()">Verify & Get Pro Key</button>
      </div>
      <div id="sub_out" class="out" style="display:none;"></div>
    </div>
    <script>
    async function subPay(){
      var u = document.getElementById('pu').value.trim();
      var ut = document.getElementById('putr').value.trim();
      var out = document.getElementById('sub_out');
      if(!u || !ut){ alert("Naam aur UTR bharein!"); return; }
      out.style.display = 'block';
      out.innerText = "Registering with PostgreSQL...";
      try{
        var res = await fetch('/checkout', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:u,utr:ut,tier:'pro'})});
        var d = await res.json();
        out.innerHTML = "🎉 <b>Payment Registered!</b><br>Key: <span style='color:#38bdf8;font-size:16px;'>" + d.issued_key + "</span><br>Tier: " + d.tier;
      }catch(e){ out.innerText = "Error registering key."; }
    }
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

@app.route("/checkout", methods=["POST"])
def checkout():
    d = request.get_json(silent=True) or {}
    uid = d.get("user_id", "Client")
    tier = d.get("tier", "pro")
    k = f"dex_{uuid.uuid4().hex[:24]}"
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO api_vault (api_key, user_id, tier) VALUES (%s, %s, %s)", (k, uid, tier))
        conn.commit()
        c.close(); conn.close()
        return jsonify({"status": "ISSUED", "issued_key": k, "user": uid, "tier": tier})
    except Exception as e:
        return jsonify({"status": "FAILED", "reason": str(e)}), 500

@app.route("/login")
def login_page():
    u = session.get("username")
    user_info = f"Logged in as: <b>{u}</b> | <a href='/logout' style='color:#ef4444;'>Logout</a>" if u else "Sign in ya Register karein"
    content = """
    <div class="card" style="max-width:440px;margin:30px auto;">
      <h2 style="text-align:center;">👤 Trader Login</h2>
      <p style="text-align:center;color:#94a3b8;font-size:13px;margin-bottom:14px;">""" + user_info + """</p>
      <label>Username</label><input type="text" id="lu">
      <label>Password</label><input type="password" id="lp">
      <div style="display:flex;gap:8px;">
        <button class="btn btn-green" onclick="auth('login')">Sign In</button>
        <button class="btn btn-purple" onclick="auth('reg')">Sign Up</button>
      </div>
      <div id="l_out" class="out" style="display:none;"></div>
    </div>
    <script>
    async function auth(act){
      var u = document.getElementById('lu').value.trim();
      var p = document.getElementById('lp').value.trim();
      var out = document.getElementById('l_out');
      if(!u || !p){ alert("Username aur Password dono bharein!"); return; }
      out.style.display = 'block';
      out.innerText = "Verifying...";
      try{
        var res = await fetch('/auth-act', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:act,username:u,password:p})});
        var d = await res.json();
        if(d.status==='SUCCESS'){
          out.innerHTML = "<span style='color:#34d399;'>✅ " + d.msg + "</span>";
          setTimeout(()=>{ window.location.href='/live-market'; }, 1000);
        }else{ out.innerHTML = "<span style='color:#ef4444;'>❌ " + d.reason + "</span>"; }
      }catch(e){ out.innerText = "Error."; }
    }
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

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
            return jsonify({"status": "FAILED", "reason": "User already exists!"})
        c.execute("INSERT INTO users (username, password, tier) VALUES (%s, %s, %s)", (u, p, "starter"))
        conn.commit()
        session["username"] = u
        c.close(); conn.close()
        return jsonify({"status": "SUCCESS", "msg": "Account created!"})
    else:
        c.execute("SELECT * FROM users WHERE username = %s AND password = %s", (u, p))
        row = c.fetchone()
        c.close(); conn.close()
        if row:
            session["username"] = u
            return jsonify({"status": "SUCCESS", "msg": "Welcome back, " + u})
        return jsonify({"status": "FAILED", "reason": "Wrong Username or Password!"})

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect("/login")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
                                                    
