"""Generate dashboard screenshots using Playwright."""
import asyncio
from pathlib import Path

HTML_OVERVIEW = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>body{background:#030712;font-family:monospace;}</style>
</head>
<body class="bg-gray-950 text-gray-100 min-h-screen text-sm" style="width:1200px;">

<header class="border-b border-gray-800 px-6 py-3 flex items-center justify-between">
  <div class="flex items-center gap-3">
    <span class="text-orange-400 font-bold text-lg">tokenspy</span>
    <span class="text-gray-500 text-xs">local-first LLM observability</span>
  </div>
  <div class="flex items-center gap-2">
    <span class="w-2 h-2 bg-green-500 rounded-full" style="display:inline-block;animation:none;"></span>
    <span class="text-xs text-green-400">live</span>
  </div>
</header>

<nav class="border-b border-gray-800 px-6 flex gap-6">
  <button class="py-3 text-xs uppercase tracking-wider font-semibold" style="border-bottom:2px solid #f97316;color:#f97316;">Overview</button>
  <button class="py-3 text-xs uppercase tracking-wider font-semibold text-gray-400">Traces</button>
  <button class="py-3 text-xs uppercase tracking-wider font-semibold text-gray-400">Evaluations</button>
  <button class="py-3 text-xs uppercase tracking-wider font-semibold text-gray-400">Prompts</button>
  <button class="py-3 text-xs uppercase tracking-wider font-semibold text-gray-400">Settings</button>
</nav>

<main class="p-6">
  <!-- Stat cards -->
  <div class="grid grid-cols-4 gap-4 mb-6">
    <div class="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <div class="text-gray-400 text-xs mb-1">Total Cost</div>
      <div class="text-2xl font-bold text-orange-400">$0.2341</div>
    </div>
    <div class="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <div class="text-gray-400 text-xs mb-1">Total Calls</div>
      <div class="text-2xl font-bold text-white">47</div>
    </div>
    <div class="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <div class="text-gray-400 text-xs mb-1">Total Tokens</div>
      <div class="text-2xl font-bold text-white">84,320</div>
    </div>
    <div class="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <div class="text-gray-400 text-xs mb-1">Live Updates</div>
      <div class="text-2xl font-bold text-green-400">ON</div>
    </div>
  </div>

  <!-- Charts row -->
  <div class="grid grid-cols-2 gap-6 mb-6">
    <div class="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <div class="text-xs text-gray-400 mb-3">Cost per Day (last 7 days)</div>
      <canvas id="costChart" height="160"></canvas>
    </div>
    <div class="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <div class="text-xs text-gray-400 mb-3">Cost by Model</div>
      <canvas id="modelChart" height="160"></canvas>
    </div>
  </div>

  <!-- Top functions table -->
  <div class="bg-gray-900 border border-gray-800 rounded-lg p-4">
    <div class="text-xs text-gray-400 mb-3">Top Functions by Cost</div>
    <table class="w-full text-xs">
      <thead>
        <tr class="text-gray-500 border-b border-gray-800">
          <th class="text-left py-2">Function</th>
          <th class="text-right py-2">Cost</th>
          <th class="text-right py-2">Calls</th>
          <th class="text-right py-2">Tokens</th>
          <th class="text-right py-2">Avg ms</th>
          <th class="text-right py-2">Model</th>
        </tr>
      </thead>
      <tbody>
        <tr class="border-b border-gray-800/50">
          <td class="py-2 text-orange-300">fetch_and_summarize</td>
          <td class="py-2 text-right text-green-400">$0.1423</td>
          <td class="py-2 text-right text-gray-300">18</td>
          <td class="py-2 text-right text-gray-300">52,400</td>
          <td class="py-2 text-right text-gray-300">834</td>
          <td class="py-2 text-right text-gray-500">gpt-4o</td>
        </tr>
        <tr class="border-b border-gray-800/50">
          <td class="py-2 text-orange-300">generate_report</td>
          <td class="py-2 text-right text-green-400">$0.0612</td>
          <td class="py-2 text-right text-gray-300">12</td>
          <td class="py-2 text-right text-gray-300">19,840</td>
          <td class="py-2 text-right text-gray-300">412</td>
          <td class="py-2 text-right text-gray-500">gpt-4o</td>
        </tr>
        <tr class="border-b border-gray-800/50">
          <td class="py-2 text-orange-300">extract_entities</td>
          <td class="py-2 text-right text-green-400">$0.0214</td>
          <td class="py-2 text-right text-gray-300">9</td>
          <td class="py-2 text-right text-gray-300">8,120</td>
          <td class="py-2 text-right text-gray-300">198</td>
          <td class="py-2 text-right text-gray-500">gpt-4o-mini</td>
        </tr>
        <tr class="border-b border-gray-800/50">
          <td class="py-2 text-orange-300">classify_intent</td>
          <td class="py-2 text-right text-green-400">$0.0092</td>
          <td class="py-2 text-right text-gray-300">8</td>
          <td class="py-2 text-right text-gray-300">3,960</td>
          <td class="py-2 text-right text-gray-300">87</td>
          <td class="py-2 text-right text-gray-500">claude-haiku-4-5</td>
        </tr>
      </tbody>
    </table>
  </div>
</main>

<script>
const costCtx = document.getElementById('costChart').getContext('2d');
new Chart(costCtx, {
  type: 'bar',
  data: {
    labels: ['Mar 4','Mar 5','Mar 6','Mar 7','Mar 8','Mar 9','Mar 10'],
    datasets: [{
      data: [0.021, 0.034, 0.018, 0.052, 0.041, 0.038, 0.031],
      backgroundColor: '#f9731688',
      borderColor: '#f97316',
      borderWidth: 1,
      borderRadius: 3,
    }]
  },
  options: {
    responsive: true,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { color: '#1f2937' }, ticks: { color: '#6b7280', font: { size: 10 } } },
      y: { grid: { color: '#1f2937' }, ticks: { color: '#6b7280', font: { size: 10 },
           callback: v => '$' + v.toFixed(3) } }
    }
  }
});

