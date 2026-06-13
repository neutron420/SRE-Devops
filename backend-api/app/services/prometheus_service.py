import os
import time
import logging
from typing import Dict, List, Any
import httpx

logger = logging.getLogger(__name__)

class PrometheusService:
    """
    Prometheus Service layer executing real-time PromQL range queries 
    against a Prometheus HTTP server.
    """

    def __init__(self):
        self.prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090").rstrip("/")
        logger.info(f"Prometheus Service initialized with endpoint: {self.prometheus_url}")

    def _query_range(self, query: str, duration_hours: int = 1, step_seconds: int = 60) -> List[Dict[str, Any]]:
        """
        Executes a range query against the Prometheus API and parses results.
        """
        end_time = int(time.time())
        start_time = end_time - (duration_hours * 3600)
        
        url = f"{self.prometheus_url}/api/v1/query_range"
        params = {
            "query": query,
            "start": start_time,
            "end": end_time,
            "step": f"{step_seconds}s"
        }
        
        try:
            logger.info(f"Executing PromQL range query: {query}")
            response = httpx.get(url, params=params, timeout=5.0)
            
            if response.status_code != 200:
                logger.error(f"Prometheus returned status code {response.status_code}: {response.text}")
                return []
                
            data = response.json()
            if data.get("status") != "success":
                logger.error(f"Prometheus query failed: {data.get('error', 'Unknown error')}")
                return []
                
            result_list = data.get("data", {}).get("result", [])
            if not result_list:
                logger.info("Prometheus query returned empty result set.")
                return []
                
            # Process range values (format: [ [timestamp, "value"], ... ])
            values = result_list[0].get("values", [])
            formatted_values = []
            for item in values:
                ts = int(item[0])
                try:
                    val = float(item[1])
                except ValueError:
                    val = 0.0
                formatted_values.append({
                    "timestamp": ts,
                    "value": round(val, 3)
                })
            return formatted_values
            
        except httpx.RequestError as e:
            logger.warning(f"Could not connect to Prometheus server at {self.prometheus_url}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error querying Prometheus: {str(e)}")
            return []

    def get_cpu_usage(self, service_name: str, duration_hours: int = 1) -> Dict[str, Any]:
        """
        Queries actual CPU usage rate (cores or percentage) for pods in the service.
        """
        # Sum rate of CPU usage for pods matching service name
        query = f'sum(rate(container_cpu_usage_seconds_total{{container!="", pod=~"{service_name}.*"}}[5m])) by (pod)'
        values = self._query_range(query, duration_hours)
        
        # If empty, try a broader query (ignoring container name)
        if not values:
            query = f'sum(rate(container_cpu_usage_seconds_total{{pod=~"{service_name}.*"}}[5m]))'
            values = self._query_range(query, duration_hours)

        return {
            "metric": "container_cpu_usage_seconds_total",
            "service": service_name,
            "unit": "cores/rate",
            "values": values
        }

    def get_memory_usage(self, service_name: str, duration_hours: int = 1) -> Dict[str, Any]:
        """
        Queries actual working set memory usage in MiB.
        """
        # Sum memory usage and convert bytes to MiB
        query = f'sum(container_memory_working_set_bytes{{container!="", pod=~"{service_name}.*"}}) / 1024 / 1024'
        values = self._query_range(query, duration_hours)
        
        if not values:
            query = f'sum(container_memory_working_set_bytes{{pod=~"{service_name}.*"}}) / 1024 / 1024'
            values = self._query_range(query, duration_hours)

        # Retrieve namespace limit (fallback to 512 if unavailable)
        limit_mib = 512.0
        limit_query = f'sum(container_spec_memory_limit_bytes{{container!="", pod=~"{service_name}.*"}}) / 1024 / 1024'
        limit_values = self._query_range(limit_query, duration_hours)
        if limit_values and limit_values[-1]["value"] > 0:
            limit_mib = limit_values[-1]["value"]

        return {
            "metric": "container_memory_working_set_bytes",
            "service": service_name,
            "unit": "MiB",
            "limit_mib": limit_mib,
            "values": values
        }

    def get_request_latency(self, service_name: str, duration_hours: int = 1) -> Dict[str, Any]:
        """
        Queries request latency (ms) by dividing http duration sum by total count.
        """
        query = (
            f'sum(rate(http_request_duration_seconds_sum{{pod=~"{service_name}.*"}}[5m])) '
            f'/ sum(rate(http_request_duration_seconds_count{{pod=~"{service_name}.*"}}[5m])) * 1000'
        )
        values = self._query_range(query, duration_hours)

        return {
            "metric": "http_request_duration_seconds",
            "service": service_name,
            "unit": "ms",
            "values": values
        }

    def get_error_rate(self, service_name: str, duration_hours: int = 1) -> Dict[str, Any]:
        """
        Queries request HTTP error rates as a percentage.
        """
        query = (
            f'sum(rate(http_requests_failed_total{{pod=~"{service_name}.*"}}[5m])) '
            f'/ sum(rate(http_requests_total{{pod=~"{service_name}.*"}}[5m])) * 100'
        )
        values = self._query_range(query, duration_hours)

        return {
            "metric": "http_requests_failed_total",
            "service": service_name,
            "unit": "percent",
            "values": values
        }

    def get_all_metrics(self, service_name: str, duration_hours: int = 1) -> Dict[str, Any]:
        """
        Aggregates live metric data collections.
        """
        return {
            "cpu": self.get_cpu_usage(service_name, duration_hours),
            "memory": self.get_memory_usage(service_name, duration_hours),
            "latency": self.get_request_latency(service_name, duration_hours),
            "error_rate": self.get_error_rate(service_name, duration_hours)
        }
