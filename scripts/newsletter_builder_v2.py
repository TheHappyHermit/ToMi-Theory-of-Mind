#!$HOME/.hermes/newsletter_venv/bin/python3
"""
Daily Newsletter Builder for FreshRSS - Cohesive Topic-Based Version
Excludes sports, creates one cohesive narrative focusing on science, LLM/AI, and international news
"""
import os
from pathlib import Path
import sys
import json
import hashlib
import sqlite3
from datetime import datetime, timedelta
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import re

# Add the venv to path for openai/trafilatura
# Resolve the newsletter venv at runtime. This was a literal unexpanded
# '$HOME/...' string, so it inserted a path that does not exist.
sys.path.insert(0, str(Path(os.path.expanduser(
    '~/.hermes/newsletter_venv/lib/python3.14/site-packages'))))

try:
    import trafilatura
    import openai
except ImportError as e:
    print(f"Warning: Some imports failed: {e}")
    # Continue anyway - we'll have fallbacks

def load_env():
    """Load environment variables from .env file"""
    env_path = str(Path(os.path.expanduser('~/.hermes/.env')))
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
    base_url = os.getenv('FRESHRSS_URL', 'http://127.0.0.1:8080').rstrip('/')
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
        'freshrss_ip': os.environ.get('FRESHRSS_URL', 'http://127.0.0.1'),
        'freshrss_port': 443,
        'freshrss_host': os.getenv('FRESHRSS_HOST', '')  # For Host header (optional, when routing via a reverse proxy by IP)
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
            "output": "json"
            # Note: We're NOT using 'ot' or 'r' parameters here - we'll filter ourselves
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
    return filtered_items[:max_articles]

def extract_content_with_waterfall(item, jina_key=None):
    """Extract content using waterfall method"""
    title = item.get("title", "Untitled")
    url = ""
    alternates = item.get("alternate", [])
    if alternates:
        url = alternates[0].get("href", "")
    
    # Stage 1: FreshRSS content
    content = item.get("content", {}).get("content", "")
    if not content or len(content.strip()) < 100:
        content = item.get("summary", {}).get("content", "")
    
    # If we have decent content, use it
    if content and len(content.strip()) >= 200:
        return {
            "title": title,
            "url": url,
            "content": content.strip(),
            "method": "freshsrss"
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
                    
                    if extracted and len(extracted.strip()) >= 150:
                        return {
                            "title": title,
                            "url": url,
                            "content": extracted.strip(),
                            "method": "trafilatura"
                        }
                except:
                    pass
                
                # Fallback to raw text if we got something
                if len(resp.text) > 100:
                    # Simple HTML tag removal
                    import re
                    text = re.sub('<[^<]+?>', '', resp.text)
                    text = re.sub(r'\s+', ' ', text).strip()
                    if len(text) >= 100:
                        return {
                            "title": title,
                            "url": url,
                            "content": text[:2000],  # Limit size
                            "method": "html_text"
                        }
        except Exception as e:
            print(f"    URL fetch failed: {e}")
    
    # Stage 3: Jina Reader
    if url and jina_key:
        try:
            jina_url = f"https://r.jina.ai/http://{url}"
            headers = {"Authorization": f"Bearer {jina_key}"} if jina_key else {}
            resp = requests.get(jina_url, headers=headers, timeout=15, verify=False)
            if resp.status_code == 200 and len(resp.text) > 100:
                return {
                    "title": title,
                    "url": url,
                    "content": resp.text.strip(),
                    "method": "jina"
                }
        except Exception as e:
            print(f"    Jina failed: {e}")
    
    # Stage 4: Return summary with note
    summary = item.get("summary", {}).get("content", "")
    if summary and len(summary.strip()) >= 50:
        note_text = "\n\n*Note: Full content extraction failed, showing RSS summary*"
        return {
            "title": title,
            "url": url,
            "content": summary.strip() + note_text,
            "method": "summary_fallback"
        }
    
    # Stage 5: Ultimate fallback
    return {
        "title": title,
        "url": url,
        "content": f"[Unable to extract content for: {title}]",
        "method": "failed"
    }

def _get_default_model(openrouter_key):
    """Read the main default model + provider from Hermes config so the script
    always follows the agent's configured default instead of a hardcoded model.
    Note: the only API key present is OPENROUTER_API_KEY, so regardless of the
    configured provider we route through OpenRouter (hy3:free is available there)."""
    try:
        import yaml
        with open(os.path.expanduser("~/.hermes/config.yaml")) as f:
            cfg = yaml.safe_load(f)
        m = cfg.get("model", {})
        model = m.get("default", "tencent/hy3:free")
        return model, openrouter_key, "https://openrouter.ai/api/v1"
    except Exception:
        return "tencent/hy3:free", openrouter_key, "https://openrouter.ai/api/v1"


def summarize_content(text, openrouter_key=None):
    """Summarize content using the agent's default model (reads Hermes config)"""
    if not openrouter_key or not text or len(text.strip()) < 50:
        # Return first 300 chars as fallback
        return text[:300] + ("..." if len(text) > 300 else "")
    
    try:
        import openai
        model, api_key, base_url = _get_default_model(openrouter_key)
        openai.api_key = api_key
        openai.base_url = base_url
        
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a news analyst. Create a sophisticated, flowing summary that connects related developments into a coherent narrative about trends and implications."},
                {"role": "user", "content": f"Please analyze and synthesize the following news developments into a cohesive paragraph about what this means for the field and its broader implications:\\n\\n{text[:6000]}"}
            ],
            max_tokens=500,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"    Summarization failed: {e}")
        # Fallback to truncation
        return text[:500] + ("..." if len(text) > 500 else "")

