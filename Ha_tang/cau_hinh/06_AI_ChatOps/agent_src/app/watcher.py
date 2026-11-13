import asyncio
import logging
from dataclasses import dataclass

from telegram.ext import Application

from app.bot import send_sre_report
from app.config import settings
from app.llm_engine import run_sre_reasoning
from app.tools import collect_full_diagnostic_bundle, k8s
from app.webhooks import should_suppress_duplicate

logger = logging.getLogger(__name__)


@dataclass
class PodSnapshot:
    restarts: int
    waiting_reason: str


def _capture_cluster_snapshot() -> tuple[dict[str, str], dict[str, PodSnapshot]]:
    """Thu thập trạng thái Node Ready và Pod Restarts/Waiting từ Kubernetes API."""
    k8s.ensure_loaded()
    assert k8s.core_v1 is not None

    node_states: dict[str, str] = {}
    for node in k8s.core_v1.list_node().items:
        is_ready = any(
            c.type == "Ready" and c.status == "True" for c in (node.status.conditions or [])
        )
        node_states[node.metadata.name] = "Ready" if is_ready else "NotReady"

    pod_states: dict[str, PodSnapshot] = {}
    pods = k8s.core_v1.list_namespaced_pod(namespace=settings.target_app_namespace).items
    for p in pods:
        restarts = 0
        waiting_reason = ""
        for cs in p.status.container_statuses or []:
            restarts += cs.restart_count or 0
            if cs.state and cs.state.waiting and cs.state.waiting.reason:
                waiting_reason = cs.state.waiting.reason
        pod_states[p.metadata.name] = PodSnapshot(
            restarts=restarts, waiting_reason=waiting_reason
        )

    return node_states, pod_states


BAD_WAITING_REASONS = {
    "CrashLoopBackOff",
    "ImagePullBackOff",
    "ErrImagePull",
    "CreateContainerConfigError",
    "RunContainerError",
}


async def run_proactive_k8s_watcher(
    bot_app: Application, stop_event: asyncio.Event, poll_interval: float = 5.0
) -> None:
    """
    Vòng lặp giám sát chủ động cấp cụm (chu kỳ 5 giây):
    - Phát hiện thay đổi trạng thái Node (Ready <-> NotReady).
    - Phát hiện sự kiện Container Crash / Restart tăng hoặc rơi vào trạng thái Waiting lỗi.
    """
    if not settings.enable_k8s_watcher or not settings.allowed_chat_id:
        logger.info("Proactive K8s Watcher disabled or ALLOWED_CHAT_ID not set.")
        return

    logger.info("Starting Proactive K8s Watcher (interval=%.1fs)...", poll_interval)
    prev_nodes: dict[str, str] = {}
    prev_pods: dict[str, PodSnapshot] = {}
    initialized = False

    while not stop_event.is_set():
        try:
            curr_nodes, curr_pods = await asyncio.to_thread(_capture_cluster_snapshot)

            if not initialized:
                prev_nodes = curr_nodes
                prev_pods = curr_pods
                initialized = True
            else:
                anomalies: list[str] = []

                # 1. Kiểm tra biến động trạng thái Node
                for node_name, curr_state in curr_nodes.items():
                    old_state = prev_nodes.get(node_name)
                    if old_state and old_state != curr_state:
                        fp = f"watcher:node:{node_name}:{curr_state}"
                        if not should_suppress_duplicate(fp, cooldown_sec=60.0):
                            anomalies.append(
                                f"Node `{node_name}` chuyển trạng thái từ `{old_state}` sang `{curr_state}`."
                            )

                # 2. Kiểm tra sự kiện Container Restart hoặc Waiting lỗi trong namespace đích
                for pod_name, snap in curr_pods.items():
                    old_snap = prev_pods.get(pod_name)
                    if old_snap and snap.restarts > old_snap.restarts:
                        fp = f"watcher:restart:{pod_name}:{snap.restarts}"
                        if not should_suppress_duplicate(fp, cooldown_sec=45.0):
                            anomalies.append(
                                f"Pod `{pod_name}` vừa khởi động lại "
                                f"(Restarts tăng từ {old_snap.restarts} lên {snap.restarts})."
                            )
                    if (
                        snap.waiting_reason in BAD_WAITING_REASONS
                        and (not old_snap or old_snap.waiting_reason != snap.waiting_reason)
                    ):
                        fp = f"watcher:wait:{pod_name}:{snap.waiting_reason}"
                        if not should_suppress_duplicate(fp, cooldown_sec=90.0):
                            anomalies.append(
                                f"Pod `{pod_name}` chuyển sang trạng thái lỗi `{snap.waiting_reason}`."
                            )

                prev_nodes = curr_nodes
                prev_pods = curr_pods

                if anomalies:
                    incident_desc = "\n".join(f"- {item}" for item in anomalies)
                    logger.warning("Proactive K8s Watcher detected anomaly:\n%s", incident_desc)
                    telemetry = await collect_full_diagnostic_bundle()
                    sre_resp = await run_sre_reasoning(
                        telemetry_bundle=telemetry,
                        trigger_prompt=(
                            "Bộ giám sát K8s Watcher phát hiện sự cố thực thi cấp cụm/container:\n"
                            f"{incident_desc}\n"
                            "Hãy đọc [PREVIOUS CRASH LOG], Events và trạng thái Pod để phân tích nguyên nhân gốc rễ (RCA) "
                            "và xác nhận trạng thái phục hồi của ứng dụng."
                        ),
                    )
                    await send_sre_report(
                        bot_app=bot_app,
                        chat_id=settings.allowed_chat_id,
                        title="[REALTIME WATCHER - K8S]",
                        sre_resp=sre_resp,
                    )
        except Exception as exc:
            logger.warning("Watcher iteration warning: %s", exc)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=poll_interval)
        except TimeoutError:
            pass

