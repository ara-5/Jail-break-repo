from __future__ import annotations

from ..presets import get_preset, list_presets
from .registry import ToolContext, ToolRegistry


async def _preset(args: dict, ctx: ToolContext) -> str:
    action = str(args.get("action", "list")).lower()
    if action == "list":
        return "Available seed templates (use action='get'):\n" + "\n".join(
            f"  {p.name:16} {p.description}" for p in list_presets()
        )
    name = args.get("name", "")
    if not name:
        return "Error: 'name' is required for action='get'"
    p = get_preset(name)
    if p is None:
        names = ", ".join(x.name for x in list_presets())
        return f"No preset '{name}'. Available: {names}"
    return f"# {p.name}: {p.description}\n{p.template}"


def register(registry: ToolRegistry) -> None:
    registry.add(
        name="preset",
        description=(
            "Pull a curated, battle-tested jailbreak seed TEMPLATE (each has a {request} "
            "placeholder). action='list' shows the archetypes (dan, refusal_suppress, "
            "dev_mode, expert_sim, fiction, opposite, payload_split); action='get' with "
            "a name returns the template. Feed the result straight into optimize_universal "
            "as the seed, or fill {request} and fire it. Faster than hand-writing a wrapper."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "get"]},
                "name": {"type": "string", "description": "Preset name for action='get'"},
            },
        },
        handler=_preset,
    )
