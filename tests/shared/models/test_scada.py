from shared.models.scada import ScadaTagMetric


def test_scada_tag_metric_defaults():
    metric = ScadaTagMetric(source_id="scada1", source_type="scada", tag_name="Temp", node_id="ns=2;s=Temp")

    assert metric.scada_type == "unknown"
    assert metric.quality == "UNKNOWN"
    assert metric.value_float is None
    assert metric.reachable is True
