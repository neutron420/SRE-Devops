import os
import logging
from typing import Dict, List, Any, Optional
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from app.core.config import settings

logger = logging.getLogger(__name__)

class K8sService:
    """
    Kubernetes Service layer communicating in real-time with the cluster API.
    Loads configurations from in-cluster service accounts or local kubeconfig.
    """

    def __init__(self):
        self.namespace = settings.K8S_NAMESPACE
        self.k8s_connected = False
        self.mock_mode = settings.MOCK_MODE
        
        if self.mock_mode:
            logger.info("K8sService is running in MOCK mode. Live cluster calls are bypassed.")
            return
            
        try:
            # Try loading incluster config (when running inside a Kubernetes Pod)
            config.load_incluster_config()
            self.k8s_connected = True
            logger.info("Successfully loaded Kubernetes in-cluster configuration.")
        except Exception:
            try:
                # Fallback to local kubeconfig (when running on local machine)
                config.load_kube_config()
                self.k8s_connected = True
                logger.info("Successfully loaded local Kubernetes kubeconfig.")
            except Exception as e:
                logger.error(
                    f"Unable to load Kubernetes configuration: {str(e)}. "
                    "Kubernetes API calls will fail with connection exceptions."
                )

    def _check_connection(self):
        if not self.k8s_connected:
            raise RuntimeError(
                "Kubernetes client is not configured. Check that your cluster is running "
                "and ~/.kube/config is populated correctly."
            )

    def get_pod_status(self, service_name: str) -> Dict[str, Any]:
        """
        Queries Kubernetes API in real-time to retrieve pod statuses for the service.
        """
        if self.mock_mode:
            pods = []
            if service_name == "payment-service":
                pods = [
                    {
                        "name": "payment-service-5f9f8c6b9b-abc12",
                        "status": "CrashLoopBackOff",
                        "restart_count": 8,
                        "ready": "0/1",
                        "ip": "10.244.1.45",
                        "node": "node-worker-1",
                        "created_at": "2026-06-13T10:00:00Z"
                    }
                ]
            elif service_name == "analytics-service":
                pods = [
                    {
                        "name": "analytics-service-9d8f7c6b5a-xyz34",
                        "status": "OOMKilled",
                        "restart_count": 3,
                        "ready": "0/1",
                        "ip": "10.244.1.46",
                        "node": "node-worker-2",
                        "created_at": "2026-06-13T10:00:00Z"
                    }
                ]
            elif service_name == "frontend-service":
                pods = [
                    {
                        "name": "frontend-service-8f7e6d5c4b-def56",
                        "status": "Running",
                        "restart_count": 0,
                        "ready": "1/1",
                        "ip": "10.244.1.47",
                        "node": "node-worker-1",
                        "created_at": "2026-06-13T10:00:00Z"
                    }
                ]
            elif service_name == "auth-service":
                pods = [
                    {
                        "name": "auth-service-7f6e5d4c3b-ghi78",
                        "status": "Running",
                        "restart_count": 0,
                        "ready": "1/1",
                        "ip": "10.244.1.48",
                        "node": "node-worker-2",
                        "created_at": "2026-06-13T10:00:00Z"
                    }
                ]
            else:
                pods = [
                    {
                        "name": f"{service_name}-6f5e4d3c2b-jkl90",
                        "status": "Running",
                        "restart_count": 0,
                        "ready": "1/1",
                        "ip": "10.244.1.99",
                        "node": "node-worker-1",
                        "created_at": "2026-06-13T10:00:00Z"
                    }
                ]
            return {
                "service": service_name,
                "pods": pods
            }

        self._check_connection()
        logger.info(f"Querying cluster pods for service: '{service_name}' in namespace '{self.namespace}'")
        
        try:
            v1 = client.CoreV1Api()
            
            # Query by standard label selector first
            pod_list = v1.list_namespaced_pod(
                self.namespace,
                label_selector=f"app={service_name}"
            )
            
            # Fallback: Filter pods containing the service name in their metadata name
            pods = pod_list.items
            if not pods:
                logger.info(f"No pods matched label selector app={service_name}. Trying name substring search...")
                all_pods = v1.list_namespaced_pod(self.namespace)
                pods = [p for p in all_pods.items if service_name in p.metadata.name]
                
            if not pods:
                return {"status": "Not Found", "error": f"No pods found matching service: '{service_name}'"}

            formatted_pods = []
            for p in pods:
                # Inspect container states to detect fine-grained failures like CrashLoopBackOff/OOMKilled
                phase = p.status.phase
                ready_count = 0
                total_containers = len(p.spec.containers) if p.spec.containers else 0
                restart_count = 0
                
                if p.status.container_statuses:
                    for cs in p.status.container_statuses:
                        restart_count += cs.restart_count
                        if cs.ready:
                            ready_count += 1
                        
                        # Pinpoint specific waiting reasons
                        if cs.state.waiting:
                            phase = cs.state.waiting.reason  # CrashLoopBackOff, ImagePullBackOff, etc.
                        elif cs.state.terminated:
                            phase = cs.state.terminated.reason or f"ExitCode:{cs.state.terminated.exit_code}"
                
                formatted_pods.append({
                    "name": p.metadata.name,
                    "status": phase,
                    "restart_count": restart_count,
                    "ready": f"{ready_count}/{total_containers}",
                    "ip": p.status.pod_ip or "None",
                    "node": p.spec.node_name or "None",
                    "created_at": p.metadata.creation_timestamp.isoformat() if p.metadata.creation_timestamp else "Unknown"
                })
                
            return {
                "service": service_name,
                "pods": formatted_pods
            }
            
        except ApiException as e:
            logger.error(f"Kubernetes API Exception in get_pod_status: {str(e)}")
            return {"status": "Error", "error": f"Kubernetes API Error: {e.reason} ({e.status})"}
        except Exception as e:
            logger.error(f"Unexpected error in get_pod_status: {str(e)}")
            return {"status": "Error", "error": str(e)}

    def get_deployment_status(self, service_name: str) -> Dict[str, Any]:
        """
        Queries Kubernetes API in real-time to fetch deployment specs.
        """
        if self.mock_mode:
            desired = 3
            available = 3
            if service_name in ["payment-service", "analytics-service"]:
                available = 2
            return {
                "name": service_name,
                "replicas_desired": desired,
                "replicas_available": available,
                "replicas_updated": desired,
                "strategy": "RollingUpdate"
            }

        self._check_connection()
        logger.info(f"Querying deployment status for: '{service_name}'")
        
        try:
            apps_v1 = client.AppsV1Api()
            
            # Read deployment directly
            deploy = apps_v1.read_namespaced_deployment(
                name=service_name,
                namespace=self.namespace
            )
            
            return {
                "name": deploy.metadata.name,
                "replicas_desired": deploy.spec.replicas,
                "replicas_available": deploy.status.available_replicas or 0,
                "replicas_updated": deploy.status.updated_replicas or 0,
                "strategy": deploy.spec.strategy.type
            }
            
        except ApiException as e:
            logger.warning(f"Deployment '{service_name}' not found or inaccessible: {e.reason}")
            return {"error": f"Deployment details unavailable: {e.reason}"}

    def get_pod_events(self, service_name: str) -> List[Dict[str, Any]]:
        """
        Queries Kubernetes events for the service's pods in real-time.
        """
        if self.mock_mode:
            if service_name == "payment-service":
                return [
                    {"type": "Warning", "reason": "BackOff", "message": "Back-off restarting failed container"},
                    {"type": "Normal", "reason": "Scheduled", "message": "Successfully assigned default/payment-service-5f9f8c6b9b-abc12 to node-worker-1"}
                ]
            elif service_name == "analytics-service":
                return [
                    {"type": "Warning", "reason": "OOMKilled", "message": "System memory limit exceeded"},
                    {"type": "Normal", "reason": "Created", "message": "Created container analytics-service"}
                ]
            elif service_name == "frontend-service":
                return [
                    {"type": "Normal", "reason": "Started", "message": "Started container frontend-service"}
                ]
            return [
                {"type": "Normal", "reason": "Started", "message": f"Started container {service_name}"}
            ]

        self._check_connection()
        logger.info(f"Querying cluster events for service: '{service_name}'")
        
        try:
            v1 = client.CoreV1Api()
            
            # Fetch namespaced events
            events = v1.list_namespaced_event(self.namespace)
            
            filtered_events = []
            for e in events.items:
                involved_name = e.involved_object.name or ""
                # Correlate events related to this service name
                if service_name in involved_name:
                    filtered_events.append({
                        "type": e.type,
                        "reason": e.reason,
                        "message": e.message
                    })
                    
            # Return last 10 events
            return filtered_events[-10:]
            
        except Exception as e:
            logger.error(f"Error fetching Kubernetes events: {str(e)}")
            return []

    def get_pod_logs(self, service_name: str, tail_lines: int = 100, since_seconds: Optional[int] = None, query_filter: Optional[str] = None) -> str:
        """
        Retrieves live log streams from the first active pod of the service,
        with optional timeframe (since_seconds) and string query filters.
        """
        if self.mock_mode:
            pod_name = f"{service_name}-mock-pod"
            logs = ""
            if service_name == "payment-service":
                logs = (
                    "2026-06-13T12:00:40Z [INFO] Initializing connection pool...\n"
                    "2026-06-13T12:00:45Z [ERROR] Failed to connect to database: Connection timeout after 30 seconds.\n"
                    "2026-06-13T12:00:45Z [WARNING] Retrying database connection in 5 seconds...\n"
                )
            elif service_name == "analytics-service":
                logs = (
                    "2026-06-13T12:05:00Z [INFO] Starting event processing batch of 250,000 items...\n"
                    "2026-06-13T12:05:05Z [INFO] Heap memory usage exceeding 90%...\n"
                    "2026-06-13T12:05:10Z [FATAL] OutOfMemory: Java heap space. Exceeded memory limit of 512MiB.\n"
                )
            elif service_name == "frontend-service":
                logs = (
                    "2026-06-13T12:09:55Z [INFO] Incoming GET /dashboard request from 192.168.1.100\n"
                    "2026-06-13T12:10:00Z [WARNING] Gateway Timeout (504) received while calling downstream service: payment-service.\n"
                )
            elif service_name == "auth-service":
                logs = (
                    "2026-06-13T12:14:59Z [INFO] Incoming POST /login request\n"
                    "2026-06-13T12:15:00Z [INFO] Successfully authenticated user session. Request processed in 15ms.\n"
                )
            else:
                logs = f"2026-06-13T12:20:00Z [INFO] Service {service_name} is healthy and running operational checks.\n"
                
            if query_filter:
                lines = logs.strip().split("\n")
                filtered_lines = [line for line in lines if query_filter.lower() in line.lower()]
                logs = "\n".join(filtered_lines)
                
            return f"--- Log dump from pod {pod_name} ---\n" + logs

        self._check_connection()
        logger.info(f"Querying live pod logs for service: '{service_name}' (since_seconds={since_seconds}, query_filter={query_filter})")
        
        try:
            v1 = client.CoreV1Api()
            
            # Find matching pods
            pod_list = v1.list_namespaced_pod(
                self.namespace,
                label_selector=f"app={service_name}"
            )
            pods = pod_list.items
            
            if not pods:
                # Fallback substring name matching
                all_pods = v1.list_namespaced_pod(self.namespace)
                pods = [p for p in all_pods.items if service_name in p.metadata.name]
                
            if not pods:
                return f"[ERROR] No pods found for service '{service_name}' to retrieve logs."
                
            # Grab logs from the first pod
            target_pod_name = pods[0].metadata.name
            logger.info(f"Streaming logs from pod: '{target_pod_name}'")
            
            # Formulate query arguments
            log_args = {
                "name": target_pod_name,
                "namespace": self.namespace
            }
            if since_seconds:
                log_args["since_seconds"] = since_seconds
            else:
                log_args["tail_lines"] = tail_lines

            logs = v1.read_namespaced_pod_log(**log_args)
            
            # Apply keyword filter
            if query_filter:
                lines = logs.strip().split("\n")
                filtered_lines = [line for line in lines if query_filter.lower() in line.lower()]
                logs = "\n".join(filtered_lines)
                
            return f"--- Log dump from pod {target_pod_name} ---\n" + logs
            
        except ApiException as e:
            logger.error(f"Failed to read pod logs via Kubernetes API: {str(e)}")
            return f"[ERROR] Kubernetes API failed reading logs: {e.reason} ({e.status})"
        except Exception as e:
            logger.error(f"Error reading pod logs: {str(e)}")
            return f"[ERROR] Failed to fetch logs: {str(e)}"

    def list_deployments(self) -> List[str]:
        """
        Lists all deployment names in the namespace.
        """
        if self.mock_mode:
            return ["payment-service", "auth-service", "analytics-service", "frontend-service"]

        self._check_connection()
        try:
            apps_v1 = client.AppsV1Api()
            deploys = apps_v1.list_namespaced_deployment(self.namespace)
            return [d.metadata.name for d in deploys.items]
        except Exception as e:
            logger.error(f"Error listing deployments: {str(e)}")
            return []

