"""Entry point for JARVIS. Run with: python run.py"""
import threading
import time
import webbrowser

import uvicorn

from jarvis.server.app import app, settings
from jarvis.utils.logger import get_logger

log = get_logger("run")


def _start_server(host: str, port: int) -> None:
    uvicorn.run(app, host=host, port=port, log_level="warning")


def main() -> None:
    host = settings["server"]["host"]
    port = settings["server"]["port"]
    url = f"http://{host}:{port}"

    server_thread = threading.Thread(target=_start_server, args=(host, port), daemon=True)
    server_thread.start()
    time.sleep(1.0)  # give uvicorn a moment to bind before opening the window

    if settings["server"]["open_in_app_window"]:
        try:
            import webview

            webview.create_window("JARVIS", url, width=1200, height=800, background_color="#05070d")
            webview.start()
            return
        except ImportError:
            log.info("pywebview not installed; opening in the default browser instead.")

    webbrowser.open(url)
    log.info("JARVIS is running at %s (Ctrl+C to stop)", url)
    try:
        while server_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
