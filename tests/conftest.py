import pytest
from typesense_exporter import TypesenseCollector


@pytest.fixture
def response_metrics_json():
    yield {
        "system_cpu1_active_percentage": "9.09",
        "system_cpu2_active_percentage": "0.00",
        "system_cpu3_active_percentage": "0.00",
        "system_cpu4_active_percentage": "0.00",
        "system_cpu_active_percentage": "0.00",
        "system_disk_total_bytes": "102888095744",
        "system_disk_used_bytes": "4177268736",
        "system_memory_total_bytes": "16764186624",
        "system_memory_total_swap_bytes": "0",
        "system_memory_used_bytes": "3234148352",
        "system_memory_used_swap_bytes": "0",
        "system_network_received_bytes": "6534814741",
        "system_network_sent_bytes": "4613106962",
        "typesense_memory_active_bytes": "51126272",
        "typesense_memory_allocated_bytes": "43065104",
        "typesense_memory_fragmentation_ratio": "0.16",
        "typesense_memory_mapped_bytes": "97370112",
        "typesense_memory_metadata_bytes": "9009280",
        "typesense_memory_resident_bytes": "51126272",
        "typesense_memory_retained_bytes": "30556160",
    }


@pytest.fixture
def response_stats_json():
    yield {
        "delete_latency_ms": 0,
        "delete_requests_per_second": 0,
        "import_latency_ms": 0,
        "import_requests_per_second": 0,
        "latency_ms": {"GET /health": 0.0, "GET /status": 0.0},
        "overloaded_requests_per_second": 0,
        "pending_write_batches": 0,
        "requests_per_second": {"GET /health": 1.5, "GET /status": 0.6},
        "search_latency_ms": 0,
        "search_requests_per_second": 0,
        "total_requests_per_second": 2.1,
        "write_latency_ms": 0,
        "write_requests_per_second": 0,
    }


@pytest.fixture
def response_debug_json():
    yield {"state": 1, "version": "0.24.0"}


@pytest.fixture
def response_collections_json():
    yield [
        {"name": "products", "num_documents": 100},
        {"name": "users", "num_documents": 50},
    ]


@pytest.fixture(autouse=True)
def mock_typesense_api(
    requests_mock,
    response_metrics_json,
    response_stats_json,
    response_debug_json,
    response_collections_json,
):
    base_url = "http://localhost:8108"

    requests_mock.get(f"{base_url}/metrics.json", json=response_metrics_json)
    requests_mock.get(f"{base_url}/stats.json", json=response_stats_json)
    requests_mock.get(f"{base_url}/debug", json=response_debug_json)
    requests_mock.get(f"{base_url}/collections", json=response_collections_json)

    yield requests_mock


@pytest.fixture
def typesense_collector():
    return TypesenseCollector(
        typesense_api_key="123",
        metrics_url="http://localhost:8108/metrics.json",
        stats_url="http://localhost:8108/stats.json",
        debug_url="http://localhost:8108/debug",
        nodes=[{"host": "localhost", "port": "8108", "protocol": "http"}],
    )
