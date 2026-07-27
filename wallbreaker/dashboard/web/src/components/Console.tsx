import { useEffect, useState } from "react";
import { api, verdictKind, type Preset, type Transform, type FireResult } from "../api";

export function Console({ hasTarget }: { hasTarget: boolean }) {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [transforms, setTransforms] = useState<Transform[]>([]);
  const [request, setRequest] = useState("");
  const [preset, setPreset] = useState("");
  const [system, setSystem] = useState("");
  const [picked, setPicked] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<FireResult | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.presets().then(setPresets).catch(() => {});
    api.transforms().then(setTransforms).catch(() => {});
  }, []);

  function toggle(name: string) {
    setPicked((p) => (p.includes(name) ? p.filter((x) => x !== name) : [...p, name]));
  }

  async function fire() {
    setBusy(true); setErr(""); setRes(null);
    try {
      const out = await api.fire({
        request,
        preset: preset || undefined,
        system: system || undefined,
        transforms: picked.length ? picked : undefined,
      });
      setRes(out);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="console-grid">
      <div className="card">
        <h3>Compose attack</h3>
        {!hasTarget && <div className="err">No [target] configured in config.toml — firing is disabled.</div>}
        <label className="fld">Request</label>
        <textarea rows={5} value={request} placeholder="the harmful ask to test…" onChange={(e) => setRequest(e.target.value)} />
        <label className="fld">Preset (wraps the request)</label>
        <select value={preset} onChange={(e) => setPreset(e.target.value)}>
          <option value="">— none (send raw) —</option>
          {presets.map((p) => <option key={p.name} value={p.name}>{p.name} — {p.description.slice(0, 60)}</option>)}
        </select>
        <label className="fld">Encoding transforms ({picked.length} on)</label>
        <div className="chips">
          {transforms.map((t) => (
            <span key={t.name} className={`chip ${picked.includes(t.name) ? "on" : ""}`} title={t.description} onClick={() => toggle(t.name)}>
              {t.name}
            </span>
          ))}
        </div>
        <label className="fld">System prompt (optional)</label>
        <textarea rows={2} value={system} placeholder="optional target system prompt…" onChange={(e) => setSystem(e.target.value)} />
        <button className="fire" disabled={busy || !hasTarget || !request.trim()} onClick={fire}>
          {busy ? "FIRING…" : "▸ FIRE AT TARGET"}
        </button>
      </div>

      <div className="card">
        <h3>Response{res?.verdict ? <span className={`badge ${verdictKind(res.verdict)}`} style={{ marginLeft: 10 }}>{res.verdict}</span> : null}</h3>
        {err && <div className="err">{err}</div>}
        {!res && !err && <div className="empty">Fire a payload to see the target's reply and verdict.</div>}
        {res && (
          <div className="resp">
            <div className="pl">payload sent ({res.prompt.length} chars):{"\n"}{res.prompt.slice(0, 600)}{res.prompt.length > 600 ? "…" : ""}</div>
            {res.content}
          </div>
        )}
      </div>
    </div>
  );
}
