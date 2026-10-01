#!/home/operator/.hermes/newsletter_venv/bin/python3
"""
Daily Newsletter Builder for FreshRSS - Cohesive Topic-Based Version
Excludes sports, creates one cohesive narrative focusing on science, LLM/AI, and international news
"""
import os
import sys
import json
import hashlib
import html
import sqlite3
from datetime import datetime, timedelta
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import re

# Fullwidth -> ASCII punctuation normalization (some feeds return U+FF06 etc.)
_FULLWIDTH_MAP = {c: chr(c - 0xFEE0) for c in range(0xFF01, 0xFF5F)}
_FULLWIDTH_MAP[0x3000] = ' '

_REFUSAL_PATTERNS = (
    '我无法提供', '我无法', '无法提供相关信息',
    'i cannot provide', 'i am unable to', 'i can\'t provide',
    'access denied', 'are you a robot', 'verify you are human',
    'just a moment', 'checking your browser', 'captcha',
    '404 not found', '403 forbidden', 'page not found',
    'enable javascript', 'microsoft_clarity', 'cloudflare',
)


def clean_text(text):
    """Strip HTML tags + decode entities + normalize whitespace/fullwidth punctuation."""
    if not text:
        return ''
    text = re.sub(r'<[^<]+?>', ' ', text)
    text = html.unescape(text)
    text = text.translate(_FULLWIDTH_MAP)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_paragraphs(html, min_len=40):
    """
    Extract article prose from <p> tags only, discarding boilerplate.

    Stripping tags from a whole document keeps everything: the nav menu,
    the footer, the cookie banner, the newsletter signup form, share buttons
    and every "related stories" link. The summariser then spends its budget
    describing how the website works instead of reporting what happened --
    which is what made the brief read as operating instructions rather than
    news.

    Only paragraphs, minimum length, joined with blank lines. Any failure
    returns "" so the caller can move to the next waterfall stage rather
    than pass junk downstream.
    """
    if not html:
        return ""
    try:
        from html.parser import HTMLParser

        class _P(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.buf = []
                self.depth = 0
                self.skip = 0
                # These never contain article prose.
                self.BAD = ("script", "style", "nav", "header", "footer",
                            "aside", "form", "noscript", "iframe", "svg")

            def handle_starttag(self, tag, attrs):
                if tag in self.BAD:
                    self.skip += 1
                elif tag == "p" and not self.skip:
                    self.depth += 1
                    if self.depth == 1:
                        self.buf.append("\n\n")

            def handle_endtag(self, tag):
                if tag in self.BAD:
                    self.skip = max(0, self.skip - 1)
                elif tag == "p" and not self.skip:
                    self.depth = max(0, self.depth - 1)
                    if self.depth == 0:
                        self.buf.append("\n\n")

            def handle_data(self, data):
                if not self.skip and self.depth:
                    self.buf.append(data)

        p = _P()
        try:
            p.feed(html)
        except Exception:
            return ""

        paras = []
        for chunk in "".join(p.buf).split("\n\n"):
            t = re.sub(r"\s+", " ", chunk).strip()
            if len(t) >= min_len:
                paras.append(t)
        return "\n\n".join(paras)
    except Exception:
        return ""


def is_refusal(text):
    """Detect boilerplate / refusal / non-article junk returned by extraction."""
    if not text or len(text.strip()) < 30:
        return True
    low = text.lower()
    return any(p in low for p in _REFUSAL_PATTERNS)

# Add the venv to path for openai/trafilatura
sys.path.insert(0, '/home/operator/.hermes/newsletter_venv/lib/python3.14/site-packages')

try:
    import trafilatura
    import openai
except ImportError as e:
    print(f"Warning: Some imports failed: {e}")
    # Continue anyway - we'll have fallbacks

def load_env():
    """Load environment variables from .env file"""
    env_path = '/home/operator/.hermes/.env'
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

def get_freshrss_config():
    """Get FreshRSS configuration from environment"""
    load_env()
    
    # Get base URL and ensure it doesn't have trailing slash
    base_url = os.getenv('FRESHRSS_URL', 'https://freshrss.example.com').rstrip('/')
    # If the URL already ends with /api, don't add another
    if base_url.endswith('/api'):
        api_base = base_url
    else:
        api_base = f"{base_url}/api"
    
    config = {
        'username': os.getenv('FRESHRSS_USERNAME'),
        'password': os.getenv('FRESHRSS_API_PASSWORD'),
        'base_url': base_url,  # Base URL without /api
        'api_base': api_base,  # Base URL with /api
        'openrouter_key': os.getenv('OPENROUTER_API_KEY'),
        'jina_key': os.getenv('JINA_API_KEY'),
        'max_articles': int(os.getenv('MAX_ARTICLES', '50')),  # Increased to get more content for topics
        'lookback_hours': int(os.getenv('LOOKBACK_HOURS', '24')),
        # IP Direct settings - use IP directly but preserve Host header
        'use_ip_direct': True,
        'freshrss_ip': '10.0.0.10',
        'freshrss_port': 443,
        'freshrss_host': 'freshrss.example.com'  # For Host header
    }
    
    return config

def get_auth_token_ip_direct(username, password, config):
    """Get FreshRSS authentication token using IP direct connection"""
    # Build the base URL we'll connect to (IP direct)
    ip_base = f"https://{config['freshrss_ip']}:{config['freshrss_port']}/api"
    
    # But we need to set the Host header to make the server think we're coming from the domain
    headers = {
        'Host': config['freshrss_host'],
        'User-Agent': 'Mozilla/5.0 (compatible; Hermes-Newsletter/1.0)'
    }
    
    resp = requests.post(
        f"{ip_base}/greader.php/accounts/ClientLogin",
        data={
            "Email": username,
            "Passwd": password,
            "service": "reader"
        },
        headers=headers,
        timeout=30,
        verify=False  # Accept self-signed cert
    )
    
    for line in resp.text.splitlines():
        if line.startswith("Auth="):
            return line[5:]
    raise ValueError(f"Authentication failed: {resp.text[:200]}")

def api_get_ip_direct(auth_token, path, params=None, config=None):
    """Make authenticated GET request using IP direct connection"""
    if config is None:
        config = get_freshrss_config()
    
    # Build the base URL we'll connect to (IP direct)
    ip_base = f"https://{config['freshrss_ip']}:{config['freshrss_port']}/api"
    
    # But we need to set the Host header to make the server think we're coming from the domain
    headers = {
        'Authorization': f'GoogleLogin auth={auth_token}',
        'Host': config['freshrss_host'],
        'User-Agent': 'Mozilla/5.0 (compatible; Hermes-Newsletter/1.0)'
    }
    
    resp = requests.get(
        f"{ip_base}/greader.php{path}",
        params=params,
        headers=headers,
        timeout=60,
        verify=False
    )
    
    return resp

def fetch_unread_articles_ip_direct(auth_token, config, max_articles, lookback_hours):
    """Fetch unread articles from FreshRSS using IP direct - get recent items and filter by time and exclude sports"""
    # Get a batch of recent items (we'll filter by time, read status, and exclude sports ourselves)
    resp = api_get_ip_direct(
        auth_token,
        "/reader/api/0/stream/contents/user/-/state/com.google/reading-list",
        params={
            "n": max_articles * 4,  # Get extra to account for filtering
            "output": "json",
            "r": "n",  # Newest first - critical to get recent articles
        },
        config=config
    )
    
    if resp.status_code != 200:
        raise Exception(f"Failed to fetch articles: {resp.status_code} - {resp.text[:200]}")
    
    items = resp.json().get("items", [])
    
    # Filter items by time, read status, and exclude sports
    cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
    cutoff_timestamp = cutoff_time.timestamp()
    
    # Sports-related keywords and categories to exclude
    sports_indicators = {
        # Explicit sports categories
        'sports', 'fox-news/sports', 'fox-news/sports/injuries', 'fox-news/sports/wnba',
        'fox-news/sports/wnba/chicago-sky', 'fox-news/sports/wnba/indiana-fever',
        'fox-news/sports/nfl', 'seahawks', 'washington huskies football', 'huskies',
        'cubs', 'chicago cubs', 'mlb', 'national', 'news'  # These need content checking
    }
    
    filtered_items = []
    for item in items:
        if not isinstance(item, dict):
            continue
            
        # Check if item is unread (has reading-list category)
        categories = item.get('categories', [])
        is_unread = 'user/-/state/com.google/reading-list' in categories
        
        if not is_unread:
            continue
            
        # Check item timestamp - try different timestamp fields
        item_time = None
        timestamp_usec = item.get('timestampUsec')
        crawl_time = item.get('crawlTimeMsec')
        published = item.get('published')
        
        if timestamp_usec:
            try:
                item_time = float(timestamp_usec) / 1000000
            except (ValueError, TypeError):
                pass
        elif crawl_time:
            try:
                item_time = float(crawl_time) / 1000
            except (ValueError, TypeError):
                pass
        elif published:
            try:
                item_time = float(published)
            except (ValueError, TypeError):
                pass
        
        if item_time is None:
            # If we can't determine time, include it (better to include than miss)
            item_time = cutoff_timestamp + 1  # Treat as recent
            
        # Include if item is newer than cutoff
        if item_time < cutoff_timestamp:
            continue
            
        # EXCLUDE SPORTS CONTENT
        title = item.get('title', '').lower()
        summary = item.get('summary', {}).get('content', '').lower()
        content_to_check = f"{title} {summary}"
        
        # Check for explicit sports indicators in categories
        has_sports_category = False
        for cat in categories:
            cat_lower = cat.lower()
            if any(indicator in cat_lower for indicator in ['sports', 'fox-news/sports']):
                has_sports_category = True
                break
                
        # Check for sports team/league indicators
        sports_teams = ['seahawks', 'huskies', 'cubs', 'chicago cubs', 'yankees', 'red sox',
                       'lakers', 'warriors', 'patriots', 'chiefs', 'packers', 'steelers']
        has_sports_team = any(team in content_to_check for team in sports_teams)
        
        # Check for sports event keywords
        sports_events = ['match', 'game', 'score', 'win', 'lose', 'tournament', 'championship',
                        'league', 'cup', 'premier', 'liga', 'bundesliga', 'serie a', 'ligue 1',
                        'nfl', 'nba', 'mlb', 'nhl', 'fifa', 'uefa', 'olympics', 'cricket', 'tennis',
                        'formula 1', 'motogp', 'rugby', 'golf', 'boxing', 'mma', 'athletics',
                        'super bowl', 'world series', 'stanley cup']
        has_sports_event = any(event in content_to_check for event in sports_events)
        
        # Skip if it's sports content
        if has_sports_category or has_sports_team or has_sports_event:
            continue
            
        filtered_items.append(item)
    
    # Sort by timestamp (newest first) and limit
    def get_item_time(item):
        timestamp_usec = item.get('timestampUsec')
        crawl_time = item.get('crawlTimeMsec')
        published = item.get('published')
        
        if timestamp_usec:
            try:
                return float(timestamp_usec) / 1000000
            except (ValueError, TypeError):
                pass
        elif crawl_time:
            try:
                return float(crawl_time) / 1000
            except (ValueError, TypeError):
                pass
        elif published:
            try:
                return float(published)
            except (ValueError, TypeError):
                pass
        return 0
    
    filtered_items.sort(key=get_item_time, reverse=True)
    # Do NOT truncate here. The caller needs a surplus of candidates so it can
    # discard the unextractable ones and still reach its target. Previously
    # this cut to exactly max_articles, so any article that failed extraction
    # simply reduced the final count -- 50 candidates yielded ~23 articles
    # because ~27 failed and were dropped with no replacement.
    return filtered_items

def extract_content_with_waterfall(item, jina_key=None):
    """Extract content using waterfall method. Returns cleaned text or None if unusable."""
    title = item.get("title", "Untitled")
    url = ""
    alternates = item.get("alternate", [])
    if alternates:
        url = alternates[0].get("href", "")

    # Stage 1: FreshRSS content
    content = item.get("content", {}).get("content", "")
    if not content or len(content.strip()) < 100:
        content = item.get("summary", {}).get("content", "")

    if content and len(content.strip()) >= 200:
        clean_content = clean_text(content)
        if len(clean_content) >= 150 and not is_refusal(clean_content):
            return {
                "title": title,
                "url": url,
                "content": clean_content,
                "method": "freshrss"
            }

    # Stage 2: Fetch original URL
    if url:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            resp = requests.get(url, headers=headers, timeout=10, verify=False)
            if resp.status_code == 200:
                # Try trafilatura if available
                try:
                    extracted = trafilatura.extract(
                        resp.text,
                        favor_precision=True
                    ) if 'trafilatura' in sys.modules else None

                    if extracted and len(extracted.strip()) >= 150 and not is_refusal(extracted.strip()):
                        return {
                            "title": title,
                            "url": url,
                            "content": extracted.strip(),
                            "method": "trafilatura"
                        }
                except Exception:
                    pass

                # Fallback to raw text extraction.
                #
                # Only if trafilatura failed, and only from the parsed
                # <p> tags -- never from the raw HTML. Stripping tags off the
                # whole document returns the nav menu, footer, cookie banner
                # and newsletter signup form along with the story, and the
                # summariser then writes a paragraph about how the site works
                # instead of what happened.
                if len(resp.text) > 100:
                    text = extract_paragraphs(resp.text)
                    if text and len(text) >= 100 and not is_refusal(text):
                        return {
                            "title": title,
                            "url": url,
                            "content": text[:2000],
                            "method": "paragraphs"
                        }
        except Exception as e:
            print(f"    URL fetch failed: {e}")

    # Stage 3: Jina Reader (fix double-protocol bug)
    if url and jina_key:
        try:
            jina_url = f"https://r.jina.ai/{url}"
            headers = {"Authorization": f"Bearer {jina_key}"} if jina_key else {}
            resp = requests.get(jina_url, headers=headers, timeout=15, verify=False)
            if resp.status_code == 200 and len(resp.text) > 100 and not is_refusal(resp.text.strip()):
                return {
                    "title": title,
                    "url": url,
                    "content": resp.text.strip(),
                    "method": "jina"
                }
        except Exception as e:
            print(f"    Jina failed: {e}")

    # Stage 4: Return cleaned summary with note
    summary = item.get("summary", {}).get("content", "")
    if summary and len(summary.strip()) >= 50:
        clean_summary = clean_text(summary)
        if len(clean_summary) >= 50 and not is_refusal(clean_summary):
            return {
                "title": title,
                "url": url,
                "content": clean_summary + "\n\n*Note: Full content extraction failed, showing RSS summary*",
                "method": "summary_fallback"
            }

    # Stage 5: Ultimate fallback — mark as failed so the caller can skip
    return {
        "title": title,
        "url": url,
        "content": None,
        "method": "failed"
    }

# hy3:free was removed from OpenRouter's free tier (404 "unavailable for free").
# Fall back to a known-good free model on this key when the configured default
# is dead/empty.
_FALLBACK_FREE_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"


def _is_reasoning_model(model):
    """Heuristic: does this model require the `reasoning` extra_body param?"""
    m = (model or "").lower()
    return any(t in m for t in ("hy3", "r1", "reasoning", "thinking", "qwq", "deepseek-r1"))


def _get_default_model(openrouter_key):
    """Read the main default model + provider from Hermes config so the script
    always follows the agent's configured default instead of a hardcoded model.
    Note: the only API key present is OPENROUTER_API_KEY, so regardless of the
    configured provider we route through OpenRouter. If the configured default is
    the now-dead hy3:free (or missing), fall back to a working free model."""
    try:
        import yaml
        with open(os.path.expanduser("~/.hermes/config.yaml")) as f:
            cfg = yaml.safe_load(f)
        m = cfg.get("model", {})
        model = m.get("default") or ""
    except Exception:
        model = ""
    model = model.strip()
    if not model or model == "tencent/hy3:free":
        model = _FALLBACK_FREE_MODEL
    return model, openrouter_key, "https://openrouter.ai/api/v1"


def summarize_content(text, openrouter_key=None):
    """Summarize content using the agent's default model (reads Hermes config).

    Robust against reasoning-only models (e.g. tencent/hy3:free):
      - they need `reasoning.effort: minimal` and a LARGE max_tokens budget
        (the reasoning trace eats tokens before `content` is emitted; a 300-token
        budget returns None content and crashes naive `.strip()`).
      - on any None/empty, we retry with a bigger budget, then fall back to truncation.
    """
    if not text or len(text.strip()) < 50:
        return (text or "")[:300] + ("..." if len(text or "") > 300 else "")
    if not openrouter_key:
        return text[:300] + ("..." if len(text) > 300 else "")

    try:
        from openai import OpenAI
        model, api_key, base_url = _get_default_model(openrouter_key)
        client = OpenAI(api_key=api_key, base_url=base_url)

        messages = [
            {"role": "system", "content": (
                "You are a newsletter editor. Summarize the news items below into ONE tight section. "
                "Rules: (1) Output ONLY the summary text - never any meta-commentary such as 'the user wants', "
                "'let me process', or 'here is a summary'. (2) Do NOT use numbered lists (1. 2. 3.); use short "
                "bullet points instead, each starting with a **bold lead phrase:** then 1-2 sentences of fact + implication. "
                "(3) Each bullet max 2 sentences, no fluff, no 'this means for the field' commentary. "
                "(4) Skip items that are not real news (gardening, recipes, promotions, pure celebrity/entertainment). "
                "(5) Be direct and factual."
            )},
            {"role": "user", "content": f"Summarize these news items into the section. No meta-text, no numbered lists, no fluff.\n\n{text[:6000]}"}
        ]

        # World/large sections can contain 15 items and need ~2500 tokens to
        # summarize without truncation; smaller sections simply stop early, so a
        # generous budget is safe for every model type.
        # Reasoning-only models (e.g. tencent/hy3:free) need the `reasoning`
        # extra_body param; standard models must NOT receive it (it errors).
        is_reasoning = _is_reasoning_model(model)
        extra = {"reasoning": {"effort": "minimal"}} if is_reasoning else {}
        budgets = (2500, 4000)
        for budget in budgets:
            try:
                kwargs = dict(
                    model=model,
                    messages=messages,
                    max_tokens=budget,
                    temperature=0.2,
                )
                if extra:
                    kwargs["extra_body"] = extra
                response = client.chat.completions.create(**kwargs)
                message = response.choices[0].message
                summary = message.content
                if not summary or not summary.strip():
                    # Last resort: pull the final answer out of the reasoning trace
                    reasoning = getattr(message, "reasoning", None)
                    if reasoning and reasoning.strip():
                        summary = reasoning.strip().split("\n")[-1]
                if summary and summary.strip():
                    return summary.strip()
            except Exception as e:
                print(f"    Summarization attempt (budget={budget}) failed: {e}")
        raise ValueError("Empty content from model after retries")
    except Exception as e:
        print(f"    Summarization failed: {e}")
        print(f"    Fallback text length: {len(text)}")
        # Fallback to truncation - clean up the "TITLE: ... CONTENT: ..." format
        if len(text.strip()) == 0:
            return "No content available for summarization."
        lines = text.split('\n')
        clean_parts = []
        for line in lines:
            line = line.strip()
            if line.startswith('TITLE:') or line.startswith('CONTENT:'):
                content = line.split(':', 1)[1].strip() if ':' in line else line
                if content and content != 'Untitled':
                    clean_parts.append(content)
            elif line and not line.startswith('TITLE:') and not line.startswith('CONTENT:'):
                clean_parts.append(line)
        clean_text = ' '.join(clean_parts)
        return clean_text[:500] + ("..." if len(clean_text) > 500 else "")

def categorize_and_synthesize(articles, config):
    """Categorize articles by topic and create synthesized narratives"""
    science_content = []
    llm_ai_content = []
    international_content = []
    other_content = []
    
    # Keywords for topic detection
    science_keywords = [
        'science', 'research', 'study', 'discovery', 'breakthrough', 'nasa', 'space',
        'climate', 'environment', 'physics', 'biology', 'chemistry', 'medical',
        'health', 'disease', 'vaccine', 'drug', 'treatment', 'innovation',
        'quantum', 'particle', 'genetics', 'dna', 'rna', 'protein', 'cell', 'molecule',
        'astronomy', 'astrophysics', 'cosmology', 'geology', 'oceanography',
        'heatwave', 'temperature', 'weather', 'storm', 'hurricane', 'flood',
        'robot', 'robotics', 'autonomous', 'electric vehicle', 'ev', 'battery',
        'semiconductor', 'chip', 'microprocessor', 'computing', 'supercomputer',
        'crispr', 'gene therapy', 'clinical trial', 'fda', 'pharmaceutical',
        'renewable energy', 'solar', 'wind power', 'nuclear', 'fusion'
    ]
    
    llm_ai_keywords = [
        'ai ', 'ai-', 'artificial intelligence', 'machine learning', 'llm', 'language model',
        'neural network', 'deep learning', 'chatbot', 'openai', 'anthropic', 'google ai',
        'gpt-', 'gpt4', 'claude', 'gemini', 'llama', 'mistral', 'phi-', 'transformer model',
        'diffusion model', 'generative ai', 'foundation model', 'multimodal',
        'large language model', 'fine-tuning', 'fine tuning', 'rag ', 'agentic',
        'nvidia', 'cuda', 'gpu', 'ai chip', 'ai hardware', 'inference',
        'text-to-', 'image generation', 'text generation', 'ai model',
        'benchmark', 'training data', 'reinforcement learning from human',
        'rlhf', 'alignment', 'hallucination', 'reasoning model'
    ]
    
    international_keywords = [
        'international', 'global', 'world', 'europe', 'asia', 'africa', 'middle east',
        'china', 'russia', 'ukraine', 'israel', 'palestine', 'india', 'japan',
        'korea', 'brazil', 'mexico', 'canada', 'australia', 'germany', 'france',
        'diplomacy', 'foreign policy', 'sanctions', 'alliance', 'nato', 'un ',
        'european union', 'brexit', 'india-pakistan', 'south china sea',
        'prime minister', 'president', 'congress', 'parliament', 'election',
        'primary', 'gop', 'democrat', 'republican', 'trump', 'biden',
        'war', 'conflict', 'military', 'army', 'navy', 'missile', 'nuclear weapon',
        'treaty', 'summit', 'embargo', 'refugee', 'humanitarian'
    ]
    
    # Exclude pure finance/business from topic sections
    # These match earnings calls, fund reports, and SEC filings that aren't newsworthy otherwise
    finance_business_keywords = [
        'earnings call', 'earnings presentation', 'earnings call transcript',
        'fund commentary', 'q1 2026', 'q2 2026', 'q3 2026', 'q4 2026',
        'q1 2025', 'q2 2025', 'q3 2025', 'q4 2025',
        'form 144', 'form 13d', 'form def', 'sec filing',
        'stock analysis', 'stock surges', 'stock rally', 'market cap',
        'dividend growth', 'corporate bond', 'rising dividend',
        'index dynamics', 'egress filtering', 'security tool',
        'named official', 'official partner', 'design software partner',
        'validates ai-ran', 'ai-ran blueprint', 'infrastructure',
        'press release', 'announces partnership', 'strategic partnership',
        'collaboration agreement', 'memorandum of understanding',
        'wall street', 'beat estimates', 'beat consensus', 'consensus estimates',
        'fiscal quarter', 'fiscal year', 'year-to-date', 'ytd',
        'revenue beat', 'earnings beat', 'eps beat', 'guidance',
        'cheap stocks', 'stocks to buy', 'stocks to watch', 'about to explode',
        'undervalued', 'overvalued', 'price target', 'analyst rating',
        'upgrade', 'downgrade', 'buy rating', 'sell rating', 'hold rating',
        'portfolio', 'investment', 'investor', 'shareholder', 'dividend yield',
        'market beat', 'seeking alpha', 'motley fool', 'insider monkey',
        'zacks', 'benzinga', 'streetinsider', 'fool.com'
    ]
    # Regex pattern: Company (TICKER) Q[1-4] or "Q[1-4] [Year] Earnings"
    import re as _re
    earnings_pattern = _re.compile(r'\([A-Z]{1,5}\)\s*(?:Q[1-4]|presents)|Q[1-4]\s+\d{4}\s+(?:earnings|results|commentary)|(?:Q[1-4]\s+)?\d{4}\s+(?:Earnings|Results)\s+(?:Call|Transcript|Presentation)', re.I)
    # Additional pattern for corporate press releases with tickers
    corp_press_pattern = _re.compile(r'\([A-Z]{1,5}\)\s+(?:named|announces?|validates?|partners?|launches?|acquires?|acquires?|reports?|signs?|extends?)', re.I)
    
    for article in articles:
        if not isinstance(article, dict):
            continue
            
        title = article.get('title', '').lower()
        # Handle content which is now a dict after extraction
        content_field = article.get('content', {})
        if isinstance(content_field, dict):
            content = str(content_field.get('content', '') or '').lower()
        else:
            content = str(content_field or '').lower()
        combined = f"{title} {content}"
        
        # Check categories for stronger signals
        categories = article.get('categories', [])
        category_str = ' '.join(categories).lower()
        
        # Score each category (count keyword matches for ranking)
        science_score = sum(1 for kw in science_keywords if kw in combined)
        llm_ai_score = sum(1 for kw in llm_ai_keywords if kw in combined)
        international_score = sum(1 for kw in international_keywords if kw in combined)
        
        # Check if it's primarily a finance/business article (check title AND combined)
        is_finance = any(kw in combined for kw in finance_business_keywords) or bool(earnings_pattern.search(title)) or bool(corp_press_pattern.search(title))
        
        # Category labels from FreshRSS feeds.
        # NOTE: match 'ai' as a delimited token (e.g. '.../label/ai'), NOT as a bare
        # substring -- 'entertainment' contains 'ai' (enter*tai*nment) and was wrongly
        # boosting crime/entertainment items into the AI & Tech section.
        has_tech_cat = (
            any(c in category_str for c in ['technology', 'tech news'])
            or re.search(r'(?:^|[/ ])ai(?:$|[/ ])', category_str, re.I) is not None
        )
        has_science_cat = any(c in category_str for c in ['science'])
        has_world_cat = any(c in category_str for c in ['news-global', 'world', 'politics'])
        
        # Boost scores based on feed categories
        if has_tech_cat:
            llm_ai_score += 3
        if has_science_cat:
            science_score += 3
        if has_world_cat:
            international_score += 3
        
        # Determine primary category with priority: Finance exclusion > AI > Science > International
        # Pure finance articles are excluded from all topic sections even if they match keywords
        if is_finance:
            other_content.append(article)
        elif llm_ai_score >= 2 and llm_ai_score >= science_score:
            llm_ai_content.append(article)
        elif science_score >= 2:
            science_content.append(article)
        elif international_score >= 1:
            international_content.append(article)
        else:
            other_content.append(article)
    
    # Create synthesized narratives for each topic
    narratives = {}
    
    if science_content:
        science_text = "\n\n".join([
            f"TITLE: {a.get('title', 'Untitled')}\nCONTENT: {a.get('content', {}).get('content', '')[:1000] if isinstance(a.get('content', {}), dict) else str(a.get('content', '') or '')[:1000]}"
            for a in science_content[:15]  # Limit to prevent overload
        ])
        narratives['science'] = summarize_content(science_text, config['openrouter_key']) if science_text.strip() else "No significant science developments detected."

    if llm_ai_content:
        llm_text = "\n\n".join([
            f"TITLE: {a.get('title', 'Untitled')}\nCONTENT: {a.get('content', {}).get('content', '')[:1000] if isinstance(a.get('content', {}), dict) else str(a.get('content', '') or '')[:1000]}"
            for a in llm_ai_content[:15]
        ])
        narratives['llm_ai'] = summarize_content(llm_text, config['openrouter_key']) if llm_text.strip() else "No significant LLM/AI developments detected."

    if international_content:
        international_text = "\n\n".join([
            f"TITLE: {a.get('title', 'Untitled')}\nCONTENT: {a.get('content', {}).get('content', '')[:1000] if isinstance(a.get('content', {}), dict) else str(a.get('content', '') or '')[:1000]}"
            for a in international_content[:15]
        ])
        narratives['international'] = summarize_content(international_text, config['openrouter_key']) if international_text.strip() else "No significant international developments detected."
    
    return narratives

def generate_newsletter():
    """Main newsletter generation function - creates one cohesive narrative"""
    print("=== Starting Cohesive Newsletter Generation (IP Direct) ===")
    
    # Get configuration
    config = get_freshrss_config()
    
    print(f"Username: {config['username']}")
    print(f"Base URL (from config): {config['base_url']}")
    print(f"API Base (from config): {config['api_base']}")
    print(f"Using IP Direct: {config['freshrss_ip']}:{config['freshrss_port']} with Host: {config['freshrss_host']}")
    print(f"Max articles to process: {config['max_articles']}")
    print(f"Lookback hours: {config['lookback_hours']}")
    print(f"Has OpenRouter key: {'Yes' if config['openrouter_key'] else 'No'}")
    print(f"Has Jina key: {'Yes' if config['jina_key'] else 'No'}")
    
    if not config['username'] or not config['password']:
        return "Error: FreshRSS credentials not configured"
    
    try:
        # Authenticate using IP direct
        print("\n1. Authenticating with FreshRSS (IP Direct)...")
        auth_token = get_auth_token_ip_direct(
            config['username'], 
            config['password'], 
            config
        )
        print("   ✓ Authentication successful")
        
        # Fetch articles using IP direct (with sports filtering)
        print(f"\n2. Fetching up to {config['max_articles']} articles from last {config['lookback_hours']} hours (excluding sports)...")
        articles = fetch_unread_articles_ip_direct(
            auth_token,
            config,
            config['max_articles'],
            config['lookback_hours']
        )
        print(f"   ✓ Found {len(articles)} non-sports articles")
        
        # Extract content for each article using waterfall method.
        #
        # The target is N EXTRACTABLE articles, not N candidates. Roughly
        # half of what a news feed offers cannot be extracted by a plain
        # HTTP fetch, so candidates are drawn in waves: extract, drop the
        # failures, and pull replacements until the target is met or the
        # feed is exhausted. Previously the list was cut to 50 up front and
        # every failure was simply lost, so a bad hour produced a thin
        # newsletter built from a fraction of the available stories.
        if articles and (config['jina_key'] or True):
            target = config['max_articles']
            # Over-fetch: extraction failure is common enough that asking for
            # exactly `target` candidates guarantees a short result.
            candidates = articles
            print(f"\n   Extracting content for articles (target: {target} extractable)...")

            extracted_articles = []
            seen_titles = set()
            cursor = 0
            attempts = 0
            # A hard ceiling so a bad feed cannot spin here for an hour.
            max_attempts = max(target * 6, 300)

            while (len(extracted_articles) < target
                   and cursor < len(candidates)
                   and attempts < max_attempts):
                batch = candidates[cursor:cursor + 10]
                cursor += 10
                for article in batch:
                    if len(extracted_articles) >= target or attempts >= max_attempts:
                        break
                    attempts += 1
                    key = (article.get('title') or '').strip().lower()[:120]
                    if key in seen_titles:
                        continue
                    seen_titles.add(key)

                    if attempts % 5 == 0:
                        print(f"     tried {attempts}, have "
                              f"{len(extracted_articles)}/{target} extractable...")

                    extracted = extract_content_with_waterfall(article, config['jina_key'])
                    if not extracted or not extracted.get('content'):
                        continue
                    article['content'] = {'content': extracted['content']}
                    article['_extraction_method'] = extracted.get('method', 'unknown')
                    extracted_articles.append(article)

            articles = extracted_articles[:target]
            print(f"   ✓ {len(articles)} extractable articles from {attempts} attempts")
            if len(articles) < target:
                print(f"   ! short of target by {target - len(articles)}: "
                      f"feed exhausted ({len(candidates)} candidates available)")
            methods = {}
            for a in articles:
                m = a.get('_extraction_method', '?')
                methods[m] = methods.get(m, 0) + 1
            print(f"   extraction methods: {methods}")
        
        if not articles:
            return f"""# News Brief

*{datetime.now().strftime('%Y-%m-%d %H:%M')}*
*No significant non-sports developments found in the last {config['lookback_hours']} hours.*"""
        
        # Synthesize content by topic
        print(f"\n3. Synthesizing content by topic...")
        narratives = categorize_and_synthesize(articles, config)
        
        # Build the cohesive newsletter
        print(f"\n4. Assembling cohesive narrative...")
        newsletter_lines = [
            "# News Brief",
            f"*{datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            "",
            "---",
            ""
        ]
        
        # Add synthesized sections in order of priority
        sections = [
            ('science', '🔬 Science'),
            ('llm_ai', '🤖 AI & Tech'),
            ('international', '🌍 World')
        ]
        
        for section_key, section_title in sections:
            if section_key in narratives and narratives[section_key].strip():
                newsletter_lines.extend([
                    f"## {section_title}",
                    "",
                    narratives[section_key],
                    "",
                    "---",
                    ""
                ])
        
        # Remove trailing separators
        if len(newsletter_lines) >= 2 and newsletter_lines[-2] == "---" and newsletter_lines[-1] == "":
            newsletter_lines = newsletter_lines[:-2]
        elif len(newsletter_lines) >= 1 and newsletter_lines[-1] == "---":
            newsletter_lines = newsletter_lines[:-1]
        
        # Join and return
        newsletter_text = "\n".join(newsletter_lines)
        print(f"\n5. Newsletter synthesized successfully ({len(newsletter_text)} characters)")
        return newsletter_text
        
    except Exception as e:
        import traceback
        print(f"\n✗ Error during generation: {e}")
        traceback.print_exc()
        return f"""# Newsletter Generation Error

*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Error: {str(e)}*

Please check:
1. FreshRSS service is running at 10.0.0.10 (local server)
2. The IP direct connection is working (no /etc/hosts changes needed)
3. Credentials in /home/operator/.hermes/.env are correct
4. Network connectivity"""

if __name__ == "__main__":
    import os
    import tempfile
    result = generate_newsletter()
    
    # Write to a temp file for delivery
    temp_dir = os.environ.get('TMPDIR', '/home/operator/.hermes/cache/scratch')
    newsletter_path = os.path.join(temp_dir, f"newsletter_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt")
    with open(newsletter_path, 'w') as f:
        f.write(result)
    print(f"Newsletter written to: {newsletter_path}")
    print("\n" + "="*60)
    print("NEWSLETTER OUTPUT:")
    print("="*60)
    print(result)
