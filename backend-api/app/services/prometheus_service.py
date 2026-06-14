import os
import time
import logging
from typing import Dict, List, Any, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class PrometheusService:
    """
    Prometheus Service layer executing real-time PromQL range queries 
    against a Prometheus HTTP server.
    """

    def __init__(self, guild_id: Optional[str] = None):
        self.prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090").rstrip("/")
        self.mock_mode = settings.MOCK_MODE
        self.guild_id = guild_id
        
        if guild_id and not self.mock_mode:
            try:
                from app.core.database import SessionLocal
                from app.models.db_models import ClusterConfiguration
                db = SessionLocal()
                try:
                    config_record = db.query(ClusterConfiguration).filter(ClusterConfiguration.guild_id == guild_id).first()
                    if config_record and config_record.prometheus_url:
                        self.prometheus_url = config_record.prometheus_url.rstrip("/")
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Failed to load dynamic Prometheus URL for guild {guild_id}: {str(e)}")

        logger.info(f"Prometheus Service initialized (mock_mode={self.mock_mode}, url={self.prometheus_url}, guild_id={guild_id})")

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
        if self.mock_mode:
            val = 0.05
            if service_name == "payment-service":
                val = 0.12
            elif service_name == "analytics-service":
                val = 0.82
            elif service_name == "frontend-service":
                val = 0.22
            return {
                "metric": "container_cpu_usage_seconds_total",
                "service": service_name,
                "unit": "cores/rate",
                "values": [{"timestamp": int(time.time()), "value": val}]
            }

        # Sum rate of CPU usage for pods matching service name from settings template
        query = settings.PROM_QUERY_CPU.replace("{service_name}", service_name)
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
        if self.mock_mode:
            val = 120.0
            limit = 512.0
            if service_name == "payment-service":
                val = 180.0
            elif service_name == "analytics-service":
                val = 512.0
            elif service_name == "frontend-service":
                val = 220.0
            elif service_name == "auth-service":
                val = 80.0
                limit = 256.0
            return {
                "metric": "container_memory_working_set_bytes",
                "service": service_name,
                "unit": "MiB",
                "limit_mib": limit,
                "values": [{"timestamp": int(time.time()), "value": val}]
            }

        # Sum memory usage and convert bytes to MiB
        query = settings.PROM_QUERY_MEMORY.replace("{service_name}", service_name)
        values = self._query_range(query, duration_hours)

        # Retrieve namespace limit (fallback to 512 if unavailable)
        limit_mib = 512.0
        limit_query = settings.PROM_QUERY_MEMORY_LIMIT.replace("{service_name}", service_name)
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
        if self.mock_mode:
            val = 50.0
            if service_name == "payment-service":
                val = 30000.0
            elif service_name == "analytics-service":
                val = 450.0
            elif service_name == "frontend-service":
                val = 5000.0
            elif service_name == "auth-service":
                val = 12.0
            return {
                "metric": "http_request_duration_seconds",
                "service": service_name,
                "unit": "ms",
                "values": [{"timestamp": int(time.time()), "value": val}]
            }

        query = settings.PROM_QUERY_LATENCY.replace("{service_name}", service_name)
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
        if self.mock_mode:
            val = 0.0
            if service_name == "payment-service":
                val = 100.0
            elif service_name == "analytics-service":
                val = 10.0
            elif service_name == "frontend-service":
                val = 100.0
            elif service_name == "auth-service":
                val = 0.0
            return {
                "metric": "http_requests_failed_total",
                "service": service_name,
                "unit": "percent",
                "values": [{"timestamp": int(time.time()), "value": val}]
            }

        query = settings.PROM_QUERY_ERROR_RATE.replace("{service_name}", service_name)
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