const modelCtx = document.getElementById('modelChart').getContext('2d');
new Chart(modelCtx, {
  type: 'doughnut',
  data: {
    labels: ['gpt-4o', 'gpt-4o-mini', 'claude-haiku-4-5', 'claude-sonnet-4-6'],
    datasets: [{
      data: [0.2035, 0.0214, 0.0092, 0],
      backgroundColor: ['#f97316','#3b82f6','#8b5cf6','#10b981'],
      borderWidth: 0,
    }]
  },
  options: {
    responsive: true,
    plugins: {
      legend: {
        position: 'right',
        labels: { color: '#9ca3af', font: { size: 11 }, boxWidth: 12 }
      }
    }
  }
});
</script>
</body>
</html>"""

HTML_TRACES = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<script src="https://cdn.tailwindcss.com"></script>
<style>body{background:#030712;font-family:monospace;}</style>
</head>
<body class="bg-gray-950 text-gray-100 min-h-screen text-sm" style="width:1200px;">

<header class="border-b border-gray-800 px-6 py-3 flex items-center justify-between">
  <div class="flex items-center gap-3">
    <span class="text-orange-400 font-bold text-lg">tokenspy</span>
    <span class="text-gray-500 text-xs">local-first LLM observability</span>
  </div>
  <div class="flex items-center gap-2">
    <span class="w-2 h-2 bg-green-500 rounded-full" style="display:inline-block;"></span>
    <span class="text-xs text-green-400">live</span>
  </div>
</header>

<nav class="border-b border-gray-800 px-6 flex gap-6">
  <button class="py-3 text-xs uppercase tracking-wider font-semibold text-gray-400">Overview</button>
  <button class="py-3 text-xs uppercase tracking-wider font-semibold" style="border-bottom:2px solid #f97316;color:#f97316;">Traces</button>
  <button class="py-3 text-xs uppercase tracking-wider font-semibold text-gray-400">Evaluations</button>
  <button class="py-3 text-xs uppercase tracking-wider font-semibold text-gray-400">Prompts</button>
  <button class="py-3 text-xs uppercase tracking-wider font-semibold text-gray-400">Settings</button>
</nav>

<main class="p-6">
  <div class="flex items-center justify-between mb-4">
    <div class="text-xs text-gray-400">47 traces</div>
    <input type="text" placeholder="Filter traces..." class="bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-xs text-gray-300 w-48" value="">
  </div>

  <div class="space-y-2">

    <!-- Trace 1 expanded -->
    <div class="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
      <div class="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-gray-800/50">
        <span class="text-orange-400">▼</span>
        <span class="text-orange-300 font-semibold">research_pipeline</span>
        <span class="text-gray-500 text-xs ml-2">842ms</span>
        <span class="text-green-400 text-xs">$0.0523</span>
        <span class="ml-auto text-gray-500 text-xs">2026-03-10 14:23:01</span>
        <span class="text-xs px-2 py-0.5 rounded" style="background:#14532d;color:#86efac;">ok</span>
      </div>
      <!-- Span tree -->
      <div class="border-t border-gray-800 px-4 py-2 space-y-1 bg-gray-950/50">
        <div class="flex items-center gap-2 py-1.5 pl-4">
          <span class="text-gray-600">├─</span>
          <span class="text-xs px-1.5 py-0.5 rounded text-blue-300" style="background:#1e3a5f;">retrieval</span>
          <span class="text-gray-300">retrieve_docs</span>
          <span class="text-gray-500 text-xs">12ms</span>
          <span class="text-gray-600 text-xs">$0.0000</span>
          <span class="text-gray-500 text-xs ml-auto">→ 5 documents</span>
        </div>
        <div class="flex items-center gap-2 py-1.5 pl-4">
          <span class="text-gray-600">├─</span>
          <span class="text-xs px-1.5 py-0.5 rounded text-orange-300" style="background:#431407;">llm</span>
          <span class="text-gray-300">summarize</span>
          <span class="text-gray-500 text-xs">810ms</span>
          <span class="text-green-400 text-xs">$0.0144</span>
          <span class="text-gray-500 text-xs ml-2">gpt-4o · 4,200 in · 380 out</span>
        </div>
        <div class="flex items-center gap-2 py-1.5 pl-4">
          <span class="text-gray-600">└─</span>
          <span class="text-xs px-1.5 py-0.5 rounded text-purple-300" style="background:#3b1f6e;">function</span>
          <span class="text-gray-300">rank_results</span>
          <span class="text-gray-500 text-xs">8ms</span>
          <span class="text-gray-600 text-xs">$0.0000</span>
          <span class="text-gray-500 text-xs ml-auto">→ [doc3, doc1, doc5]</span>
        </div>
        <!-- Scores -->
        <div class="flex items-center gap-3 mt-2 pt-2 border-t border-gray-800/50 pl-4">
          <span class="text-gray-500 text-xs">scores:</span>
          <span class="text-xs px-2 py-0.5 rounded" style="background:#1c3a2a;color:#6ee7b7;">relevance 0.92</span>
          <span class="text-xs px-2 py-0.5 rounded" style="background:#1c3a2a;color:#6ee7b7;">hallucination 0.05</span>
          <span class="text-gray-500 text-xs ml-1">· llm_judge</span>
        </div>
      </div>
    </div>

    <!-- Trace 2 collapsed -->
    <div class="bg-gray-900 border border-gray-800 rounded-lg">
      <div class="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-gray-800/50">
        <span class="text-gray-500">▶</span>
        <span class="text-orange-300 font-semibold">data_extraction</span>
        <span class="text-gray-500 text-xs ml-2">340ms</span>
        <span class="text-green-400 text-xs">$0.0214</span>
        <span class="ml-auto text-gray-500 text-xs">2026-03-10 14:19:44</span>
        <span class="text-xs px-2 py-0.5 rounded" style="background:#14532d;color:#86efac;">ok</span>
      </div>
    </div>

    <!-- Trace 3 collapsed -->
    <div class="bg-gray-900 border border-gray-800 rounded-lg">
      <div class="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-gray-800/50">
        <span class="text-gray-500">▶</span>
        <span class="text-orange-300 font-semibold">report_generation</span>
        <span class="text-gray-500 text-xs ml-2">190ms</span>
        <span class="text-green-400 text-xs">$0.0091</span>
        <span class="ml-auto text-gray-500 text-xs">2026-03-10 14:15:12</span>
        <span class="text-xs px-2 py-0.5 rounded" style="background:#14532d;color:#86efac;">ok</span>
      </div>
    </div>

    <!-- Trace 4 - error -->
    <div class="bg-gray-900 border border-gray-800 rounded-lg">
      <div class="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-gray-800/50">
        <span class="text-gray-500">▶</span>
        <span class="text-orange-300 font-semibold">batch_classify</span>
        <span class="text-gray-500 text-xs ml-2">2,341ms</span>
        <span class="text-green-400 text-xs">$0.0381</span>
        <span class="ml-auto text-gray-500 text-xs">2026-03-10 14:08:55</span>
        <span class="text-xs px-2 py-0.5 rounded" style="background:#450a0a;color:#fca5a5;">error</span>
      </div>
    </div>

    <!-- Trace 5 collapsed -->
    <div class="bg-gray-900 border border-gray-800 rounded-lg">
      <div class="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-gray-800/50">
        <span class="text-gray-500">▶</span>
        <span class="text-orange-300 font-semibold">fetch_and_summarize</span>
        <span class="text-gray-500 text-xs ml-2">612ms</span>
        <span class="text-green-400 text-xs">$0.0318</span>
        <span class="ml-auto text-gray-500 text-xs">2026-03-10 14:02:31</span>
        <span class="text-xs px-2 py-0.5 rounded" style="background:#14532d;color:#86efac;">ok</span>
      </div>
    </div>

  </div>
</main>
</body>
</html>"""

async def take_screenshots():
    from playwright.async_api import async_playwright

    out_dir = Path("docs/assets")
    out_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1200, "height": 700})

        # Overview
        await page.set_content(HTML_OVERVIEW, wait_until="networkidle")
        await page.wait_for_timeout(1500)  # let charts render
        await page.screenshot(path=str(out_dir / "dashboard-overview.png"), full_page=True)
        print("✓ dashboard-overview.png")

        # Traces
        await page.set_content(HTML_TRACES, wait_until="networkidle")
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(out_dir / "dashboard-traces.png"), full_page=True)
        print("✓ dashboard-traces.png")

        await browser.close()

asyncio.run(take_screenshots())
