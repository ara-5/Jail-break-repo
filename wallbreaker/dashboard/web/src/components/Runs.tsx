import { useEffect, useState } from "react";
import { api, verdictKind, type RunSummary } from "../api";

function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function Runs() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [records, setRecords] = useState<Record<string, unknown>[]>([]);

  useEffect(() => { api.runs().then(setRuns).catch(() => setRuns([])); }, []);

  useEffect(() => {
    if (!open) return;
    api.run(open).then((r) => setRecords(r.records)).catch(() => setRecords([]));
  }, [open]);

  if (!runs) return <div className="empty">Loading…</div>;
  if (!runs.length) return <div className="empty">No run logs in sessions/ yet.</div>;

  if (open) {
    return (
      <div className="card">
        <div className="section-title">
          <h2 className="mono">{open}</h2>
          <div className="rule" />
          <span className="chip" onClick={() => setOpen(null)}>← back</span>
        </div>
        <table>
          <thead><tr><th>#</th><th>kind</th><th>verdict</th><th>technique</th><th>detail</th></tr></thead>
          <tbody>
            {records.map((r, i) => {
              const label = (r.label as string) || "";
              const detail = (r.payload || r.reason || r.text || r.content || "") as string;
              return (
                <tr key={i}>
                  <td className="muted">{i + 1}</td>
                  <td className="mono muted">{(r.kind as string) || ""}</td>
                  <td>{label ? <span className={`badge ${verdictKind(label)}`}>{label}</span> : ""}</td>
                  <td className="mono">{(r.technique as string) || ""}</td>
                  <td className="mono clip" title={String(detail)}>{String(detail).replace(/\n/g, " ").slice(0, 200)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="section-title"><h2>{runs.length} run log{runs.length === 1 ? "" : "s"}</h2><div className="rule" /></div>
      <table>
        <thead><tr><th>Run</th><th>Records</th><th>Hits</th><th>Size</th></tr></thead>
        <tbody>
          {runs.map((r) => (
            <tr key={r.name} style={{ cursor: "pointer" }} onClick={() => setOpen(r.name)}>
              <td className="mono">{r.name}</td>
              <td className="mono">{r.records}</td>
              <td className="mono" style={{ color: r.hits ? "var(--bad)" : "var(--muted)" }}>{r.hits}</td>
              <td className="mono muted">{fmtBytes(r.size)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
