import re

with open('docs/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update <style> root variables and glass classes
style_replacement = """    :root {
      --primary: #2563eb;
      --primary-dark: #1d4ed8;
      --primary-light: #dbeafe;
      --secondary: #0d9488;
      --accent: #f59e0b;
      --bg-main: #f8fafc;
      --bg-card: #ffffff;
      --text-main: #0f172a;
      --text-muted: #475569;
      --border: #e2e8f0;
      --code-bg: #0f172a;
    }

    body {
      font-family: "Plus Jakarta Sans", sans-serif;
      background-color: #f8fafc;
      color: #0f172a;
    }

    h1, h2, h3, h4, .font-heading {
      font-family: "Outfit", sans-serif;
    }

    /* Clean Card Styles */
    .glass-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.05), 0 1px 2px -1px rgb(0 0 0 / 0.05);
    }

    .glass-nav {
      background: rgba(255, 255, 255, 0.95);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border-bottom: 1px solid #e2e8f0;
    }

    .hero-glow {
      background: radial-gradient(circle at 50% -20%, rgba(37, 99, 235, 0.12) 0%, rgba(13, 148, 136, 0.06) 35%, transparent 70%);
    }

    /* Custom Scrollbar */
    ::-webkit-scrollbar {
      width: 8px;
      height: 8px;
    }
    ::-webkit-scrollbar-track {
      background: #f1f5f9;
    }
    ::-webkit-scrollbar-thumb {
      background: #cbd5e1;
      border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: #94a3b8;
    }

    /* Range slider styling */
    input[type=range] {
      accent-color: #2563eb;
    }

    /* Interactive Table Hover */
    .table-row-hover:hover {
      background-color: rgba(239, 246, 255, 0.7);
    }"""

html = re.sub(r':root\s*\{.*?(?=</style>)', style_replacement, html, flags=re.DOTALL)

# 2. Update section #benchmarks
benchmarks_old_header = r'<section id="benchmarks" class="py-20 relative">.*?<h2 class="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">.*?</h2>.*?<p class="mt-4 text-slate-400 text-base sm:text-lg">.*?</p>'
benchmarks_new_header = """<section id="benchmarks" class="py-16 md:py-24 bg-white border-b border-slate-200 relative">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="text-center max-w-3xl mx-auto mb-14">
                <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cyan-50 border border-cyan-200 text-cyan-800 text-xs font-bold uppercase tracking-wider mb-4">
                    <i class="fa-solid fa-chart-line text-cyan-600"></i> Empirical Findings
                </div>
                <h2 class="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
                    Interactive Performance & Pareto Trade-offs
                </h2>
                <p class="mt-4 text-slate-600 text-base sm:text-lg leading-relaxed">
                    Explore empirical efficiency across downstream tasks, memory footprints, and multi-GPU communication overheads.
                </p>
            </div>"""
html = re.sub(r'<section id="benchmarks" class="py-20 relative">.*?<div class="text-center max-w-3xl mx-auto mb-16">.*?</div>', benchmarks_new_header, html, flags=re.DOTALL)

# Update chart buttons in #benchmarks
chart_btns_old = r'<div class="flex flex-wrap justify-center gap-3 mb-10">.*?</div>'
chart_btns_new = """<div class="flex flex-wrap justify-center gap-3 mb-10">
                <button onclick="switchChartTab('pareto')" id="btn-chart-pareto" class="px-5 py-2.5 rounded-xl font-semibold text-sm transition-all bg-blue-600 text-white shadow-sm border border-blue-700 flex items-center gap-2">
                    <i class="fa-solid fa-chart-scatter"></i> Accuracy vs. Memory & Latency (Pareto)
                </button>
                <button onclick="switchChartTab('comm')" id="btn-chart-comm" class="px-5 py-2.5 rounded-xl font-semibold text-sm transition-all bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 flex items-center gap-2">
                    <i class="fa-solid fa-network-wired"></i> Inter-GPU All-to-All Comm Overhead
                </button>
                <button onclick="switchChartTab('tasks')" id="btn-chart-tasks" class="px-5 py-2.5 rounded-xl font-semibold text-sm transition-all bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 flex items-center gap-2">
                    <i class="fa-solid fa-layer-group"></i> Multi-Task Benchmark Breakdown
                </button>
            </div>"""
html = re.sub(chart_btns_old, chart_btns_new, html, flags=re.DOTALL)

# Chart container & views
html = html.replace('class="glass-card rounded-3xl p-6 sm:p-8 border border-slate-800"', 'class="bg-slate-50 rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-sm"')
html = html.replace('<h3 class="text-xl font-bold text-white flex items-center gap-2">', '<h3 class="text-xl font-bold text-slate-900 flex items-center gap-2">')
html = html.replace('<p class="text-xs sm:text-sm text-slate-400">', '<p class="text-xs sm:text-sm text-slate-600 font-medium">')
html = html.replace('<span class="text-xs text-slate-400 font-medium">Model:</span>', '<span class="text-xs text-slate-700 font-bold">Model:</span>')
html = html.replace('<span class="text-xs text-slate-400 font-medium">Technique:</span>', '<span class="text-xs text-slate-700 font-bold">Technique:</span>')
html = html.replace('class="bg-slate-950 text-slate-200 text-xs rounded-lg border border-slate-700 px-3 py-1.5 focus:outline-none focus:border-blue-500"', 'class="bg-white text-slate-800 text-xs sm:text-sm font-semibold rounded-lg border border-slate-300 px-3 py-1.5 focus:outline-none focus:border-blue-500 shadow-sm"')
html = html.replace('class="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-slate-800/60 text-xs text-slate-400"', 'class="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-slate-200 text-xs text-slate-700 font-medium"')
html = html.replace('class="text-xs bg-slate-800/80 px-3 py-1 rounded-lg text-slate-300 border border-slate-700"', 'class="text-xs bg-white px-3 py-1 rounded-lg text-slate-700 border border-slate-200 font-semibold shadow-sm"')
html = html.replace('class="p-4 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-400 leading-relaxed"', 'class="p-4 rounded-xl bg-white border border-slate-200 text-xs sm:text-sm text-slate-700 leading-relaxed shadow-sm"')
html = html.replace('<strong class="text-slate-200">Key Finding:</strong>', '<strong class="text-slate-900 font-bold">Key Finding:</strong>')
html = html.replace('<span class="text-cyan-400 font-semibold">37.5%</span>', '<span class="text-cyan-700 font-bold">37.5%</span>')

# 3. Update section #calculator
calculator_old = r'<section id="calculator" class="py-20 relative overflow-hidden bg-slate-900/40 border-y border-slate-800/60">.*?<div class="text-center max-w-3xl mx-auto mb-16">.*?</div>'
calculator_new = """<section id="calculator" class="py-16 md:py-24 bg-slate-50 border-b border-slate-200 relative overflow-hidden">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div class="text-center max-w-3xl mx-auto mb-14">
                <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-purple-50 border border-purple-200 text-purple-800 text-xs font-bold uppercase tracking-wider mb-4">
                    <i class="fa-solid fa-calculator text-purple-600"></i> Interactive System Tool
                </div>
                <h2 class="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
                    MoE Compression Recipe Planner & Calculator
                </h2>
                <p class="mt-4 text-slate-600 text-base sm:text-lg leading-relaxed">
                    Select your base architecture, configure intra-expert slimming & structural trimming parameters, and instantly compute memory savings, throughput gain, and ready-to-run CLI commands.
                </p>
            </div>"""
html = re.sub(calculator_old, calculator_new, html, flags=re.DOTALL)

# Update calculator controls card & results card
html = html.replace('<div class="lg:col-span-7 glass-card rounded-3xl p-6 sm:p-8 border border-slate-800 space-y-6">', '<div class="lg:col-span-7 bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">')
html = html.replace('<h3 class="text-lg font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3">', '<h3 class="text-lg font-bold text-slate-900 flex items-center gap-2 border-b border-slate-200 pb-3">')
html = html.replace('<label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">', '<label class="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">')

# Model buttons in calculator
calc_btn_mixtral_old = r'<button type="button" onclick="setCalcModel\(\'mixtral\'\)" id="calc-model-mixtral".*?</button>'
calc_btn_mixtral_new = """<button type="button" onclick="setCalcModel('mixtral')" id="calc-model-mixtral" class="calc-btn active p-4 rounded-xl border-2 border-blue-600 bg-blue-50/70 text-left transition-all flex flex-col shadow-sm">
                                <span class="font-bold text-blue-950 text-sm sm:text-base">Mixtral-8x7B-v0.1</span>
                                <span class="text-xs text-slate-700 font-medium mt-1">46.7B Total | 12.9B Active (Top-2 / 8 Exp)</span>
                                <span class="text-xs text-blue-700 font-bold mt-2 font-mono">32 Layers, 8 Experts/Layer</span>
                            </button>"""
html = re.sub(calc_btn_mixtral_old, calc_btn_mixtral_new, html, flags=re.DOTALL)

calc_btn_deepseek_old = r'<button type="button" onclick="setCalcModel\(\'deepseek\'\)" id="calc-model-deepseek".*?</button>'
calc_btn_deepseek_new = """<button type="button" onclick="setCalcModel('deepseek')" id="calc-model-deepseek" class="calc-btn p-4 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-left transition-all flex flex-col">
                                <span class="font-bold text-slate-800 text-sm sm:text-base">DeepSeek-MoE-16B</span>
                                <span class="text-xs text-slate-600 mt-1">16.4B Total | 2.8B Active (Fine-grained)</span>
                                <span class="text-xs text-slate-500 font-semibold mt-2 font-mono">28 Layers, 64 Experts + 2 Shared</span>
                            </button>"""
html = re.sub(calc_btn_deepseek_old, calc_btn_deepseek_new, html, flags=re.DOTALL)

# Trim buttons
html = html.replace('class="calc-btn-trim active py-2.5 px-3 rounded-lg border border-blue-500/40 bg-blue-950/30 text-xs font-medium text-center text-slate-200"', 'class="calc-btn-trim active py-2.5 px-3 rounded-lg border-2 border-blue-600 bg-blue-600 text-xs sm:text-sm font-semibold text-center text-white shadow-sm"')
html = html.replace('class="calc-btn-trim py-2.5 px-3 rounded-lg border border-slate-800 bg-slate-900/50 hover:bg-slate-800/60 text-xs font-medium text-center text-slate-400"', 'class="calc-btn-trim py-2.5 px-3 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-xs sm:text-sm font-medium text-center text-slate-700"')

# Slim buttons
html = html.replace('class="calc-btn-slim active py-2.5 px-3 rounded-lg border border-blue-500/40 bg-blue-950/30 text-xs font-medium text-center text-slate-200"', 'class="calc-btn-slim active py-2.5 px-3 rounded-lg border-2 border-blue-600 bg-blue-600 text-xs sm:text-sm font-semibold text-center text-white shadow-sm"')
html = html.replace('class="calc-btn-slim py-2.5 px-3 rounded-lg border border-slate-800 bg-slate-900/50 hover:bg-slate-800/60 text-xs font-medium text-center text-slate-400"', 'class="calc-btn-slim py-2.5 px-3 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-xs sm:text-sm font-medium text-center text-slate-700"')

# FT buttons
html = html.replace('class="calc-btn-ft active py-2.5 px-3 rounded-lg border border-blue-500/40 bg-blue-950/30 text-xs font-medium text-center text-slate-200"', 'class="calc-btn-ft active py-2.5 px-3 rounded-lg border-2 border-blue-600 bg-blue-600 text-xs sm:text-sm font-semibold text-center text-white shadow-sm"')
html = html.replace('class="calc-btn-ft py-2.5 px-3 rounded-lg border border-slate-800 bg-slate-900/50 hover:bg-slate-800/60 text-xs font-medium text-center text-slate-400"', 'class="calc-btn-ft py-2.5 px-3 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-xs sm:text-sm font-medium text-center text-slate-700"')

# Calculator results side
html = html.replace('<div class="glass-card rounded-3xl p-6 sm:p-8 border border-slate-800 space-y-6 bg-gradient-to-b from-slate-900/90 to-slate-950/90">', '<div class="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">')
html = html.replace('<h3 class="text-lg font-bold text-white flex items-center justify-between border-b border-slate-800 pb-3">', '<h3 class="text-lg font-bold text-slate-900 flex items-center justify-between border-b border-slate-200 pb-3">')
html = html.replace('<span class="flex items-center gap-2"><i class="fa-solid fa-gauge-high text-cyan-400"></i> Estimated System Impact</span>', '<span class="flex items-center gap-2"><i class="fa-solid fa-gauge-high text-blue-600"></i> Estimated System Impact</span>')
html = html.replace('class="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-semibold"', 'class="text-xs px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-300 font-bold"')
html = html.replace('class="p-4 rounded-2xl bg-slate-950/80 border border-slate-800/80"', 'class="p-4 rounded-2xl bg-slate-50 border border-slate-200/80"')
html = html.replace('class="text-xs text-slate-400 font-medium">Model VRAM (Weights)</div>', 'class="text-xs text-slate-600 font-bold uppercase tracking-wider">Model VRAM (Weights)</div>')
html = html.replace('class="text-xs text-slate-400 font-medium">Active Params / Token</div>', 'class="text-xs text-slate-600 font-bold uppercase tracking-wider">Active Params / Token</div>')
html = html.replace('class="text-xs text-slate-400 font-medium">Throughput Speedup</div>', 'class="text-xs text-slate-600 font-bold uppercase tracking-wider">Throughput Speedup</div>')
html = html.replace('class="text-xs text-slate-400 font-medium">Est. MMLU Retention</div>', 'class="text-xs text-slate-600 font-bold uppercase tracking-wider">Est. MMLU Retention</div>')

html = html.replace('class="text-2xl sm:text-3xl font-extrabold text-white mt-1 flex items-baseline gap-1"', 'class="text-2xl sm:text-3xl font-black text-slate-900 mt-1 flex items-baseline gap-1"')
html = html.replace('class="text-2xl sm:text-3xl font-extrabold text-cyan-400 mt-1 flex items-baseline gap-1"', 'class="text-2xl sm:text-3xl font-black text-blue-600 mt-1 flex items-baseline gap-1"')
html = html.replace('class="text-2xl sm:text-3xl font-extrabold text-indigo-400 mt-1 flex items-baseline gap-1"', 'class="text-2xl sm:text-3xl font-black text-indigo-700 mt-1 flex items-baseline gap-1"')

html = html.replace('class="text-sm font-normal text-slate-400">GB</span>', 'class="text-sm font-semibold text-slate-500">GB</span>')
html = html.replace('class="text-sm font-normal text-slate-400">B</span>', 'class="text-sm font-semibold text-slate-500">B</span>')
html = html.replace('class="text-sm font-normal text-slate-400">x</span>', 'class="text-sm font-semibold text-slate-500">x</span>')
html = html.replace('class="text-sm font-normal text-slate-400">%</span>', 'class="text-sm font-semibold text-slate-500">%</span>')

html = html.replace('id="res-vram-diff" class="text-xs text-emerald-400 font-medium mt-1"', 'id="res-vram-diff" class="text-xs text-emerald-700 font-bold mt-1"')
html = html.replace('id="res-active-diff" class="text-xs text-slate-400 font-medium mt-1"', 'id="res-active-diff" class="text-xs text-slate-600 font-medium mt-1"')
html = html.replace('id="res-speedup-detail" class="text-xs text-slate-400 font-medium mt-1"', 'id="res-speedup-detail" class="text-xs text-slate-600 font-medium mt-1"')
html = html.replace('id="res-mmlu-score" class="text-xs text-slate-400 font-medium mt-1"', 'id="res-mmlu-score" class="text-xs text-slate-600 font-medium mt-1"')

# Hardware recommendation banner
html = html.replace('<div class="p-3.5 rounded-xl bg-blue-950/30 border border-blue-500/20 text-xs text-slate-300 flex items-center gap-3">', '<div class="p-4 rounded-xl bg-blue-50 border border-blue-200 text-xs sm:text-sm text-slate-800 flex items-center gap-3 font-medium">')
html = html.replace('<span class="font-semibold text-white">Recommended Hardware: </span>', '<span class="font-bold text-slate-900">Recommended Hardware: </span>')
html = html.replace('<span id="res-hardware" class="text-slate-300">2x A100 (80GB) or 4x RTX 4090 (24GB)</span>', '<span id="res-hardware" class="text-slate-700 font-semibold">2x A100 (80GB) or 4x RTX 4090 (24GB)</span>')

# CLI command box
html = html.replace('<div class="glass-card rounded-3xl p-6 border border-slate-800 space-y-3">', '<div class="bg-white rounded-3xl p-6 border border-slate-200 shadow-sm space-y-3">')
html = html.replace('<span class="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">', '<span class="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-2">')
html = html.replace('<button onclick="copyGeneratedCommand()" class="text-xs px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-all flex items-center gap-1.5 border border-slate-700">', '<button onclick="copyGeneratedCommand()" class="text-xs px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold transition-all flex items-center gap-1.5 border border-slate-300">')

# 4. Update section #results (Matrix table)
results_old = r'<section id="results" class="py-20 relative">.*?<div class="text-center max-w-3xl mx-auto mb-14">.*?</div>'
results_new = """<section id="results" class="py-16 md:py-24 bg-white border-b border-slate-200 relative">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="text-center max-w-3xl mx-auto mb-14">
                <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-50 border border-blue-200 text-blue-800 text-xs font-bold uppercase tracking-wider mb-4">
                    <i class="fa-solid fa-table-list text-blue-600"></i> Comprehensive Evaluation
                </div>
                <h2 class="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
                    Benchmark Results Matrix
                </h2>
                <p class="mt-4 text-slate-600 text-base sm:text-lg leading-relaxed">
                    Systematic evaluation across MMLU, GSM8K, ARC-c, WinoGrande, HellaSwag, downstream retention, and memory footprint.
                </p>
            </div>"""
html = re.sub(results_old, results_new, html, flags=re.DOTALL)

# Table filter buttons
tbl_filters_old = r'<div class="flex flex-wrap items-center justify-between gap-4 mb-6">.*?</div>'
tbl_filters_new = """<div class="flex flex-wrap items-center justify-between gap-4 mb-6">
                <div class="flex flex-wrap gap-2">
                    <button onclick="filterTable('all')" id="tbl-btn-all" class="tbl-filter-btn active px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-semibold bg-blue-600 text-white border border-blue-700 shadow-sm">
                        All Configurations
                    </button>
                    <button onclick="filterTable('mixtral')" id="tbl-btn-mixtral" class="tbl-filter-btn px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium bg-white text-slate-700 hover:bg-slate-100 border border-slate-300">
                        Mixtral-8x7B
                    </button>
                    <button onclick="filterTable('deepseek')" id="tbl-btn-deepseek" class="tbl-filter-btn px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium bg-white text-slate-700 hover:bg-slate-100 border border-slate-300">
                        DeepSeek-MoE-16B
                    </button>
                    <button onclick="filterTable('slimming')" id="tbl-btn-slimming" class="tbl-filter-btn px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium bg-white text-slate-700 hover:bg-slate-100 border border-slate-300">
                        Slimming (Quant)
                    </button>
                    <button onclick="filterTable('trimming')" id="tbl-btn-trimming" class="tbl-filter-btn px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium bg-white text-slate-700 hover:bg-slate-100 border border-slate-300">
                        Trimming (Drop)
                    </button>
                    <button onclick="filterTable('synergy')" id="tbl-btn-synergy" class="tbl-filter-btn px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium bg-white text-slate-700 hover:bg-slate-100 border border-slate-300">
                        Unified Recipes
                    </button>
                </div>
                <div class="text-xs sm:text-sm text-slate-600 font-mono">
                    Showing <span id="tbl-row-count" class="text-slate-900 font-bold">12</span> verified evaluations
                </div>
            </div>"""
html = re.sub(tbl_filters_old, tbl_filters_new, html, flags=re.DOTALL)

# Table body & classes
html = html.replace('<div class="glass-card rounded-3xl border border-slate-800 overflow-hidden shadow-2xl">', '<div class="bg-white rounded-3xl border border-slate-200 overflow-hidden shadow-sm">')
html = html.replace('<thead class="bg-slate-950/90 text-slate-400 uppercase text-[11px] font-bold tracking-wider border-b border-slate-800">', '<thead class="bg-slate-100 text-slate-700 uppercase text-xs font-bold tracking-wider border-b border-slate-200">')
html = html.replace('<tbody id="benchmarkTableBody" class="divide-y divide-slate-800/60 font-mono text-xs">', '<tbody id="benchmarkTableBody" class="divide-y divide-slate-200 font-mono text-xs sm:text-sm text-slate-800">')
html = html.replace('text-white', 'text-slate-900')
html = html.replace('text-slate-300', 'text-slate-700')
html = html.replace('text-slate-400', 'text-slate-600')
html = html.replace('text-emerald-400', 'text-emerald-700 font-bold')
html = html.replace('hover:bg-slate-800/30 transition-colors', 'hover:bg-blue-50/50 transition-colors')
html = html.replace('bg-slate-800 text-slate-300 text-[10px]', 'bg-slate-100 text-slate-800 text-xs font-semibold px-2 py-0.5 rounded-full border border-slate-200')
html = html.replace('bg-blue-900/50 text-blue-300 text-[10px]', 'bg-blue-50 text-blue-800 text-xs font-semibold px-2 py-0.5 rounded-full border border-blue-200')
html = html.replace('bg-purple-900/50 text-purple-300 text-[10px]', 'bg-purple-50 text-purple-800 text-xs font-semibold px-2 py-0.5 rounded-full border border-purple-200')
html = html.replace('bg-pink-900/50 text-pink-300 text-[10px]', 'bg-pink-50 text-pink-800 text-xs font-semibold px-2 py-0.5 rounded-full border border-pink-200')

# 5. Quickstart section
html = html.replace('<section id="quickstart" class="py-20 relative bg-slate-900/30 border-t border-slate-800/60">', '<section id="quickstart" class="py-16 md:py-24 bg-slate-50 border-b border-slate-200 relative">')
html = html.replace('<div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-4">', '<div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-bold uppercase tracking-wider mb-4">')
html = html.replace('<div class="glass-card rounded-3xl border border-slate-800 p-6 sm:p-8 relative">', '<div class="bg-white rounded-3xl border border-slate-200 p-6 sm:p-8 relative shadow-sm">')

# 6. Citation section
html = html.replace('<section id="citation" class="py-20 relative">', '<section id="citation" class="py-16 md:py-24 bg-white relative">')
html = html.replace('<div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold uppercase tracking-wider mb-3">', '<div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-800 text-xs font-bold uppercase tracking-wider mb-3">')
html = html.replace('<div class="glass-card rounded-2xl border border-slate-800 p-6 relative">', '<div class="bg-slate-50 rounded-2xl border border-slate-200 p-6 relative shadow-sm">')

# 7. Footer
html = html.replace('<footer class="border-t border-slate-800 bg-slate-950/80 py-12">', '<footer class="border-t border-slate-200 bg-white py-12">')

# 8. Update JavaScript functions for theme toggling
old_js_block = r'// ----------------------------------------------------\s*// Tab Switchers \(Taxonomy, Code, Charts\)\s*// ----------------------------------------------------.*?(?=// ----------------------------------------------------\s*// Initialize on DOM Ready)'
new_js_block = """// ----------------------------------------------------
        // Tab Switchers (Taxonomy, Code, Charts)
        // ----------------------------------------------------
        function switchTaxTab(tabId) {
            ['slimming', 'trimming', 'hybrid', 'table'].forEach(t => {
                const btn = document.getElementById('tab-btn-' + t);
                const panel = document.getElementById('tax-panel-' + t);
                if (btn && panel) {
                    if (t === tabId) {
                        btn.className = 'tax-tab-btn px-5 py-2.5 rounded-xl font-bold text-sm transition-all duration-200 bg-blue-600 text-white shadow-md';
                        panel.classList.remove('hidden');
                    } else {
                        btn.className = 'tax-tab-btn px-5 py-2.5 rounded-xl font-bold text-sm transition-all duration-200 bg-white text-slate-700 hover:bg-slate-100 border border-slate-200';
                        panel.classList.add('hidden');
                    }
                }
            });
        }

        function switchCodeTab(tabId) {
            ['env', 'trim', 'slim', 'ft', 'eval'].forEach(t => {
                const btn = document.getElementById('btn-code-' + t);
                const content = document.getElementById('code-content-' + t);
                if (btn && content) {
                    if (t === tabId) {
                        btn.className = 'code-tab-btn active px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold bg-blue-600 text-white border border-blue-700 shadow-sm flex items-center gap-2';
                        content.classList.remove('hidden');
                    } else {
                        btn.className = 'code-tab-btn px-4 py-2 rounded-xl text-xs sm:text-sm font-medium bg-white text-slate-700 hover:bg-slate-100 border border-slate-300 flex items-center gap-2';
                        content.classList.add('hidden');
                    }
                }
            });
        }

        function switchChartTab(tabId) {
            ['pareto', 'comm', 'tasks'].forEach(t => {
                const btn = document.getElementById('btn-chart-' + t);
                const view = document.getElementById('view-chart-' + t);
                if (btn && view) {
                    if (t === tabId) {
                        btn.className = 'px-5 py-2.5 rounded-xl font-semibold text-sm transition-all bg-blue-600 text-white shadow-sm border border-blue-700 flex items-center gap-2';
                        view.classList.remove('hidden');
                    } else {
                        btn.className = 'px-5 py-2.5 rounded-xl font-semibold text-sm transition-all bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 flex items-center gap-2';
                        view.classList.add('hidden');
                    }
                }
            });
        }

        // ----------------------------------------------------
        // Table Filtering
        // ----------------------------------------------------
        function filterTable(cat) {
            const rows = document.querySelectorAll('#benchmarkTableBody tr');
            let visibleCount = 0;
            rows.forEach(r => {
                const m = r.getAttribute('data-model');
                const c = r.getAttribute('data-category');
                let match = false;
                if (cat === 'all') match = true;
                else if (cat === 'mixtral' && m === 'mixtral') match = true;
                else if (cat === 'deepseek' && m === 'deepseek') match = true;
                else if (cat === 'slimming' && c === 'slimming') match = true;
                else if (cat === 'trimming' && c === 'trimming') match = true;
                else if (cat === 'synergy' && c === 'synergy') match = true;

                if (match) {
                    r.classList.remove('hidden');
                    visibleCount++;
                } else {
                    r.classList.add('hidden');
                }
            });
            document.getElementById('tbl-row-count').innerText = visibleCount;

            document.querySelectorAll('.tbl-filter-btn').forEach(btn => {
                btn.className = 'tbl-filter-btn px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium bg-white text-slate-700 hover:bg-slate-100 border border-slate-300';
            });
            const activeBtn = document.getElementById('tbl-btn-' + cat);
            if (activeBtn) {
                activeBtn.className = 'tbl-filter-btn active px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-semibold bg-blue-600 text-white border border-blue-700 shadow-sm';
            }
        }

        // ----------------------------------------------------
        // Interactive MoE Recipe Calculator Logic
        // ----------------------------------------------------
        function setCalcModel(m) {
            calcState.model = m;
            document.querySelectorAll('.calc-btn').forEach(b => {
                b.className = 'calc-btn p-4 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-left transition-all flex flex-col';
                const spans = b.querySelectorAll('span');
                if (spans.length >= 3) {
                    spans[0].className = 'font-bold text-slate-800 text-sm sm:text-base';
                    spans[1].className = 'text-xs text-slate-600 mt-1';
                    spans[2].className = 'text-xs text-slate-500 font-semibold mt-2 font-mono';
                }
            });
            const active = document.getElementById('calc-model-' + m);
            if (active) {
                active.className = 'calc-btn active p-4 rounded-xl border-2 border-blue-600 bg-blue-50/70 text-left transition-all flex flex-col shadow-sm';
                const spans = active.querySelectorAll('span');
                if (spans.length >= 3) {
                    spans[0].className = 'font-bold text-blue-950 text-sm sm:text-base';
                    spans[1].className = 'text-xs text-slate-700 font-medium mt-1';
                    spans[2].className = 'text-xs text-blue-700 font-bold mt-2 font-mono';
                }
            }
            recalculateRecipe();
        }

        function setCalcTrim(t) {
            calcState.trim = t;
            document.querySelectorAll('.calc-btn-trim').forEach(b => {
                b.className = 'calc-btn-trim py-2.5 px-3 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-xs sm:text-sm font-medium text-center text-slate-700';
            });
            const active = document.getElementById('calc-trim-' + t);
            if (active) {
                active.className = 'calc-btn-trim active py-2.5 px-3 rounded-lg border-2 border-blue-600 bg-blue-600 text-xs sm:text-sm font-semibold text-center text-white shadow-sm';
            }
            recalculateRecipe();
        }

        function setCalcSlim(s) {
            calcState.slim = s;
            document.querySelectorAll('.calc-btn-slim').forEach(b => {
                b.className = 'calc-btn-slim py-2.5 px-3 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-xs sm:text-sm font-medium text-center text-slate-700';
            });
            const active = document.getElementById('calc-slim-' + s);
            if (active) {
                active.className = 'calc-btn-slim active py-2.5 px-3 rounded-lg border-2 border-blue-600 bg-blue-600 text-xs sm:text-sm font-semibold text-center text-white shadow-sm';
            }
            recalculateRecipe();
        }

        function setCalcFT(f) {
            calcState.ft = f;
            document.querySelectorAll('.calc-btn-ft').forEach(b => {
                b.className = 'calc-btn-ft py-2.5 px-3 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-xs sm:text-sm font-medium text-center text-slate-700';
            });
            const active = document.getElementById('calc-ft-' + f);
            if (active) {
                active.className = 'calc-btn-ft active py-2.5 px-3 rounded-lg border-2 border-blue-600 bg-blue-600 text-xs sm:text-sm font-semibold text-center text-white shadow-sm';
            }
            recalculateRecipe();
        }

        function recalculateRecipe() {
            const meta = modelMeta[calcState.model];
            let vram = meta.baseVRAM;
            let active = meta.activeParams;
            let speedup = 1.0;
            let retention = 100.0;
            let command = '';

            // Precision scalar
            let precMult = 1.0;
            if (calcState.slim === 'int8') {
                precMult = 0.51;
                speedup *= 1.65;
                retention -= 0.6;
            } else if (calcState.slim === 'w4a16_awq') {
                precMult = 0.285;
                speedup *= 2.10;
                retention -= 1.2;
            } else if (calcState.slim === 'w4a16_gptq') {
                precMult = 0.285;
                speedup *= 2.05;
                retention -= 1.9;
            }

            // Trimming scalar
            let trimMult = 1.0;
            if (calcState.trim === 'exp_drop_6') {
                trimMult = (calcState.model === 'mixtral') ? 0.77 : 0.78;
                speedup *= 1.25;
                retention -= 2.5;
            } else if (calcState.trim === 'exp_drop_4') {
                trimMult = (calcState.model === 'mixtral') ? 0.54 : 0.56;
                speedup *= 1.55;
                retention -= 8.7;
            } else if (calcState.trim === 'layer_drop_4') {
                trimMult = 0.875;
                speedup *= 1.22;
                retention -= 3.2;
            }

            // Recovery FT impact
            if (calcState.ft === 'lora') {
                retention += (100.0 - retention) * 0.70;
            } else if (calcState.ft === 'full') {
                retention += (100.0 - retention) * 0.90;
            }

            vram = (meta.baseVRAM * precMult * trimMult).toFixed(1);
            if (retention > 100.0) retention = 100.0;
            const estMMLU = ((meta.baseMMLU * retention) / 100.0).toFixed(2);

            let hwText = '';
            if (vram <= 12) {
                hwText = 'Single RTX 3090 / 4090 (24GB VRAM) or A10G';
            } else if (vram <= 24) {
                hwText = 'Single RTX 4090 (24GB) or 1x A100 (40GB)';
            } else if (vram <= 48) {
                hwText = '2x RTX 4090 (24GB) or 1x A100 (80GB)';
            } else {
                hwText = '2x A100 (80GB) or 4x RTX 4090 (24GB)';
            }

            // Generate CLI command
            if (calcState.trim === 'none' && calcState.slim === 'fp16') {
                command = `bash scripts/compression/expert_drop/${calcState.model}_expert_drop.sh --model_path ${meta.hfPath} --preserve_n ${meta.expertsPerLayer} --save_path ./compressed_models/${calcState.model}_base`;
            } else if (calcState.trim.startsWith('exp_drop')) {
                const keepN = calcState.trim === 'exp_drop_6' ? (calcState.model === 'mixtral' ? 6 : 48) : (calcState.model === 'mixtral' ? 4 : 32);
                let cmd = `bash scripts/compression/expert_drop/${calcState.model}_expert_drop.sh --model_path ${meta.hfPath} --preserve_n ${keepN} --save_path ./compressed_models/${calcState.model}_trimmed`;
                if (calcState.slim.startsWith('w4a16')) {
                    cmd += `\\n\\n# Step 2: AWQ Quantization\\npython -m src.compression.quantize_awq --model_path ./compressed_models/${calcState.model}_trimmed --w_bit 4 --save_path ./compressed_models/${calcState.model}_unified`;
                }
                if (calcState.ft === 'lora') {
                    cmd += `\\n\\n# Step 3: LoRA Recovery Finetuning\\ndeepspeed scripts/finetuning/run_moe_finetune.py --model_path ./compressed_models/${calcState.model}_unified --lora_r 64 --max_steps 250`;
                }
                command = cmd;
            } else {
                command = `python -m src.compression.quantize_awq --model_path ${meta.hfPath} --w_bit 4 --save_path ./compressed_models/${calcState.model}_awq4b`;
            }

            document.getElementById('res-vram').innerText = vram;
            document.getElementById('res-speedup').innerText = speedup.toFixed(2);
            document.getElementById('res-retention').innerText = retention.toFixed(1);
            document.getElementById('res-mmlu-score').innerText = `${estMMLU} Est. MMLU (Base ${meta.baseMMLU})`;
            document.getElementById('res-hardware').innerText = hwText;
            document.getElementById('res-cli-cmd').innerText = command;
            
            const badge = document.getElementById('badge-recipe-rating');
            if (retention >= 97.0 && speedup >= 2.0) {
                badge.className = 'text-xs px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-300 font-bold';
                badge.innerText = 'Pareto Optimal';
            } else if (retention >= 95.0) {
                badge.className = 'text-xs px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-800 border border-blue-300 font-bold';
                badge.innerText = 'High Retention';
            } else {
                badge.className = 'text-xs px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-300 font-bold';
                badge.innerText = 'Aggressive Compression';
            }
        }

        // ----------------------------------------------------
        // Chart.js Visualizations Setup
        // ----------------------------------------------------
        let paretoChart, commChart, tasksChart;

        function initCharts() {
            // 1. Pareto Bubble Chart
            const ctxPareto = document.getElementById('paretoChartCanvas').getContext('2d');
            paretoChart = new Chart(ctxPareto, {
                type: 'bubble',
                data: {
                    datasets: [
                        {
                            label: 'Baseline (FP16)',
                            data: [{ x: 93.4, y: 70.6, r: 12 }],
                            backgroundColor: 'rgba(59, 130, 246, 0.8)',
                            borderColor: '#2563eb',
                            borderWidth: 2
                        },
                        {
                            label: 'Intra-Expert Slimming (AWQ / GPTQ)',
                            data: [
                                { x: 26.8, y: 69.8, r: 22 },
                                { x: 26.8, y: 69.3, r: 20 },
                                { x: 48.2, y: 70.2, r: 16 }
                            ],
                            backgroundColor: 'rgba(13, 148, 136, 0.8)',
                            borderColor: '#0d9488',
                            borderWidth: 2
                        },
                        {
                            label: 'Structural Trimming (Expert Drop)',
                            data: [
                                { x: 72.1, y: 68.9, r: 15 },
                                { x: 50.8, y: 64.5, r: 18 }
                            ],
                            backgroundColor: 'rgba(99, 102, 241, 0.8)',
                            borderColor: '#6366f1',
                            borderWidth: 2
                        },
                        {
                            label: 'Unified Synergy (Trimming + Slimming + FT)',
                            data: [
                                { x: 20.7, y: 69.4, r: 26 }
                            ],
                            backgroundColor: 'rgba(236, 72, 153, 0.85)',
                            borderColor: '#db2777',
                            borderWidth: 3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            title: { display: true, text: 'Model VRAM Footprint (GB) — Lower is better', color: '#334155', font: { weight: 'bold', size: 12 } },
                            grid: { color: 'rgba(226, 232, 240, 0.9)' },
                            ticks: { color: '#475569', font: { weight: '600' } }
                        },
                        y: {
                            title: { display: true, text: 'Average Downstream Accuracy (%) — Higher is better', color: '#334155', font: { weight: 'bold', size: 12 } },
                            grid: { color: 'rgba(226, 232, 240, 0.9)' },
                            ticks: { color: '#475569', font: { weight: '600' } },
                            min: 60,
                            max: 73
                        }
                    },
                    plugins: {
                        legend: {
                            labels: { color: '#1e293b', font: { weight: '600', size: 12 }, boxWidth: 14 }
                        },
                        tooltip: {
                            backgroundColor: '#0f172a',
                            titleColor: '#f8fafc',
                            bodyColor: '#f8fafc',
                            callbacks: {
                                label: function(context) {
                                    return `${context.dataset.label}: VRAM ${context.raw.x} GB, Acc ${context.raw.y}%`;
                                }
                            }
                        }
                    }
                }
            });

            // 2. Inter-GPU Comm Chart
            const ctxComm = document.getElementById('commChartCanvas').getContext('2d');
            commChart = new Chart(ctxComm, {
                type: 'bar',
                data: {
                    labels: ['Base Mixtral-8x7B', 'Layer Drop (-4L)', 'Expert Drop (6/8)', 'Expert Drop (4/8)', 'Unified Synergy'],
                    datasets: [
                        {
                            label: 'All-to-All Token Dispatch Volume (GB/s)',
                            data: [14.8, 12.9, 10.8, 8.2, 7.9],
                            backgroundColor: 'rgba(14, 165, 233, 0.85)',
                            borderColor: '#0284c7',
                            borderWidth: 1,
                            borderRadius: 6
                        },
                        {
                            label: 'Inter-Node Network Latency (ms/token)',
                            data: [42.5, 38.1, 31.4, 24.2, 23.5],
                            backgroundColor: 'rgba(168, 85, 247, 0.85)',
                            borderColor: '#9333ea',
                            borderWidth: 1,
                            borderRadius: 6
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            grid: { color: 'rgba(226, 232, 240, 0.8)' },
                            ticks: { color: '#475569', font: { weight: '600' } }
                        },
                        y: {
                            grid: { color: 'rgba(226, 232, 240, 0.8)' },
                            ticks: { color: '#475569', font: { weight: '600' } }
                        }
                    },
                    plugins: {
                        legend: {
                            labels: { color: '#1e293b', font: { weight: '600', size: 12 }, boxWidth: 14 }
                        }
                    }
                }
            });

            // 3. Multi-Task Chart
            const ctxTasks = document.getElementById('tasksChartCanvas').getContext('2d');
            tasksChart = new Chart(ctxTasks, {
                type: 'bar',
                data: {
                    labels: ['MMLU', 'GSM8K', 'ARC-Challenge', 'WinoGrande', 'HellaSwag'],
                    datasets: [
                        {
                            label: 'FP16 Baseline',
                            data: [70.6, 58.4, 66.8, 81.2, 84.5],
                            backgroundColor: 'rgba(59, 130, 246, 0.8)',
                            borderRadius: 6
                        },
                        {
                            label: 'W4A16 AWQ',
                            data: [69.8, 56.2, 65.4, 80.6, 83.9],
                            backgroundColor: 'rgba(13, 148, 136, 0.85)',
                            borderRadius: 6
                        },
                        {
                            label: 'W4A16 + Expert Drop 6/8 + LoRA',
                            data: [69.4, 55.7, 65.2, 80.4, 83.7],
                            backgroundColor: 'rgba(236, 72, 153, 0.85)',
                            borderRadius: 6
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            grid: { color: 'rgba(226, 232, 240, 0.8)' },
                            ticks: { color: '#475569', font: { weight: '600' } }
                        },
                        y: {
                            min: 40,
                            max: 90,
                            grid: { color: 'rgba(226, 232, 240, 0.8)' },
                            ticks: { color: '#475569', font: { weight: '600' } }
                        }
                    },
                    plugins: {
                        legend: {
                            labels: { color: '#1e293b', font: { weight: '600', size: 12 }, boxWidth: 14 }
                        }
                    }
                }
            });
        }

        function updateParetoData() {
            const m = document.getElementById('paretoModelFilter').value;
            if (m === 'deepseek') {
                paretoChart.data.datasets[0].data = [{ x: 32.8, y: 49.3, r: 12 }];
                paretoChart.data.datasets[1].data = [
                    { x: 9.4, y: 48.6, r: 24 },
                    { x: 9.4, y: 47.9, r: 22 },
                    { x: 17.2, y: 49.0, r: 16 }
                ];
                paretoChart.data.datasets[2].data = [
                    { x: 25.1, y: 47.8, r: 16 },
                    { x: 18.2, y: 44.1, r: 19 }
                ];
                paretoChart.data.datasets[3].data = [
                    { x: 7.2, y: 48.4, r: 28 }
                ];
                paretoChart.options.scales.y.min = 40;
                paretoChart.options.scales.y.max = 52;
            } else {
                paretoChart.data.datasets[0].data = [{ x: 93.4, y: 70.6, r: 12 }];
                paretoChart.data.datasets[1].data = [
                    { x: 26.8, y: 69.8, r: 22 },
                    { x: 26.8, y: 69.3, r: 20 },
                    { x: 48.2, y: 70.2, r: 16 }
                ];
                paretoChart.data.datasets[2].data = [
                    { x: 72.1, y: 68.9, r: 15 },
                    { x: 50.8, y: 64.5, r: 18 }
                ];
                paretoChart.data.datasets[3].data = [
                    { x: 20.7, y: 69.4, r: 26 }
                ];
                paretoChart.options.scales.y.min = 60;
                paretoChart.options.scales.y.max = 73;
            }
            paretoChart.update();
        }

        function updateTaskChartData() {
            const tech = document.getElementById('taskTechniqueFilter').value;
            if (tech === 'quant') {
                tasksChart.data.datasets[1].label = 'AWQ 4-bit';
                tasksChart.data.datasets[1].data = [69.8, 56.2, 65.4, 80.6, 83.9];
                tasksChart.data.datasets[2].label = 'GPTQ 4-bit';
                tasksChart.data.datasets[2].data = [69.3, 55.8, 65.1, 79.8, 83.4];
            } else if (tech === 'trim') {
                tasksChart.data.datasets[1].label = 'Expert Drop (6/8)';
                tasksChart.data.datasets[1].data = [68.9, 54.3, 64.2, 79.5, 82.8];
                tasksChart.data.datasets[2].label = 'Layer Drop (-4L)';
                tasksChart.data.datasets[2].data = [68.4, 53.9, 63.8, 78.9, 82.1];
            } else {
                tasksChart.data.datasets[1].label = 'W4A16 AWQ';
                tasksChart.data.datasets[1].data = [69.8, 56.2, 65.4, 80.6, 83.9];
                tasksChart.data.datasets[2].label = 'W4A16 + ExpDrop 6/8 + LoRA';
                tasksChart.data.datasets[2].data = [69.4, 55.7, 65.2, 80.4, 83.7];
            }
            tasksChart.update();
        }
        
        """

html = re.sub(old_js_block, new_js_block, html, flags=re.DOTALL)

with open('docs/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('Successfully refactored Unified-MoE-Compression docs/index.html & index.html')
