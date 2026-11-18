import asyncio
import base64
import io
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from ruamel.yaml import YAML

from app.config import settings
from app.security import redact_sensitive_text, validate_replica_bounds

logger = logging.getLogger(__name__)


class ClusterClients:
    """Quản lý kết nối Read-Only tới Kubernetes API In-Cluster (v1.0)."""

    def __init__(self) -> None:
        self._loaded = False
        self.core_v1: client.CoreV1Api | None = None
        self.apps_v1: client.AppsV1Api | None = None
        self.custom_api: client.CustomObjectsApi | None = None

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        try:
            config.load_incluster_config()
            logger.info("Loaded In-Cluster Kubernetes configuration.")
        except config.ConfigException:
            config.load_kube_config()
            logger.info("Loaded local Kubeconfig configuration.")
        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.custom_api = client.CustomObjectsApi()
        self._loaded = True


k8s = ClusterClients()


# ==============================================================================
# 1. PROMETHEUS PROMQL CLIENT (Truy vấn qua mạng nội bộ WireGuard wg0)
# ==============================================================================
async def query_prometheus(promql: str) -> list[dict[str, Any]]:
    url = f"{settings.prometheus_url.rstrip('/')}/api/v1/query"
    try:
        async with httpx.AsyncClient(timeout=4.0) as http:
            resp = await http.get(url, params={"query": promql})
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "success":
                return data.get("data", {}).get("result", [])
    except Exception as exc:
        logger.warning("PromQL query failed (%s): %s", promql, exc)
    return []


async def get_prometheus_node_metrics() -> dict[str, dict[str, str]]:
    """Lấy % CPU, % RAM và % Disk của 3 VPS từ node-exporter trên Prometheus."""
    cpu_results, mem_results, disk_results = await asyncio.gather(
        query_prometheus('100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'),
        query_prometheus('(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100'),
        query_prometheus(
            '(1 - (node_filesystem_avail_bytes{mountpoint="/",fstype!="tmpfs"} '
            '/ node_filesystem_size_bytes{mountpoint="/",fstype!="tmpfs"})) * 100'
        ),
    )

    metrics_by_ip: dict[str, dict[str, str]] = {}

    def _extract_ip(metric_item: dict[str, Any]) -> str:
        inst = metric_item.get("metric", {}).get("instance", "")
        return inst.split(":")[0]

    for item in cpu_results:
        ip = _extract_ip(item)
        metrics_by_ip.setdefault(ip, {})["cpu"] = f"{float(item['value'][1]):.1f}%"

    for item in mem_results:
        ip = _extract_ip(item)
        metrics_by_ip.setdefault(ip, {})["ram"] = f"{float(item['value'][1]):.1f}%"

    for item in disk_results:
        ip = _extract_ip(item)
        metrics_by_ip.setdefault(ip, {})["disk"] = f"{float(item['value'][1]):.1f}%"

    return metrics_by_ip


# ==============================================================================
# 2. READ-ONLY OBSERVABILITY TOOLS (K8s + PromQL + Argo CD — v1.0)
# ==============================================================================
def _sync_list_nodes() -> list[dict[str, str]]:
    k8s.ensure_loaded()
    assert k8s.core_v1 is not None
    nodes = k8s.core_v1.list_node().items
    result: list[dict[str, str]] = []
    for n in nodes:
        name = n.metadata.name
        labels = n.metadata.labels or {}
        workload = labels.get("workload", "control-plane")
        internal_ip = next(
            (addr.address for addr in (n.status.addresses or []) if addr.type == "InternalIP"),
            "unknown",
        )
        ready = any(
            c.type == "Ready" and c.status == "True" for c in (n.status.conditions or [])
        )
        result.append(
            {
                "name": name,
                "ip": internal_ip,
                "workload": workload,
                "status": "Ready" if ready else "NotReady",
            }
        )
    return result


async def get_cluster_overview() -> str:
    nodes, prom_map = await asyncio.gather(
        asyncio.to_thread(_sync_list_nodes),
        get_prometheus_node_metrics(),
    )
    lines = ["**[CLUSTER OVERVIEW] WireGuard Mesh**"]
    for n in nodes:
        tag = "[OK]" if n["status"] == "Ready" else "[ERR]"
        m = prom_map.get(n["ip"], {})
        hw = (
            f"CPU: `{m.get('cpu', 'N/A')}` | RAM: `{m.get('ram', 'N/A')}` | Disk: `{m.get('disk', 'N/A')}`"
            if m
            else "Metrics: N/A"
        )
        lines.append(
            f"- {tag} `{n['name']}` (`{n['ip']}` | {n['workload']}) — {hw}"
        )
    return "\n".join(lines)


