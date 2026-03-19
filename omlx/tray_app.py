# SPDX-License-Identifier: Apache-2.0
"""
Windows system tray application for oMLX.

Provides a system tray icon for:
- Starting/stopping the oMLX server
- Viewing server status and statistics
- Quick access to admin panel and logs
- Model management
"""

import logging
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import requests

# Optional imports
try:
    import pystray
    from pystray import Icon, MenuItem, Menu
    
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False
    pystray = None

try:
    from PIL import Image, ImageDraw
    
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False
    Image = None

logger = logging.getLogger(__name__)

# Server configuration
DEFAULT_SERVER_HOST = "127.0.0.1"
DEFAULT_SERVER_PORT = 8000
DEFAULT_MODEL_DIR = Path.home() / ".omlx" / "models"


class oMLXTrayApp:
    """System tray application for oMLX."""
    
    def __init__(self):
        """Initialize the tray application."""
        self.icon: Optional[Icon] = None
        self.server_process: Optional[subprocess.Popen] = None
        self.server_running = False
        self.server_url = f"http://{DEFAULT_SERVER_HOST}:{DEFAULT_SERVER_PORT}"
        
        # Statistics
        self.stats = {
            "uptime": 0,
            "requests_processed": 0,
            "models_loaded": 0,
            "memory_usage_mb": 0,
        }
        
        # Create icon image
        self.icon_image = self._create_icon_image()
        
        logger.info("oMLX Tray Application initialized")
    
    def _create_icon_image(self) -> Image.Image:
        """Create a simple icon image programmatically."""
        if not HAS_PILLOW:
            return None
        
        # Create a 64x64 icon
        img = Image.new("RGB", (64, 64), color="#2196F3")
        draw = ImageDraw.Draw(img)
        
        # Draw a circle
        draw.ellipse([8, 8, 56, 56], fill="#64B5F6")
        
        # Draw "oMLX" text
        draw.text(
            (16, 24),
            "oM",
            fill="#0D47A1",
            font=None  # Use default font
        )
        
        return img
    
    def run(self) -> None:
        """Run the tray application."""
        if not HAS_PYSTRAY:
            logger.error("pystray not installed. Install with: pip install pystray")
            print("Error: pystray not installed.")
            print("Install with: pip install pystray Pillow")
            return
        
        # Create menu
        menu = Menu(
            MenuItem("Start Server", self._start_server, enabled=lambda: not self.server_running),
            MenuItem("Stop Server", self._stop_server, enabled=lambda: self.server_running),
            MenuItem("Open Admin Panel", self._open_admin),
            MenuItem("View Logs", self._view_logs),
            MenuItem("Model Directory", self._open_model_dir),
            MenuItem("-", None),  # Separator
            MenuItem("Statistics", self._show_stats),
            MenuItem("-", None),  # Separator
            MenuItem("Exit", self._exit_app),
        )
        
        # Create and run icon
        self.icon = Icon(
            "omlx",
            self.icon_image,
            "oMLX - LLM Inference Server",
            menu
        )
        
        logger.info("Starting tray icon")
        self.icon.run()
    
    def _start_server(self, icon: Icon, item: MenuItem) -> None:
        """Start the oMLX server."""
        if self.server_running:
            logger.warning("Server already running")
            return
        
        try:
            logger.info("Starting oMLX server")
            
            # Build command
            cmd = [
                sys.executable,
                "-m",
                "omlx.cli",
                "serve",
                "--model-dir",
                str(DEFAULT_MODEL_DIR),
                "--host",
                DEFAULT_SERVER_HOST,
                "--port",
                str(DEFAULT_SERVER_PORT),
            ]
            
            # Start server process
            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            
            # Wait for server to start
            threading.Thread(target=self._wait_for_server, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            self._show_notification(f"Failed to start server: {e}")
    
    def _wait_for_server(self) -> None:
        """Wait for server to become available."""
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            time.sleep(1)
            attempt += 1
            
            try:
                response = requests.get(f"{self.server_url}/health", timeout=2)
                if response.status_code == 200:
                    self.server_running = True
                    self.stats["uptime"] = time.time()
                    logger.info("Server started successfully")
                    self._show_notification("oMLX Server started")
                    
                    # Start stats updater
                    threading.Thread(target=self._update_stats_loop, daemon=True).start()
                    break
            except Exception:
                pass
        
        if not self.server_running:
            logger.error("Server failed to start")
            self._show_notification("Server failed to start")
    
    def _stop_server(self, icon: Icon, item: MenuItem) -> None:
        """Stop the oMLX server."""
        if not self.server_running:
            logger.warning("Server not running")
            return
        
        try:
            logger.info("Stopping oMLX server")
            
            if self.server_process:
                self.server_process.terminate()
                self.server_process.wait(timeout=10)
                self.server_process = None
            
            self.server_running = False
            self.stats["uptime"] = 0
            
            self._show_notification("oMLX Server stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop server: {e}")
            self._show_notification(f"Failed to stop server: {e}")
            
            # Force kill if terminate failed
            if self.server_process:
                self.server_process.kill()
                self.server_process = None
    
    def _open_admin(self, icon: Icon, item: MenuItem) -> None:
        """Open admin panel in default browser."""
        admin_url = f"{self.server_url}/admin"
        
        try:
            import webbrowser
            
            webbrowser.open(admin_url)
            logger.info(f"Opened admin panel: {admin_url}")
        except Exception as e:
            logger.error(f"Failed to open admin panel: {e}")
            self._show_notification(f"Failed to open admin panel: {e}")
    
    def _view_logs(self, icon: Icon, item: MenuItem) -> None:
        """Open logs directory."""
        log_dir = Path.home() / ".omlx" / "logs"
        
        try:
            if not log_dir.exists():
                log_dir.mkdir(parents=True, exist_ok=True)
            
            # Open file explorer
            if sys.platform == "win32":
                subprocess.run(["explorer", str(log_dir)], check=True)
            else:
                subprocess.run(["xdg-open", str(log_dir)], check=True)
            
            logger.info(f"Opened logs directory: {log_dir}")
        except Exception as e:
            logger.error(f"Failed to open logs directory: {e}")
            self._show_notification(f"Failed to open logs: {e}")
    
    def _open_model_dir(self, icon: Icon, item: MenuItem) -> None:
        """Open model directory."""
        try:
            if not DEFAULT_MODEL_DIR.exists():
                DEFAULT_MODEL_DIR.mkdir(parents=True, exist_ok=True)
            
            # Open file explorer
            if sys.platform == "win32":
                subprocess.run(["explorer", str(DEFAULT_MODEL_DIR)], check=True)
            else:
                subprocess.run(["xdg-open", str(DEFAULT_MODEL_DIR)], check=True)
            
            logger.info(f"Opened model directory: {DEFAULT_MODEL_DIR}")
        except Exception as e:
            logger.error(f"Failed to open model directory: {e}")
            self._show_notification(f"Failed to open model directory: {e}")
    
    def _show_stats(self, icon: Icon, item: MenuItem) -> None:
        """Show server statistics."""
        stats_text = self._format_stats()
        
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            root = tk.Tk()
            root.withdraw()  # Hide main window
            
            messagebox.showinfo("oMLX Statistics", stats_text)
            
            root.destroy()
        except Exception as e:
            logger.error(f"Failed to show stats: {e}")
            print(stats_text)
    
    def _format_stats(self) -> str:
        """Format statistics as text."""
        uptime = self.stats.get("uptime", 0)
        
        if uptime > 0:
            uptime_seconds = int(time.time() - uptime)
            hours = uptime_seconds // 3600
            minutes = (uptime_seconds % 3600) // 60
            seconds = uptime_seconds % 60
            uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            uptime_str = "Not running"
        
        return (
            f"oMLX Server Statistics\n"
            f"{'='*40}\n"
            f"Status: {'Running' if self.server_running else 'Stopped'}\n"
            f"Uptime: {uptime_str}\n"
            f"Requests: {self.stats.get('requests_processed', 0)}\n"
            f"Models Loaded: {self.stats.get('models_loaded', 0)}\n"
            f"Memory: {self.stats.get('memory_usage_mb', 0):.1f} MB\n"
            f"URL: {self.server_url}"
        )
    
    def _update_stats_loop(self) -> None:
        """Periodically update statistics."""
        while self.server_running:
            time.sleep(5)
            
            try:
                response = requests.get(f"{self.server_url}/admin/stats", timeout=2)
                if response.ok:
                    data = response.json()
                    self.stats.update(data)
            except Exception:
                pass
    
    def _exit_app(self, icon: Icon, item: MenuItem) -> None:
        """Exit the application."""
        logger.info("Exiting oMLX Tray Application")
        
        # Stop server if running
        if self.server_running:
            self._stop_server(icon, item)
        
        # Stop icon
        if self.icon:
            self.icon.stop()
    
    def _show_notification(self, message: str) -> None:
        """Show a notification."""
        logger.info(f"Notification: {message}")
        
        if self.icon and HAS_PYSTRAY:
            self.icon.notify(message)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="oMLX System Tray Application")
    parser.add_argument(
        "--host",
        type=str,
        default=DEFAULT_SERVER_HOST,
        help=f"Server host (default: {DEFAULT_SERVER_HOST})"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_SERVER_PORT,
        help=f"Server port (default: {DEFAULT_SERVER_PORT})"
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        default=str(DEFAULT_MODEL_DIR),
        help=f"Model directory (default: {DEFAULT_MODEL_DIR})"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Update configuration
    global DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT, DEFAULT_MODEL_DIR
    DEFAULT_SERVER_HOST = args.host
    DEFAULT_SERVER_PORT = args.port
    DEFAULT_MODEL_DIR = Path(args.model_dir)
    
    # Run application
    app = oMLXTrayApp()
    app.run()


if __name__ == "__main__":
    main()
