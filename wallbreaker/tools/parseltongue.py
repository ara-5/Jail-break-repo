from __future__ import annotations

import sys

from ..transforms import (
    TRANSFORMS,
    apply_chain,
    list_transforms,
    reverse_chain,
)
from ..transforms import bijection as _bij
from ..transforms import structural as _struct
from .registry import ToolContext, ToolRegistry


def _catalog_names() -> str:
    return ", ".join(t.name for t in list_transforms())


def _catalog_full() -> str:
    lines = [f"{len(list_transforms())} transforms (chain them left-to-right):"]
    for t in list_transforms():
        flags = []
        if t.reversible:
            flags.append("reversible")
        else:
            flags.append("one-way")
        if t.lossy:
            flags.append("lossy")
        lines.append(f"  {t.name:14} [{', '.join(flags)}] {t.description}")
    lines.append("")
    lines.append("Frames: frame='bijection' wraps output with a decode-key preamble; "
                 "frame='split' breaks it into concatenated variables.")
    lines.append("Set decode=true to reverse a reversible chain.")
    return "\n".join(lines)


async def _catalog_tool(args: dict, ctx: ToolContext) -> str:
    return _catalog_full()


async def _parseltongue(args: dict, ctx: ToolContext) -> str:
    text = args.get("text", "")
    if not text:
        return "Error: 'text' is required"
    chain = args.get("transforms", []) or []
    if isinstance(chain, str):
        chain = [c for c in chain.split(",") if c.strip()]
    decode = bool(args.get("decode", False))
    frame = args.get("frame", "none")

    unknown = [c for c in chain if c.strip() not in TRANSFORMS]
    if unknown:
        return f"Error: unknown transform(s): {', '.join(unknown)}. Available: {', '.join(TRANSFORMS)}"

    try:
        result = reverse_chain(text, chain) if decode else apply_chain(text, chain)
    except (KeyError, ValueError) as exc:
        return f"Error: {exc}"

    if frame == "bijection":
        seed = int(args.get("seed", 1337))
        return _bij.bijection_payload(result, seed)
    if frame == "split":
        parts = int(args.get("parts", 3))
        split_mode = str(args.get("split_mode", "char"))
        return _struct.payload_split(result, parts, split_mode)
    return result


def register(registry: ToolRegistry) -> None:
    registry.add(
        name="parseltongue",
        description=(
            "Obfuscate or encode text by applying a chain of Parseltongue transforms "
            "(left to right) to craft payloads that bypass keyword filters. Chain freely, "
            "e.g. ['leet','homoglyph','zero_width'] or ['base64'] then tell the target how "
            "to decode. Set decode=true to reverse a reversible chain. frame='bijection' "
            "wraps with a decode-key preamble; frame='split' splits into concatenated "
            "parts. Call parseltongue_catalog for the full option list with flags. "
            "Transforms: " + _catalog_names()
        ),
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Input text"},
                "transforms": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ordered transform names, e.g. ['leet','zero_width']",
                },
                "decode": {"type": "boolean", "description": "Reverse the chain"},
                "frame": {
                    "type": "string",
                    "enum": ["none", "bijection", "split"],
                    "description": "Optional attack framing wrapper",
                },
                "parts": {"type": "integer", "description": "Chunks for frame='split'"},
                "split_mode": {
                    "type": "string",
                    "enum": ["char", "word", "sentence", "line"],
                    "description": "Splitting strategy for frame='split'",
                },
                "seed": {"type": "integer", "description": "Seed for frame='bijection'"},
            },
            "required": ["text", "transforms"],
        },
        handler=_parseltongue,
    )
    registry.add(
        name="parseltongue_catalog",
        description=(
            "List every Parseltongue transform with its reversibility and lossy flags, "
            "plus the available frames. Call this to see all obfuscation options before "
            "building a chain."
        ),
        parameters={"type": "object", "properties": {}},
        handler=_catalog_tool,
    )


def run_chain_cli(args) -> int:
    chain = [c for c in args.transforms.split(",") if c.strip()]
    text = args.text
    if text is None:
        text = sys.stdin.read()
    unknown = [c for c in chain if c not in TRANSFORMS]
    if unknown:
        print(f"Unknown transform(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"Available: {', '.join(TRANSFORMS)}", file=sys.stderr)
        return 1
    try:
        result = reverse_chain(text, chain) if args.decode else apply_chain(text, chain)
    except (KeyError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(result)
    if not result.endswith("\n"):
        sys.stdout.write("\n")
    return 0
