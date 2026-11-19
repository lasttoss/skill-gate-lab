import { useEffect, useState } from "react";

type Step = {
  step_id: string; skill: string; passed: number; failed: number;
  pass_rate: number; p50_ms: number; p95_ms: number; reasons: Record<string, number>;
};
type Document = {
  generated_at: string;
  tier1: { skills: number; passed: boolean; findings: Finding[] };
  tier2: { cases: number; workflows: number; rank1_rate: number; passed: boolean; findings: Finding[] };
  tier3: {
    rows: number; passed: number; failed: number; pass_rate: number; cost_usd: number;
    p50_ms: number; p95_ms: number; stability_pct: number; runs_per_input: number;
    model: string; per_step: Step[];
    failures?: { input_id: string; step_id: string; reason_codes: string[]; trace: string }[];
  };
  baseline: { rank1_floor: number };
};
type Finding = { skill?: string; workflow?: string; step?: string; code: string; detail: string };

function Card({ label, value }: { label: string; value: string | number }) {
  return <div className="card"><span>{label}</span><b>{value}</b></div>;
}

export default function App() {
  const [doc, setDoc] = useState<Document | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    fetch("report.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`)))
      .then(setDoc)
      .catch((e) => setError(`No report.json yet. Run: make smoke && cp out/report.json console/public/report.json (${e})`));
  }, []);

  if (error) return <main><h1>Skill gate console</h1><p className="empty">{error}</p></main>;
  if (!doc) return <main><h1>Skill gate console</h1><p className="empty">loading…</p></main>;

  const t3 = doc.tier3;
  return (
    <main>
      <h1>Skill gate console</h1>
      <p className="sub">
        generated {doc.generated_at} · tier 1 {doc.tier1.passed ? "pass" : "fail"} ·
        tier 2 {doc.tier2.passed ? "pass" : "fail"} · routing rank-1 {doc.tier2.rank1_rate}%
        (floor {doc.baseline.rank1_floor}%) · executor {t3.model}
      </p>

      <div className="cards">
        <Card label="pass rate" value={`${t3.pass_rate}%`} />
        <Card label="rows" value={t3.rows} />
        <Card label="cost" value={`$${t3.cost_usd.toFixed(6)}`} />
        <Card label="p50" value={`${t3.p50_ms} ms`} />
        <Card label="p95" value={`${t3.p95_ms} ms`} />
        <Card label="stability" value={`${t3.stability_pct}%`} />
      </div>

      <h2>Per step</h2>
      <table>
        <thead>
          <tr><th>step</th><th>skill</th><th>pass</th><th>failed</th><th>rate</th><th>p95</th><th>reasons</th></tr>
        </thead>
        <tbody>
          {t3.per_step.map((s) => (
            <tr key={s.step_id}>
              <td>{s.step_id}</td>
              <td>{s.skill}</td>
              <td>{s.passed}</td>
              <td className={s.failed ? "fail" : ""}>{s.failed}</td>
              <td>
                <div className="bar"><i style={{ width: `${s.pass_rate}%` }} /></div>
                {s.pass_rate}%
              </td>
              <td>{s.p95_ms} ms</td>
              <td>{Object.entries(s.reasons).map(([k, v]) => `${k}×${v}`).join(", ") || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Failures</h2>
      {t3.failures && t3.failures.length ? (
        <table>
          <thead><tr><th>input</th><th>step</th><th>reasons</th><th>output</th></tr></thead>
          <tbody>
            {t3.failures.slice(0, 20).map((f, i) => (
              <tr key={i}>
                <td>{f.input_id}</td><td>{f.step_id}</td>
                <td><code>{f.reason_codes.join(", ")}</code></td>
                <td>{f.trace}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : <p className="empty">No failures.</p>}

      <h2>Tier 2 — routing and wiring</h2>
      {doc.tier2.findings.length ? (
        <table>
          <thead><tr><th>unit</th><th>step</th><th>code</th><th>detail</th></tr></thead>
          <tbody>
            {doc.tier2.findings.map((f, i) => (
              <tr key={i}>
                <td>{f.skill || f.workflow}</td><td>{f.step || ""}</td>
                <td><code>{f.code}</code></td><td>{f.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : <p className="empty">No findings.</p>}
    </main>
  );
}
