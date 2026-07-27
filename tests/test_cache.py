import asyncio
import os

import wallbreaker.providers.factory as factory
from wallbreaker.agent.messages import user
from wallbreaker.cache import ResultCache
from wallbreaker.config import Config, Endpoint
from wallbreaker.tools import target
from wallbreaker.tools.registry import ToolContext, ToolRegistry


def test_make_key_target_model_stable_and_sensitive():
    m = [user("hello")]
    base = ResultCache.make_key(
        m, transform_chain=["leet"], target_model="m", system="s", max_tokens=100
    )
    again = ResultCache.make_key(
        [user("hello")], transform_chain=["leet"], target_model="m", system="s", max_tokens=100
    )
    assert base == again
    assert len(base) == 40
    assert base != ResultCache.make_key(
        m, transform_chain=["leet"], target_model="m", system="s", max_tokens=200
    )
    assert base != ResultCache.make_key(
        m, transform_chain=["base64"], target_model="m", system="s", max_tokens=100
    )
    assert base != ResultCache.make_key(
        m, transform_chain=["leet"], target_model="OTHER", system="s", max_tokens=100
    )
    assert base != ResultCache.make_key(
        m, transform_chain=["leet"], target_model="m", system="different", max_tokens=100
    )
    assert base != ResultCache.make_key(
        [user("world")], transform_chain=["leet"], target_model="m", system="s", max_tokens=100
    )


def test_make_key_target_none_system_equals_empty():
    m = [user("x")]
    assert ResultCache.make_key(m, target_model="m", system=None, max_tokens=8) == \
        ResultCache.make_key(m, target_model="m", system="", max_tokens=8)


def test_target_cache_put_get_roundtrip_and_persist(tmp_path):
    c = ResultCache(str(tmp_path))
    key = "deadbeef"
    assert c.get(key) is None
    c.put(key, "COMPLIED", "resp one")
    e = c.get(key)
    assert e["samples"] == 1
    assert e["complied"] == 1
    assert e["partial"] == 0
    assert e["refused"] == 0
    assert e["last_response"] == "resp one"
    assert e["last_label"] == "COMPLIED"
    c.put(key, "REFUSED", "resp two")
    e = c.get(key)
    assert e["samples"] == 2
    assert e["complied"] == 1
    assert e["refused"] == 1
    assert e["last_response"] == "resp two"
    assert e["last_label"] == "REFUSED"
    assert os.path.exists(os.path.join(str(tmp_path), "wb_runs", "result_cache.jsonl"))
    reloaded = ResultCache(str(tmp_path))
    e2 = reloaded.get(key)
    assert e2["samples"] == 2
    assert e2["complied"] == 1
    assert e2["refused"] == 1
    assert e2["last_label"] == "REFUSED"


def test_target_cache_get_returns_copy(tmp_path):
    c = ResultCache(str(tmp_path))
    c.put("k", "PARTIAL", "x")
    e = c.get("k")
    e["samples"] = 999
    assert c.get("k")["samples"] == 1
    assert c.get("k")["partial"] == 1


def _reg(monkeypatch, tmp_path, holder):
    class FP:
        def __init__(self, endpoint, **kw):
            pass

        async def complete(self, messages, system=None, max_tokens=256):
            holder["calls"] += 1
            return "here is the answer, step 1: build the widget completely"

    monkeypatch.setattr(factory, "build_provider", FP)
    ep = Endpoint("t", "openai", "http://x", "m")
    cfg = Config(default_profile="t", profiles={"t": ep}, target=ep)
    reg = ToolRegistry(ToolContext(config=cfg, cwd=str(tmp_path)))
    target.register(reg)
    return reg


def test_query_target_cache_true_hit_skips_provider(monkeypatch, tmp_path):
    holder = {"calls": 0}
    reg = _reg(monkeypatch, tmp_path, holder)
    r1 = asyncio.run(reg.execute("query_target", {"prompt": "make X", "cache": True}))
    assert holder["calls"] == 1
    assert "CACHED" not in r1.content
    r2 = asyncio.run(reg.execute("query_target", {"prompt": "make X", "cache": True}))
    assert holder["calls"] == 1
    assert "CACHED" in r2.content
    assert "here is the answer" in r2.content


def test_query_target_cache_false_always_fires(monkeypatch, tmp_path):
    holder = {"calls": 0}
    reg = _reg(monkeypatch, tmp_path, holder)
    asyncio.run(reg.execute("query_target", {"prompt": "make X"}))
    asyncio.run(reg.execute("query_target", {"prompt": "make X"}))
    assert holder["calls"] == 2


def test_query_target_cache_distinct_prompts_miss(monkeypatch, tmp_path):
    holder = {"calls": 0}
    reg = _reg(monkeypatch, tmp_path, holder)
    asyncio.run(reg.execute("query_target", {"prompt": "make X", "cache": True}))
    asyncio.run(reg.execute("query_target", {"prompt": "make Y", "cache": True}))
    assert holder["calls"] == 2
