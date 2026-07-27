import { useEffect, useMemo, useState } from "react";
import { api, type Preset, type Transform, type Tool } from "../api";

type Kind = "presets" | "transforms" | "tools";

export function Arsenal() {
  const [kind, setKind] = useState<Kind>("presets");
  const [presets, setPresets] = useState<Preset[]>([]);
  const [transforms, setTransforms] = useState<Transform[]>([]);
  const [tools, setTools] = useState<Tool[]>([]);
  const [q, setQ] = useState("");

  useEffect(() => {
    api.presets().then(setPresets).catch(() => {});
    api.transforms().then(setTransforms).catch(() => {});
    api.tools().then(setTools).catch(() => {});
  }, []);

  const rows = useMemo(() => {
    const src =
      kind === "presets" ? presets.map((p) => ({ name: p.name, desc: p.description, tag: "" }))
      : kind === "transforms" ? transforms.map((t) => ({ name: t.name, desc: t.description, tag: t.lossy ? "lossy" : t.reversible ? "reversible" : "one-way" }))
      : tools.map((t) => ({ name: t.name, desc: t.description, tag: "" }));
    const needle = q.toLowerCase();
    return src.filter((r) => !needle || r.name.toLowerCase().includes(needle) || r.desc.toLowerCase().includes(needle));
  }, [kind, q, presets, transforms, tools]);

  const counts = { presets: presets.length, transforms: transforms.length, tools: tools.length };

  return (
    <div className="card">
      <div className="section-title" style={{ gap: 16 }}>
        {(["presets", "transforms", "tools"] as Kind[]).map((k) => (
          <span key={k} className={`chip ${kind === k ? "on" : ""}`} onClick={() => setKind(k)}>
            {k} ({counts[k]})
          </span>
        ))}
        <div className="rule" />
      </div>
      <input className="search" type="text" placeholder={`search ${kind}…`} value={q} onChange={(e) => setQ(e.target.value)} />
      <table>
        <thead><tr><th>Name</th>{kind === "transforms" && <th>Type</th>}<th>Description</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.name}>
              <td className="mono" style={{ color: "var(--accent)" }}>{r.name}</td>
              {kind === "transforms" && <td className="mono muted">{r.tag}</td>}
              <td className="muted">{r.desc}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {!rows.length && <div className="empty">No matches.</div>}
    </div>
  );
}
