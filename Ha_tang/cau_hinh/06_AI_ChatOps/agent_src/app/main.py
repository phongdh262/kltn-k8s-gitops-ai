import asyncio
import logging
import signal

import uvicorn

from app.bot import build_telegram_application
from app.config import settings
from app.security import redact_sensitive_text
from app.watcher import run_proactive_k8s_watcher
from app.webhooks import create_webhook_api


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Bao gồm cả traceback và log SDK (URL Telegram chứa bot token).
        return redact_sensitive_text(super().format(record), max_chars=None)


logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(
        RedactingFormatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    )
logger = logging.getLogger("chatops.main")


async def async_main() -> None:
    settings.validate_security()
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    bot_app = build_telegram_application()
    fastapi_app = create_webhook_api(bot_app)

    uvicorn_cfg = uvicorn.Config(
        app=fastapi_app,
        host="0.0.0.0",
        port=settings.webhook_port,
        log_level="info",
        access_log=False,
    )
    uvicorn_server = uvicorn.Server(uvicorn_cfg)

    logger.info("Initializing Telegram Bot Async Long-Polling...")
    await bot_app.initialize()
    await bot_app.start()
    assert bot_app.updater is not None
    await bot_app.updater.start_polling(drop_pending_updates=True)

    server_task = asyncio.create_task(uvicorn_server.serve(), name="webhook-server")
    watcher_task = asyncio.create_task(
        run_proactive_k8s_watcher(bot_app, stop_event), name="k8s-watcher"
    )

    logger.info(
        "AI ChatOps SRE Agent v1.1 is LIVE (Webhook Port=%d, TargetNamespace=%s).",
        settings.webhook_port,
        settings.target_app_namespace,
    )

    await stop_event.wait()
    logger.info("Shutting down AI ChatOps Agent gracefully...")

    uvicorn_server.should_exit = True
    await bot_app.updater.stop()
    await bot_app.stop()
    await bot_app.shutdown()
    await asyncio.gather(server_task, watcher_task, return_exceptions=True)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
