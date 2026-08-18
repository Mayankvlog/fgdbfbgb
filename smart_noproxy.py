#!/usr/bin/env python3
"""
Adsterra Smartlink Opener V2 - Multi-traffic automation with proxy support
Opens Adsterra smartlinks using different user profiles, device fingerprints, and proxies
Enhanced with fake-useragent package for realistic user agent generation
"""

import asyncio
import json
import os
import sys
import random
import time
from pathlib import Path
from flask import request
from playwright.async_api import (
    Browser,
    BrowserType,
    Playwright,
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlparse
from fake_useragent import UserAgent
import requests


class TrafficStats:
    """Track traffic statistics with detailed logging."""

    def __init__(self):
        self.total_opens = 0
        self.successful_opens = 0
        self.failed_opens = 0
        self.profile_stats = {}
        self.start_time = datetime.now()
        self.detailed_logs = []  # List of all operations with details
        self.cycle_stats = []  # List of cycle statistics

    def record_success(
        self, profile_name: str, url: str, final_url: str = None, duration: float = None
    ):
        """Record a successful open."""
        self.total_opens += 1
        self.successful_opens += 1
        if profile_name not in self.profile_stats:
            self.profile_stats[profile_name] = {"success": 0, "failed": 0}
        self.profile_stats[profile_name]["success"] += 1

        # Log detailed information
        self.detailed_logs.append(
            {
                "timestamp": datetime.now().isoformat(),
                "profile": profile_name,
                "url": url,
                "final_url": final_url or url,
                "status": "success",
                "duration": duration,
                "error": None,
            }
        )

    def record_failure(
        self, profile_name: str, url: str, error: str = None, duration: float = None
    ):
        """Record a failed open."""
        self.total_opens += 1
        self.failed_opens += 1
        if profile_name not in self.profile_stats:
            self.profile_stats[profile_name] = {"success": 0, "failed": 0}
        self.profile_stats[profile_name]["failed"] += 1

        # Log detailed information
        self.detailed_logs.append(
            {
                "timestamp": datetime.now().isoformat(),
                "profile": profile_name,
                "url": url,
                "final_url": None,
                "status": "failed",
                "duration": duration,
                "error": error or "Unknown error",
            }
        )

    def record_cycle(
        self,
        cycle_num: int,
        cycle_success: int,
        cycle_failed: int,
        cycle_duration: float,
    ):
        """Record cycle statistics."""
        self.cycle_stats.append(
            {
                "cycle": cycle_num,
                "timestamp": datetime.now().isoformat(),
                "success": cycle_success,
                "failed": cycle_failed,
                "total": cycle_success + cycle_failed,
                "duration": cycle_duration,
            }
        )

    def print_summary(self):
        """Print statistics summary."""
        duration = datetime.now() - self.start_time
        print("\n" + "=" * 60)
        print("TRAFFIC STATISTICS SUMMARY")
        print("=" * 60)
        print(f"Total Opens: {self.total_opens}")
        print(
            f"Successful: {self.successful_opens} ({self.successful_opens/max(self.total_opens,1)*100:.1f}%)"
        )
        print(
            f"Failed: {self.failed_opens} ({self.failed_opens/max(self.total_opens,1)*100:.1f}%)"
        )
        print(f"Duration: {duration}")
        print(
            f"Average Rate: {self.total_opens/max(duration.total_seconds(),1):.2f} opens/sec"
        )
        print("\nPer Profile:")
        for profile, stats in self.profile_stats.items():
            total = stats["success"] + stats["failed"]
            print(f"  {profile}: {stats['success']}/{total} successful")
        print("=" * 60)

    def generate_html_report(self, output_path: str = "traffic_report.html"):
        """Generate an HTML report with detailed statistics."""
        duration = datetime.now() - self.start_time
        success_rate = (self.successful_opens / max(self.total_opens, 1)) * 100
        failure_rate = (self.failed_opens / max(self.total_opens, 1)) * 100

        # Generate profile stats HTML
        profile_rows = ""
        for profile, stats in sorted(self.profile_stats.items()):
            total = stats["success"] + stats["failed"]
            profile_success_rate = (stats["success"] / max(total, 1)) * 100
            profile_rows += f"""
            <tr>
                <td>{profile[:50]}</td>
                <td>{total}</td>
                <td><span class="badge success">{stats['success']}</span></td>
                <td><span class="badge failed">{stats['failed']}</span></td>
                <td>{profile_success_rate:.1f}%</td>
            </tr>
            """

        # Generate cycle stats HTML
        cycle_rows = ""
        for cycle in self.cycle_stats:
            cycle_success_rate = (cycle["success"] / max(cycle["total"], 1)) * 100
            cycle_rows += f"""
            <tr>
                <td>#{cycle['cycle']}</td>
                <td>{cycle['timestamp'][:19]}</td>
                <td>{cycle['total']}</td>
                <td><span class="badge success">{cycle['success']}</span></td>
                <td><span class="badge failed">{cycle['failed']}</span></td>
                <td>{cycle_success_rate:.1f}%</td>
                <td>{cycle['duration']:.1f}s</td>
            </tr>
            """

        # Generate recent logs HTML (last 50)
        recent_logs = (
            self.detailed_logs[-50:]
            if len(self.detailed_logs) > 50
            else self.detailed_logs
        )
        log_rows = ""
        for log in reversed(recent_logs):
            status_class = "success" if log["status"] == "success" else "failed"
            log_rows += f"""
            <tr>
                <td>{log['timestamp'][:19]}</td>
                <td>{log['profile'][:30]}</td>
                <td><a href="{log['url']}" target="_blank">{log['url'][:50]}...</a></td>
                <td>{log['final_url'][:50] + '...' if log['final_url'] and len(log['final_url']) > 50 else (log['final_url'] or 'N/A')}</td>
                <td><span class="badge {status_class}">{log['status']}</span></td>
                <td>{'{:.1f}s'.format(log['duration']) if log['duration'] else 'N/A'}</td>
                <td>{log['error'] or '-'}</td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Adsterra Smartlink Opener - Traffic Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 3px solid #667eea;
        }}
        
        .header h1 {{
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .header p {{
            color: #666;
            font-size: 1.1em;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }}
        
        .stat-card.success {{
            background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);
        }}
        
        .stat-card.failed {{
            background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
        }}
        
        .stat-card.info {{
            background: linear-gradient(135deg, #2196f3 0%, #1976d2 100%);
        }}
        
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        
        .stat-label {{
            font-size: 1em;
            opacity: 0.9;
        }}
        
        .section {{
            margin-bottom: 40px;
        }}
        
        .section-title {{
            font-size: 1.5em;
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        th {{
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        
        td {{
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        tr:hover {{
            background: #f9f9f9;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        
        .badge.success {{
            background: #4caf50;
            color: white;
        }}
        
        .badge.failed {{
            background: #f44336;
            color: white;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            color: #666;
        }}
        
        a {{
            color: #667eea;
            text-decoration: none;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Traffic Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card info">
                <div class="stat-value">{self.total_opens}</div>
                <div class="stat-label">Total Opens</div>
            </div>
            <div class="stat-card success">
                <div class="stat-value">{self.successful_opens}</div>
                <div class="stat-label">Successful ({success_rate:.1f}%)</div>
            </div>
            <div class="stat-card failed">
                <div class="stat-value">{self.failed_opens}</div>
                <div class="stat-label">Failed ({failure_rate:.1f}%)</div>
            </div>
            <div class="stat-card info">
                <div class="stat-value">{duration.total_seconds():.0f}s</div>
                <div class="stat-label">Duration</div>
            </div>
            <div class="stat-card info">
                <div class="stat-value">{self.total_opens/max(duration.total_seconds(),1):.2f}</div>
                <div class="stat-label">Opens/sec</div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">Profile Statistics</h2>
            <table>
                <thead>
                    <tr>
                        <th>Profile</th>
                        <th>Total</th>
                        <th>Success</th>
                        <th>Failed</th>
                        <th>Success Rate</th>
                    </tr>
                </thead>
                <tbody>
                    {profile_rows}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2 class="section-title">Cycle Statistics</h2>
            <table>
                <thead>
                    <tr>
                        <th>Cycle</th>
                        <th>Timestamp</th>
                        <th>Total</th>
                        <th>Success</th>
                        <th>Failed</th>
                        <th>Success Rate</th>
                        <th>Duration</th>
                    </tr>
                </thead>
                <tbody>
                    {cycle_rows}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2 class="section-title">Recent Activity (Last 50)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Profile</th>
                        <th>URL</th>
                        <th>Final URL</th>
                        <th>Status</th>
                        <th>Duration</th>
                        <th>Error</th>
                    </tr>
                </thead>
                <tbody>
                    {log_rows}
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Report generated by Adsterra Smartlink Opener</p>
            <p>Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
        """

        # Write HTML file
        output_file = Path(output_path)
        output_file.write_text(html_content, encoding="utf-8")
        return output_file.absolute()


class AdsterraSmartlinkOpener:
    def __init__(self, config_path: str = "config.json"):
        """Initialize the Adsterra Smartlink Opener with configuration."""
        self.config_path = config_path
        self.config = self._load_config()
        self.profiles_dir = Path("profiles")
        self.profiles_dir.mkdir(exist_ok=True)
        self.stats = TrafficStats()

        # Initialize UserAgent generator
        try:
            self.ua = UserAgent(
                browsers=["Edge", "Safari", "Chrome"],
                platforms=["desktop"],
                fallback="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3.1 Safari/605.1.15",
            )
            print("✓ UserAgent generator initialized")
        except Exception as e:
            print(f"⚠ Warning: Failed to initialize UserAgent generator: {e}")
            print("  Falling back to manual user agent generation")
            self.ua = None

        # Proxy list - format: username:password
        # These will be randomly selected for each smartlink visit
        self.proxy_credentials = [
            "zhogyichan.custom36:hello123",
            "zhogyichan.custom38:hello123",
        ]

        # Proxy server configuration (adjust if your proxy service uses different host/port)
        # Common proxy services:
        # - Bright Data: zproxy.lum-superproxy.io:22225
        # - Smartproxy: gateway.smartproxy.com:10000
        # - ProxyEmpire: rotating-residential.proxyempire.io:8080
        # Update these to match your proxy service
        self.proxy_server_host = "154.198.32.71"  # Update this to your proxy server
        self.proxy_server_port = 8083  # Update this to your proxy port

    def _load_config(self) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file {self.config_path} not found!")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")

    def _get_profile_path(self, profile_name: str) -> Path:
        """Get the path for a user profile directory."""
        return self.profiles_dir / profile_name

    def _parse_proxy(self, proxy_string: Optional[str]) -> Optional[Dict]:
        """Parse proxy string into Playwright format.

        Supports formats:
        - http://user:pass@host:port
        - socks5://user:pass@host:port
        - host:port (defaults to http)
        - username:password (constructs full URL using proxy_server_host/port)
        """
        if not proxy_string:
            return None

        try:
            # If format is "username:password" (no @ or ://), construct full proxy URL
            if "://" not in proxy_string and "@" not in proxy_string:
                if ":" in proxy_string:
                    parts = proxy_string.split(":", 1)
                    if len(parts) == 2:
                        username = parts[0]
                        password = parts[1]
                        # Construct full proxy URL
                        proxy_string = f"http://{username}:{password}@{self.proxy_server_host}:{self.proxy_server_port}"

            # If no protocol, assume http
            if not proxy_string.startswith(("http://", "https://", "socks5://")):
                proxy_string = f"http://{proxy_string}"

            parsed = urlparse(proxy_string)

            proxy_dict = {
                "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
            }

            if parsed.username and parsed.password:
                proxy_dict["username"] = parsed.username
                proxy_dict["password"] = parsed.password

            return proxy_dict
        except Exception as e:
            print(f"Warning: Invalid proxy format '{proxy_string}': {e}")
            return None

    def _get_random_proxy(self) -> Optional[str]:
        """Get a random proxy from the proxy list."""
        if not self.proxy_credentials:
            return None
        return random.choice(self.proxy_credentials)

    async def _create_browser_and_context(self, chromium: BrowserType, profile: Dict):
        """Create a browser instance and context with custom fingerprint, profile, and proxy."""
        profile_path = self._get_profile_path(profile["name"])
        # profile_path.mkdir(exist_ok=True)

        # Parse proxy configuration
        proxy_config = self._parse_proxy(profile.get("proxy"))

        # Browser arguments - minimal set to avoid crashes
        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            # '--disable-crash-reporter',
            "--disable-breakpad",
            "--disable-logging",
            "--log-level=3",
            "--disable-infobars",
            "--disable-notifications",
            "--disable-background-networking",
            "--disable-background-timer-throttling",
        ]

        # Only add --no-sandbox on Linux, not on macOS
        if sys.platform != "darwin":
            args.append("--no-sandbox")

        # Launch browser first (more stable than persistent context)
        try:
            browser = await chromium.launch(
                headless=self.config["settings"]["headless"],
                args=args,
                ignore_default_args=["--enable-automation", "--metrics-recording-only"],
            )

            # Create context with profile settings
            context_options = {
                "viewport": {
                    "width": profile["viewport"]["width"],
                    "height": profile["viewport"]["height"],
                },
                "locale": profile["locale"],
                "timezone_id": profile["timezone"],
                "user_agent": profile["user_agent"],
                "extra_http_headers": {
                    "Accept-Language": profile["locale"],
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                },
            }
            print(proxy_config, "===")
            # Add proxy if configured
            if proxy_config:
                context_options["proxy"] = proxy_config
                print(
                    f"[{profile['name']}] Using proxy: {proxy_config['server']} {proxy_config['username']}"
                )

            # Create context from browser
            context = await browser.new_context(**context_options)

            # Store profile config and browser reference for later use
            context._profile_config = profile
            context._browser = browser  # Keep browser reference to close later

            return context
        except Exception as e:
            print(
                f"Failed to create browser context for profile '{profile['name']}': {e}"
            )
            raise

    def _get_edge_user_agent_data(self, profile: Dict) -> str:
        """Generate Edge-specific userAgentData property."""
        user_agent = profile.get("user_agent", "")

        # Extract Edge and Chrome versions from user agent
        edge_version = "120.0.0.0"
        chrome_version = "141.0.0.0"

        if "Edg/" in user_agent:
            try:
                edge_version = user_agent.split("Edg/")[1].split()[0]
            except:
                pass

        if "Chrome/" in user_agent:
            try:
                chrome_version = user_agent.split("Chrome/")[1].split()[0]
            except:
                pass

        return f"""
                // Edge-specific userAgentData
                Object.defineProperty(navigator, 'userAgentData', {{
                    get: () => ({{
                        brands: [
                            {{ brand: "Microsoft Edge", version: "{edge_version}" }},
                            {{ brand: "Chromium", version: "{chrome_version}" }},
                            {{ brand: "Not A(Brand", version: "24" }}
                        ],
                        platform: "Windows",
                        platformVersion: "15.0.0",
                        architecture: "x86",
                        model: "",
                        uaFullVersion: "{edge_version}"
                    }})
                }});
        """

    def _get_safari_fingerprint_script(self, profile: Dict) -> str:
        """Generate Safari-specific fingerprinting properties."""
        user_agent = profile.get("user_agent", "")

        # Extract Safari version from user agent
        safari_version = "17.2"
        webkit_version = "605.1.15"
        if "Version/" in user_agent:
            try:
                safari_version = user_agent.split("Version/")[1].split()[0]
            except:
                pass
        if "AppleWebKit/" in user_agent:
            try:
                webkit_version = user_agent.split("AppleWebKit/")[1].split()[0]
            except:
                pass

        # Extract app version
        app_version = "5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
        if "Mozilla/" in user_agent:
            try:
                app_version = user_agent.split("Mozilla/")[1]
            except:
                pass

        return f"""
                // Safari-specific properties - comprehensive fingerprinting
                
                // Remove Chrome-specific objects
                delete window.chrome;
                if (window.chrome) {{
                    delete window.chrome;
                }}
                
                // Safari vendor (must be Apple Computer, Inc.)
                Object.defineProperty(navigator, 'vendor', {{
                    get: () => 'Apple Computer, Inc.',
                    configurable: true
                }});
                
                // Safari app version
                Object.defineProperty(navigator, 'appVersion', {{
                    get: () => '{app_version}',
                    configurable: true
                }});
                
                // Safari app name
                Object.defineProperty(navigator, 'appName', {{
                    get: () => 'Netscape',
                    configurable: true
                }});
                
                // Safari product (should be Gecko for compatibility, but Safari-specific)
                Object.defineProperty(navigator, 'product', {{
                    get: () => 'Gecko',
                    configurable: true
                }});
                
                // Safari maxTouchPoints (macOS = 0, iOS = 5)
                Object.defineProperty(navigator, 'maxTouchPoints', {{
                    get: () => 0,
                    configurable: true
                }});
                
                // Safari does NOT have userAgentData (Chrome/Edge only)
                if (navigator.userAgentData) {{
                    delete navigator.userAgentData;
                }}
                Object.defineProperty(navigator, 'userAgentData', {{
                    get: () => undefined,
                    configurable: true
                }});
                
                // Safari connection properties
                if (navigator.connection) {{
                    Object.defineProperty(navigator.connection, 'rtt', {{
                        get: () => 50 + Math.floor(Math.random() * 100),
                        configurable: true
                    }});
                    Object.defineProperty(navigator.connection, 'downlink', {{
                        get: () => 5 + Math.random() * 5,
                        configurable: true
                    }});
                }}
                
                // Safari-specific permissions
                const originalPermissions = navigator.permissions;
                if (originalPermissions && originalPermissions.query) {{
                    const originalQuery = originalPermissions.query.bind(originalPermissions);
                    navigator.permissions.query = function(parameters) {{
                        // Safari has limited permission support
                        if (parameters.name === 'notifications') {{
                            return Promise.resolve({{ state: 'default' }});
                        }}
                        return originalQuery(parameters).catch(() => Promise.resolve({{ state: 'prompt' }}));
                    }};
                }}
                
                // Safari-specific battery API (if available)
                if (navigator.getBattery) {{
                    const originalGetBattery = navigator.getBattery;
                    navigator.getBattery = function() {{
                        return originalGetBattery().catch(() => Promise.resolve({{
                            charging: true,
                            chargingTime: 0,
                            dischargingTime: Infinity,
                            level: 0.8 + Math.random() * 0.2
                        }}));
                    }};
                }}
                
                // Safari-specific media devices
                if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {{
                    const originalEnumerateDevices = navigator.mediaDevices.enumerateDevices;
                    navigator.mediaDevices.enumerateDevices = function() {{
                        return originalEnumerateDevices().catch(() => Promise.resolve([]));
                    }};
                }}
        """

    def _get_fingerprint_script(self, profile: Dict, profile_name: str) -> str:
        """Generate fingerprint injection script."""
        profile_hash = hash(profile_name) % 4
        hardware_value = 4 + profile_hash
        browser_type = profile.get("browser_type", "chrome")
        is_edge = browser_type == "edge"
        is_safari = browser_type == "safari"

        # Safari doesn't support deviceMemory
        device_memory_script = ""
        if not is_safari:
            device_memory_script = f"""
                // Device memory (not supported in Safari)
                Object.defineProperty(navigator, 'deviceMemory', {{
                    get: () => {hardware_value}
                }});"""

        # Chrome object (Safari doesn't have it)
        chrome_object_script = ""
        if not is_safari:
            chrome_object_script = """
                // Browser-specific objects
                window.chrome = {
                    runtime: {}
                };"""

        return f"""
            (function() {{
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {{
                    get: () => undefined
                }});
                
                // Platform override
                Object.defineProperty(navigator, 'platform', {{
                    get: () => '{profile.get("platform", "Win32").split(" (")[0]}'
                }});
                
                // Hardware concurrency
                Object.defineProperty(navigator, 'hardwareConcurrency', {{
                    get: () => {hardware_value}
                }});
                {device_memory_script}
                
                // WebGL fingerprinting
                {f'''
                // Safari WebGL uses native rendering, not ANGLE
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {{
                    if (parameter === 37445) {{
                        return '{profile.get("webgl_vendor", "Apple Inc.")}';
                    }}
                    if (parameter === 37446) {{
                        return '{profile.get("webgl_renderer", "Apple M1")}';
                    }}
                    return getParameter.call(this, parameter);
                }};
                ''' if is_safari else f'''
                // Chrome/Edge WebGL uses ANGLE
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {{
                    if (parameter === 37445) {{
                        return '{profile.get("webgl_vendor", "Google Inc. (NVIDIA)")}';
                    }}
                    if (parameter === 37446) {{
                        return '{profile.get("webgl_renderer", "ANGLE (NVIDIA)")}';
                    }}
                    return getParameter.call(this, parameter);
                }};
                '''}
                
                // Languages
                Object.defineProperty(navigator, 'languages', {{
                    get: () => ['{profile.get("locale", "en-US")}']
                }});
                
                // Plugins (Safari has minimal/no plugins in modern versions)
                Object.defineProperty(navigator, 'plugins', {{
                    get: () => {{
                        {'return [];' if is_safari else '''const plugins = [];
                        const pluginCount = 5;
                        for (let i = 0; i < pluginCount; i++) {
                            plugins.push({ name: `Plugin ${i}`, description: 'Plugin description' });
                        }
                        return plugins;'''}
                    }},
                    configurable: true
                }});
                
                // Safari-specific mimeTypes (empty in modern Safari)
                {'''Object.defineProperty(navigator, 'mimeTypes', {
                    get: () => [],
                    configurable: true
                });''' if is_safari else ''}
                {chrome_object_script}
                {self._get_edge_user_agent_data(profile) if is_edge else ''}
                {self._get_safari_fingerprint_script(profile) if is_safari else ''}
                
                // Permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({{ state: Notification.permission }}) :
                        originalQuery(parameters)
                );
            }})();
        """

    async def _safe_evaluate(self, page, script: str, default_value=None):
        """Safely evaluate JavaScript, handling navigation/context destruction."""
        try:
            if page.is_closed():
                return default_value
            return await page.evaluate(script)
        except Exception as e:
            # Context destroyed or page navigated - this is normal during redirects
            if "Execution context was destroyed" in str(e) or "Target closed" in str(e):
                return default_value
            raise

    async def _safe_scroll(self, page, position: int):
        """Safely scroll to position, handling navigation events."""
        try:
            if page.is_closed():
                return False
            await page.evaluate(
                f"window.scrollTo({{top: {position}, behavior: 'smooth'}})"
            )
            return True
        except Exception as e:
            # Context destroyed or page navigated - this is normal during redirects
            if "Execution context was destroyed" in str(e) or "Target closed" in str(e):
                return False
            return False

    async def _simulate_human_scrolling(self, page, duration: float):
        """Simulate human-like scrolling behavior during page visit."""
        try:
            # Check if page is still valid
            if page.is_closed():
                await asyncio.sleep(duration)
                return

            # Get page dimensions with error handling
            viewport_size = page.viewport_size
            if not viewport_size:
                viewport_size = {"width": 1920, "height": 1080}

            # Get page height safely
            page_height = await self._safe_evaluate(
                page,
                "document.body.scrollHeight || document.documentElement.scrollHeight",
                default_value=viewport_size["height"]
                * 3,  # Default to 3x viewport if can't get height
            )
            viewport_height = viewport_size["height"]

            # If we can't get page height, just wait (page might be redirecting)
            if page_height is None or page_height <= viewport_height:
                await asyncio.sleep(duration)
                return

            # Calculate scroll steps
            scroll_steps = max(3, int(duration / 2))  # Scroll every ~2 seconds
            scroll_distance = max(100, page_height / scroll_steps)

            elapsed = 0
            current_position = 0

            while elapsed < duration:
                # Check if page is still valid before each action
                if page.is_closed():
                    # If page closed, just wait remaining time
                    remaining = duration - elapsed
                    if remaining > 0:
                        await asyncio.sleep(remaining)
                    break

                # Random scroll action
                scroll_type = random.choice(["down", "down", "down", "up", "pause"])

                if (
                    scroll_type == "down"
                    and current_position < page_height - viewport_height
                ):
                    # Scroll down
                    scroll_amount = random.randint(100, min(500, int(scroll_distance)))
                    current_position = min(
                        current_position + scroll_amount, page_height - viewport_height
                    )

                    # Safely scroll
                    scroll_success = await self._safe_scroll(page, current_position)

                    if not scroll_success:
                        # Page navigated, break out
                        remaining = duration - elapsed
                        if remaining > 0:
                            await asyncio.sleep(remaining)
                        break

                    wait_time = random.uniform(0.5, 2.0)
                    await asyncio.sleep(wait_time)
                    elapsed += wait_time

                elif scroll_type == "up" and current_position > 0:
                    # Scroll up a bit (like reading)
                    scroll_amount = random.randint(50, 200)
                    current_position = max(0, current_position - scroll_amount)

                    # Safely scroll
                    scroll_success = await self._safe_scroll(page, current_position)
                    if not scroll_success:
                        # Page navigated, break out
                        remaining = duration - elapsed
                        if remaining > 0:
                            await asyncio.sleep(remaining)
                        break

                    wait_time = random.uniform(0.3, 1.5)
                    await asyncio.sleep(wait_time)
                    elapsed += wait_time

                else:
                    # Pause (reading)
                    wait_time = random.uniform(1.0, 3.0)
                    await asyncio.sleep(wait_time)
                    elapsed += wait_time

                # Random mouse movements
                if random.random() < 0.3:  # 30% chance
                    try:
                        if not page.is_closed():
                            x = random.randint(100, viewport_size["width"] - 100)
                            y = random.randint(100, viewport_size["height"] - 100)
                            await page.mouse.move(x, y)
                    except:
                        pass  # Ignore mouse movement errors

                # Check if we've used up the duration
                if elapsed >= duration:
                    break

            # Final scroll to bottom or random position (only if page is still valid)
            if not page.is_closed() and elapsed < duration:
                try:
                    if random.random() < 0.5:
                        await self._safe_scroll(page, page_height)
                    else:
                        final_pos = random.randint(
                            0, max(0, page_height - viewport_height)
                        )
                        await self._safe_scroll(page, final_pos)
                    await asyncio.sleep(0.5)
                except:
                    pass  # Ignore final scroll errors

        except Exception as e:
            # If scrolling fails completely, just wait for the duration
            error_msg = str(e)
            # Only print if it's not a context destruction error (which is normal)
            if (
                "Execution context was destroyed" not in error_msg
                and "Target closed" not in error_msg
            ):
                print(f"  Warning: Scrolling simulation error: {error_msg[:100]}")
            # Wait remaining time
            await asyncio.sleep(duration)

    async def _wait_for_adsterra_redirect(self, page, max_wait: int = 30) -> bool:
        """Wait for Adsterra redirect chain to complete."""
        try:
            # Wait for page to be ready (more lenient for redirects)
            try:
                await page.wait_for_load_state(
                    "domcontentloaded", timeout=max_wait * 1000
                )
            except:
                # If domcontentloaded fails, try load state
                try:
                    await page.wait_for_load_state("load", timeout=10000)
                except:
                    pass  # Continue anyway

            # Wait a bit for JavaScript redirects
            await asyncio.sleep(1)

            # Check if we're still on the page (not closed)
            if page.is_closed():
                return False

            return True
        except PlaywrightTimeoutError:
            return True  # Timeout is okay, page might still be loading
        except Exception as e:
            # Don't fail on redirect errors - they're common with Adsterra
            return True

    async def open_smartlink(
        self, context, url: str, profile_name: str, visit_duration: Optional[int] = None
    ) -> bool:
        """Open an Adsterra smartlink in a new page with full fingerprinting."""
        page = None
        start_time = time.time()
        try:
            page = await context.new_page()

            # Get profile config
            profile = getattr(context, "_profile_config", {})

            # Inject fingerprinting script before navigation
            fingerprint_script = self._get_fingerprint_script(profile, profile_name)
            await page.add_init_script(fingerprint_script)

            # Set extra headers
            await page.set_extra_http_headers(
                {
                    "Accept-Language": profile.get("locale", "en-US"),
                }
            )

            print(f"[{profile_name}] Opening: {url[:60]}...")

            # Navigate to smartlink with better error handling for redirects
            try:
                # Use commit instead of domcontentloaded to handle redirects better
                response = await page.goto(
                    url,
                    wait_until="commit",  # Changed from domcontentloaded to commit for better redirect handling
                    timeout=self.config["settings"]["timeout"],
                )

                # Check if response is valid (redirects might return None)
                if response and response.status >= 400:
                    # If we get an error status, try to continue anyway (redirects might still work)
                    print(
                        f"[{profile_name}] Warning: HTTP {response.status}, continuing..."
                    )

            except Exception as nav_error:
                # If navigation fails, check if page loaded anyway (redirects can cause this)
                try:
                    current_url = page.url
                    if current_url and current_url != "about:blank":
                        print(
                            f"[{profile_name}] Navigation error but page loaded: {current_url[:60]}..."
                        )
                    else:
                        raise nav_error
                except:
                    # If page didn't load, try one more time with networkidle
                    try:
                        await page.goto(
                            url,
                            wait_until="networkidle",
                            timeout=self.config["settings"]["timeout"],
                        )
                    except:
                        raise nav_error

            # Wait for Adsterra redirect chain with better error handling
            redirect_success = await self._wait_for_adsterra_redirect(page)

            if not redirect_success or page.is_closed():
                raise Exception("Page closed during redirect")

            # Random visit duration to simulate human behavior
            if visit_duration is None:
                visit_duration = self.config["settings"].get("visit_duration", 5)
                # Add some randomness
                visit_duration += random.uniform(-1, 3)

            # Simulate human scrolling behavior during visit
            await self._simulate_human_scrolling(page, max(1, visit_duration))

            # Check final URL (for debugging)
            final_url = url
            try:
                final_url = page.url
                if final_url != url and final_url != "about:blank":
                    print(f"[{profile_name}] Redirected to: {final_url[:60]}...")
            except:
                pass

            duration = time.time() - start_time
            self.stats.record_success(
                profile_name, url, final_url=final_url, duration=duration
            )
            print(f"[{profile_name}] ✓ Successfully processed")

            return True

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)[:100]
            self.stats.record_failure(
                profile_name, url, error=error_msg, duration=duration
            )
            # Don't print common redirect errors as failures
            if "ERR_HTTP_RESPONSE_CODE_FAILURE" in error_msg or "net::ERR" in error_msg:
                print(
                    f"[{profile_name}] ⚠ Redirect error (may still be successful): {error_msg}"
                )
                # Sometimes redirect errors still result in successful visits
                # Check if page loaded anyway
                try:
                    if page and not page.is_closed():
                        current_url = page.url
                        if current_url and current_url != "about:blank":
                            print(
                                f"[{profile_name}] Page loaded despite error: {current_url[:60]}..."
                            )
                            duration = time.time() - start_time
                            self.stats.record_success(
                                profile_name,
                                url,
                                final_url=current_url,
                                duration=duration,
                            )
                            return True
                except:
                    pass
            else:
                print(f"[{profile_name}] ✗ Error: {error_msg}")
            return False
        finally:
            # Close page after processing
            try:
                if page and not page.is_closed():
                    await page.close()
            except:
                pass

    def _generate_random_profile(
        self, profile_index: int = 0, use_proxy: bool = True
    ) -> Dict:
        """Generate a random profile with random fingerprints and optional random proxy.
        Uses fake-useragent package for realistic user agent generation."""
        # Random viewports
        viewports = [
            {"width": 1920, "height": 1080},
            {"width": 1440, "height": 900},
            {"width": 1366, "height": 768},
            {"width": 2560, "height": 1440},
            {"width": 1536, "height": 864},
        ]

        # Random timezones
        timezones = [
            "America/New_York",
            "America/Los_Angeles",
            "America/Chicago",
            "America/Denver",
            "Europe/London",
            "Europe/Paris",
            "Asia/Tokyo",
            "Asia/Shanghai",
            "Australia/Sydney",
            "America/Sao_Paulo",
        ]

        # Random locales
        locales = [
            "en-US",
            "en-GB",
            "en-CA",
            "en-AU",
            "fr-FR",
            "de-DE",
            "es-ES",
            "ja-JP",
            "zh-CN",
        ]

        # Random WebGL vendors/renderers (Safari uses different format)
        chrome_webgl_configs = [
            {
                "vendor": "Google Inc. (NVIDIA)",
                "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            },
            {
                "vendor": "Google Inc. (Mesa)",
                "renderer": "ANGLE (Mesa, Mesa DRI Intel(R) HD Graphics 620 (KBL GT2), OpenGL 4.5)",
            },
            {
                "vendor": "Google Inc. (AMD)",
                "renderer": "ANGLE (AMD, AMD Radeon RX 6800 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
            },
            {
                "vendor": "Google Inc. (Intel)",
                "renderer": "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            },
        ]

        safari_webgl_configs = [
            {"vendor": "Apple Inc.", "renderer": "Apple M1"},
            {"vendor": "Apple Inc.", "renderer": "Apple M2"},
            {"vendor": "Intel Inc.", "renderer": "Intel Iris OpenGL Engine"},
            {"vendor": "Apple Inc.", "renderer": "Apple GPU"},
        ]

        # Generate user agent using fake-useragent package with weighted distribution
        # Target: 45% Edge, 45% Safari, 10% Chrome
        user_agent = None
        browser = "chrome"  # Default
        platform_name = "Win32"

        if self.ua:
            try:
                # Determine target browser based on weighted random (45% Edge, 45% Safari, 10% Chrome)
                target_browser_roll = random.random()
                target_browser = None

                if target_browser_roll < 0.60:  # 45% Edge
                    target_browser = "edge"
                elif target_browser_roll < 0.40:  # 45% Safari (45% + 45% = 90%)
                    target_browser = "safari"
                else:  # 10% Chrome (90% + 10% = 100%)
                    target_browser = "chrome"

                # Try to get a user agent matching target browser
                max_attempts = 20  # Try up to 20 times to get the desired browser
                attempt = 0

                while attempt < max_attempts:
                    try:
                        # Get random user agent from package
                        user_agent = self.ua.random
                        ua_lower = user_agent.lower()

                        # Detect browser type from user agent
                        detected_browser = None
                        if "edg/" in ua_lower or (
                            "edge" in ua_lower and "edg/" in ua_lower
                        ):
                            detected_browser = "edge"
                        elif (
                            "safari" in ua_lower
                            and "chrome" not in ua_lower
                            and "edg" not in ua_lower
                        ):
                            detected_browser = "safari"
                        elif "chrome" in ua_lower and "edg" not in ua_lower:
                            detected_browser = "chrome"

                        # If detected browser matches target, use it
                        if detected_browser == target_browser:
                            browser = detected_browser
                            break

                        # If we're looking for Chrome and got Chrome, use it (even if not perfect match)
                        if target_browser == "chrome" and detected_browser == "chrome":
                            browser = "chrome"
                            break

                        attempt += 1

                    except Exception as e:
                        attempt += 1
                        if attempt >= max_attempts:
                            print(
                                f"⚠ Warning: Failed to get user agent after {max_attempts} attempts: {e}"
                            )
                            user_agent = None
                            break

                # If we got a user agent, set browser and platform
                if user_agent:
                    ua_lower = user_agent.lower()
                    if browser == "edge":
                        platform_name = "Win32 (Edge)"
                    elif browser == "safari":
                        platform_name = "MacIntel (Safari)"
                    elif browser == "chrome":
                        # Detect platform from user agent
                        if "windows" in ua_lower:
                            platform_name = "Win32"
                        elif "mac" in ua_lower or "macintosh" in ua_lower:
                            platform_name = "MacIntel"
                        elif "linux" in ua_lower:
                            platform_name = "Linux x86_64"
                        else:
                            platform_name = "Win32"  # Default
                    else:
                        # Fallback: detect from user agent
                        if "edg/" in ua_lower or "edge" in ua_lower:
                            browser = "edge"
                            platform_name = "Win32 (Edge)"
                        elif "safari" in ua_lower and "chrome" not in ua_lower:
                            browser = "safari"
                            platform_name = "MacIntel (Safari)"
                        else:
                            browser = "chrome"
                            platform_name = "Win32"
                else:
                    user_agent = None

            except Exception as e:
                print(f"⚠ Warning: Failed to get user agent from package: {e}")
                user_agent = None

        # Fallback to manual generation if package fails
        if not user_agent:
            print("///////////////////////////////////////////////")
            print("No user_agent condition")
            print("///////////////////////////////////////////////")
            # Platform selection (OS first, then browser)
            os_platforms = [
                {"name": "Win32", "ua_base": "Windows NT 10.0; Win64; x64"},
                {"name": "Win11", "ua_base": "Windows NT 11.0; Win64; x64"},
                {"name": "MacIntel", "ua_base": "Macintosh; Intel Mac OS X 10_15_7"},
                {
                    "name": "MacAppleSilicon_M1",
                    "ua_base": "Macintosh; arm64; Mac OS X 14_0",
                },
                {
                    "name": "MacAppleSilicon_M2",
                    "ua_base": "Macintosh; arm64; Mac OS X 13_5",
                },
                {
                    "name": "MacAppleSilicon_M3",
                    "ua_base": "Macintosh; arm64; Mac OS X 15_0",
                },
                {"name": "Linux x86_64", "ua_base": "X11; Linux x86_64"},
            ]

            os_platform = random.choice(os_platforms)

            # Then select browser based on weighted distribution (45% Edge, 45% Safari, 10% Chrome)
            browser_roll = random.random()

            if os_platform["name"] == "Win32" or os_platform["name"] == "Win11":
                # Windows: 45% Edge, 10% Chrome (Safari not available on Windows)
                if browser_roll < 0.45:  # 45% Edge
                    browser = "edge"
                    platform_name = "Win32 (Edge)"
                else:  # 55% Chrome (adjusted since Safari not available)
                    browser = "chrome"
                    platform_name = "Win32"
            elif os_platform["name"].startswith("Mac"):
                # macOS: 45% Safari, 10% Chrome (Edge not common on macOS)
                if browser_roll < 0.45:  # 45% Safari
                    browser = "safari"
                    platform_name = "MacIntel (Safari)"
                else:  # 55% Chrome (adjusted since Edge not common)
                    browser = "chrome"
                    platform_name = "MacIntel"
            else:
                # Linux: 10% Chrome only (Edge and Safari not available)
                browser = "chrome"
                platform_name = "Linux x86_64"

            # Override: Force weighted distribution regardless of OS
            # This ensures we get the target distribution
            browser_roll_override = random.random()
            if browser_roll_override < 0.45:  # 45% Edge
                # Force Edge - use Windows platform
                browser = "edge"
                os_platform = {
                    "name": "Win32",
                    "ua_base": "Windows NT 10.0; Win64; x64",
                }
                platform_name = "Win32 (Edge)"
            elif browser_roll_override < 0.90:  # 45% Safari
                # Force Safari - use macOS platform
                browser = "safari"
                os_platform = {
                    "name": "MacIntel",
                    "ua_base": "Macintosh; Intel Mac OS X 10_15_7",
                }
                platform_name = "MacIntel (Safari)"
            else:  # 10% Chrome
                # Keep Chrome with original OS platform
                browser = "chrome"
                platform_name = os_platform["name"]

            # Browser versions for fallback
            chrome_versions = [
                "120.0.0.0",
                "121.0.0.0",
                "122.0.0.0",
                "141.0.7390.37",
                "142.0.7444.60",
                "140.0.0.0",
            ]
            edge_versions = [
                "123.0.0.0",
                "139.0.3405.111",
                "140.0.3485.54",
                "141.0.3537.99",
                "142.0.3595.80",
                "142.0.3595.65",
            ]
            safari_versions = [
                "17.2",
                "17.1",
                "18.0",
                "18.1",
                "18.2",
                "18.5",
                "18.6",
                "26.0",
                "26.1",
            ]
            webkit_versions = ["605.1.15", "605.1.12", "605.1.10", "604.5.6"]
            # Generate user agent based on browser type
            if browser == "edge":
                edge_version = random.choice(edge_versions)
                user_agent = f"Mozilla/5.0 ({os_platform['ua_base']}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{edge_version} Safari/537.36 Edg/{edge_version}"
            elif browser == "safari":
                safari_version = random.choice(safari_versions)
                webkit_version = random.choice(webkit_versions)
                user_agent = f"Mozilla/5.0 ({os_platform['ua_base']}) AppleWebKit/{webkit_version} (KHTML, like Gecko) Version/{safari_version} Safari/{webkit_version}"
            else:  # chrome
                chrome_version = random.choice(chrome_versions)
                user_agent = f"Mozilla/5.0 ({os_platform['ua_base']}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"

        # Select random values
        viewport = random.choice(viewports)
        timezone = random.choice(timezones)
        locale = random.choice(locales)

        # Select WebGL config based on browser
        if browser == "safari":
            webgl = random.choice(safari_webgl_configs)
        else:
            webgl = random.choice(chrome_webgl_configs)

        # Randomly select proxy for this profile
        proxy = None
        if use_proxy and self.proxy_credentials:
            proxy = self._get_random_proxy()

        print("======", browser, "======", user_agent)
        return {
            "name": f"auto_profile_{profile_index}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "user_agent": user_agent,
            "viewport": viewport,
            "timezone": timezone,
            "locale": locale,
            "platform": platform_name,
            "webgl_vendor": webgl["vendor"],
            "webgl_renderer": webgl["renderer"],
            "proxy": proxy,
            "browser_type": browser,
        }

    async def _open_smartlink_with_random_profile(
        self, browser, smartlink: str, link_index: int = 0
    ) -> bool:
        """Open a single smartlink with completely random profile and random proxy."""
        # Generate a completely new random profile for this smartlink
        profile = self._generate_random_profile(link_index, use_proxy=False)

        # Create context with this random profile
        context_options = {
            "viewport": {
                "width": profile["viewport"]["width"],
                "height": profile["viewport"]["height"],
            },
            "locale": profile["locale"],
            "timezone_id": profile["timezone"],
            "user_agent": profile["user_agent"],
            "extra_http_headers": {
                "Accept-Language": profile["locale"],
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
        }

        # Add proxy if configured
        proxy_config = self._parse_proxy(profile.get("proxy"))
        if proxy_config:
            context_options["proxy"] = proxy_config
            print(
                f"[{profile['name']}] Using proxy: {proxy_config['server']} {proxy_config['username']}"
            )

        print(f"{profile['user_agent']}")
        context = None

        try:
            # Create new context with random profile and proxy
            context = await browser.new_context(**context_options)
            context._profile_config = profile

            # Open smartlink with this context
            result = await self.open_smartlink(context, smartlink, profile["name"])
            return result

        except Exception as e:
            print(f"[{profile['name']}] Error: {str(e)[:100]}")
            return False
        finally:
            # Close context after use
            try:
                if context:
                    await context.close()
            except:
                pass

    async def _process_smartlinks_parallel(
        self, browser: Browser, smartlinks: List[str], parallel_count: int = 3
    ):
        """Process smartlinks in parallel batches with random profile and proxy per smartlink."""

        # changeIp2 = requests.get(
        #     "https://proxypanel.io/proxy/change-ip/zhogyichan/custom38/83d4482377a26ffafeb311fdd6881895:xytt3t3F25OL_ow_-DSctI_cEc6qc_a-H2PPQXRDzlA"
        # )
        # changeIp2.raise_for_status()
        # Process smartlinks in batches
        for i in range(0, len(smartlinks), parallel_count):
            # changeIp = requests.get("proxypanel.io/proxy/change-ip/zhogyichan/custom36/83d4482377a26ffafeb311fdd6881895:xytt3t3F25OL_ow_-DSctI_cEc6qc_a-H2PPQXRDzlA")
            # changeIp.raise_for_status()

            # time.sleep(10)
            batch = smartlinks[i : i + parallel_count]

            # Create tasks for parallel processing - each gets its own random profile
            tasks = [
                self._open_smartlink_with_random_profile(browser, smartlink, i + j)
                for j, smartlink in enumerate(batch)
            ]

            # Execute batch in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Small delay between batches
            if i + parallel_count < len(smartlinks):
                await asyncio.sleep(random.uniform(5.0, 15.0))

    async def _run_cycle(
        self, p: Playwright, smartlinks: List[str], recycle_interval: int = 300
    ):
        """Run one cycle: generate random profile for each smartlink, then recycle."""
        cycle_count = 0

        while True:
            cycle_count += 1
            print("\n" + "=" * 60)
            print(
                f"CYCLE #{cycle_count} - Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            print("=" * 60)

            # Create a browser instance (no profile needed upfront)
            # We'll create contexts with random profiles for each smartlink
            browser = None
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                try:
                    # Browser arguments
                    args = [
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--disable-crash-reporter",
                        "--disable-breakpad",
                        "--disable-logging",
                        "--log-level=3",
                        "--disable-infobars",
                        "--disable-notifications",
                        "--disable-background-networking",
                        "--disable-background-timer-throttling",
                        "--enable-gpu",
                        "--use-gl=desktop",
                        "--ignore-gpu-blocklist",
                    ]

                    if sys.platform != "darwin":
                        args.append("--no-sandbox")

                    browser = await p.chromium.launch(
                        headless=False,
                        args=args,
                        ignore_default_args=[
                            "--enable-automation",
                            "--metrics-recording-only",
                        ],
                    )
                    print(f"✓ Browser initialized successfully")
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        print(
                            f"⚠ Retry {retry_count}/{max_retries} for browser initialization..."
                        )
                        await asyncio.sleep(2)
                    else:
                        print(
                            f"✗ Failed to initialize browser after {max_retries} attempts: {e}"
                        )
                        print("Waiting before next cycle...")
                        await asyncio.sleep(recycle_interval)
                        continue

            if browser is None:
                continue

            # Process all smartlinks in parallel - each gets its own random profile
            parallel_count = self.config["settings"].get("parallel_smartlinks", 3)
            print(
                f"\nProcessing {len(smartlinks)} smartlinks in parallel (batch size: {parallel_count})..."
            )
            print(f"Each smartlink will use:")
            print(f"  - Random profile (platform, timezone, locale, viewport, WebGL)")
            print(f"  - Random proxy from: {self.proxy_credentials}")
            shuffled_smartlinks = smartlinks.copy()
            random.shuffle(shuffled_smartlinks)  # Randomize order each cycle

            # Track cycle start stats
            cycle_start_time = datetime.now()
            cycle_start_success = self.stats.successful_opens
            cycle_start_failed = self.stats.failed_opens

            # Process smartlinks with random profiles
            await self._process_smartlinks_parallel(
                browser, shuffled_smartlinks, parallel_count
            )

            # Close browser for this cycle
            try:
                await browser.close()
                print(f"✓ Closed browser")
            except Exception as e:
                print(f"Warning: Error closing browser: {e}")

            # Calculate cycle statistics
            cycle_end_time = datetime.now()
            cycle_duration = cycle_end_time - cycle_start_time
            cycle_success = self.stats.successful_opens - cycle_start_success
            cycle_failed = self.stats.failed_opens - cycle_start_failed
            cycle_total = cycle_success + cycle_failed

            # Record cycle statistics
            self.stats.record_cycle(
                cycle_count, cycle_success, cycle_failed, cycle_duration.total_seconds()
            )

            # Print cycle summary report
            print("\n" + "=" * 60)
            print(f"CYCLE #{cycle_count} SUMMARY REPORT")
            print("=" * 60)
            print(f"Duration: {cycle_duration}")
            print(f"Smartlinks Processed: {cycle_total}")
            print(
                f"  ✓ Successful: {cycle_success} ({cycle_success/max(cycle_total,1)*100:.1f}%)"
            )
            print(
                f"  ✗ Failed: {cycle_failed} ({cycle_failed/max(cycle_total,1)*100:.1f}%)"
            )
            print(
                f"Average Time per Smartlink: {cycle_duration.total_seconds()/max(cycle_total,1):.2f} seconds"
            )
            print(f"Mode: Random profile per smartlink")
            print("=" * 60)

            # Generate HTML report after each cycle
            # try:
            #     report_path = self.stats.generate_html_report(
            #         f"traffic_report_cycle_{cycle_count}.html"
            #     )
            #     print(f"\n📊 HTML Report generated: {report_path}")
            # except Exception as e:
            #     print(f"⚠ Warning: Failed to generate HTML report: {e}")
            now = datetime.now()
            next_date = now + timedelta(minutes=int(recycle_interval / 60))
            string_next_date = next_date.strftime("%Y-%m-%d %I:%M %p")

            print(
                f"\nNext cycle will start in {recycle_interval} seconds ({recycle_interval/60:.1f} minutes) => {string_next_date}"
            )

            # Wait for recycle interval
            await asyncio.sleep(recycle_interval)

    async def run(self):
        """Main execution method - auto-generates profiles and recycles every 5 minutes."""
        async with async_playwright() as p:
            smartlinks = self.config["smartlinks"]
            settings = self.config["settings"]

            # Get recycle interval (default 5 minutes = 300 seconds)
            recycle_interval = settings.get("recycle_interval_seconds", 300)

            print("=" * 60)
            print("ADSTERRRA SMARTLINK OPENER - AUTO MODE")
            print("=" * 60)
            print(f"Smartlinks: {len(smartlinks)}")
            print(
                f"Recycle Interval: {recycle_interval} seconds ({recycle_interval/60:.1f} minutes)"
            )
            print(f"Processing: Sequential (one by one)")
            print("=" * 60)
            print("\nStarting automated cycles...")
            print("Press Ctrl+C to stop\n")

            try:
                await self._run_cycle(p, smartlinks, recycle_interval)
            except KeyboardInterrupt:
                print("\n\n" + "=" * 60)
                print("STOPPING - User Interrupted")
                print("=" * 60)
                self.stats.print_summary()

                # Generate final HTML report
                # try:
                #     report_path = self.stats.generate_html_report("traffic_report_final.html")
                #     print(f"\n📊 Final HTML Report generated: {report_path}")
                # except Exception as e:
                #     print(f"⚠ Warning: Failed to generate final HTML report: {e}")

                # print("\nExiting...")


async def main():
    """Entry point for the application."""
    # Suppress macOS crash reporter warnings
    if sys.platform == "darwin":
        os.environ["CHROME_CRASH_PAD_HANDLER"] = "0"
        os.environ["ELECTRON_DISABLE_CRASH_REPORTER"] = "1"

    opener = AdsterraSmartlinkOpener()
    await opener.run()


if __name__ == "__main__":
    asyncio.run(main())
