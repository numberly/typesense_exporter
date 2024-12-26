# Typesense Prometheus Exporter (On-Demand Fetch)

A **Prometheus** exporter that queries a [Typesense](https://typesense.org/) cluster on-demand each time Prometheus scrapes the `/metrics` endpoint. This ensures that the data is always **fresh** and eliminates the need for a separate polling loop.

## Key Features

- **On-Demand Scraping**: Data is fetched live from Typesense whenever Prometheus scrapes.
- **Easy Configuration**: Set options via environment variables or command-line arguments.
- **Collections**: Exposes per-collection document counts.
- **Automatic SSL Verification Control**: Optionally disable SSL cert verification for development or when using self-signed certs.

## Requirements

- Python 3.7+
- [typesense](https://pypi.org/project/typesense/) (Python client)
- [prometheus_client](https://pypi.org/project/prometheus_client/)
- [requests](https://pypi.org/project/requests/)

You can install these with:

```bash
pip install prometheus_client requests typesense
```

## Usage

1. Clone or copy the script into your environment.

2. Install Dependencies:
```bash
pip install prometheus_client requests typesense
```

3. Run the Exporter:
```bash
./typesense_exporter.py --port 8000 \
  --typesense-api-key "YOUR_API_KEY" \
  --typesense-nodes "host1:8108,host2:8108"
```
Or rely on environment variables:
```bash
export TYPESENSE_API_KEY="YOUR_API_KEY"
export TYPESENSE_NODES="host1:8108,host2:8108"
./typesense_exporter.py
```

4. Scrape with Prometheus:

Add to your Prometheus `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: "typesense_exporter"
    static_configs:
      - targets: ["localhost:8000"]
```

5. Verify

Navigate to http://localhost:8000/metrics in your browser or use `curl http://localhost:8000/metrics` to see the exposed metrics.

## Command-Line Arguments

| Argument                  | Env Var                    | Default                                     | Description                                                                                                      |
|---------------------------|----------------------------|---------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| `--typesense-api-key`     | `TYPESENSE_API_KEY`        | *(none)*                                    | Your Typesense API key.                                                                                          |
| `--typesense-metrics-url` | `TYPESENSE_METRICS_URL`    | `https://localhost:8108/metrics.json`       | The full URL to `metrics.json` endpoint.                                                                         |
| `--typesense-stats-url`   | `TYPESENSE_STATS_URL`      | `https://localhost:8108/stats.json`         | The full URL to `stats.json` endpoint.                                                                           |
| `--typesense-debug-url`   | `TYPESENSE_DEBUG_URL`      | `https://localhost:8108/debug`              | The full URL to `stats.json` endpoint.                                                                           |
| `--typesense-nodes`       | `TYPESENSE_NODES`          | `localhost:8108`                            | A comma-separated list of `host:port` entries for Typesense nodes (e.g., `node1:8108,node2:8108`).               |
| `--verify`                | `VERIFY_SSL`               | `False`                                     | Verify SSL certificates. Set `--verify` to enable, or `VERIFY_SSL=true` for environment.                         |
| `--port`                  | *(not applicable)*         | `8000`                                      | Which port the exporter will listen on for Prometheus scrapes.                                                   |

> **Tip**: Command-line arguments override environment variables, which override the defaults.

## How It Works

* The script registers a custom TypesenseCollector with Prometheus.
* Every time Prometheus sends a GET request to /metrics:
  * The collector fetches /metrics.json, /stats.json, and the list of collections from the configured Typesense node(s).
  * Each field is converted to a Prometheus metric and yielded dynamically.

This design guarantees that metrics are always up-to-date at scrape time (with no in-memory caching or stale metrics).

## Customization
* Modify `_collect_metrics_json` or `_collect_stats_json` to handle additional fields or parse additional endpoints as needed.
* Adjust `_sanitize_metric_name` if you want to add or remove transformations for metric names.
* Wrap the exporter in Docker or a systemd service to manage it in production environments.


## License

This exporter is released under the MIT License. See LICENSE for details (or replace with your preferred license).