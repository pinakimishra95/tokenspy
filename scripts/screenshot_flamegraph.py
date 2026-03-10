"""Generate a terminal-style screenshot of the tokenspy flame graph output."""
from __future__ import annotations

from pathlib import Path

FLAME_TEXT = """\
╔══════════════════════════════════════════════════════════════════════╗
║  tokenspy cost report                                                ║
║  total: $0.0523  ·  18,734 tokens  ·  3 calls                       ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  fetch_and_summarize      $0.038  ████████████░░░░  73%             ║
║    └─ gpt-4o               $0.038  ████████████░░░░  73%            ║
║       └─ 12,000 tokens                                               ║
║                                                                      ║
║  generate_report          $0.011  ████░░░░░░░░░░░░  21%            ║
║    └─ gpt-4o               $0.011  ████░░░░░░░░░░░░  21%            ║
║       └─ 3,600 tokens                                                ║
║                                                                      ║
║  extract_entities         $0.003  █░░░░░░░░░░░░░░░   6%            ║
║    └─ gpt-4o-mini          $0.003  █░░░░░░░░░░░░░░░   6%            ║
║       └─ 3,134 tokens                                                ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║  Optimization hints                                                  ║
║                                                                      ║
║  🔴 fetch_and_summarize [gpt-4o]                                     ║
║     Switch to gpt-4o-mini — 94% cheaper  (~$540/month savings)      ║
╚══════════════════════════════════════════════════════════════════════╝"""

HTML = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #0d1117;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 32px;
    font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  }}
  .terminal {{
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    overflow: hidden;
    width: 740px;
    box-shadow: 0 16px 48px rgba(0,0,0,0.6);
  }}
  .titlebar {{
    background: #21262d;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 8px;
    border-bottom: 1px solid #30363d;
  }}
  .dot {{ width: 12px; height: 12px; border-radius: 50%; }}
  .dot.red {{ background: #ff5f57; }}
  .dot.yellow {{ background: #febc2e; }}
  .dot.green {{ background: #28c840; }}
  .title {{
    color: #8b949e;
    font-size: 13px;
    margin-left: 8px;
  }}
  .content {{
    padding: 20px 24px 24px;
    color: #e6edf3;
    font-size: 13.5px;
    line-height: 1.65;
    white-space: pre;
  }}
  .prompt {{
    color: #3fb950;
    display: block;
    margin-bottom: 6px;
  }}
</style>
</head>
<body>
<div class="terminal">
  <div class="titlebar">
    <div class="dot red"></div>
    <div class="dot yellow"></div>
    <div class="dot green"></div>
    <span class="title">python run_pipeline.py</span>
  </div>
  <div class="content"><span class="prompt">$ python run_pipeline.py</span>{FLAME_TEXT}</div>
</div>
</body>
</html>"""

out_path = Path(__file__).parent.parent / "docs" / "assets" / "flamegraph-demo.png"
out_path.parent.mkdir(parents=True, exist_ok=True)

html_path = Path(__file__).parent / "_flamegraph_tmp.html"
html_path.write_text(HTML, encoding="utf-8")

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 900, "height": 520})
    page.goto(f"file://{html_path.resolve()}")
    page.wait_for_timeout(300)
    page.screenshot(path=str(out_path), full_page=False)
    browser.close()

html_path.unlink()
print(f"Saved: {out_path}  ({out_path.stat().st_size // 1024}KB)")
