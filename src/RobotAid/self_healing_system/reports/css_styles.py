ACTION_LOG_CSS: str = (
    "<style>"
    "body{font-family:'Segoe UI',Tahoma,sans-serif;line-height:1.2;background:#f7f9fa;color:#333;margin:0;padding:10px}"
    "h1{color:#2c3e50;margin-bottom:10px;line-height:1.2}"
    "details{background:#fff;border:1px solid #ddd;border-radius:5px;box-shadow:0 2px 4px rgba(0,0,0,0.1);margin-bottom:10px;overflow:hidden}"
    "summary{padding:8px 12px;line-height:1.2;list-style:none;display:flex;justify-content:space-between;align-items:center;cursor:pointer}"
    "summary::-webkit-details-marker{display:none}"
    "summary::before{content:'▶';font-size:0.8em;margin-right:8px;transition:transform 0.2s ease;color:#34495e}"
    "details[open] summary::before{transform:rotate(90deg)}"
    "summary .path{font-size:0.85em;color:#7f8c8d;font-style:italic}"
    "table.inner{width:100%;border-collapse:collapse;margin:10px 0}"
    "table.inner th,table.inner td{padding:4px 6px;line-height:1.2;border-bottom:1px solid #e0e0e0}"
    "table.inner th{background:#34495e;color:#fff;text-align:left;font-weight:600}"
    "table.inner tr:nth-child(even){background:#f2f8fc}"
    "table.inner tr:hover{background:#d6eaf8}"
    "</style>"
)


DIFF_CSS: str = (
    "<style>"
    "body{font-family:'Segoe UI',Tahoma,sans-serif;line-height:1.2;background:#fafbfc;color:#2c3e50;margin:0;padding:10px}"
    "table.diff{width:100%;border-collapse:collapse;margin:10px 0;box-shadow:0 2px 4px rgba(0,0,0,0.1)}"
    "table.diff th{background:#34495e;color:#ecf0f1;padding:6px;border:1px solid #ddd;text-align:left;line-height:1.2}"
    "table.diff td{padding:4px;border:1px solid #ddd;font-family:monospace;font-size:0.9em;vertical-align:top;line-height:1.2}"
    "td.diff_header{background:#2c3e50;color:#ecf0f1;font-weight:600}"
    "td.diff_next{background:#ecf0f1}"
    "span.diff_add{background:#e8f5e9;color:#2e7d32;display:inline-block;padding:2px 4px;border-radius:3px}"
    "span.diff_sub{background:#ffebee;color:#c62828;display:inline-block;padding:2px 4px;border-radius:3px}"
    "span.diff_chg{background:#fff8e1;color:#f9a825;display:inline-block;padding:2px 4px;border-radius:3px}"
    "</style>"
)
