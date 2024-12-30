import pytest
from typesense_exporter import parse_nodes_from_str


@pytest.mark.parametrize("test_input,expected,protocol,description", [
    (
        "localhost:8108",
        [{"host": "localhost", "port": "8108", "protocol": "https"}],
        "https",
        "single node with port"
    ),
    (
        "host1:8108,host2:8108",
        [
            {"host": "host1", "port": "8108", "protocol": "https"},
            {"host": "host2", "port": "8108", "protocol": "https"}
        ],
        "https",
        "multiple nodes"
    ),
    (
        "localhost",
        [{"host": "localhost", "port": "8108", "protocol": "https"}],
        "https",
        "default port"
    ),
    (
        "localhost:8108",
        [{"host": "localhost", "port": "8108", "protocol": "http"}],
        "http",
        "custom protocol"
    ),
])
def test_parse_nodes_from_str(test_input, expected, protocol, description):
    nodes = parse_nodes_from_str(test_input, default_protocol=protocol)
    assert len(nodes) == len(expected)
    assert nodes == expected
