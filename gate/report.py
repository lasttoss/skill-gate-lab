"""Two outputs from the same numbers: a JSON document (for the console) and a
single self-contained HTML file (to send to a team lead, no server, no assets).
"""

import html
import json
import os

CSS = """
:root{--paper:#f5f5f5;--ink:#2d3142;--muted:#4f5d75;--soft:#7a8399;--accent:#eb6c36;--rule:#bfc0c0;--ok:#2f7d4f;--bad:#b23b3b}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:13px/1.55 Inter,system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1000px;margin:0 auto;padding:32px 20px 64px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:15px;margin:32px 0 10px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
.sub{color:var(--soft);margin:0 0 24px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.card{background:#fff;border:1px solid var(--rule);border-radius:8px;padding:12px}
.card b{display:block;font-size:20px;line-height:1.2}
.card span{color:var(--soft);font-size:11px;text-transform:uppercase;letter-spacing:.05em}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--rule);border-radius:8px;overflow:hidden}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid #e8e8e8;vertical-align:top}
th{background:#eceff3;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.05em}
td.num{font-variant-numeric:tabular-nums}
.pass{color:var(--ok);font-weight:600}.fail{color:var(--bad);font-weight:600}
code{background:#eceff3;border-radius:3px;padding:1px 4px;font-size:12px}
.detail{color:var(--muted);font-size:12px}
.empty{color:var(--soft);font-style:italic}
"""


def _esc(value) -> str:
    return html.escape(str(value), quote=True)


def _cards(summary: dict) -> str:
    items = [
        ("pass rate", f"{summary.get('pass_rate', 0)}%"),
        ("rows", summary.get("rows", 0)),
        ("cost", f"${summary.get('cost_usd', 0):.4f}"),
        ("p50", f"{summary.get('p50_ms', 0)} ms"),
        ("p95", f"{summary.get('p95_ms', 0)} ms"),
        ("stability", f"{summary.get('stability_pct', 0)}%"),
    ]
    return "<div class='cards'>" + "".join(
        f"<div class='card'><span>{_esc(a)}</span><b>{_esc(b)}</b></div>" for a, b in items
    ) + "</div>"


def _findings_table(findings: list, title: str) -> str:
    if not findings:
        return f"<h2>{_esc(title)}</h2><p class='empty'>No findings.</p>"
    rows = "".join(
        f"<tr><td>{_esc(f.get('skill') or f.get('workflow') or '')}</td>"
        f"<td>{_esc(f.get('step') or '')}</td>"
        f"<td><code>{_esc(f['code'])}</code></td>"
        f"<td class='detail'>{_esc(f['detail'])}</td></tr>"
        for f in findings
    )
    return (f"<h2>{_esc(title)}</h2><table><tr><th>unit</th><th>step</th>"
            f"<th>code</th><th>detail</th></tr>{rows}</table>")


def _steps_table(summary: dict) -> str:
    steps = summary.get("per_step", [])
    if not steps:
        return ""
    rows = "".join(
        f"<tr><td>{_esc(s['step_id'])}</td><td>{_esc(s['skill'])}</td>"
        f"<td class='num'>{s['passed']}</td>"
        f"<td class='num {'fail' if s['failed'] else ''}'>{s['failed']}</td>"
        f"<td class='num'>{s['pass_rate']}%</td>"
        f"<td class='num'>{s['p50_ms']}</td><td class='num'>{s['p95_ms']}</td>"
        f"<td class='detail'>{_esc(', '.join(f'{k}×{v}' for k, v in sorted(s['reasons'].items())) or '—')}</td></tr>"
        for s in steps
    )
    return ("<h2>Per step</h2><table><tr><th>step</th><th>skill</th><th>passed</th>"
            "<th>failed</th><th>pass</th><th>p50 ms</th><th>p95 ms</th><th>reasons</th></tr>"
            f"{rows}</table>")


def _failures_table(summary: dict) -> str:
    failures = summary.get("failures", [])
    if not failures:
        return "<h2>Failures</h2><p class='empty'>No failures.</p>"
    rows = "".join(
        f"<tr><td>{_esc(f['input_id'])}</td><td>{_esc(f['step_id'])}</td>"
        f"<td><code>{_esc(', '.join(f['reason_codes']))}</code></td>"
        f"<td class='detail'>{_esc(f['trace'])}</td></tr>"
        for f in failures[:20]
    )
    return ("<h2>Failures (first 20)</h2><table><tr><th>input</th><th>step</th>"
            f"<th>reasons</th><th>output</th></tr>{rows}</table>")


def to_json(tier1: dict, tier2: dict, summary: dict, baseline: dict) -> dict:
    return {
        "generated_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
        "tier1": {"skills": tier1["skills"], "findings": tier1["findings"], "passed": tier1["passed"]},
        "tier2": {"cases": tier2["cases"], "workflows": tier2["workflows"],
                  "rank1_rate": tier2["rank1_rate"], "findings": tier2["findings"],
                  "passed": tier2["passed"]},
        "tier3": summary,
        "baseline": baseline,
    }


def to_html(document: dict) -> str:
    tier1, tier2, summary = document["tier1"], document["tier2"], document["tier3"]
    baseline = document.get("baseline", {})
    gate_state = "PASS" if tier1["passed"] and tier2["passed"] else "FAIL"
    body = [
        "<h1>Skill gate report</h1>",
        f"<p class='sub'>generated {_esc(document['generated_at'])} · "
        f"tier 1 {'pass' if tier1['passed'] else 'fail'} · "
        f"tier 2 {'pass' if tier2['passed'] else 'fail'} · "
        f"routing rank-1 {tier2['rank1_rate']}% "
        f"(floor {baseline.get('rank1_floor', 'n/a')}) · gate {gate_state}</p>",
        _cards(summary),
        _steps_table(summary),
        _failures_table(summary),
        _findings_table(tier2["findings"], "Tier 2 — routing and wiring"),
        _findings_table(tier1["findings"], "Tier 1 — structure"),
    ]
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>Skill gate report</title><style>{CSS}</style></head>"
            f"<body><main>{''.join(body)}</main></body></html>")


def write(root: str, document: dict) -> tuple:
    out_dir = os.path.join(root, "out")
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "report.json")
    html_path = os.path.join(out_dir, "report.html")
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2, ensure_ascii=False)
    with open(html_path, "w", encoding="utf-8") as handle:
        handle.write(to_html(document))
    return json_path, html_path
