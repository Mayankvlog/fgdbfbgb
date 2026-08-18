#!/usr/bin/env python3
"""
Click Link - Static web application with smartlink cards and automated clicking
Creates a web page with cards for each smartlink and automates clicking them
Enhanced with real fingerprint spoofing and random profiles for each opened page
"""

import asyncio
import json
import os
import sys
import random
import time
from pathlib import Path
from playwright.async_api import Browser, BrowserType, Playwright, async_playwright, TimeoutError as PlaywrightTimeoutError
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import urlparse


class ClickLinkApp:
    def __init__(self, config_path: str = "config.json"):
        """Initialize the Click Link application."""
        self.config_path = config_path
        self.config = self._load_config()
        self.html_file = Path("smartlinks_page.html")
        
        # Proxy list - format: username:password
        # These will be randomly selected for each smartlink visit
        self.proxy_credentials = [
            'zhogyichan.custom36:hello123',
            'zhogyichan.custom38:hello123',
        ]
        
        # Proxy server configuration (adjust if your proxy service uses different host/port)
        self.proxy_server_host = "154.198.32.71"  # Update this to your proxy server
        self.proxy_server_port = 8083  # Update this to your proxy port
        
        # Browser versions for profile generation
        self.chrome_versions = ["120.0.0.0", "121.0.0.0", "122.0.0.0", "119.0.0.0", "141.0.7390.37"]
        self.edge_versions = ["120.0.0.0", "121.0.0.0", "122.0.0.0", "123.0.0.0"]
        self.safari_versions = ["17.2", "17.1", "17.0", "16.6", "16.5"]
        self.webkit_versions = ["605.1.15", "605.1.12", "605.1.10", "604.5.6"]
        
    def _load_config(self) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file {self.config_path} not found!")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
    
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
            if '://' not in proxy_string and '@' not in proxy_string:
                if ':' in proxy_string:
                    parts = proxy_string.split(':', 1)
                    if len(parts) == 2:
                        username = parts[0]
                        password = parts[1]
                        # Construct full proxy URL
                        proxy_string = f"http://{username}:{password}@{self.proxy_server_host}:{self.proxy_server_port}"
            
            # If no protocol, assume http
            if not proxy_string.startswith(('http://', 'https://', 'socks5://')):
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
    
    def _get_edge_user_agent_data(self, profile: Dict) -> str:
        """Generate Edge-specific userAgentData property."""
        user_agent = profile.get("user_agent", "")
        
        # Extract Edge and Chrome versions from user agent
        edge_version = "120.0.0.0"
        chrome_version = "120.0.0.0"
        
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
        if "Version/" in user_agent:
            try:
                safari_version = user_agent.split("Version/")[1].split()[0]
            except:
                pass
        
        return f"""
                // Safari-specific properties
                // Safari doesn't have chrome object
                delete window.chrome;
                
                // Safari vendor
                Object.defineProperty(navigator, 'vendor', {{
                    get: () => 'Apple Computer, Inc.'
                }});
                
                // Safari app version
                Object.defineProperty(navigator, 'appVersion', {{
                    get: () => '{user_agent.split("Mozilla/")[1].split(" (")[0] if "Mozilla/" in user_agent else "5.0"}'
                }});
                
                // Safari maxTouchPoints (iOS/macOS)
                Object.defineProperty(navigator, 'maxTouchPoints', {{
                    get: () => 0
                }});
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
                
                // Languages
                Object.defineProperty(navigator, 'languages', {{
                    get: () => ['{profile.get("locale", "en-US")}']
                }});
                
                // Plugins (Safari has different plugin structure)
                Object.defineProperty(navigator, 'plugins', {{
                    get: () => {{
                        const plugins = [];
                        const pluginCount = {3 if is_safari else 5};
                        for (let i = 0; i < pluginCount; i++) {{
                            plugins.push({{ name: `Plugin ${{i}}`, description: 'Plugin description' }});
                        }}
                        return plugins;
                    }}
                }});
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
    
    def _generate_random_profile(self, profile_index: int = 0, use_proxy: bool = True) -> Dict:
        """Generate a random profile with random fingerprints and optional random proxy."""
        # Platform selection (OS first, then browser)
        os_platforms = [
            {"name": "Win32", "ua_base": "Windows NT 10.0; Win64; x64"},
            {"name": "MacIntel", "ua_base": "Macintosh; Intel Mac OS X 10_15_7"},
            {"name": "Linux x86_64", "ua_base": "X11; Linux x86_64"},
        ]
        
        # Select OS platform first
        os_platform = random.choice(os_platforms)
        
        # Then select browser based on OS
        # Windows: 50% Edge, 50% Chrome
        # macOS: 50% Safari, 50% Chrome
        # Linux: 100% Chrome
        if os_platform["name"] == "Win32":
            browser = random.choice(["edge", "edge", "chrome", "chrome"])  # 50% Edge, 50% Chrome
        elif os_platform["name"] == "MacIntel":
            browser = random.choice(["safari", "safari", "chrome", "chrome"])  # 50% Safari, 50% Chrome
        else:
            browser = "chrome"  # Linux only Chrome
        
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
            "America/New_York", "America/Los_Angeles", "America/Chicago",
            "America/Denver", "Europe/London", "Europe/Paris", "Asia/Tokyo",
            "Asia/Shanghai", "Australia/Sydney", "America/Sao_Paulo"
        ]
        
        # Random locales
        locales = ["en-US", "en-GB", "en-CA", "en-AU", "fr-FR", "de-DE", "es-ES", "ja-JP", "zh-CN"]
        
        # Random WebGL vendors/renderers (Safari uses different format)
        chrome_webgl_configs = [
            {"vendor": "Google Inc. (NVIDIA)", "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11)"},
            {"vendor": "Google Inc. (Mesa)", "renderer": "ANGLE (Mesa, Mesa DRI Intel(R) HD Graphics 620 (KBL GT2), OpenGL 4.5)"},
            {"vendor": "Google Inc. (AMD)", "renderer": "ANGLE (AMD, AMD Radeon RX 6800 XT Direct3D11 vs_5_0 ps_5_0, D3D11)"},
            {"vendor": "Google Inc. (Intel)", "renderer": "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)"},
        ]
        
        safari_webgl_configs = [
            {"vendor": "Apple Inc.", "renderer": "Apple M1"},
            {"vendor": "Apple Inc.", "renderer": "Apple M2"},
            {"vendor": "Intel Inc.", "renderer": "Intel Iris OpenGL Engine"},
            {"vendor": "Apple Inc.", "renderer": "Apple GPU"},
        ]
        
        # Select random values
        viewport = random.choice(viewports)
        timezone = random.choice(timezones)
        locale = random.choice(locales)
        
        # Select WebGL config based on browser
        if browser == "safari":
            webgl = random.choice(safari_webgl_configs)
        else:
            webgl = random.choice(chrome_webgl_configs)
        
        # Generate user agent based on browser type
        if browser == "edge":
            edge_version = random.choice(self.edge_versions)
            user_agent = f"Mozilla/5.0 ({os_platform['ua_base']}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{edge_version} Safari/537.36 Edg/{edge_version}"
            platform_name = "Win32 (Edge)"
        elif browser == "safari":
            safari_version = random.choice(self.safari_versions)
            webkit_version = random.choice(self.webkit_versions)
            user_agent = f"Mozilla/5.0 ({os_platform['ua_base']}) AppleWebKit/{webkit_version} (KHTML, like Gecko) Version/{safari_version} Safari/{webkit_version}"
            platform_name = "MacIntel (Safari)"
        else:  # chrome
            chrome_version = random.choice(self.chrome_versions)
            user_agent = f"Mozilla/5.0 ({os_platform['ua_base']}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"
            platform_name = os_platform["name"]
        
        # Randomly select proxy for this profile
        proxy = None
        if use_proxy and self.proxy_credentials:
            proxy = self._get_random_proxy()
        
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
            "browser_type": browser
        }
    
    def _generate_html_page(self) -> str:
        """Generate HTML page with cards for each smartlink."""
        smartlinks = self.config["smartlinks"]
        
        # Generate card HTML for each smartlink
        cards_html = ""
        for i, smartlink in enumerate(smartlinks, 1):
            # Extract domain for display
            domain = smartlink.split('/')[2] if len(smartlink.split('/')) > 2 else "Smartlink"
            cards_html += f"""
            <div class="card" data-link="{smartlink}" data-index="{i}">
                <div class="card-header">
                    <h3>Smartlink #{i}</h3>
                    <span class="status" id="status-{i}">Ready</span>
                </div>
                <div class="card-body">
                    <p class="link-url">{domain}</p>
                    <button class="click-btn" id="btn-{i}" onclick="handleClick({i}, '{smartlink}')">Click Link</button>
                </div>
            </div>
            """
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smartlinks Clicker</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .header p {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        
        .cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }}
        
        .card {{
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            cursor: pointer;
        }}
        
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        }}
        
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
        }}
        
        .card-header h3 {{
            color: #333;
            font-size: 1.3em;
        }}
        
        .status {{
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
            background: #e0e0e0;
            color: #666;
        }}
        
        .status.clicked {{
            background: #4caf50;
            color: white;
        }}
        
        .status.processing {{
            background: #ff9800;
            color: white;
        }}
        
        .status.error {{
            background: #f44336;
            color: white;
        }}
        
        .card-body {{
            text-align: center;
        }}
        
        .link-url {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 15px;
            word-break: break-all;
        }}
        
        .click-btn {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 25px;
            font-size: 1em;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }}
        
        .click-btn:hover {{
            transform: scale(1.05);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }}
        
        .click-btn:active {{
            transform: scale(0.95);
        }}
        
        .click-btn:disabled {{
            background: #ccc;
            cursor: not-allowed;
            box-shadow: none;
        }}
        
        .stats {{
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        
        .stat-item {{
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        
        .stat-label {{
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔗 Smartlinks Clicker</h1>
            <p>Click on any card to open the smartlink</p>
        </div>
        
        <div class="stats">
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value" id="total-links">{len(smartlinks)}</div>
                    <div class="stat-label">Total Links</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="clicked-links">0</div>
                    <div class="stat-label">Clicked</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="success-links">0</div>
                    <div class="stat-label">Success</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="error-links">0</div>
                    <div class="stat-label">Errors</div>
                </div>
            </div>
        </div>
        
        <div class="cards-grid">
            {cards_html}
        </div>
    </div>
    
    <script>
        let clickedCount = 0;
        let successCount = 0;
        let errorCount = 0;
        
        function updateStats() {{
            document.getElementById('clicked-links').textContent = clickedCount;
            document.getElementById('success-links').textContent = successCount;
            document.getElementById('error-links').textContent = errorCount;
        }}
        
        function handleClick(index, link) {{
            const btn = document.getElementById(`btn-${{index}}`);
            const status = document.getElementById(`status-${{index}}`);
            
            btn.disabled = true;
            status.textContent = 'Processing...';
            status.className = 'status processing';
            clickedCount++;
            updateStats();
            
            // Trigger a custom event that Playwright can listen to
            // This allows us to intercept and handle the click properly
            const clickEvent = new CustomEvent('smartlinkClick', {{
                detail: {{ index: index, link: link }}
            }});
            window.dispatchEvent(clickEvent);
            
            // Also open link in new window (for Adsterra click tracking)
            // This ensures the click event is registered
            const newWindow = window.open(link, '_blank');
            
            if (newWindow) {{
                status.textContent = 'Opened';
                status.className = 'status clicked';
                successCount++;
            }} else {{
                status.textContent = 'Blocked';
                status.className = 'status error';
                errorCount++;
                btn.disabled = false;
            }}
            
            updateStats();
        }}
        
        // Auto-click functionality (can be triggered externally)
        window.autoClick = function(index) {{
            const card = document.querySelector(`[data-index="${{index}}"]`);
            if (card) {{
                const link = card.getAttribute('data-link');
                handleClick(index, link);
            }}
        }};
        
        // Auto-click all
        window.autoClickAll = function() {{
            const cards = document.querySelectorAll('.card');
            cards.forEach((card, index) => {{
                setTimeout(() => {{
                    const link = card.getAttribute('data-link');
                    handleClick(index + 1, link);
                }}, index * 1000);
            }});
        }};
    </script>
</body>
</html>
"""
        return html_content
    
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
            await page.evaluate(f"window.scrollTo({{top: {position}, behavior: 'smooth'}})")
            return True
        except Exception as e:
            # Context destroyed or page navigated - this is normal during redirects
            if "Execution context was destroyed" in str(e) or "Target closed" in str(e):
                return False
            return False
    
    async def _simulate_human_scrolling(self, page, duration: float = 10):
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
                default_value=viewport_size["height"] * 3  # Default to 3x viewport if can't get height
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
                scroll_type = random.choice(['down', 'down', 'down', 'up', 'pause'])
                
                if scroll_type == 'down' and current_position < page_height - viewport_height:
                    # Scroll down
                    scroll_amount = random.randint(100, min(500, int(scroll_distance)))
                    current_position = min(current_position + scroll_amount, page_height - viewport_height)
                    
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
                    
                elif scroll_type == 'up' and current_position > 0:
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
                        final_pos = random.randint(0, max(0, page_height - viewport_height))
                        await self._safe_scroll(page, final_pos)
                    await asyncio.sleep(0.5)
                except:
                    pass  # Ignore final scroll errors
                
        except Exception as e:
            # If scrolling fails completely, just wait for the duration
            error_msg = str(e)
            # Only print if it's not a context destruction error (which is normal)
            if "Execution context was destroyed" not in error_msg and "Target closed" not in error_msg:
                print(f"  Warning: Scrolling simulation error: {error_msg[:100]}")
            # Wait remaining time
            await asyncio.sleep(duration)
    
    async def _click_and_handle_redirect(self, browser: Browser, page, card_index: int, smartlink: str):
        """Click on a card and handle the redirect with scrolling using a random profile."""
        new_page = None
        new_context = None
        
        try:
            # Generate a random profile for this click
            profile = self._generate_random_profile(card_index, use_proxy=True)
            print(f"\n[Card {card_index}] Using random profile: {profile['name']}")
            print(f"[Card {card_index}] Browser: {profile['browser_type']}, Platform: {profile['platform']}")
            
            # Find the button on the main page
            button_selector = f"#btn-{card_index}"
            await page.wait_for_selector(button_selector, timeout=5000)
            
            # Human-like behavior: hover first, then click
            button = page.locator(button_selector)
            await button.hover()
            await asyncio.sleep(random.uniform(0.3, 0.8))  # Random delay before click
            
            print(f"[Card {card_index}] Clicking button to trigger Adsterra click tracking...")
            
            # Actually click the button - this triggers the click event and opens a new window
            # The click will trigger window.open() which Adsterra tracks
            print(f"[Card {card_index}] Clicking button (real click for Adsterra tracking)...")
            
            # Wait for the new page to open from the click
            async with page.context.expect_page(timeout=15000) as new_page_info:
                # Click the button - this triggers the REAL click event that Adsterra detects
                await button.click(delay=random.randint(50, 150))  # Human-like click delay
            
            # Get the new page that was opened by the click
            clicked_page = await new_page_info.value
            
            print(f"[Card {card_index}] Page opened from click, now creating fingerprinting context...")
            
            # The clicked page is in the default context (no fingerprinting)
            # We need to create a new context with fingerprinting and navigate to the same URL
            # But we keep the clicked page open briefly so Adsterra registers the click
            
            # Get the URL from the clicked page
            try:
                await clicked_page.wait_for_load_state("domcontentloaded", timeout=5000)
                clicked_url = clicked_page.url
                if clicked_url == "about:blank":
                    clicked_url = smartlink
            except:
                clicked_url = smartlink
            
            # Create context options with random profile
            context_options = {
                "viewport": {
                    "width": profile["viewport"]["width"],
                    "height": profile["viewport"]["height"]
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
                print(f"[Card {card_index}] Using proxy: {proxy_config['server']} ({proxy_config.get('username', 'N/A')})")
            
            # Create a new context with random profile
            new_context = await browser.new_context(**context_options)
            
            # Create a new page in this context
            new_page = await new_context.new_page()
            
            # Inject fingerprinting script before navigation
            fingerprint_script = self._get_fingerprint_script(profile, profile["name"])
            await new_page.add_init_script(fingerprint_script)
            
            # Wait a moment for the clicked page to register with Adsterra
            await asyncio.sleep(1)
            
            # Close the clicked page (we have the fingerprinting page now)
            try:
                await clicked_page.close()
            except:
                pass
            
            # Navigate to the smartlink with fingerprinting
            print(f"[Card {card_index}] Navigating to smartlink with fingerprinting...")
            try:
                # Navigate to smartlink with better error handling for redirects
                response = await new_page.goto(
                    clicked_url,
                    wait_until="commit",  # Better for redirects
                    timeout=self.config["settings"].get("timeout", 60000)
                )
                
                # Check if response is valid (redirects might return None)
                if response and response.status >= 400:
                    print(f"[Card {card_index}] Warning: HTTP {response.status}, continuing...")
                
            except Exception as nav_error:
                # If navigation fails, check if page loaded anyway (redirects can cause this)
                try:
                    current_url = new_page.url
                    if current_url and current_url != "about:blank":
                        print(f"[Card {card_index}] Navigation error but page loaded: {current_url[:60]}...")
                    else:
                        raise nav_error
                except:
                    # If page didn't load, try one more time
                    try:
                        await new_page.goto(smartlink, wait_until="networkidle", timeout=self.config["settings"].get("timeout", 60000))
                    except:
                        raise nav_error
            
            # Wait for Adsterra redirect chain
            print(f"[Card {card_index}] Waiting for redirects...")
            await asyncio.sleep(3)
            
            # Check if page navigated
            try:
                await new_page.wait_for_load_state("domcontentloaded", timeout=30000)
            except:
                pass  # Continue even if timeout
            
            try:
                await new_page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass  # Continue even if networkidle times out
            
            # Get final URL
            final_url = new_page.url
            print(f"[Card {card_index}] Final URL: {final_url[:80]}...")
            
            # Simulate human scrolling on the redirected page
            visit_duration = self.config["settings"].get("visit_duration", 10)
            print(f"[Card {card_index}] Scrolling like a real user for {visit_duration} seconds...")
            await self._simulate_human_scrolling(new_page, visit_duration)
            
            print(f"[Card {card_index}] ✓ Completed successfully")
            
        except asyncio.TimeoutError:
            print(f"[Card {card_index}] ⚠ Timeout waiting for new page (popup may be blocked)")
        except Exception as e:
            print(f"[Card {card_index}] ⚠ Error: {e}")
            # Try to scroll anyway if page is still open
            if new_page and not new_page.is_closed():
                try:
                    visit_duration = self.config["settings"].get("visit_duration", 10)
                    await self._simulate_human_scrolling(new_page, visit_duration)
                except:
                    pass
        finally:
            # Close the redirected page (only if we created a new context)
            try:
                if new_page and not new_page.is_closed():
                    await new_page.close()
            except:
                pass
            
            # Only close context if we created one (not if we used the clicked page's context)
            try:
                if new_context:
                    await new_context.close()
            except:
                pass
    
    async def run(self):
        """Main execution method."""
        async with async_playwright() as p:
            smartlinks = self.config["smartlinks"]
            settings = self.config["settings"]
            
            print("="*60)
            print("CLICK LINK APPLICATION")
            print("="*60)
            print(f"Smartlinks: {len(smartlinks)}")
            print(f"Visit Duration: {settings.get('visit_duration', 10)} seconds")
            print("="*60)
            
            # Generate HTML page
            print("\nGenerating HTML page with smartlink cards...")
            html_content = self._generate_html_page()
            self.html_file.write_text(html_content, encoding='utf-8')
            html_path = self.html_file.absolute()
            print(f"✓ HTML page generated: {html_path}")
            
            # Launch browser
            browser = await p.chromium.launch(
                headless=settings.get("headless", False),
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-crash-reporter',
                    '--disable-breakpad',
                    '--disable-logging',
                    '--log-level=3',
                    '--disable-infobars',
                    '--disable-notifications',
                    '--disable-background-networking',
                    '--disable-background-timer-throttling',
                ] + ([] if sys.platform == 'darwin' else ['--no-sandbox']),
                ignore_default_args=['--enable-automation', '--metrics-recording-only'],
            )
            
            # Create a simple context for the main HTML page (no fingerprinting needed here)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080}
            )
            
            # Open the HTML page
            page = await context.new_page()
            await page.goto(f"file://{html_path}", wait_until="networkidle")
            print(f"✓ Opened HTML page in browser")
            
            print(f"\nStarting automated clicking with fingerprint spoofing...")
            print(f"Each click will use a random profile with:")
            print(f"  - Random browser (Chrome/Edge/Safari)")
            print(f"  - Random platform (Windows/macOS/Linux)")
            print(f"  - Random viewport, timezone, locale")
            print(f"  - Random proxy (if configured)")
            print(f"  - Full fingerprint spoofing")
            print(f"\nClicking {len(smartlinks)} smartlinks...\n")
            
            # Click each card sequentially
            for i, smartlink in enumerate(smartlinks, 1):
                try:
                    await self._click_and_handle_redirect(browser, page, i, smartlink)
                    
                    # Wait between clicks (human-like delay)
                    if i < len(smartlinks):
                        wait_time = random.uniform(2.0, 5.0)
                        print(f"Waiting {wait_time:.1f} seconds before next click...\n")
                        await asyncio.sleep(wait_time)
                        
                except Exception as e:
                    print(f"[Card {i}] Error: {e}")
                    continue
            
            print(f"\n✓ All smartlinks clicked!")
            print(f"\nPress Ctrl+C to close the browser...")
            
            # Keep browser open
            try:
                await asyncio.Event().wait()
            except KeyboardInterrupt:
                print("\n\nClosing browser...")
                await browser.close()
                print("Browser closed. Exiting...")


async def main():
    """Entry point for the application."""
    # Suppress macOS crash reporter warnings
    if sys.platform == 'darwin':
        os.environ['CHROME_CRASH_PAD_HANDLER'] = '0'
        os.environ['ELECTRON_DISABLE_CRASH_REPORTER'] = '1'
    
    app = ClickLinkApp()
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())

