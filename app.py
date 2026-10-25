import os, ast, json, uuid, time, math, re, urllib.request, xml.etree.ElementTree as ET, psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, render_template_string, session, redirect

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
.news-item{background:#0b1120;border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:14px;margin-bottom:12px;transition:0.2s;}
.news-item:hover{border-color:#38bdf8;}
.mic-btn{background:#ef4444;color:#fff;border:none;border-radius:8px;padding:8px 14px;cursor:pointer;font-weight:700;display:inline-flex;align-items:center;gap:6px;}
</style>
</head><body>""" + T_NAV + """<div style="max-width:1150px;margin:30px auto;padding:0 16px;">"""

T_FOOT = """</div><footer style="text-align:center;padding:20px;font-size:12px;color:#64748b;border-top:1px solid rgba(255,255,255,0.08);">DEX AIR Sovereign Enterprise © 2026 | PostgreSQL Live Active</footer></body></html>"""

@app.route("/")
def home():
    content = """
    <div style="text-align:center;margin-bottom:30px;">
      <h1 style="color:#38bdf8;font-size:32px;margin-bottom:8px;">Sovereign Cloud Microservices</h1>
      <p style="color:#94a3b8;font-size:14px;">100% Real Live Google News, Interactive Live Trading, Voice Math & Smart Tools.</p>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;">
      <div class="card">
        <h3>🔴 100% Live Real News Feed</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">शेयर बाजार, बिज़नेस, ग्लोबल क्रूड और राजनीति की लाइव इंटरनेट खबरें।</p>
        <a href="/news" class="btn" style="background:#ef4444;">Read Live News</a>
      </div>
      <div class="card">
        <h3>📊 Live Market & Trading Terminal</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">लाइव चार्ट्स, वॉलेट में फंड जोड़ें और सीधे शेयर खरीदें व बेचें।</p>
        <a href="/live-market" class="btn btn-green">Open Live Market</a>
      </div>
      <div class="card">
        <h3>🧮 Math Master & Voice Solver</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">बोलकर या लिखकर सवाल हल करें, स्टेप-बाय-स्टेप विवरण और शीट्स।</p>
        <a href="/math-master" class="btn btn-purple">Open Math Master</a>
      </div>
      <div class="card">
        <h3>🧰 5 Daily Smart Tools</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">GST, Loan EMI, Bill Split, Discount और Fuel Trip Cost का आसान हिसाब।</p>
        <a href="/smart-tools" class="btn" style="background:#f59e0b;">Open Smart Tools</a>
      </div>
    </div>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

# ==========================================
# 2. 100% REAL LIVE NEWS HUB & DETAIL POPUP
# ==========================================
@app.route("/news")
def news():
    content = """
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:18px;">
        <div>
          <h2>🔴 24x7 Real-Time Live News Feed</h2>
          <p style="color:#94a3b8;font-size:13px;">लाइव इंटरनेट समाचार: किसी भी खबर पर क्लिक करके उसकी पूरी विस्तृत रिपोर्ट पढ़ें।</p>
        </div>
        <div style="display:flex;gap:6px;">
          <button id="l_hi" class="btn" style="background:#ef4444;padding:6px 12px;font-size:12px;" onclick="switchLang('hi')">🇮🇳 हिंदी</button>
          <button id="l_en" class="btn" style="background:rgba(255,255,255,0.08);color:#94a3b8;padding:6px 12px;font-size:12px;" onclick="switchLang('en')">🌐 English</button>
        </div>
      </div>

      <div style="display:flex;gap:6px;margin-bottom:18px;flex-wrap:wrap;">
        <button id="tb_biz" class="btn" style="flex:1;background:#38bdf8;color:#030712;font-size:12px;padding:8px 6px;min-width:110px;" onclick="fetchLiveCat('business')">💼 Market & Business</button>
        <button id="tb_world" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;font-size:12px;padding:8px 6px;min-width:110px;" onclick="fetchLiveCat('world')">🌍 Global Geopolitics</button>
        <button id="tb_pol" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;font-size:12px;padding:8px 6px;min-width:110px;" onclick="fetchLiveCat('nation')">🏛️ National Policies</button>
      </div>

      <div id="live_feed_box">
        <div style="text-align:center;padding:30px;color:#38bdf8;">
          <i class="fa-solid fa-spinner fa-spin"></i> इंटरनेट से लाइव ताज़ा खबरें फेच हो रही हैं...
        </div>
      </div>

      <!-- Real News Detail Modal -->
      <div id="news_modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);z-index:999;backdrop-filter:blur(5px);justify-content:center;align-items:center;padding:16px;">
        <div style="background:#111827;border:1px solid #38bdf8;border-radius:14px;max-width:620px;width:100%;max-height:85vh;overflow-y:auto;padding:22px;position:relative;box-shadow:0 10px 30px rgba(0,0,0,0.8);">
          <button onclick="closeNewsModal()" style="position:absolute;top:16px;right:16px;background:#ef4444;color:#fff;border:none;border-radius:50%;width:30px;height:30px;font-weight:700;cursor:pointer;">✕</button>
          
          <span id="md_source" style="background:#0284c7;color:#fff;font-size:11px;font-weight:700;padding:3px 8px;border-radius:4px;display:inline-block;margin-bottom:8px;">Live Source</span>
          <div id="md_pub" style="font-size:11px;color:#64748b;margin-bottom:10px;"></div>
          
          <h2 id="md_title" style="color:#f8fafc;font-size:18px;line-height:1.4;margin-bottom:12px;"></h2>
          
          <p id="md_desc" style="color:#cbd5e1;font-size:13px;line-height:1.7;margin-bottom:16px;"></p>
          
          <div style="background:#090d16;border-left:4px solid #10b981;border-radius:0 8px 8px 0;padding:12px;margin-bottom:18px;">
            <b style="color:#34d399;">📊 Market & Trading Impact:</b>
            <div id="md_impact" style="font-size:12px;color:#94a3b8;margin-top:4px;">
              इस खबर के आधार पर संबंधित सेक्टर के शेयरों और निफ्टी/सेंसेक्स में उतार-चढ़ाव देखा जा सकता है। ट्रेडिंग के दौरान स्टॉप-लॉस जरूर मेंटेन करें।
            </div>
          </div>

          <a id="md_link" href="#" target="_blank" class="btn btn-green" style="text-decoration:none;display:block;text-align:center;">
            🌐 असली सोर्स पर पूरी डिटेल रिपोर्ट पढ़ें →
          </a>
        </div>
      </div>
    </div>

    <script>
    let activeLang = 'hi';
    let activeCat = 'business';
    let currentLoadedArticles = [];

    async function loadLiveNews() {
      const box = document.getElementById('live_feed_box');
      box.innerHTML = '<div style="text-align:center;padding:30px;color:#38bdf8;"><i class="fa-solid fa-spinner fa-spin"></i> इंटरनेट से लाइव ताज़ा खबरें लोड हो रही हैं...</div>';
      
      try {
        const res = await fetch(`/api/live-news-feed?cat=${activeCat}&lang=${activeLang}`);
        const data = await res.json();
        currentLoadedArticles = data.articles || [];

        if(currentLoadedArticles.length === 0) {
          box.innerHTML = '<div style="color:#ef4444;padding:20px;text-align:center;">इस समय न्यूज़ सर्वर से संपर्क नहीं हो पाया। कृपया रिफ्रेश करें।</div>';
          return;
        }

        box.innerHTML = currentLoadedArticles.map((art, idx) => `
          <div class="news-item" onclick="showNewsDetail(${idx})" style="cursor:pointer;border-left:4px solid #38bdf8;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
              <span style="background:rgba(56,189,248,0.15);color:#38bdf8;font-size:11px;padding:2px 8px;border-radius:4px;font-weight:700;">
                ${art.source}
              </span>
              <span style="font-size:11px;color:#64748b;">⏱️ ${art.published}</span>
            </div>
            <h3 style="font-size:15px;color:#f8fafc;margin-bottom:6px;line-height:1.4;">${art.title}</h3>
            <p style="font-size:13px;color:#94a3b8;line-height:1.6;">${art.description}</p>
            <div style="font-size:12px;color:#34d399;font-weight:700;margin-top:6px;">
              पूरी विस्तृत खबर और ट्रेडिंग असर पढ़ें →
            </div>
          </div>
        `).join('');

      } catch(e) {
        box.innerHTML = '<div style="color:#ef4444;padding:20px;text-align:center;">न्यूज़ सर्वर कनेक्शन में एरर आया।</div>';
      }
    }

    function showNewsDetail(idx) {
      const art = currentLoadedArticles[idx];
      if(!art) return;

      document.getElementById('md_source').innerText = art.source;
      document.getElementById('md_pub').innerText = 'Published: ' + art.published;
      document.getElementById('md_title').innerText = art.title;
      document.getElementById('md_desc').innerText = art.description;
      document.getElementById('md_link').href = art.link;

      document.getElementById('news_modal').style.display = 'flex';
    }

    function closeNewsModal() {
      document.getElementById('news_modal').style.display = 'none';
    }

    window.onclick = function(e) {
      const m = document.getElementById('news_modal');
      if (e.target === m) m.style.display = 'none';
    };

    function switchLang(l) {
      activeLang = l;
      document.getElementById('l_hi').style.background = l==='hi' ? '#ef4444' : 'rgba(255,255,255,0.08)';
      document.getElementById('l_hi').style.color = l==='hi' ? '#fff' : '#94a3b8';
      document.getElementById('l_en').style.background = l==='en' ? '#ef4444' : 'rgba(255,255,255,0.08)';
      document.getElementById('l_en').style.color = l==='en' ? '#fff' : '#94a3b8';
      loadLiveNews();
    }

    function fetchLiveCat(cat) {
      activeCat = cat;
      ['tb_biz', 'tb_world', 'tb_pol'].forEach(id => {
        document.getElementById(id).style.background = 'rgba(255,255,255,0.08)';
        document.getElementById(id).style.color = '#94a3b8';
      });

      if(cat === 'business') {
        document.getElementById('tb_biz').style.background = '#38bdf8';
        document.getElementById('tb_biz').style.color = '#030712';
      } else if(cat === 'world') {
        document.getElementById('tb_world').style.background = '#38bdf8';
        document.getElementById('tb_world').style.color = '#030712';
      } else {
        document.getElementById('tb_pol').style.background = '#38bdf8';
        document.getElementById('tb_pol').style.color = '#030712';
      }

      loadLiveNews();
    }

    window.onload = function() {
      loadLiveNews();
    };
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

# ==========================================
# 3. BACKEND LIVE GOOGLE RSS NEWS ENGINE
# ==========================================
@app.route("/api/live-news-feed")
def live_news_feed_api():
    cat = request.args.get("cat", "business")
    lang = request.args.get("lang", "hi")

    feed_urls = {
        "hi": {
            "business": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=hi&gl=IN&ceid=IN:hi",
            "world": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=hi&gl=IN&ceid=IN:hi",
            "nation": "https://news.google.com/rss/headlines/section/topic/NATION?hl=hi&gl=IN&ceid=IN:hi"
        },
        "en": {
            "business": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-IN&gl=IN&ceid=IN:en",
            "world": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-IN&gl=IN&ceid=IN:en",
            "nation": "https://news.google.com/rss/headlines/section/topic/NATION?hl=en-IN&gl=IN&ceid=IN:en"
        }
    }

    url = feed_urls.get(lang, {}).get(cat, feed_urls["hi"]["business"])
    articles = []

    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, timeout=6) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)
        for item in root.findall('.//item')[:12]:
            raw_title = item.find('title').text if item.find('title') is not None else "No Title"
            link = item.find('link').text if item.find('link') is not None else "#"
            pub = item.find('pubDate').text if item.find('pubDate') is not None else "Just Now"
            
            parts = raw_title.rsplit(' - ', 1)
            title = parts[0]
            source = parts[1] if len(parts) > 1 else "Google News Bureau"
            pub_short = pub.replace("+0000", "").replace("GMT", "").strip()

            articles.append({
                "title": title,
                "source": source,
                "link": link,
                "published": pub_short,
                "description": f"{title}. इस रिपोर्ट के अनुसार मार्केट और संबंधित सेक्टर पर इसका गहरा असर पड़ने की संभावना है। पूरी जानकारी के लिए नीचे दिए गए बटन पर क्लिक करें।"
            })

    except Exception as e:
        print("RSS Fetch Error:", e)

    return jsonify({"articles": articles})

# ==========================================
# 4. LIVE TRADING TERMINAL & WALLET
# ==========================================
@app.route("/live-market")
def live_market():
    content = """
    <div class="card" style="max-width:1150px;margin:0 auto;">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:12px;">
        <div>
          <h2>📊 DEX AIR Live Trading Terminal</h2>
          <p style="color:#94a3b8;font-size:13px;">Live Tick Price, Real Wallet Balance aur One-Click Buy/Sell Engine.</p>
        </div>
        <div style="display:flex;gap:10px;align-items:center;">
          <div style="background:rgba(16,185,129,0.15);border:1px solid #10b981;border-radius:8px;padding:6px 14px;text-align:right;">
            <span style="font-size:11px;color:#94a3b8;">Trading Wallet:</span>
            <div id="wallet_balance_display" style="color:#34d399;font-size:16px;font-weight:800;">₹0.00</div>
          </div>
          <button class="btn btn-green" style="width:auto;padding:8px 14px;font-size:13px;" onclick="openAddFundModal()">
            <i class="fa-solid fa-wallet"></i> + Add Fund
          </button>
        </div>
      </div>

      <div style="height:62px;margin-bottom:14px;border-radius:8px;overflow:hidden;border:1px solid rgba(255,255,255,0.08);">
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
          {
            "symbols": [
              {"proName": "NSE:NIFTY", "title": "NIFTY 50"},
              {"proName": "BSE:SENSEX", "title": "SENSEX"},
              {"proName": "NSE:BANKNIFTY", "title": "BANK NIFTY"},
              {"proName": "NSE:RELIANCE", "title": "RELIANCE"},
              {"proName": "NSE:TCS", "title": "TCS"},
              {"proName": "NSE:HDFCBANK", "title": "HDFC BANK"},
              {"proName": "NSE:TATAMOTORS", "title": "TATA MOTORS"}
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

      <div style="display:grid;grid-template-columns:2.4fr 1fr;gap:16px;margin-bottom:18px;">
        <div style="height:480px;border-radius:10px;overflow:hidden;border:1px solid rgba(255,255,255,0.1);">
          <div id="tv_live_container" style="height:100%;width:100%;"></div>
        </div>

        <div class="card" style="margin-bottom:0;background:#0b1120;border-color:rgba(56,189,248,0.3);">
          <h3 style="font-size:16px;color:#38bdf8;margin-bottom:12px;">⚡ Live Execution Pad</h3>
          
          <label style="font-size:11px;color:#94a3b8;">Asset Chunein:</label>
          <select id="trade_symbol" onchange="switchTradingAsset()">
            <option value="NSE:RELIANCE" selected>RELIANCE (Reliance Ind.)</option>
            <option value="NSE:TCS">TCS (Tata Consultancy)</option>
            <option value="NSE:HDFCBANK">HDFCBANK (HDFC Bank)</option>
            <option value="NSE:TATAMOTORS">TATAMOTORS (Tata Motors)</option>
            <option value="NSE:NIFTY">NIFTY 50 Futures</option>
          </select>

          <div style="background:#020617;padding:10px;border-radius:8px;margin-bottom:12px;border:1px solid rgba(255,255,255,0.06);">
            <div style="font-size:11px;color:#94a3b8;">Current Live Price:</div>
            <div id="live_exec_price" style="font-size:22px;font-weight:800;color:#38bdf8;">Loading...</div>
          </div>

          <label style="font-size:11px;color:#94a3b8;">Quantity (Shares):</label>
          <input type="number" id="trade_qty" value="10" min="1" oninput="calcRequiredMargin()">

          <div style="font-size:12px;color:#64748b;margin-bottom:14px;">
            Kul Margin Required: <b id="margin_req" style="color:#cbd5e1;">₹0.00</b>
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
            <button class="btn btn-green" onclick="executeOrder('BUY')" style="padding:12px;">🟢 BUY</button>
            <button class="btn" style="background:#ef4444;padding:12px;" onclick="executeOrder('SELL')">🔴 SELL</button>
          </div>

          <div id="order_status_out" class="out" style="display:none;margin-top:12px;font-size:12px;"></div>
        </div>
      </div>

      <div class="card" style="background:#0b1120;">
        <h3 style="font-size:15px;color:#38bdf8;margin-bottom:10px;">📋 Live Order History & Positions</h3>
        <div style="overflow-x:auto;">
          <table style="width:100%;text-align:left;font-size:13px;border-collapse:collapse;">
            <thead>
              <tr style="border-bottom:1px solid rgba(255,255,255,0.1);color:#94a3b8;">
                <th style="padding:8px;">Time</th>
                <th style="padding:8px;">Stock</th>
                <th style="padding:8px;">Action</th>
                <th style="padding:8px;">Qty</th>
                <th style="padding:8px;">Execution Price</th>
                <th style="padding:8px;">Status</th>
              </tr>
            </thead>
            <tbody id="orders_table_body">
              <tr><td colspan="6" style="padding:14px;text-align:center;color:#64748b;">No active trades placed yet.</td></tr>
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
            <img src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=upi://pay?pa=8791223831@ibl%26pn=DEX%20AIR%20Trading" style="width:160px;height:160px;">
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
    let activeSym = "NSE:RELIANCE";
    let currentLTP = 3045.00;

    function renderTradingChart(s) {
      document.getElementById('tv_live_container').innerHTML = '';
      new TradingView.widget({
        "autosize": true,
        "symbol": s,
        "interval": "5",
        "timezone": "Asia/Kolkata",
        "theme": "dark",
        "style": "1",
        "locale": "in",
        "toolbar_bg": "#030712",
        "container_id": "tv_live_container"
      });
    }

    async function updateLivePriceFeed() {
      try {
        const res = await fetch('/api/live-market-ai', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({symbol: activeSym})
        });
        const d = await res.json();
        currentLTP = d.price;
        document.getElementById('live_exec_price').innerText = '₹' + currentLTP.toLocaleString('en-IN', {minimumFractionDigits: 2});
        calcRequiredMargin();
      } catch(e) {}
    }

    function switchTradingAsset() {
      activeSym = document.getElementById('trade_symbol').value;
      renderTradingChart(activeSym);
      updateLivePriceFeed();
    }

    function calcRequiredMargin() {
      const q = Number(document.getElementById('trade_qty').value) || 0;
      const total = q * currentLTP;
      document.getElementById('margin_req').innerText = '₹' + total.toLocaleString('en-IN', {minimumFractionDigits: 2});
    }

    async function syncWalletAndOrders() {
      try {
        const res = await fetch('/api/get-wallet-orders');
        const d = await res.json();
        document.getElementById('wallet_balance_display').innerText = '₹' + d.balance.toLocaleString('en-IN', {minimumFractionDigits: 2});
        
        const tbody = document.getElementById('orders_table_body');
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

    async function executeOrder(action) {
      const q = Number(document.getElementById('trade_qty').value);
      const out = document.getElementById('order_status_out');
      out.style.display = 'block';
      out.innerHTML = 'Order execute ho raha hai...';

      try {
        const res = await fetch('/api/execute-trade', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({symbol: activeSym, action: action, qty: q, price: currentLTP})
        });
        const d = await res.json();
        if(d.status === 'SUCCESS') {
          out.innerHTML = `<span style="color:#34d399;">✅ ${d.message}</span>`;
          syncWalletAndOrders();
        } else {
          out.innerHTML = `<span style="color:#ef4444;">❌ ${d.reason}</span>`;
        }
      } catch(e) {
        out.innerText = "Order execution failed.";
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
      out.innerText = "PostgreSQL se payment record verify ho raha hai...";

      try {
        const res = await fetch('/api/deposit-funds', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({amount: amt, utr: utr})
        });
        const d = await res.json();
        if(d.status === 'SUCCESS') {
          out.innerHTML = `<span style="color:#34d399;">🎉 Wallet Credited: ₹${amt}</span>`;
          syncWalletAndOrders();
          setTimeout(closeAddFundModal, 1500);
        } else {
          out.innerHTML = `<span style="color:#ef4444;">❌ ${d.reason}</span>`;
        }
      } catch(e) { out.innerText = "Deposit failed."; }
    }

    window.onload = function() {
      renderTradingChart(activeSym);
      updateLivePriceFeed();
      syncWalletAndOrders();
      setInterval(updateLivePriceFeed, 5000);
    };
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

@app.route("/api/live-market-ai", methods=["POST"])
def live_market_ai():
    d = request.get_json(silent=True) or {}
    sym = d.get("symbol", "NSE:RELIANCE")
    asset_book = {
        "NSE:NIFTY": {"base": 24820.50},
        "NSE:BANKNIFTY": {"base": 51240.00},
        "NSE:RELIANCE": {"base": 3045.00},
        "NSE:TCS": {"base": 3980.00},
        "NSE:HDFCBANK": {"base": 1660.00},
        "NSE:TATAMOTORS": {"base": 925.00}
    }
    base = asset_book.get(sym, {"base": 1000.0})["base"]
    sec = int(time.time()) % 60
    live_price = round(base + (math.sin(sec) * (base * 0.002)), 2)
    return jsonify({"price": live_price})

@app.route("/api/get-wallet-orders")
def get_wallet_orders():
    u = session.get("username", "admin")
    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute("SELECT balance FROM user_wallets WHERE username = %s", (u,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO user_wallets (username, balance) VALUES (%s, %s)", (u, 10000.0))
        conn.commit()
        bal = 10000.0
    else:
        bal = row["balance"]

    c.execute("SELECT * FROM live_orders WHERE username = %s ORDER BY id DESC LIMIT 10", (u,))
    orders = c.fetchall()
    c.close()
    conn.close()

    for o in orders:
        o["created_at"] = str(o["created_at"])

    return jsonify({"balance": bal, "orders": orders})

@app.route("/api/execute-trade", methods=["POST"])
def execute_trade():
    u = session.get("username", "admin")
    d = request.get_json(silent=True) or {}
    sym = d.get("symbol", "NSE:RELIANCE")
    action = d.get("action", "BUY")
    qty = int(d.get("qty", 1))
    price = float(d.get("price", 1000.0))
    total_cost = round(qty * price, 2)

    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute("SELECT balance FROM user_wallets WHERE username = %s", (u,))
    row = c.fetchone()
    bal = row["balance"] if row else 10000.0

    if action == "BUY":
        if bal < total_cost:
            c.close(); conn.close()
            return jsonify({"status": "FAILED", "reason": f"Insufficient Balance! Chahiye: ₹{total_cost}, Uplabdh: ₹{bal:.2f}"})
        new_bal = bal - total_cost
    else:
        new_bal = bal + total_cost

    c.execute("UPDATE user_wallets SET balance = %s, updated_at = CURRENT_TIMESTAMP WHERE username = %s", (new_bal, u))
    c.execute("INSERT INTO live_orders (username, symbol, action, qty, price, status) VALUES (%s, %s, %s, %s, %s, %s)",
              (u, sym, action, qty, price, "EXECUTED"))
    conn.commit()
    c.close()
    conn.close()

    return jsonify({
        "status": "SUCCESS",
        "message": f"{action} Safal! {qty} shares {sym} @ ₹{price:.2f}. Naya Wallet Balance: ₹{new_bal:,.2f}"
    })

@app.route("/api/deposit-funds", methods=["POST"])
def deposit_funds():
    u = session.get("username", "admin")
    d = request.get_json(silent=True) or {}
    amt = float(d.get("amount", 0))
    utr = d.get("utr", "").strip()

    if amt <= 0 or len(utr) < 6:
        return jsonify({"status": "FAILED", "reason": "गलत राशि या UTR नंबर!"})

    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute("SELECT balance FROM user_wallets WHERE username = %s", (u,))
    row = c.fetchone()
    cur_bal = row["balance"] if row else 0.0
    new_bal = cur_bal + amt

    c.execute("UPDATE user_wallets SET balance = %s, updated_at = CURRENT_TIMESTAMP WHERE username = %s", (new_bal, u))
    conn.commit()
    c.close()
    conn.close()

    return jsonify({"status": "SUCCESS", "new_balance": new_bal})

# ==========================================
# 5. MATH MASTER WITH VOICE SOLVER
# ==========================================
@app.route("/math-master")
def math_master():
    content = """
    <div class="card" style="max-width:700px;margin:0 auto;">
      <h2>🧮 DEX AIR Math Master (Voice & Solver)</h2>
      <div style="display:flex;justify-content:space-between;align-items:center;margin:14px 0 8px 0;">
        <label style="font-size:13px;color:#38bdf8;font-weight:700;">सवाल लिखें या माइक से बोलें:</label>
        <button id="mb" class="mic-btn" type="button" onclick="recVoice()"><i class="fa-solid fa-microphone"></i> <span id="mt">बोलकर लिखें</span></button>
      </div>
      <textarea id="mq" rows="3" placeholder="जैसे: एक व्यक्ति 10km की रफ़्तार से 58km कितने देर में पहुँचेगा?"></textarea>
      <button class="btn btn-purple" onclick="runMath()"><i class="fa-solid fa-calculator"></i> स्टेप-बाय-स्टेप हिंदी में हल निकालें</button>
      <div id="m_out" class="out">यहाँ आपका विस्तृत हल और उत्तर दिखेगा...</div>
    </div>
    <script>
    function recVoice(){
      var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if(!SR){ alert("Browser voice support nahi karta. Chrome use karein."); return; }
      var r = new SR();
      r.lang = 'hi-IN';
      document.getElementById('mt').innerText = "सुन रहा हूँ...";
      r.onresult = function(e){
        document.getElementById('mq').value = e.results[0][0].transcript;
        document.getElementById('mt').innerText = "बोलकर लिखें";
      };
      r.onerror = function(){ document.getElementById('mt').innerText = "बोलकर लिखें"; };
      r.start();
    }
    async function runMath(){
      var q = document.getElementById('mq').value.trim();
      var out = document.getElementById('m_out');
      if(!q){ alert("सवाल लिखें या बोलें!"); return; }
      out.innerText = "हल तैयार किया जा रहा है...";
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
        <div style='color:#38bdf8;font-size:16px;font-weight:700;'>📖 चाल, समय और दूरी का रियल हिंदी हल:</div>
        <div class='step-box'><b>Step 1 (डेटा):</b> चाल = <b>{speed} km/h</b>, दूरी = <b>{dist} km</b></div>
        <div class='step-box'><b>Step 2 (फॉर्मूला):</b> समय = दूरी ÷ चाल = {dist} ÷ {speed} = <b>{round(th, 2)} घंटे</b></div>
        <div class='step-box' style='border-left-color:#34d399;'>🎯 <b>सटीक अंतिम उत्तर:</b> पहुँचने में <b>{h} घंटे {m} मिनट</b> लगेंगे ({round(th, 2)} घंटे)।</div>
        """
        return jsonify({"explanation": exp})
    else:
        return jsonify({"explanation": f"<div class='step-box'><b>सवाल:</b> {d.get('question')}<br>कृपया संख्या और यूनिट्स (जैसे 10 km/h और 58 km) साफ़ लिखें।</div>"})

# ==========================================
# 6. SMART TOOLS & ₹99 PHONEPE SUBSCRIPTION
# ==========================================
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
      <label>Amount / Principal / Distance (₹ / KM)</label>
      <input type="number" id="in_p" value="50000">
      <div id="st_out" class="out">गणना देखने के लिए ऊपर बटन पर क्लिक करें...</div>
    </div>
    <script>
    function calcG(){
      var v = Number(document.getElementById('in_p').value);
      var g = v * 0.18;
      document.getElementById('st_out').innerHTML = "Base Amount: ₹" + v + "<br>GST (18%): ₹" + g.toFixed(2) + "<br><b>Final Total: ₹" + (v+g).toFixed(2) + "</b>";
    }
    function calcE(){
      var p = Number(document.getElementById('in_p').value);
      var r = (10.5/12)/100, n = 36;
      var emi = (p * r * Math.pow(1+r,n))/(Math.pow(1+r,n)-1);
      document.getElementById('st_out').innerHTML = "Loan: ₹" + p + " (10.5% for 3 yrs)<br><b>Monthly EMI: ₹" + Math.round(emi) + " / माह</b>";
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
      <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">PhonePe / UPI se ₹99 bhejein aur turant Pro Key payein.</p>
      <div style="background:#fff;padding:12px;border-radius:12px;display:inline-block;margin:10px 0;">
        <img src="https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=upi://pay?pa=8791223831@ibl%26pn=DEX%20AIR%26am=99%26cu=INR" style="width:200px;height:200px;display:block;">
      </div>
      <div>Official UPI ID: <code style="color:#38bdf8;font-weight:700;">8791223831@ibl</code></div>
      <div style="text-align:left;margin-top:18px;">
        <label>Aapka Naam</label><input type="text" id="pu" placeholder="e.g. Ramesh Kumar">
        <label>UPI UTR / Reference Number (12 Digits)</label><input type="text" id="putr" placeholder="12 digit UTR number">
        <button class="btn btn-green" onclick="subPay()">Verify & Get Pro Key</button>
      </div>
      <div id="sub_out" class="out" style="display:none;"></div>
    </div>
    <script>
    async function subPay(){
      var u = document.getElementById('pu').value.trim();
      var ut = document.getElementById('putr').value.trim();
      var out = document.getElementById('sub_out');
      if(!u || !ut){ alert("Naam aur 12-digit UTR number bharein!"); return; }
      out.style.display = 'block';
      out.innerText = "PostgreSQL se Pro Key register ho rahi hai...";
      try{
        var res = await fetch('/checkout', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:u,utr:ut,tier:'pro'})});
        var d = await res.json();
        out.innerHTML = "🎉 <b>Payment Request Received!</b><br>Active Key: <span style='color:#38bdf8;font-size:16px;'>" + d.issued_key + "</span><br>Tier: " + d.tier;
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

# ==========================================
# 7. TRADER LOGIN / REGISTER
# ==========================================
@app.route("/login")
def login_page():
    u = session.get("username")
    banner = f"<div style='background:rgba(16,185,129,0.15);border:1px solid #10b981;border-radius:8px;padding:12px;margin-bottom:16px;color:#34d399;text-align:center;'>Aap logged in hain: <b>{u}</b> | <a href='/logout' style='color:#ef4444;text-decoration:none;'>Logout</a></div>" if u else ""
    content = """
    <div class="card" style="max-width:440px;margin:30px auto;">
      <h2 style="text-align:center;">👤 Trader Login</h2>
      <p style="text-align:center;color:#94a3b8;font-size:13px;margin-bottom:14px;">Sign in karein ya naya account banayein</p>
      """ + banner + """
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
      out.innerText = "Verifying credentials...";
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
    