def _sync_inspect_pods(namespace: str) -> str:
    k8s.ensure_loaded()
    assert k8s.core_v1 is not None
    pods = k8s.core_v1.list_namespaced_pod(namespace=namespace).items
    if not pods:
        return f"**[POD STATUS]** Không tìm thấy Pod nào trong namespace `{namespace}`."

    ready_pods = 0
    pod_lines: list[str] = []
    for p in pods:
        name = p.metadata.name
        node = p.spec.node_name or "Pending"
        phase = p.status.phase or "Unknown"
        restarts = 0
        ready_cnt = 0
        total_cnt = len(p.spec.containers or [])
        state_detail = phase
        last_exit: int | None = None

        for cs in p.status.container_statuses or []:
            restarts += cs.restart_count or 0
            if cs.ready:
                ready_cnt += 1
            if cs.state and cs.state.waiting and cs.state.waiting.reason:
                state_detail = cs.state.waiting.reason
            elif cs.state and cs.state.terminated and cs.state.terminated.reason:
                state_detail = cs.state.terminated.reason
            elif (
                cs.last_state
                and cs.last_state.terminated
                and restarts > 0
            ):
                last_exit = cs.last_state.terminated.exit_code

        is_ok = phase == "Running" and ready_cnt == total_cnt
        if is_ok:
            ready_pods += 1
        tag = "[OK]" if is_ok else "[WARN]"
        meta = f"Restarts: {restarts}" + (f", LastExit: {last_exit}" if last_exit is not None else "")
        pod_lines.append(
            f"- {tag} `{name}` | `{node}` | `{ready_cnt}/{total_cnt} {state_detail}` ({meta})"
        )

    other_errors: list[str] = []
    for p in k8s.core_v1.list_pod_for_all_namespaces().items:
        p_ns = p.metadata.namespace
        if p_ns == namespace:
            continue
        p_phase = p.status.phase or "Unknown"
        if p_phase == "Succeeded":
            continue
        cs_list = p.status.container_statuses or []
        if p_phase != "Running" or not cs_list or not all(cs.ready for cs in cs_list):
            other_errors.append(f"`{p_ns}/{p.metadata.name}` ({p_phase})")

    summary_line = (
        f"- **Toàn cụm:** {len(other_errors)} Pod bất thường ở namespace khác: {', '.join(other_errors[:5])}"
        if other_errors
        else "- **Toàn cụm:** 0 Pod lỗi ở các namespace khác."
    )
    header = f"**[POD STATUS]** Namespace: `{namespace}` ({ready_pods}/{len(pods)} Ready)"
    return "\n".join([header, *pod_lines, summary_line])


async def inspect_app_pods(namespace: str | None = None) -> str:
    return await asyncio.to_thread(_sync_inspect_pods, namespace or settings.target_app_namespace)


def _sync_fetch_smart_logs_and_events(namespace: str, tail_lines: int = 40) -> str:
    k8s.ensure_loaded()
    assert k8s.core_v1 is not None
    sections: list[str] = []
    pods = k8s.core_v1.list_namespaced_pod(namespace=namespace).items

    for p in pods:
        pod_name = p.metadata.name
        restarts = sum((cs.restart_count or 0) for cs in (p.status.container_statuses or []))
        if restarts > 0:
            try:
                prev_log = k8s.core_v1.read_namespaced_pod_log(
                    name=pod_name, namespace=namespace, previous=True, tail_lines=tail_lines
                )
                if prev_log:
                    sections.append(
                        f"=== [PREVIOUS CRASH LOG] Pod {pod_name} (Restarts={restarts}) ===\n"
                        f"{redact_sensitive_text(prev_log, max_chars=1800)}"
                    )
            except ApiException:
                pass

        try:
            curr_log = k8s.core_v1.read_namespaced_pod_log(
                name=pod_name, namespace=namespace, previous=False, tail_lines=tail_lines
            )
            sections.append(
                f"=== [CURRENT LOG] Pod {pod_name} (Node={p.spec.node_name}) ===\n"
                f"{redact_sensitive_text(curr_log or '(empty)', max_chars=1800)}"
            )
        except ApiException as exc:
            sections.append(f"=== [LOG ERROR] Pod {pod_name}: {exc.reason} ===")

    try:
        events = k8s.core_v1.list_namespaced_event(namespace=namespace).items
        warn_events = [e for e in events if e.type != "Normal"][-10:]
        if warn_events:
            ev_lines = [
                f"- [{e.reason}] {e.involved_object.name}: {e.message} (count={e.count})"
                for e in warn_events
            ]
            sections.append("=== [K8S WARNING EVENTS] ===\n" + "\n".join(ev_lines))
    except ApiException:
        pass

    return "\n\n".join(sections) if sections else "Không có log hoặc sự kiện bất thường."


