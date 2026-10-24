import os, ast, json, uuid, time, math, psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

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
<header style="background:rgba(3,7,18,0.9);padding:14px 20px;border-bottom:1px solid rgba(255,255,255,0.1);position:sticky;top:0;z-index:99;">
  <div style="max-width:1150px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
    <a href="/" style="font-size:20px;font-weight:800;color:#38bdf8;text-decoration:none;">⚡ DEX AIR</a>
    <div style="display:flex;gap:8px;flex-wrap:wrap;">
      <a href="/" style="color:#cbd5e1;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:rgba(255,255,255,0.05);">Home</a>
      <a href="/compounding" style="color:#cbd5e1;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:rgba(255,255,255,0.05);">Compounding</a>
      <a href="/math-master" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 12px;border-radius:6px;background:#6366f1;font-weight:700;">🧮 Math Master</a>
      <a href="/ai" style="color:#cbd5e1;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:rgba(255,255,255,0.05);">AI Safety</a>
      <a href="/api" style="color:#cbd5e1;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:rgba(255,255,255,0.05);">API Vault</a>
      <a href="/subscription" style="color:#cbd5e1;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:rgba(255,255,255,0.05);">Pricing</a>
      <a href="/help" style="color:#cbd5e1;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;background:rgba(255,255,255,0.05);">Help</a>
      <a href="/developer" style="color:#fff;text-decoration:none;font-size:13px;padding:6px 12px;border-radius:6px;background:#0284c7;font-weight:700;">Developer Studio</a>
    </div>
  </div>
</header>
"""

T_HEAD = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>DEX AIR Sovereign Enterprise</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;}
body{background:#030712;color:#f8fafc;min-height:100vh;}
.card{background:rgba(17,24,39,0.85);border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:22px;margin-bottom:20px;}
.btn{background:#0284c7;color:#fff;border:none;border-radius:8px;padding:10px 16px;font-weight:700;cursor:pointer;width:100%;text-decoration:none;display:inline-block;text-align:center;}
.btn-green{background:#059669;}
.btn-purple{background:#6366f1;}
input,textarea,select{width:100%;background:#090d16;border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:10px;color:#38bdf8;margin:6px 0 14px 0;}
.out{background:#020617;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:14px;color:#34d399;font-family:monospace;font-size:13px;margin-top:14px;}

/* BODMAS Calculator Keyboard Grid */
.calc-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-top: 12px;
}
.c-btn {
  background: #1e293b;
  color: #f8fafc;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 14px;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.1s ease;
}
.c-btn:hover { background: #334155; }
.c-btn:active { transform: scale(0.96); }
.c-op { background: #0284c7; color: #fff; }
.c-op:hover { background: #0369a1; }
.c-action { background: #ef4444; color: #fff; }
.c-action:hover { background: #dc2626; }
.c-equals { background: #059669; color: #fff; grid-column: span 2; }
.c-equals:hover { background: #047857; }
</style>
</head><body>""" + T_NAV + """<div style="max-width:1000px;margin:30px auto;padding:0 16px;">"""

T_FOOT = """</div><footer style="text-align:center;padding:20px;font-size:12px;color:#64748b;border-top:1px solid rgba(255,255,255,0.08);">DEX AIR Sovereign Enterprise © 2026 | PostgreSQL Live Active</footer></body></html>"""

