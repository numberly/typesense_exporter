#!/usr/bin/env python3
"""
A Prometheus exporter that fetches metrics from a Typesense cluster
each time Prometheus scrapes the /metrics endpoint. This approach
ensures fresh metrics on every scrape, without running a separate
polling loop.

Usage:
  1. Install dependencies:
     pip install prometheus_client requests typesense
  2. Run this script, e.g.:
     ./typesense_exporter.py --port=8000
  3. Add a scrape config in Prometheus to target this exporter:
     scrape_configs:
       - job_name: "typesense_exporter"
         static_configs:
           - targets: ["localhost:8000"]
"""

import os
import argparse
import time
import requests
import typesense
from typing import Dict, List, TypedDict

from prometheus_client import start_http_server, REGISTRY
from prometheus_client.core import GaugeMetricFamily
class NodeConfigDict(TypedDict):
  host: str
  port: str
  protocol: str

def parse_nodes_from_str(
    nodes_str: str, default_protocol: str = "https"
) -> List[NodeConfigDict]:
    """
    Parse a comma-separated list of "host:port" strings into a list of node
    configuration dictionaries suitable for the Typesense Python client.

    Args:
        nodes_str (str):
            Comma-separated host:port pairs, e.g. "host1:8108,host2:8108".
        default_protocol (str, optional):
            The protocol to use for each node ("https", "http"). Defaults to "https".

    Returns:
        List[Dict[str, str]]:
            A list of node dictionaries, each containing "host", "port", and "protocol".
    """
    nodes_config: List[Dict[str, str]] = []
    raw_nodes = [entry.strip() for entry in nodes_str.split(",") if entry.strip()]
    for entry in raw_nodes:
        host, *port_list = entry.split(":", maxsplit=1)
        if port_list:
            port = port_list[0]  # Convert list to string
        else:
          port = "8108"
        nodes_config.append(
            {
                "host": host,
                "port": port,
                "protocol": default_protocol,
            }
        )
    return nodes_config


