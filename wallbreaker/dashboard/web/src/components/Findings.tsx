import { useEffect, useState } from "react";
import { api, verdictKind, type Finding } from "../api";

export function Findings() {
  const [rows, setRows] = useState<Finding[] | null>(null);

  useEffect(() => { api.findings().then(setRows).catch(() => setRows([])); }, []);

  if (!rows) return <div className="empty">Loading…</div>;
  if (!rows.length) return <div className="empty">No bypasses (COMPLIED / PARTIAL) in the latest run log.</div>;

  return (
    <div className="card">
      <div className="section-title"><h2>{rows.length} finding{rows.length === 1 ? "" : "s"}</h2><div className="rule" /></div>
      <table>
        <thead>
          <tr><th>Verdict</th><th>Technique</th><th>Category</th><th>Payload</th><th>Reason</th></tr>
        </thead>
        <tbody>
          {rows.map((f, i) => (
            <tr key={i}>
              <td><span className={`badge ${verdictKind(f.label)}`}>{f.label}</span></td>
              <td className="mono">{f.technique ?? "manual"}</td>
              <td className="mono muted">{f.category ?? "—"}</td>
              <td className="mono clip" title={f.payload}>{(f.payload ?? "").replace(/\n/g, " ")}</td>
              <td className="muted clip" title={f.reason}>{f.reason ?? ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