def categorize_and_synthesize(articles, config):
    """Categorize articles by topic and create synthesized narratives"""
    science_content = []
    llm_ai_content = []
    international_content = []
    other_content = []
    
    # Keywords for topic detection
    science_keywords = [
        'science', 'research', 'study', 'discovery', 'breakthrough', 'nasa', 'space',
        'climate', 'environment', 'energy', 'physics', 'biology', 'chemistry', 'medical',
        'health', 'disease', 'vaccine', 'drug', 'treatment', 'technology', 'innovation',
        'quantum', 'particle', 'genetics', 'dna', 'rna', 'protein', 'cell', 'molecule',
        'astronomy', 'astrophysics', 'cosmology', 'geology', 'oceanography'
    ]
    
    llm_ai_keywords = [
        'ai', 'artificial intelligence', 'machine learning', 'llm', 'language model',
        'neural network', 'deep learning', 'chatbot', 'openai', 'anthropic', 'google ai',
        'gpt', 'claude', 'gemini', 'llama', 'mistral', 'phi', 'transformer', 'diffusion',
        'generative ai', 'foundation model', 'multimodal', 'prompt engineering'
    ]
    
    international_keywords = [
        'international', 'global', 'world', 'europe', 'asia', 'africa', 'middle east',
        'china', 'russia', 'uk', 'ukraine', 'israel', 'palestine', 'india', 'japan',
        'korea', 'brazil', 'mexico', 'canada', 'australia', 'germany', 'france',
        'diplomacy', 'foreign policy', 'trade', 'sanctions', 'alliance', 'nato', 'un',
        'european union', 'brexit', 'india-pakistan', 'south china sea'
    ]
    
    for article in articles:
        if not isinstance(article, dict):
            continue
            
        title = article.get('title', '').lower()
        content = article.get('content', '').lower()
        combined = f"{title} {content}"
        
        # Check categories for stronger signals
        categories = article.get('categories', [])
        category_str = ' '.join(categories).lower()
        
        # Determine primary category
        is_science = any(kw in category_str for kw in ['science', 'tech news', 'technology']) or \
                     any(kw in combined for kw in science_keywords)
                     
        is_llm_ai = any(kw in category_str for kw in ['ai', 'technology']) or \
                    any(kw in combined for kw in llm_ai_keywords)
                    
        is_international = any(kw in category_str for kw in ['news-global', 'world']) or \
                          any(kw in combined for kw in international_keywords)
        
        # Avoid double-counting - prioritize more specific categories
        if is_science and not (is_llm_ai or is_international):
            science_content.append(article)
        elif is_llm_ai and not is_international:
            llm_ai_content.append(article)
        elif is_international:
            international_content.append(article)
        else:
            other_content.append(article)
    
    # Create synthesized narratives for each topic
    narratives = {}
    
    if science_content:
        science_text = "\n\n".join([
            f"TITLE: {a.get('title', 'Untitled')}\nCONTENT: {a.get('content', '')[:1000]}"
            for a in science_content[:15]  # Limit to prevent overload
        ])
        narratives['science'] = summarize_content(science_text, config['openrouter_key']) if science_text.strip() else "No significant science developments detected."
    
    if llm_ai_content:
        llm_text = "\n\n".join([
            f"TITLE: {a.get('title', 'Untitled')}\nCONTENT: {a.get('content', '')[:1000]}"
            for a in llm_ai_content[:15]
        ])
        narratives['llm_ai'] = summarize_content(llm_text, config['openrouter_key']) if llm_text.strip() else "No significant LLM/AI developments detected."
    
    if international_content:
        international_text = "\n\n".join([
            f"TITLE: {a.get('title', 'Untitled')}\nCONTENT: {a.get('content', '')[:1000]}"
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
        
        if not articles:
            return f"""# Weekly News Synthesis: Science, Technology & Global Affairs

*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*No significant non-sports developments found in the last {config['lookback_hours']} hours.*"""
        
        # Synthesize content by topic
        print(f"\n3. Synthesizing content by topic...")
        narratives = categorize_and_synthesize(articles, config)
        
        # Build the cohesive newsletter
        print(f"\n4. Assembling cohesive narrative...")
        newsletter_lines = [
            "# Weekly Intelligence Brief: Science, Technology & Global Affairs",
            f"*Synthesized: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            f"*Analyzed {len(articles)} developments across scientific, technological, and international domains*",
            "",
            "---",
            ""
        ]
        
        # Add synthesized sections in order of priority
        sections = [
            ('science', '🔬 SCIENTIFIC ADVANCEMENTS', 'Breakthroughs in research, discovery, and innovation'),
            ('llm_ai', '🤖 ARTIFICIAL INTELLIGENCE & TECHNOLOGY', 'Developments in AI, LLMs, and computing'),
            ('international', '🌍 GLOBAL AFFAIRS & INTERNATIONAL RELATIONS', 'Diplomacy, conflicts, and global trends')
        ]
        
        for section_key, section_title, section_desc in sections:
            if section_key in narratives and narratives[section_key].strip():
                newsletter_lines.extend([
                    f"## {section_title}",
                    f"*{section_desc}*",
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
1. FreshRSS service is running at $FRESHRSS_URL
2. The IP direct connection is working (no /etc/hosts changes needed)
3. Credentials in $HOME/.hermes/.env are correct
4. Network connectivity"""

if __name__ == "__main__":
    result = generate_newsletter()
    print("\n" + "="*60)
    print("NEWSLETTER OUTPUT:")
    print("="*60)
    print(result)
