import os, sys, json, re
from datetime import datetime, timedelta
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# --- load .env ---
def _resolve_hermes_data_dir() -> str:
    for env_var in ("HERMES_DATA_DIR", "HERMES_HOME"):
        val = os.environ.get(env_var, "").strip()
        if val:
            return os.path.abspath(val)
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        win_hermes = os.path.join(os.environ["LOCALAPPDATA"], "hermes")
        if os.path.exists(win_hermes):
            return win_hermes
    default_hermes = os.path.join(os.path.expanduser("~"), ".hermes")
    if os.path.exists(default_hermes):
        return default_hermes
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        return os.path.join(os.environ["LOCALAPPDATA"], "hermes")
    return default_hermes

_HERMES_DIR = _resolve_hermes_data_dir()
env_path = os.path.join(_HERMES_DIR, ".env")
if not os.path.exists(env_path):
    env_path = os.path.expanduser('~/.hermes/.env')
if os.path.exists(env_path):
    for line in open(env_path):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k, v)

USER = os.getenv('FRESHRSS_USERNAME', 'admin')
PASS = os.getenv('FRESHRSS_API_PASSWORD', '')
IP = os.environ.get('FRESHRSS_URL', 'http://127.0.0.1').replace('http://','').replace('https://','').split('/')[0]
PORT = 443
HOST = os.getenv('FRESHRSS_HOST', '')
API_BASE = f"https://{IP}:{PORT}/api/greader.php"

def make_session():
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[502, 503, 504])
    s.mount('https://', HTTPAdapter(max_retries=retry))
    return s

def get_token(s):
    r = s.post(f"{API_BASE}/accounts/ClientLogin",
               data={"Email": USER, "Passwd": PASS, "service": "reader"},
               headers={"Host": HOST, "User-Agent": "Mozilla/5.0 (compatible; Hermes/1.0)"},
               timeout=30, verify=False)
    for ln in r.text.splitlines():
        if ln.startswith("Auth="):
            return ln[5:]
    raise ValueError(f"Auth failed: {r.text[:200]}")

def main():
    s = make_session()
    token = get_token(s)
    headers = {"Host": HOST, "Authorization": f"GoogleLogin auth={token}",
               "User-Agent": "Mozilla/5.0 (compatible; Hermes/1.0)"}
    params = {"n": 40, "r": "n", "output": "json"}  # newest first
    r = s.get(f"{API_BASE}/reader/api/0/stream/contents/user/-/state/com.google/reading-list",
              params=params, headers=headers, timeout=60, verify=False)
    data = r.json()
    items = data.get("items", [])
    print(f"Fetched {len(items)} items", file=sys.stderr)

    cutoff = (datetime.now() - timedelta(hours=24)).timestamp()
    sports_kw = re.compile(r'\b(nba|nfl|mlb|nhl|football|soccer|baseball|basketball|tennis|'
                           r'premier league|world cup|olympic|fifa|uefa|espn|formula 1|'
                           r'cricket|golf|rugby|horse racing|match report|scoreline|'
                           r'playoff|super bowl|world series|champions league)\b', re.I)

    out = []
    for it in items:
        ts = None
        for fld in ('timestampUsec', 'crawlTimeMsec'):
            v = it.get(fld)
            if v:
                try:
                    ts = float(v) / (1e6 if fld.endswith('Usec') else 1e3)
                    break
                except (ValueError, TypeError):
                    pass
        if ts is None:
            continue
        if ts < cutoff:
            continue
        title = (it.get('title') or '').strip()
        alts = it.get('alternate') or []
        url = alts[0]['href'] if alts else ''
        cats = ' '.join(it.get('categories', []))
        if sports_kw.search(title) or sports_kw.search(cats):
            continue
        out.append({"title": title, "url": url, "ts": ts,
                    "published": datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')})

    out.sort(key=lambda x: x['ts'], reverse=True)
    print(f"After 24h+sports filter: {len(out)}", file=sys.stderr)
    with open('/tmp/freshrss_articles.json', 'w') as f:
        json.dump(out, f, indent=2)
    for i, a in enumerate(out[:40]):
        print(f"{i:2d}. [{a['published']}] {a['title'][:90]}")
        print(f"    {a['url']}")

if __name__ == '__main__':
    main()
