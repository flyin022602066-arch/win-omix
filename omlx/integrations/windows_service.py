# SPDX-License-Identifier: Apache-2.0
"""
Windows Service management for oMLX.

Provides Windows Service integration using:
- pywin32 for native Windows Service API
- NSSM (Non-Sucking Service Manager) as alternative
- sc.exe for service control
"""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Service configuration
SERVICE_NAME = "oMLX"
SERVICE_DISPLAY_NAME = "oMLX LLM Inference Server"
SERVICE_DESCRIPTION = "Local LLM inference server optimized for Windows with DirectML acceleration"

# Default paths
DEFAULT_MODEL_DIR = Path.home() / ".omlx" / "models"
DEFAULT_LOG_DIR = Path.home() / ".omlx" / "logs"
DEFAULT_CONFIG_DIR = Path.home() / ".omlx"


class WindowsServiceManager:
    """
    Windows Service manager for oMLX.
    
    Supports two modes:
    1. Native Windows Service using pywin32
    2. NSSM-based service (lighter weight alternative)
    """
    
    def __init__(self, use_nssm: bool = False):
        """
        Initialize service manager.
        
        Args:
            use_nssm: Use NSSM instead of pywin32
        """
        self.use_nssm = use_nssm
        self.service_installed = self._check_service_installed()
    
    def _check_service_installed(self) -> bool:
        """Check if oMLX service is installed."""
        try:
            result = subprocess.run(
                ["sc", "query", SERVICE_NAME],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def install(
        self,
        model_dir: Optional[Path] = None,
        port: int = 8000,
        host: str = "127.0.0.1",
        auto_start: bool = True,
    ) -> bool:
        """
        Install oMLX as a Windows service.
        
        Args:
            model_dir: Model directory path
            port: Server port
            host: Server host
            auto_start: Auto-start service on boot
        
        Returns:
            True if successful
        """
        model_dir = model_dir or DEFAULT_MODEL_DIR
        
        logger.info(f"Installing {SERVICE_NAME} service")
        
        if self.use_nssm:
            return self._install_nssm(model_dir, port, host, auto_start)
        else:
            return self._install_pywin32(model_dir, port, host, auto_start)
    
    def _install_pywin32(self, model_dir: Path, port: int, host: str, auto_start: bool) -> bool:
        """Install using pywin32."""
        try:
            import win32service
            import win32serviceutil
            import servicemanager
        except ImportError:
            logger.error("pywin32 not installed. Install with: pip install pywin32")
            print("Error: pywin32 not installed.")
            print("Install with: pip install pywin32")
            print("Or use NSSM: omlx service install --nssm")
            return False
        
        try:
            # Get Python executable path
            python_exe = sys.executable
            
            # Get service script path
            service_script = Path(__file__).parent / "windows_service_host.py"
            
            # Build command line
            cmd_line = (
                f'"{python_exe}" "{service_script}" '
                f"--model-dir \"{model_dir}\" "
                f"--port {port} "
                f"--host {host}"
            )
            
            # Install service
            win32serviceutil.InstallService(
                serviceName=SERVICE_NAME,
                displayName=SERVICE_DISPLAY_NAME,
                startType=win32service.SERVICE_AUTO_START if auto_start else win32service.SERVICE_DEMAND_START,
                bRunInteractive=0,
                lpdsvPath=None,
                lpServiceStartName=None,
                lpPassword=None,
                lpArguments=cmd_line,
                lpDescription=SERVICE_DESCRIPTION,
            )
            
            logger.info(f"Service {SERVICE_NAME} installed successfully")
            print(f"✓ Service '{SERVICE_NAME}' installed")
            print(f"  Display name: {SERVICE_DISPLAY_NAME}")
            print(f"  Model directory: {model_dir}")
            print(f"  Port: {port}")
            
            if auto_start:
                print(f"  Auto-start: Enabled (will start on boot)")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to install service: {e}")
            print(f"✗ Failed to install service: {e}")
            return False
    
    def _install_nssm(self, model_dir: Path, port: int, host: str, auto_start: bool) -> bool:
        """Install using NSSM."""
        try:
            # Check if NSSM is available
            nssm_path = self._find_nssm()
            
            if not nssm_path:
                logger.error("NSSM not found. Please install NSSM or use pywin32.")
                print("Error: NSSM not found.")
                print("Download from: https://nssm.cc/download")
                print("Or use pywin32: omlx service install --pywin32")
                return False
            
            # Get Python executable path
            python_exe = sys.executable
            
            # Get service script path
            service_script = Path(__file__).parent / "windows_service_host.py"
            
            # Install service
            subprocess.run(
                [
                    nssm_path,
                    "install",
                    SERVICE_NAME,
                    python_exe,
                    str(service_script),
                    "--model-dir", str(model_dir),
                    "--port", str(port),
                    "--host", host,
                ],
                check=True,
            )
            
            # Set service description
            subprocess.run(
                [nssm_path, "set", SERVICE_NAME, "Description", SERVICE_DESCRIPTION],
                check=True,
            )
            
            # Set log directory
            subprocess.run(
                [nssm_path, "set", SERVICE_NAME, "AppStdout", str(DEFAULT_LOG_DIR / "service.log")],
                check=True,
            )
            subprocess.run(
                [nssm_path, "set", SERVICE_NAME, "AppStderr", str(DEFAULT_LOG_DIR / "service.error.log")],
                check=True,
            )
            
            # Set auto-start
            if auto_start:
                subprocess.run(
                    [nssm_path, "set", SERVICE_NAME, "Start", "SERVICE_AUTO_START"],
                    check=True,
                )
            
            logger.info(f"Service {SERVICE_NAME} installed via NSSM")
            print(f"✓ Service '{SERVICE_NAME}' installed via NSSM")
            return True
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install service via NSSM: {e}")
            print(f"✗ Failed to install service: {e}")
            return False
    
    def _find_nssm(self) -> Optional[str]:
        """Find NSSM executable."""
        # Check PATH
        nssm_paths = [
            "nssm.exe",
            r"C:\Windows\System32\nssm.exe",
            r"C:\Program Files\nssm\nssm.exe",
        ]
        
        for path in nssm_paths:
            try:
                result = subprocess.run(
                    [path, "version"],
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return path
            except Exception:
                pass
        
        return None
    
    def uninstall(self) -> bool:
        """Uninstall the service."""
        logger.info(f"Uninstalling {SERVICE_NAME} service")
        
        # Stop service first if running
        self.stop()
        
        if self.use_nssm:
            return self._uninstall_nssm()
        else:
            return self._uninstall_pywin32()
    
    def _uninstall_pywin32(self) -> bool:
        """Uninstall using pywin32."""
        try:
            import win32serviceutil
            
            win32serviceutil.RemoveService(SERVICE_NAME)
            logger.info(f"Service {SERVICE_NAME} uninstalled")
            print(f"✓ Service '{SERVICE_NAME}' uninstalled")
            return True
        
        except Exception as e:
            logger.error(f"Failed to uninstall service: {e}")
            print(f"✗ Failed to uninstall service: {e}")
            return False
    
    def _uninstall_nssm(self) -> bool:
        """Uninstall using NSSM."""
        try:
            nssm_path = self._find_nssm()
            
            if not nssm_path:
                logger.error("NSSM not found")
                print("Error: NSSM not found")
                return False
            
            subprocess.run([nssm_path, "remove", SERVICE_NAME, "confirm"], check=True)
            logger.info(f"Service {SERVICE_NAME} uninstalled via NSSM")
            print(f"✓ Service '{SERVICE_NAME}' uninstalled")
            return True
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to uninstall service: {e}")
            print(f"✗ Failed to uninstall service: {e}")
            return False
    
    def start(self) -> bool:
        """Start the service."""
        logger.info(f"Starting {SERVICE_NAME} service")
        
        try:
            subprocess.run(
                ["sc", "start", SERVICE_NAME],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            logger.info(f"Service {SERVICE_NAME} started")
            print(f"✓ Service '{SERVICE_NAME}' started")
            return True
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start service: {e}")
            print(f"✗ Failed to start service: {e.output}")
            return False
        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            print(f"✗ Failed to start service: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the service."""
        logger.info(f"Stopping {SERVICE_NAME} service")
        
        try:
            subprocess.run(
                ["net", "stop", SERVICE_NAME],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            logger.info(f"Service {SERVICE_NAME} stopped")
            print(f"✓ Service '{SERVICE_NAME}' stopped")
            return True
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stop service: {e}")
            print(f"✗ Failed to stop service: {e.output}")
            return False
        except Exception as e:
            logger.error(f"Failed to stop service: {e}")
            print(f"✗ Failed to stop service: {e}")
            return False
    
    def status(self) -> dict:
        """Get service status."""
        status_info = {
            "installed": self.service_installed,
            "running": False,
            "state": "Unknown",
        }
        
        if not self.service_installed:
            return status_info
        
        try:
            result = subprocess.run(
                ["sc", "query", SERVICE_NAME],
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            if result.returncode == 0:
                output = result.stdout
                
                # Parse state
                if "RUNNING" in output:
                    status_info["running"] = True
                    status_info["state"] = "Running"
                elif "STOPPED" in output:
                    status_info["state"] = "Stopped"
                elif "START_PENDING" in output:
                    status_info["state"] = "Starting"
                elif "STOP_PENDING" in output:
                    status_info["state"] = "Stopping"
        
        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            status_info["state"] = f"Error: {e}"
        
        return status_info
    
    def configure(
        self,
        auto_start: Optional[bool] = None,
        log_dir: Optional[Path] = None,
        model_dir: Optional[Path] = None,
    ) -> bool:
        """
        Configure service settings.
        
        Args:
            auto_start: Auto-start on boot
            log_dir: Log directory
            model_dir: Model directory
        
        Returns:
            True if successful
        """
        if not self.service_installed:
            logger.error("Service not installed")
            print("Error: Service not installed. Install first.")
            return False
        
        if auto_start is not None:
            try:
                start_type = "auto" if auto_start else "demand"
                subprocess.run(
                    ["sc", "config", SERVICE_NAME, "start=", start_type],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                logger.info(f"Service auto-start set to: {auto_start}")
            except Exception as e:
                logger.error(f"Failed to configure auto-start: {e}")
                return False
        
        if log_dir or model_dir:
            logger.warning("To change log/model directory, reinstall the service")
            print("Note: To change log/model directory, please reinstall the service:")
            print("  1. omlx service uninstall")
            print("  2. omlx service install --log-dir <path> --model-dir <path>")
        
        return True


def main():
    """CLI for service management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="oMLX Windows Service Manager")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Install command
    install_parser = subparsers.add_parser("install", help="Install oMLX as a Windows service")
    install_parser.add_argument(
        "--model-dir",
        type=str,
        default=str(DEFAULT_MODEL_DIR),
        help=f"Model directory (default: {DEFAULT_MODEL_DIR})"
    )
    install_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Server port (default: 8000)"
    )
    install_parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Server host (default: 127.0.0.1)"
    )
    install_parser.add_argument(
        "--no-auto-start",
        action="store_true",
        help="Disable auto-start on boot"
    )
    install_parser.add_argument(
        "--nssm",
        action="store_true",
        help="Use NSSM instead of pywin32"
    )
    
    # Uninstall command
    subparsers.add_parser("uninstall", help="Uninstall oMLX service")
    
    # Start command
    subparsers.add_parser("start", help="Start oMLX service")
    
    # Stop command
    subparsers.add_parser("stop", help="Stop oMLX service")
    
    # Status command
    subparsers.add_parser("status", help="Show oMLX service status")
    
    # Configure command
    config_parser = subparsers.add_parser("configure", help="Configure oMLX service")
    config_parser.add_argument(
        "--auto-start",
        action="store_true",
        help="Enable auto-start on boot"
    )
    config_parser.add_argument(
        "--no-auto-start",
        action="store_true",
        help="Disable auto-start on boot"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Create service manager
    manager = WindowsServiceManager(use_nssm=args.nssm if hasattr(args, 'nssm') else False)
    
    # Execute command
    if args.command == "install":
        manager.install(
            model_dir=Path(args.model_dir),
            port=args.port,
            host=args.host,
            auto_start=not args.no_auto_start,
        )
    
    elif args.command == "uninstall":
        manager.uninstall()
    
    elif args.command == "start":
        manager.start()
    
    elif args.command == "stop":
        manager.stop()
    
    elif args.command == "status":
        status = manager.status()
        print(f"Service: {SERVICE_NAME}")
        print(f"Installed: {status['installed']}")
        print(f"Running: {status['running']}")
        print(f"State: {status['state']}")
    
    elif args.command == "configure":
        if args.auto_start:
            manager.configure(auto_start=True)
        elif args.no_auto_start:
            manager.configure(auto_start=False)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