async def fetch_smart_pod_logs(namespace: str | None = None, tail_lines: int = 40) -> str:
    return await asyncio.to_thread(
        _sync_fetch_smart_logs_and_events, namespace or settings.target_app_namespace, tail_lines
    )


async def query_sli_metrics() -> str:
    ns = settings.target_app_namespace
    pod_cpu, pod_mem, restarts_15m, db_ready = await asyncio.gather(
        query_prometheus(
            f'sum by (pod) (rate(container_cpu_usage_seconds_total{{namespace="{ns}",container!=""}}[5m])) * 1000'
        ),
        query_prometheus(
            f'sum by (pod) (container_memory_working_set_bytes{{namespace="{ns}",container!=""}}) / 1024 / 1024'
        ),
        query_prometheus(
            f'sum by (pod) (increase(kube_pod_container_status_restarts_total{{namespace="{ns}"}}[15m]))'
        ),
        query_prometheus('kube_pod_status_ready{namespace="database",condition="true"}'),
    )

    lines = [f"**[SLI METRICS]** `{ns}` & `database`"]
    cpu_map = {i["metric"].get("pod", "?"): float(i["value"][1]) for i in pod_cpu}
    mem_map = {i["metric"].get("pod", "?"): float(i["value"][1]) for i in pod_mem}
    rst_map = {i["metric"].get("pod", "?"): float(i["value"][1]) for i in restarts_15m}

    all_pods = sorted(set(cpu_map) | set(mem_map))
    if all_pods:
        for pod in all_pods:
            lines.append(
                f"- `{pod}`: CPU `{cpu_map.get(pod, 0.0):.1f}m` | "
                f"RAM `{mem_map.get(pod, 0.0):.1f} MiB` | "
                f"Restarts(15m): `{int(round(rst_map.get(pod, 0.0)))}`"
            )
    else:
        lines.append("- Chưa thu thập được metrics container từ Prometheus.")

    if db_ready:
        is_up = any(float(i["value"][1]) >= 1.0 for i in db_ready)
        lines.append(f"- PostgreSQL (`k3s-master`): `{'Ready' if is_up else 'NotReady'}`")

    return "\n".join(lines)


def _sync_get_argocd_status(app_name: str) -> str:
    k8s.ensure_loaded()
    assert k8s.custom_api is not None
    try:
        app_obj = k8s.custom_api.get_namespaced_custom_object(
            group="argoproj.io",
            version="v1alpha1",
            namespace=settings.argocd_namespace,
            plural="applications",
            name=app_name,
        )
        status = app_obj.get("status", {})
        sync_status = status.get("sync", {}).get("status", "Unknown")
        revision = status.get("sync", {}).get("revision", "N/A")[:7]
        health_status = status.get("health", {}).get("status", "Unknown")
        tag = "[OK]" if (sync_status == "Synced" and health_status == "Healthy") else "[WARN]"
        return (
            f"**[GITOPS STATUS]** {tag} `{app_name}`\n"
            f"- Sync: `{sync_status}` (Revision: `{revision}`)\n"
            f"- Health: `{health_status}`"
        )
    except ApiException as exc:
        return f"**[GITOPS STATUS]** [ERR] Không đọc được trạng thái Argo CD `{app_name}`: `{exc.reason}`"


async def get_argocd_app_status(app_name: str | None = None) -> str:
    return await asyncio.to_thread(_sync_get_argocd_status, app_name or settings.argocd_app_name)


async def collect_full_diagnostic_bundle() -> str:
    overview, pods, sli, argo, logs = await asyncio.gather(
        get_cluster_overview(),
        inspect_app_pods(),
        query_sli_metrics(),
        get_argocd_app_status(),
        fetch_smart_pod_logs(tail_lines=35),
    )
    return "\n\n".join([overview, pods, sli, argo, logs])


# ==============================================================================
# 3. WRITE / REMEDIATION EXECUTORS (CHỈ GỌI SAU KHI ADMIN XÁC NHẬN HITL)
# ==============================================================================
def _sync_get_deployment_replicas(namespace: str, deployment_name: str) -> int | None:
    try:
        k8s.ensure_loaded()
        assert k8s.apps_v1 is not None
        dep = k8s.apps_v1.read_namespaced_deployment(name=deployment_name, namespace=namespace)
        return dep.spec.replicas if dep.spec else None
    except Exception:
        return None


async def get_deployment_replicas(
    namespace: str | None = None, deployment_name: str | None = None
) -> int | None:
    ns = namespace or settings.target_app_namespace
    dep = deployment_name or settings.target_deployment_name
    return await asyncio.to_thread(_sync_get_deployment_replicas, ns, dep)


