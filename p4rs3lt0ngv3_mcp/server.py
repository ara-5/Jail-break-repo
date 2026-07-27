from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from . import bridge, format

mcp = FastMCP("p4rs3lt0ngv3", log_level="WARNING")


def _err(exc: Exception) -> str:
    return f"[parsel error] {exc}"


@mcp.tool()
def parsel_list(category: str = "") -> str:
    """List the P4RS3LT0NGV3 transform catalog (222 transforms in 11 categories).

    This is the discovery entry point: call it first to see what is available, then use
    parsel_inspect for one transform's options, and parsel_transform / parsel_chain to apply.
    Pass an empty category for the full catalog, or one of: case, cipher, concealment,
    encoding, format, signwriting, special, symbol, technical, unicode, visual.
    Each row shows the transform KEY (use that with the other tools), its category, whether
    it can decode as well as encode, and its display name.
    """
    try:
        transforms = bridge.list_transforms()
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    cat = category.strip().lower()
    if cat:
        transforms = [t for t in transforms if t["category"].lower() == cat]
        if not transforms:
            return (
                f"No transforms in category '{category}'. Categories: "
                + ", ".join(bridge.categories())
            )
    return format.list_block(transforms, bridge.categories(), cat)


@mcp.tool()
def parsel_search(query: str) -> str:
    """Search the transform catalog by keyword (matches key, name, and category).

    Use when you want an obfuscation of a certain flavor but don't know the exact key,
    e.g. 'zero width', 'rune', 'emoji', 'base', 'morse', 'reverse'. Returns ranked matches;
    take the KEY from a row and pass it to parsel_transform / parsel_inspect.
    """
    try:
        hits = bridge.search(query)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return format.search_block(query, hits)


@mcp.tool()
def parsel_inspect(transform: str) -> str:
    """Inspect one transform: its category, whether it decodes, and its configurable options.

    `transform` is a key (e.g. 'caesar') or a loose name (e.g. 'Pig Latin', 'rot 13') — it is
    fuzzily resolved. Read the options here, then pass them as `options` to parsel_transform.
    Example: parsel_inspect('caesar') shows option 'shift' (number, default 3, 1-25).
    """
    try:
        key = bridge.resolve_key(transform)
        if not key:
            return f"Unknown transform '{transform}'. Use parsel_search or parsel_list."
        meta = bridge.inspect(key)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return format.inspect_block(meta)


@mcp.tool()
def parsel_transform(
    transform: str,
    text: str,
    action: str = "encode",
    options: dict[str, Any] | None = None,
) -> str:
    """Apply ONE transform to text. The core encoder/cipher/obfuscator tool.

    - transform: key or loose name (fuzzily resolved), e.g. 'base64', 'caesar', 'zalgo',
      'emoji_encoding', 'zerowidth_steganography', 'elder_futhark', 'morse_code'.
    - text: the input string.
    - action: 'encode' (default), 'decode' (reverse it; only for decodable transforms),
      or 'preview' (a short sample).
    - options: transform-specific settings from parsel_inspect, e.g. {"shift": 5} for caesar.
      Omit for defaults.
    Returns the transformed text. Example: parsel_transform('caesar','Attack at dawn',
    options={'shift':5}) -> 'Fyyfhp fy ifbs'.
    """
    try:
        key = bridge.resolve_key(transform)
        if not key:
            return f"Unknown transform '{transform}'. Use parsel_search or parsel_list."
        result = bridge.run_transform(action.strip().lower(), key, text, options)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return result["output"]


@mcp.tool()
def parsel_chain(
    text: str,
    steps: list[dict[str, Any]],
    decode: bool = False,
) -> str:
    """Apply an ordered CHAIN of transforms (left-to-right) to craft layered payloads.

    `steps` is a list, each item {"transform": <key-or-name>, "options": {...}} (options
    optional). Example to leetspeak then base64 then zero-width-hide:
      steps=[{"transform":"leetspeak"},{"transform":"base64"},
             {"transform":"zerowidth_steganography"}]
    Set decode=true to REVERSE a chain: steps are applied in reverse order with action=decode
    (every transform in the chain must be decodable). Returns the final text.
    Stack encodings to defeat keyword filters, then tell the target how to decode.
    """
    if not steps:
        return "[parsel error] 'steps' must contain at least one {transform, options}."
    try:
        ordered = list(reversed(steps)) if decode else steps
        action = "decode" if decode else "encode"
        out = text
        applied: list[str] = []
        for step in ordered:
            name = str(step.get("transform", "")).strip()
            if not name:
                return "[parsel error] each step needs a 'transform' key."
            key = bridge.resolve_key(name)
            if not key:
                return f"[parsel error] unknown transform '{name}' in chain."
            opts = step.get("options") if isinstance(step.get("options"), dict) else None
            out = bridge.run_transform(action, key, out, opts)["output"]
            applied.append(key)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    arrow = " <- " if decode else " -> "
    return f"[chain {arrow.join(applied)}]\n{out}"


@mcp.tool()
def parsel_decode(text: str) -> str:
    """Universal smart decoder: auto-detect the encoding of `text` and decode it.

    Use when you have obfuscated/encoded text and don't know the scheme. Returns the best
    guess (method + decoded text) plus a few ranked alternatives, since detection is
    heuristic. For a known scheme, prefer parsel_transform(action='decode').
    """
    try:
        result = bridge.auto_decode(text)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return format.decode_block(result)


@mcp.tool()
def parsel_guide() -> str:
    """How to use the P4RS3LT0NGV3 toolset. Call this once to orient yourself.

    Returns a short cheat-sheet: the available tools, the transform categories with counts,
    a worked chaining example, and notes on which features are headless vs browser-only.
    """
    try:
        cats = bridge.categories()
    except Exception as exc:  # noqa: BLE001
        return f"P4RS3LT0NGV3 catalog unavailable: {exc}"
    return format.guide_text(cats, native=False)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
