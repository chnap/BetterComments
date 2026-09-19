from __future__ import annotations

from conftest import plan_source


def test_generation_is_opt_in(tmp_path) -> None:
    source = "try:\n    load_plugin()\nexcept PluginError:\n    pass\n"
    normal = plan_source(tmp_path, "normal.py", source)
    generated = plan_source(tmp_path, "generated.py", source, generate=True)
    assert normal.updated == normal.original
    assert b"# Intentionally ignore PluginError.\n    pass" in generated.updated


def test_generation_skips_bare_except(tmp_path) -> None:
    source = "try:\n    run()\nexcept:\n    pass\n"
    plan = plan_source(tmp_path, "sample.py", source, generate=True)
    assert plan.updated == plan.original
