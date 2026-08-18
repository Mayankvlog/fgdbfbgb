# Adsterra Smartlink Opener

A powerful Python application for automating Adsterra smartlink traffic generation with multi-profile support, device fingerprinting, and proxy integration. This tool uses Playwright to create unique browser sessions with different fingerprints and proxies for each profile.

## Features

### Core Features
- **Multi-Traffic Access**: Concurrent opening of smartlinks across multiple profiles
- **Multiple Profiles**: Each profile has unique device characteristics and can use different proxies
- **Proxy Support**: Full proxy support (HTTP, HTTPS, SOCKS5) with authentication
- **Device Fingerprinting**: Advanced fingerprinting to avoid detection:
  - User Agent
  - Viewport size
  - Timezone
  - Locale
  - Platform
  - WebGL vendor/renderer
  - Hardware concurrency
  - Device memory
  - Navigator properties
- **Adsterra-Specific**: Optimized for Adsterra smartlinks with redirect handling
- **Traffic Statistics**: Real-time tracking of successful/failed opens per profile
- **Persistent Profiles**: User data is saved per profile for consistent sessions
- **Stealth Mode**: Advanced fingerprinting scripts to avoid automation detection

### Advanced Features
- **Concurrent Processing**: Control how many profiles and opens run simultaneously
- **Traffic Limits**: Set total traffic limits or run unlimited
- **Randomization**: Random visit durations and link ordering for natural behavior
- **Error Handling**: Robust error handling with detailed logging

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
playwright install chromium
```

## Configuration

Edit `config.json` to customize your setup:

### Smartlinks
Add your Adsterra smartlink URLs to the `smartlinks` array:
```json
"smartlinks": [
  "https://floatingpresentedshopping.com/bk5u57id57?key=...",
  "https://floatingpresentedshopping.com/w20gucgm?key=..."
]
```

### Profiles
Each profile configuration includes:

```json
{
  "name": "profile1",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
  "viewport": {
    "width": 1920,
    "height": 1080
  },
  "timezone": "America/New_York",
  "locale": "en-US",
  "platform": "Win32",
  "webgl_vendor": "Google Inc. (NVIDIA)",
  "webgl_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3080...)",
  "proxy": "http://user:pass@proxy.example.com:8080"
}
```

#### Proxy Configuration
Set `proxy` to `null` for no proxy, or use one of these formats:
- `http://user:pass@host:port`
- `https://user:pass@host:port`
- `socks5://user:pass@host:port`
- `host:port` (defaults to http)

### Settings

```json
{
  "headless": false,                    // Run browsers in headless mode
  "timeout": 30000,                     // Page load timeout (ms)
  "wait_after_open": 5,                 // Base wait time after opening (seconds)
  "visit_duration": 5,                 // Base visit duration (seconds)
  "concurrent_profiles": 3,             // How many profiles to run simultaneously
  "concurrent_opens_per_profile": 2,   // How many smartlinks per profile simultaneously
  "total_traffic": null                 // Total traffic limit (null = unlimited)
}
```

## Usage

### Basic Usage
```bash
python smartlink_opener.py
```

### How It Works

1. **Initialization**: Creates browser contexts for each profile with unique fingerprints
2. **Proxy Setup**: Configures proxies if specified in profile config
3. **Traffic Generation**: Opens smartlinks concurrently based on settings
4. **Statistics**: Tracks and displays traffic statistics
5. **Cleanup**: Closes all browsers on Ctrl+C

## Example Output

```
============================================================
ADSTERRRA SMARTLINK OPENER
============================================================
Smartlinks: 14
Profiles: 5
Concurrent Profiles: 3
Concurrent Opens per Profile: 2
Total Traffic Limit: Unlimited
============================================================

Initializing 5 profiles...
[profile1] Using proxy: http://proxy1.example.com:8080
✓ Profile 'profile1' initialized
✓ Profile 'profile2' initialized
✓ Profile 'profile3' initialized
✓ Profile 'profile4' initialized
✓ Profile 'profile5' initialized

✓ 5 profiles ready

Starting traffic generation...
Opening 14 smartlinks with 5 profiles...

[profile1] Opening: https://floatingpresentedshopping.com/bk5u57id57?key=...
[profile1] ✓ Successfully processed
[profile2] Opening: https://floatingpresentedshopping.com/w20gucgm?key=...
[profile2] ✓ Successfully processed
...

============================================================
TRAFFIC STATISTICS SUMMARY
============================================================
Total Opens: 70
Successful: 68 (97.1%)
Failed: 2 (2.9%)
Duration: 0:05:23
Average Rate: 0.22 opens/sec

Per Profile:
  profile1: 14/14 successful
  profile2: 14/14 successful
  profile3: 13/14 successful
  profile4: 14/14 successful
  profile5: 13/14 successful
============================================================

✓ Traffic generation completed!

Press Ctrl+C to close all browsers...
```

## Project Structure

```
sfw/
├── smartlink_opener.py  # Main application
├── config.json          # Configuration file
├── requirements.txt     # Python dependencies
├── README.md           # This file
└── profiles/           # User profile data (created automatically)
    ├── profile1/
    ├── profile2/
    └── ...
```

## Advanced Configuration

### Multi-Traffic Setup
To maximize traffic generation:
- Increase `concurrent_profiles` (be careful with system resources)
- Increase `concurrent_opens_per_profile`
- Set `total_traffic` to a specific number for controlled runs

### Proxy Rotation
Use different proxies for each profile:
```json
{
  "name": "profile1",
  "proxy": "http://user1:pass1@proxy1.com:8080"
},
{
  "name": "profile2",
  "proxy": "http://user2:pass2@proxy2.com:8080"
}
```

### Headless Mode
For server/background operation:
```json
{
  "settings": {
    "headless": true
  }
}
```

## Tips & Best Practices

1. **Start Small**: Begin with 1-2 profiles and low concurrency to test
2. **Proxy Quality**: Use high-quality residential proxies for best results
3. **Fingerprinting**: Ensure each profile has unique fingerprints
4. **Rate Limiting**: Don't set concurrency too high to avoid detection
5. **Monitoring**: Watch the statistics to identify issues early
6. **Profile Diversity**: Use different timezones, locales, and devices

## Troubleshooting

### Browser Crashes
- Reduce `concurrent_profiles` and `concurrent_opens_per_profile`
- Check system resources (RAM, CPU)
- Verify proxy connectivity

### Proxy Errors
- Verify proxy format and credentials
- Test proxy connectivity manually
- Check firewall settings

### Timeout Errors
- Increase `timeout` in settings
- Check network connectivity
- Verify smartlink URLs are valid

## Requirements

- Python 3.8+
- Playwright
- Chromium browser (installed via Playwright)

## Notes

- Each profile maintains its own browser session with cookies, localStorage, etc.
- Browser windows remain open until you press Ctrl+C
- Statistics are tracked in real-time and displayed at the end
- The application handles Adsterra redirect chains automatically
- Random delays are added to simulate human behavior

## License

This tool is for educational and testing purposes. Ensure you comply with Adsterra's terms of service and applicable laws when using this tool.
# fgdbfbgb
