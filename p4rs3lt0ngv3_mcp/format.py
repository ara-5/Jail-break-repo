"""Presentation helpers for the P4RS3LT0NGV3 engine.

Single source of truth for how transforms, inspections, decoder results, and the
guide are rendered as text, so the native in-process tools
(`wallbreaker/tools/parsel_engine.py`) and the optional MCP server
(`p4rs3lt0ngv3_mcp/server.py`) emit identical output.

Every function takes plain data (dicts from `bridge`) and returns a string; nothing
here touches Node or the registry, so it imports cleanly with zero side effects.
"""

from __future__ import annotations

import json
from typing import Any

CATEGORIES = (
    "case", "cipher", "concealment", "encoding", "format",
    "signwriting", "special", "symbol", "technical", "unicode", "visual",
)


def transform_row(t: dict[str, Any]) -> str:
    flag = "decode+encode" if t.get("canDecode") else "encode-only "
    return f"  {t['key']:26} {t['category']:12} {flag}  {t['name']}"


def _cat_summary(categories: dict[str, int]) -> str:
    return ", ".join(f"{k}={v}" for k, v in categories.items())


def list_block(
    transforms: list[dict[str, Any]],
    categories: dict[str, int],
    category: str = "",
) -> str:
    cat = category.strip().lower()
    header = (
        f"{len(transforms)} transforms"
        + (f" in '{cat}'" if cat else f" (categories: {_cat_summary(categories)})")
        + ":"
    )
    return header + "\n" + "\n".join(transform_row(t) for t in transforms)


def search_block(query: str, hits: list[dict[str, Any]]) -> str:
    if not hits:
        return f"No transforms matched '{query}'. Try parsel_list to browse all 222."
    return f"{len(hits)} match(es) for '{query}':\n" + "\n".join(
        transform_row(t) for t in hits
    )


def inspect_block(meta: dict[str, Any]) -> str:
    lines = [
        f"{meta['key']}  ({meta['name']})",
        f"  category : {meta['category']}",
        f"  decodes  : {'yes' if meta.get('canDecode') else 'no (encode-only)'}",
    ]
    if meta.get("description"):
        lines.append(f"  about    : {meta['description']}")
    opts = meta.get("configurableOptions") or []
    if not opts:
        lines.append("  options  : none")
    else:
        lines.append("  options  :")
        for o in opts:
            bits = [f"type={o.get('type')}", f"default={o.get('default')!r}"]
            if o.get("min") is not None or o.get("max") is not None:
                bits.append(f"range={o.get('min')}..{o.get('max')}")
            if o.get("options"):
                choices = ", ".join(
                    str(c.get("value", c)) for c in o["options"] if isinstance(c, dict)
                ) or str(o["options"])
                bits.append(f"choices=[{choices}]")
            lines.append(f"    - {o['id']}: {o.get('label', '')}  ({', '.join(bits)})")
    defaults = meta.get("defaultOptions")
    if defaults:
        lines.append(f"  defaults : {json.dumps(defaults, ensure_ascii=False)}")
    return "\n".join(lines)


def decode_block(result: dict[str, Any] | None) -> str:
    if not result:
        return "No decoding matched. Try parsel_transform with an explicit transform+decode."
    lines = [f"best guess: {result.get('method')}", result.get("text", "")]
    alts = result.get("alternatives") or []
    if alts:
        lines.append("")
        lines.append("alternatives:")
        for a in alts[:8]:
            lines.append(f"  [{a.get('method')}] {str(a.get('text', ''))[:120]}")
    return "\n".join(lines)


def guide_text(categories: dict[str, int], native: bool = True) -> str:
    total = sum(categories.values()) if categories else 0
    cat_line = _cat_summary(categories) if categories else "(catalog unavailable)"
    craft_line = (
        "  parsel_craft ...         craft a ready-to-fire payload: encode a request\n"
        "                           through a chain + wrap it with a decode-and-comply\n"
        "                           preamble (or split it into concatenated variables)\n"
        if native else ""
    )
    return (
        "P4RS3LT0NGV3 - universal text transform / obfuscation engine.\n\n"
        f"{total} transforms across 11 categories: {cat_line}\n\n"
        "TOOLS\n"
        "  parsel_list [category]   browse the catalog (start here)\n"
        "  parsel_search <query>    find a transform by keyword\n"
        "  parsel_inspect <name>    one transform's options + decodability\n"
        "  parsel_transform ...     apply one transform (encode/decode/preview, +options)\n"
        "  parsel_chain ...         apply an ordered chain; decode=true reverses it\n"
        "  parsel_decode <text>     universal auto-decoder for unknown encodings\n"
        + craft_line +
        "\nWORKFLOW\n"
        "  1) parsel_list or parsel_search to pick transform KEYS.\n"
        "  2) parsel_inspect a key to learn its options.\n"
        "  3) parsel_transform for one layer, or parsel_chain to stack several.\n"
        "  4) parsel_craft to wrap the encoded trigger into a deliverable jailbreak.\n\n"
        "EXAMPLE (layered payload that dodges keyword filters)\n"
        "  parsel_chain(text='<your text>', steps=[\n"
        "     {'transform':'leetspeak'},\n"
        "     {'transform':'base64'},\n"
        "     {'transform':'zerowidth_steganography'}])\n"
        "  then instruct the target how to peel the layers (or use parsel_decode).\n\n"
        "NOTES\n"
        "  - Keys are fuzzily resolved, so 'rot 13' or 'Pig Latin' work too.\n"
        "  - Steganography (emoji_encoding, invisible_text, zerowidth_steganography,\n"
        "    whitespace_steganography) and every cipher/encoding are plain transforms.\n"
        "  - Upstream's browser-only AI tools (PromptCraft, AI translate, Anti-Classifier)\n"
        "    are covered by the harness's own model tools: mutate/pair/evolve_persona for\n"
        "    mutation, the 'neutralize' transform for term-softening, query_target to translate."
    )
