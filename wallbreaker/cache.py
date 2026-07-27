from __future__ import annotations

import hashlib
import json
import os


def _serialize_messages(messages) -> list:
    out = []
    for m in messages or []:
        role = getattr(m, "role", None)
        text_fn = getattr(m, "text", None)
        if role is not None and callable(text_fn):
            try:
                text = text_fn()
            except Exception:
                text = ""
            out.append([str(role), str(text)])
        elif isinstance(m, dict):
            out.append([str(m.get("role", "")), str(m.get("content", ""))])
        else:
            out.append(["", str(m)])
    return out


def _norm_label(label) -> str:
    low = str(label or "").strip().lower()
    if low.startswith("compl"):
        return "complied"
    if low.startswith("part"):
        return "partial"
    return "refused"


def _blank() -> dict:
    return {
        "samples": 0,
        "complied": 0,
        "partial": 0,
        "refused": 0,
        "last_response": "",
        "last_label": "",
    }


class ResultCache:
    """Read-through verdict cache for repeated target fires.

    Keyed by sha1 of the serialized request (messages, transform chain, target
    model, system prompt, max_tokens). Persists every put as one JSONL line under
    cwd/wb_runs/result_cache.jsonl and keeps an in-memory index; a fresh instance
    replays the file so the cache survives across calls and sessions.
    """

    FILENAME = "result_cache.jsonl"

    def __init__(self, cwd: str = "."):
        self.cwd = cwd or "."
        outdir = os.path.join(os.path.abspath(self.cwd), "wb_runs")
        self.path = os.path.join(outdir, self.FILENAME)
        self._index: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except (ValueError, TypeError):
                        continue
                    key = rec.get("key")
                    if not key:
                        continue
                    entry = _blank()
                    for field in ("samples", "complied", "partial", "refused"):
                        entry[field] = int(rec.get(field, 0) or 0)
                    entry["last_response"] = str(rec.get("last_response", "") or "")
                    entry["last_label"] = str(rec.get("last_label", "") or "")
                    self._index[key] = entry
        except OSError:
            pass

    @staticmethod
    def make_key(
        messages,
        transform_chain=None,
        target_model: str = "",
        system=None,
        max_tokens: int = 0,
    ) -> str:
        payload = {
            "messages": _serialize_messages(messages),
            "transform_chain": [str(t) for t in (transform_chain or [])],
            "target_model": str(target_model or ""),
            "system": "" if system is None else str(system),
            "max_tokens": int(max_tokens or 0),
        }
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha1(blob.encode("utf-8")).hexdigest()

    def get(self, key: str):
        entry = self._index.get(key)
        return dict(entry) if entry is not None else None

    def put(self, key: str, label: str, response: str) -> dict:
        entry = self._index.get(key) or _blank()
        entry["samples"] = int(entry.get("samples", 0)) + 1
        bucket = _norm_label(label)
        entry[bucket] = int(entry.get(bucket, 0)) + 1
        entry["last_response"] = response or ""
        entry["last_label"] = str(label or "")
        self._index[key] = entry
        self._append(key, entry)
        return dict(entry)

    def _append(self, key: str, entry: dict) -> None:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            rec = {"key": key, **entry}
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except OSError:
            pass