@app.route("/")
def home():
    content = """
    <div style="text-align:center;margin-bottom:30px;">
      <h1 style="color:#38bdf8;font-size:32px;margin-bottom:8px;">Sovereign Cloud Microservices</h1>
      <p style="color:#94a3b8;font-size:14px;">High-speed AST execution engine, financial calculators, BODMAS math solver, and AI security.</p>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;">
      <div class="card">
        <h3>🧮 Math Master & BODMAS</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">Interactive BODMAS calculator keypad, Trigonometry, and Algebra solvers.</p>
        <a href="/math-master" class="btn btn-purple">Open Math Master</a>
      </div>
      <div class="card">
        <h3>⚡ Wealth Compounding</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">Lumpsum compounding and Step-up SIP investment formulas.</p>
        <a href="/compounding" class="btn">Open Compounding</a>
      </div>
      <div class="card">
        <h3>💻 Developer Studio</h3>
        <p style="color:#94a3b8;font-size:13px;margin:8px 0 14px 0;">Sandboxed execution environment with live editor and PostgreSQL logs.</p>
        <a href="/developer" class="btn btn-green">Launch IDE</a>
      </div>
    </div>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

# ==========================================
# MATH MASTER & BODMAS CALCULATOR PAGE
# ==========================================
@app.route("/math-master")
def math_master():
    content = """
    <div class="card" style="max-width:520px;margin:0 auto;">
      <h2>🧮 DEX AIR Math Master Engine</h2>
      <p style="color:#94a3b8;font-size:13px;margin-bottom:18px;">
        Interactive BODMAS Calculator, Trigonometry, and Algebraic solvers.
      </p>

      <!-- Category Tabs -->
      <div style="display:flex;gap:6px;margin-bottom:18px;">
        <button id="m_tab1" class="btn" style="flex:1;background:#6366f1;font-size:12px;padding:8px 6px;" onclick="setMathTab('bodmas')">
          ➕ BODMAS Calc
        </button>
        <button id="m_tab2" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;font-size:12px;padding:8px 6px;" onclick="setMathTab('trig')">
          📐 Trigonometry
        </button>
        <button id="m_tab3" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;font-size:12px;padding:8px 6px;" onclick="setMathTab('algebra')">
          📈 Algebra
        </button>
      </div>

      <!-- 1. Interactive BODMAS Calculator Grid -->
      <div id="sec_bodmas">
        <label style="font-size:12px;color:#94a3b8;">Expression Display (BODMAS Rule)</label>
        <input type="text" id="calc_screen" value="50 + (12 * 8) - (100 / 4)" style="font-size:18px;letter-spacing:1px;font-weight:700;text-align:right;" placeholder="0">

        <!-- Keyboard Grid -->
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
          <button class="c-btn c-op" style="grid-column: span 2;" onclick="pressKey('%')">% Modulo</button>
        </div>
      </div>

      <!-- 2. Trigonometry Section -->
      <div id="sec_trig" style="display:none;">
        <label>Select Function</label>
        <select id="trig_fn">
          <option value="sin">sin(θ)</option>
          <option value="cos">cos(θ)</option>
          <option value="tan">tan(θ)</option>
          <option value="cot">cot(θ)</option>
          <option value="sec">sec(θ)</option>
          <option value="cosec">cosec(θ)</option>
        </select>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
          <div>
            <label>Angle Value (θ)</label>
            <input type="number" id="trig_val" value="45">
          </div>
          <div>
            <label>Angle Unit</label>
            <select id="trig_unit">
              <option value="deg">Degrees (°)</option>
              <option value="rad">Radians</option>
            </select>
          </div>
        </div>
        <button class="btn btn-purple" onclick="solveTrig()">Calculate Trigonometry</button>
      </div>

      <!-- 3. Algebra Section -->
      <div id="sec_algebra" style="display:none;">
        <p style="font-size:13px;color:#38bdf8;margin-bottom:10px;">Quadratic Formula: <b>ax² + bx + c = 0</b></p>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;">
          <div>
            <label>a</label>
            <input type="number" id="alg_a" value="1">
          </div>
          <div>
            <label>b</label>
            <input type="number" id="alg_b" value="-5">
          </div>
          <div>
            <label>c</label>
            <input type="number" id="alg_c" value="6">
          </div>
        </div>
        <button class="btn btn-purple" onclick="solveAlgebra()">Solve Roots</button>
      </div>

      <!-- Result Screen -->
      <div id="math_output" class="out" style="line-height:1.7;">
        Result ready. Tap buttons or calculate...
      </div>
    </div>

    <script>
    function pressKey(val) {
      const screen = document.getElementById('calc_screen');
      if (val === 'C') {
        screen.value = '';
      } else if (val === 'DEL') {
        screen.value = screen.value.slice(0, -1);
      } else {
        screen.value += val;
      }
    }

    function setMathTab(mode) {
      const b1 = document.getElementById('m_tab1');
      const b2 = document.getElementById('m_tab2');
      const b3 = document.getElementById('m_tab3');
      const s1 = document.getElementById('sec_bodmas');
      const s2 = document.getElementById('sec_trig');
      const s3 = document.getElementById('sec_algebra');
      const out = document.getElementById('math_output');

      [b1, b2, b3].forEach(b => {
        b.style.background = 'rgba(255,255,255,0.08)';
        b.style.color = '#94a3b8';
      });
      [s1, s2, s3].forEach(s => s.style.display = 'none');

      if(mode === 'bodmas') {
        b1.style.background = '#6366f1'; b1.style.color = '#fff';
        s1.style.display = 'block';
        out.innerText = "BODMAS calculator active...";
      } else if(mode === 'trig') {
        b2.style.background = '#6366f1'; b2.style.color = '#fff';
        s2.style.display = 'block';
        out.innerText = "Trigonometry solver ready...";
      } else {
        b3.style.background = '#6366f1'; b3.style.color = '#fff';
        s3.style.display = 'block';
        out.innerText = "Algebraic equation solver ready...";
      }
    }

    async function solveBodmas() {
      const expr = document.getElementById('calc_screen').value;
      const out = document.getElementById('math_output');
      out.innerText = "Applying BODMAS rules...";

      try {
        const res = await fetch('/math-calc', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({type: 'bodmas', expr: expr})
        });
        const d = await res.json();
        if(d.status === 'SUCCESS') {
          out.innerHTML = `
            🔢 <b>Expression:</b> ${expr}<br>
            🎯 <b>Calculated Result:</b> <span style="color:#38bdf8;font-size:20px;font-weight:700;">${d.result}</span>
          `;
          document.getElementById('calc_screen').value = d.result;
        } else {
          out.innerText = "Error: " + d.reason;
        }
      } catch(e) { out.innerText = "Error executing calculation."; }
    }

    async function solveTrig() {
      const fn = document.getElementById('trig_fn').value;
      const val = Number(document.getElementById('trig_val').value);
      const unit = document.getElementById('trig_unit').value;
      const out = document.getElementById('math_output');
      out.innerText = "Calculating trigonometry...";

      try {
        const res = await fetch('/math-calc', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({type: 'trig', fn: fn, val: val, unit: unit})
        });
        const d = await res.json();
        out.innerHTML = `📐 <b>Formula:</b> ${fn}(${val}${unit == 'deg' ? '°' : ' rad'})<br>🎯 <b>Value:</b> <span style="color:#38bdf8;font-size:16px;font-weight:700;">${d.result}</span>`;
      } catch(e) { out.innerText = "Error calculating trigonometry."; }
    }

    async function solveAlgebra() {
      const a = Number(document.getElementById('alg_a').value);
      const b = Number(document.getElementById('alg_b').value);
      const c = Number(document.getElementById('alg_c').value);
      const out = document.getElementById('math_output');
      out.innerText = "Solving quadratic roots...";

      try {
        const res = await fetch('/math-calc', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({type: 'algebra', a: a, b: b, c: c})
        });
        const d = await res.json();
        out.innerHTML = `
          📈 <b>Equation:</b> ${a}x² + (${b})x + (${c}) = 0<br>
          ⚡ <b>Discriminant (D):</b> ${d.d}<br>
          🎯 <b>Roots:</b> <span style="color:#38bdf8;font-size:16px;font-weight:700;">x₁ = ${d.root1}, x₂ = ${d.root2}</span>
        `;
      } catch(e) { out.innerText = "Error solving equation."; }
    }
    </script>
    """
    return render_template_string(T_HEAD + content + T_FOOT)

# ==========================================
# COMPOUNDING PAGE
# ==========================================
@app.route("/compounding")
def compounding():
    content = """
    <div class="card" style="max-width:650px;margin:0 auto;">
      <h2>📈 Compounding Wealth Engine</h2>
      <p style="color:#94a3b8;font-size:13px;margin-bottom:18px;">Lumpsum and Step-up SIP compounding calculations.</p>
      
      <div style="display:flex;gap:10px;margin-bottom:20px;">
        <button id="tab1" class="btn" style="flex:1;background:#0284c7;" onclick="switchMode('lump')">
          💰 Normal Lumpsum
        </button>
        <button id="tab2" class="btn" style="flex:1;background:rgba(255,255,255,0.08);color:#94a3b8;" onclick="switchMode('sip')">
          🚀 Monthly Step-up SIP
        </button>
      </div>

      <div id="lump_form">
        <label>Principal Amount (₹)</label>
        <input type="number" id="l_p" value="100000">

        <label>Annual Interest Rate (% Rate)</label>
        <input type="number" id="l_r" value="12">

        <label>Duration (Years)</label>
        <input type="number" id="l_y" value="5">

        <button class="btn btn-green" onclick="calcLump()">Calculate Lumpsum</button>
      </div>

      <div id="sip_form" style="display:none;">
        <label>Monthly SIP (₹ per month)</label>
        <input type="number" id="s_sip" value="5000">

        <label>Annual Step-up Increment (% per year)</label>
        <input type="number" id="s_step" value="10">

        <label>Expected Return (% Rate)</label>
        <input type="number" id="s_r" value="12">

        <label>Duration (Years)</label>
        <input type="number" id="s_y" value="10">

        <button class="btn btn-green" onclick="calcSip()">Calculate Step-up SIP</button>
      </div>

      <div id="comp_res" class="out" style="line-height:1.7;margin-top:18px;">
        Click button above to compute...
      </div>
    </div>

    <script>
    function switchMode(mode) {
      const t1 = document.getElementById('tab1');
      const t2 = document.getElementById('tab2');
      const f1 = document.getElementById('lump_form');
      const f2 = document.getElementById('sip_form');
      const out = document.getElementById('comp_res');

      if(mode === 'lump') {
        t1.style.background = '#0284c7'; t1.style.color = '#fff';
        t2.style.background = 'rgba(255,255,255,0.08)'; t2.style.color = '#94a3b8';
        f1.style.display = 'block'; f2.style.display = 'none';
        out.innerText = "Ready to calculate lumpsum...";
      } else {
        t2.style.background = '#0284c7'; t2.style.color = '#fff';
        t1.style.background = 'rgba(255,255,255,0.08)'; t1.style.color = '#94a3b8';
        f2.style.display = 'block'; f1.style.display = 'none';
        out.innerText = "Ready to calculate Step-up SIP...";
      }
    }

    async function calcLump() {
      const p = Number(document.getElementById('l_p').value);
      const r = Number(document.getElementById('l_r').value);
      const y = Number(document.getElementById('l_y').value);
      const out = document.getElementById('comp_res');
      out.innerText = "Processing...";

      const code = `def lump_calc(p, r, y):\\n    amt = p * ((1 + (r / 100)) ** y)\\n    gain = amt - p\\n    return {"invested": round(p), "gain": round(gain), "total": round(amt, 2)}`;
      
      try {
        const res = await fetch('/execute', {
          method: 'POST',
          headers: {'Content-Type': 'application/json', 'X-API-Key': 'dex_master_live_key_999'},
          body: JSON.stringify({code: code, func_name: 'lump_calc', args: [p, r, y]})
        });
        const d = await res.json();
        if(d.verdict === 'SUCCESS') {
          const resData = d.resul