def _sync_rollout_restart(namespace: str, deployment_name: str) -> str:
    k8s.ensure_loaded()
    assert k8s.apps_v1 is not None
    now_iso = datetime.now(UTC).isoformat()
    patch_body = {
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {
                        "kubectl.kubernetes.io/restartedAt": now_iso,
                    }
                }
            }
        }
    }
    k8s.apps_v1.patch_namespaced_deployment(
        name=deployment_name,
        namespace=namespace,
        body=patch_body,
    )
    return f"Đã kích hoạt Rolling Restart cho Deployment `{namespace}/{deployment_name}` lúc `{now_iso}`."


async def execute_rollout_restart(
    namespace: str | None = None, deployment_name: str | None = None
) -> str:
    ns = namespace or settings.target_app_namespace
    dep = deployment_name or settings.target_deployment_name
    return await asyncio.to_thread(_sync_rollout_restart, ns, dep)


def _sync_trigger_argocd_refresh(app_name: str) -> str:
    """Kích hoạt Argo CD quét Git tức thì (rút thời gian chờ đồng bộ từ 3 phút xuống ~3-5 giây)."""
    k8s.ensure_loaded()
    assert k8s.custom_api is not None
    patch_body = {
        "metadata": {
            "annotations": {
                "argocd.argoproj.io/refresh": "hard",
            }
        }
    }
    k8s.custom_api.patch_namespaced_custom_object(
        group="argoproj.io",
        version="v1alpha1",
        namespace=settings.argocd_namespace,
        plural="applications",
        name=app_name,
        body=patch_body,
    )
    return f"Argo CD hard refresh triggered for `{app_name}`."


async def execute_argocd_refresh_sync(app_name: str | None = None) -> str:
    return await asyncio.to_thread(
        _sync_trigger_argocd_refresh, app_name or settings.argocd_app_name
    )


async def execute_gitops_manifest_mutation(
    replicas: int | None = None,
    image: str | None = None,
    reason: str = "ChatOps HITL Approved Update",
) -> str:
    """
    Cập nhật chuẩn GitOps lên kho GitHub (dùng ruamel.yaml giữ nguyên comment/định dạng,
    không để LLM tự sinh YAML thô), sau đó kích hoạt Argo CD Hard Refresh ngay lập tức.
    """
    if not settings.github_token:
        raise RuntimeError("Chưa cấu hình GITHUB_TOKEN trong Secret `chatops-secrets`.")

    if replicas is not None:
        replicas = validate_replica_bounds(replicas)

    api_url = (
        f"https://api.github.com/repos/{settings.github_repo}"
        f"/contents/{settings.gitops_manifest_path}"
    )
    headers = {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient(timeout=10.0) as http:
        get_resp = await http.get(
            api_url, headers=headers, params={"ref": settings.github_branch}
        )
        get_resp.raise_for_status()
        file_info = get_resp.json()
        sha = file_info["sha"]
        raw_yaml = base64.b64decode(file_info["content"]).decode("utf-8")

        yaml_parser = YAML()
        yaml_parser.preserve_quotes = True
        docs = list(yaml_parser.load_all(raw_yaml))

        changes_applied: list[str] = []
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            if (
                doc.get("kind") == "Deployment"
                and doc.get("metadata", {}).get("name") == settings.target_deployment_name
            ):
                if replicas is not None:
                    old_rep = doc["spec"].get("replicas")
                    doc["spec"]["replicas"] = int(replicas)
                    changes_applied.append(f"replicas: {old_rep} -> {replicas}")

                if image:
                    containers = doc["spec"]["template"]["spec"].get("containers", [])
                    if containers:
                        old_img = containers[0].get("image")
                        containers[0]["image"] = image.strip()
                        changes_applied.append(f"image: {old_img} -> {image.strip()}")

        if not changes_applied:
            raise RuntimeError(
                f"Không tìm thấy Deployment `{settings.target_deployment_name}` trong `{settings.gitops_manifest_path}`."
            )

        buf = io.StringIO()
        yaml_parser.dump_all(docs, buf)
        updated_yaml = buf.getvalue()

        commit_msg = f"chore(gitops): {', '.join(changes_applied)} via AI ChatOps ({reason})"
        put_payload = {
            "message": commit_msg,
            "content": base64.b64encode(updated_yaml.encode("utf-8")).decode("ascii"),
            "sha": sha,
            "branch": settings.github_branch,
        }
        put_resp = await http.put(api_url, headers=headers, json=put_payload)
        put_resp.raise_for_status()
        commit_sha = put_resp.json().get("commit", {}).get("sha", "")[:7]

    refresh_note = ""
    try:
        await execute_argocd_refresh_sync()
        refresh_note = " & Argo CD hard refresh triggered"
    except Exception as exc:
        logger.warning("Argo CD refresh after GitOps commit warning: %s", exc)

    return (
        f"Git commit created (`{commit_sha}`): {', '.join(changes_applied)} "
        f"on `{settings.github_branch}`{refresh_note}."
    )
