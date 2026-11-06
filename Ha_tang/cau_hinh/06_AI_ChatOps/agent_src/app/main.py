import asyncio
import logging
import signal

import uvicorn
from fastapi import FastAPI

from app.bot import build_telegram_application
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("chatops.main")


def create_health_api() -> FastAPI:
    api = FastAPI(title="KLTN ChatOps Health Probe (v1.0)", docs_url=None, redoc_url=None)

    @api.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "version": "1.0.0"}

    return api


async def async_main() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    bot_app = build_telegram_application()
    uvicorn_cfg = uvicorn.Config(
        app=create_health_api(),
        host="127.0.0.1",
        port=settings.health_port,
        log_level="warning",
        access_log=False,
    )
    uvicorn_server = uvicorn.Server(uvicorn_cfg)

    logger.info("Initializing Telegram Bot Async Long-Polling (v1.0 — Read-Only SRE)...")
    await bot_app.initialize()
    await bot_app.start()
    assert bot_app.updater is not None
    await bot_app.updater.start_polling(drop_pending_updates=True)

    server_task = asyncio.create_task(uvicorn_server.serve(), name="health-probe-server")
    logger.info("AI ChatOps SRE Agent v1.0 is LIVE (TargetNamespace=%s).", settings.target_app_namespace)

    await stop_event.wait()
    logger.info("Shutting down AI ChatOps Agent v1.0 gracefully...")

    uvicorn_server.should_exit = True
    await bot_app.updater.stop()
    await bot_app.stop()
    await bot_app.shutdown()
    await asyncio.gather(server_task, return_exceptions=True)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
