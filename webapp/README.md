# Web UI for Configuration

This small Flask app provides a UI to view and edit `config.json` in the project root and a simple API.

Run (PowerShell):

```
.\env\Scripts\Activate.ps1
pip install -r requirements.txt
python webapp\app.py
```

Open http://localhost:5000 in your browser. The app will read and write the project's `config.json` file.

API: GET `/api/config` returns JSON. POST JSON to `/api/config` to replace and save configuration.