class TypesenseCollector:
    """
    A custom Prometheus collector that gathers metrics from a Typesense cluster
    upon each scrape of the /metrics endpoint. This ensures "live" data instead
    of relying on a background polling loop.
    """

    def __init__(
        self,
        typesense_api_key: str,
        metrics_url: str,
        stats_url: str,
        nodes: List[Dict[str, str]],
        verify_ssl: bool = True,
    ) -> None:
        """
        Initialize a TypesenseCollector instance.

        Args:
            typesense_api_key (str):
                Typesense API key for authentication against the cluster.
            metrics_url (str):
                The URL for retrieving /metrics.json from one of the Typesense nodes.
            stats_url (str):
                The URL for retrieving /stats.json from one of the Typesense nodes.
            nodes (List[Dict[str, str]]):
                A list of node configurations for the Typesense client.
            verify_ssl (bool, optional):
                Whether to verify SSL certificates. Defaults to True.
        """
        self.typesense_api_key = typesense_api_key
        self.metrics_url = metrics_url
        self.stats_url = stats_url
        self.verify_ssl = verify_ssl

        # Create a Typesense client to query collections, stats, etc.
        self.client = typesense.Client(
            {
                "api_key": self.typesense_api_key,
                "connection_timeout_seconds": 2,
                "nodes": nodes,
            }
        )

    def collect(self):
        """
        The main entry point for Prometheus to retrieve metrics. Prometheus
        calls this method on each scrape. We fetch from:
          - /metrics.json
          - /stats.json
          - The list of Typesense collections (for doc counts)
        and yield metric objects to the Prometheus registry.
        """
        yield from self._collect_metrics_json()
        yield from self._collect_stats_json()
        yield from self._collect_collections()

    def _collect_metrics_json(self):
        """
        Retrieve metrics from /metrics.json and yield numeric fields
        as GaugeMetricFamily objects.
        """
        try:
            resp = requests.get(
                self.metrics_url,
                headers={"X-TYPESENSE-API-KEY": self.typesense_api_key},
                verify=self.verify_ssl,
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            print(f"[ERROR] Could not fetch {self.metrics_url}: {exc}")
            return

        # Convert string values to float if possible and yield as gauges.
        for key, value in data.items():
            try:
                float_val = float(value)
            except (ValueError, TypeError):
                continue  # skip non-numeric fields

            metric_name = self._sanitize_metric_name(key)
            metric_help = f"Typesense metric: {key}"
            yield GaugeMetricFamily(metric_name, metric_help, value=float_val)

    def _collect_stats_json(self):
        """
        Retrieve metrics from /stats.json, including top-level numeric fields,
        nested latency_ms, and requests_per_second structures.
        """
        try:
            resp = requests.get(
                self.stats_url,
                headers={"X-TYPESENSE-API-KEY": self.typesense_api_key},
                verify=self.verify_ssl,
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            print(f"[ERROR] Could not fetch {self.stats_url}: {exc}")
            return

        # Handle top-level numeric fields
        for key, value in data.items():
            if isinstance(value, dict):
                continue  # we'll handle dict structures below
            try:
                float_val = float(value)
            except (ValueError, TypeError):
                continue
            metric_name = self._sanitize_metric_name(key)
            yield GaugeMetricFamily(
                metric_name, f"Typesense stats: {key}", value=float_val
            )

        # Handle latency_ms map => create a labeled metric
        latency_map = data.get("latency_ms", {})
        if isinstance(latency_map, dict):
            latency_metric = GaugeMetricFamily(
                "typesense_latency_ms",
                "Latency in milliseconds by endpoint",
                labels=["endpoint"],
            )
            for endpoint, val in latency_map.items():
                try:
                    float_val = float(val)
                except (ValueError, TypeError):
                    continue
                latency_metric.add_metric([endpoint], float_val)
            yield latency_metric

        # Handle requests_per_second map => another labeled metric
        rps_map = data.get("requests_per_second", {})
        if isinstance(rps_map, dict):
            rps_metric = GaugeMetricFamily(
                "typesense_requests_per_second",
                "Requests per second by endpoint",
                labels=["endpoint"],
            )
            for endpoint, val in rps_map.items():
                try:
                    float_val = float(val)
                except (ValueError, TypeError):
                    continue
                rps_metric.add_metric([endpoint], float_val)
            yield rps_metric

    def _collect_collections(self):
        """
        Retrieve all collections from Typesense, yielding a labeled metric
        for each collection's document count.
        """
        try:
            collections = self.client.collections.retrieve()
        except Exception as exc:
            print(f"[ERROR] Could not fetch collections: {exc}")
            return

        collection_gauge = GaugeMetricFamily(
            "typesense_collection_documents",
            "Number of documents in each Typesense collection",
            labels=["collection_name"],
        )
        for col in collections:
            name = col.get("name", "unknown")
            doc_count = col.get("num_documents", 0.0)
            try:
                doc_count_val = float(doc_count)
            except (ValueError, TypeError):
                doc_count_val = 0.0
            collection_gauge.add_metric([name], doc_count_val)

        yield collection_gauge

    @staticmethod
    def _sanitize_metric_name(name: str) -> str:
        """
        Convert a dictionary key, e.g. 'system_cpu1_active_percentage', into a valid
        Prometheus metric name. Replaces '.' or '-' with '_'.

        Args:
            name (str): Original metric key.
        Returns:
            str: Sanitized metric name.
        """
        sanitized = name.replace(".", "_").replace("-", "_")
        if not sanitized.startswith("typesense_"):
            sanitized = f"typesense_{sanitized}"
        return sanitized

def parse_args() -> argparse.Namespace:
    """
    Parse CLI arguments, with fallback to environment variables, for this exporter.

    Returns:
        argparse.Namespace: Parsed arguments including API key, URLs, and port.
    """
    parser = argparse.ArgumentParser(
        description="Typesense Prometheus Exporter (on-demand fetch)."
    )

    parser.add_argument(
        "--typesense-api-key",
        default=os.environ.get("TYPESENSE_API_KEY", ""),
        help="Typesense API Key. (Env: TYPESENSE_API_KEY)",
    )
    parser.add_argument(
        "--typesense-metrics-url",
        default=os.environ.get(
            "TYPESENSE_METRICS_URL", "https://localhost:8108/metrics.json"
        ),
        help="URL for /metrics.json. (Env: TYPESENSE_METRICS_URL)",
    )
    parser.add_argument(
        "--typesense-stats-url",
        default=os.environ.get(
            "TYPESENSE_STATS_URL", "https://localhost:8108/stats.json"
        ),
        help="URL for /stats.json. (Env: TYPESENSE_STATS_URL)",
    )
    parser.add_argument(
        "--typesense-nodes",
        default=os.environ.get("TYPESENSE_NODES", "localhost:8108"),
        help="Comma-separated 'host:port' for Typesense nodes. (Env: TYPESENSE_NODES)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        default=False
        if os.environ.get("VERIFY_SSL", "false").lower() == "false"
        else True,
        help="Verify SSL certs? (Env: VERIFY_SSL). Use --verify to enable.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port on which to expose the /metrics endpoint. Default is 8000.",
    )

    return parser.parse_args()


def main() -> None:
    """
    Main entry point for the script. Parses arguments, registers the custom
    collector, starts the HTTP server, and waits for Prometheus scrapes.
    """
    args = parse_args()
    nodes_config = parse_nodes_from_str(args.typesense_nodes, default_protocol="https")

    collector = TypesenseCollector(
        typesense_api_key=args.typesense_api_key,
        metrics_url=args.typesense_metrics_url,
        stats_url=args.typesense_stats_url,
        nodes=nodes_config,
        verify_ssl=args.verify,
    )
    print(f"Initialized TypesenseCollector with nodes: {nodes_config}")

    # Register the custom collector with Prometheus
    REGISTRY.register(collector)

    # Start the HTTP server
    print(f"Starting Prometheus HTTP server on port {args.port}...")
    start_http_server(args.port)

    # Keep the script running to service scrape requests
    while True:
        time.sleep(5)


if __name__ == "__main__":
    main()
