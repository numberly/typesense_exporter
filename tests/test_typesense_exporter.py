import pytest
from typesense_exporter import parse_nodes_from_str


@pytest.mark.parametrize(
    "test_input,expected,protocol,description",
    [
        (
            "localhost:8108",
            [{"host": "localhost", "port": "8108", "protocol": "https"}],
            "https",
            "single node with port",
        ),
        (
            "host1:8108,host2:8108",
            [
                {"host": "host1", "port": "8108", "protocol": "https"},
                {"host": "host2", "port": "8108", "protocol": "https"},
            ],
            "https",
            "multiple nodes",
        ),
        (
            "localhost",
            [{"host": "localhost", "port": "8108", "protocol": "https"}],
            "https",
            "default port",
        ),
        (
            "localhost:8108",
            [{"host": "localhost", "port": "8108", "protocol": "http"}],
            "http",
            "custom protocol",
        ),
    ],
)
def test_parse_nodes_from_str(test_input, expected, protocol, description):
    nodes = parse_nodes_from_str(test_input, default_protocol=protocol)
    assert len(nodes) == len(expected)
    assert nodes == expected


def test_typesense_collector_metrics(typesense_collector):
    metrics = list(typesense_collector._collect_metrics_json())
    assert len(metrics) == 20


def test_typesense_collector_stats(typesense_collector):
    metrics = list(typesense_collector._collect_stats_json())
    assert len(metrics) == 13


def test_typesense_collector_json(typesense_collector):
    metrics = list(typesense_collector._collect_debug_json())
    assert len(metrics) == 1


def test_typesense_collector_collections(typesense_collector):
    metrics = list(typesense_collector._collect_collections())
    assert len(metrics) == 1

    metric_family = metrics[0]
    assert metric_family.name == "typesense_collection_documents"
    assert (
        metric_family.documentation
        == "Number of documents in each Typesense collection"
    )

    assert len(metric_family.samples) == 2

    sample_1 = metric_family.samples[0]
    sample_2 = metric_family.samples[1]

    assert sample_1.name == "typesense_collection_documents"
    assert sample_1.labels == {"collection_name": "products"}
    assert sample_1.value == 100.0

    assert sample_2.name == "typesense_collection_documents"
    assert sample_2.labels == {"collection_name": "users"}
    assert sample_2.value == 50.0
