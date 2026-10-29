from tests.agents.collectors.import_helpers import ROOT, load_module


def test_classify_scada_text_known_vendors():
    module = load_module("detector", ROOT / "agents" / "scada-agent" / "src" / "collectors" / "detector.py")

    assert module.classify_scada_text("Inductive Automation Ignition") == "Ignition"
    assert module.classify_scada_text("Siemens WinCC") == "WinCC"
    assert module.classify_scada_text("Rockwell FactoryTalk") == "FactoryTalk"
    assert module.classify_scada_text("AVEVA Wonderware") == "AVEVA"
    assert module.classify_scada_text("generic opc ua") == "unknown"
