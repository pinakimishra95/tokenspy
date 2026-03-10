"""Generate a full-width hero banner for tokenspy GitHub README."""
from __future__ import annotations
from pathlib import Path

HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    width: 1400px;
    height: 320px;
    background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #0d1117 100%);
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-family: -apple-system, 'Segoe UI', sans-serif;
    overflow: hidden;
    position: relative;
  }
  /* grid lines background */
  body::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(255,100,0,0.06) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,100,0,0.06) 1px, transparent 1px);
    background-size: 40px 40px;
  }
  .left {
    padding: 0 60px;
    z-index: 1;
    flex: 1;
  }
  .logo {
    font-size: 52px;
    font-weight: 800;
    color: #fff;
    letter-spacing: -1px;
    line-height: 1;
    margin-bottom: 12px;
  }
  .logo span {
    color: #ff6600;
  }
  .tagline {
    font-size: 20px;
    color: #8b949e;
    font-weight: 400;
    line-height: 1.5;
    max-width: 500px;
    margin-bottom: 24px;
  }
  .tagline strong {
    color: #e6edf3;
  }
  .pills {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
  }
  .pill {
    background: rgba(255,102,0,0.12);
    border: 1px solid rgba(255,102,0,0.3);
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 13px;
    color: #ff8c40;
    font-weight: 500;
    font-family: 'Menlo', monospace;
  }
  .right {
    padding: 28px 60px 28px 0;
    z-index: 1;
    flex-shrink: 0;
  }
  .terminal {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    overflow: hidden;
    width: 540px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
  }
  .titlebar {
    background: #21262d;
    padding: 9px 14px;
    display: flex;
    align-items: center;
    gap: 6px;
    border-bottom: 1px solid #30363d;
  }
  .dot { width: 10px; height: 10px; border-radius: 50%; }
  .dot.r { background: #ff5f57; }
  .dot.y { background: #febc2e; }
  .dot.g { background: #28c840; }
  .code {
    padding: 14px 18px;
    font-family: 'Menlo', 'Monaco', monospace;
    font-size: 12.5px;
    line-height: 1.75;
    color: #e6edf3;
  }
  .kw { color: #ff7b72; }
  .fn { color: #d2a8ff; }
  .dec { color: #79c0ff; }
  .str { color: #a5d6ff; }
  .cm { color: #8b949e; }
  .gr { color: #3fb950; }
</style>
</head>
<body>
  <div class="left">
    <div class="logo">token<span>spy</span> 🔥</div>
    <div class="tagline">
      <strong>cProfile for LLMs.</strong> Find which function burns your AI budget.<br>
      No cloud. No signup. No proxy. Just <code style="color:#ff8c40;background:rgba(255,102,0,0.1);padding:1px 6px;border-radius:4px;font-size:17px">pip install tokenspy</code>.
    </div>
    <div class="pills">
      <div class="pill">cost flame graph</div>
      <div class="pill">tracing</div>
      <div class="pill">evaluations</div>
      <div class="pill">prompt versioning</div>
      <div class="pill">live dashboard</div>
    </div>
  </div>
  <div class="right">
    <div class="terminal">
      <div class="titlebar">
        <div class="dot r"></div><div class="dot y"></div><div class="dot g"></div>
      </div>
      <div class="code">
<span class="kw">import</span> tokenspy, openai

<span class="dec">@tokenspy.profile</span>
<span class="kw">def</span> <span class="fn">run_pipeline</span>(query):
    docs  = fetch_and_summarize(query)
    reply = generate_report(docs)
    <span class="kw">return</span> reply

run_pipeline(<span class="str">"Analyze Q3 earnings"</span>)
tokenspy.report()   <span class="cm"># ← flame graph below</span>

<span class="gr">fetch_and_summarize   $0.038  ████████████  73%</span>
<span class="cm">generate_report       $0.011  ████          21%</span>
<span class="cm">extract_entities      $0.003  █              6%</span>
      </div>
    </div>
  </div>
</body>
</html>"""

out_path = Path(__file__).parent.parent / "docs" / "assets" / "banner.png"
out_path.parent.mkdir(parents=True, exist_ok=True)
html_path = Path(__file__).parent / "_banner_tmp.html"
html_path.write_text(HTML, encoding="utf-8")

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 320})
    page.goto(f"file://{html_path.resolve()}")
    page.wait_for_timeout(300)
    page.screenshot(path=str(out_path), full_page=False)
    browser.close()

html_path.unlink()
print(f"Saved: {out_path}  ({out_path.stat().st_size // 1024}KB)")
