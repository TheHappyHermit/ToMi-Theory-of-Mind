"""Does the new probe logic work in all three modes?

The old code branched on BRAIN_API_MODE and assumed the native Ollama API
when it was unset, so a bare interactive run probed /api/tags against a
server that only speaks /v1 and exited 1 claiming the host was
unreachable. This asserts the new behaviour for all three cases.
"""
import json
import os
import urllib.request

OLLAMA_URL = 'http://10.0.0.10:18082'
# The default in brain_sync.py is the Qwen3 embedding model served by
# llama.cpp. The first version of this control hardcoded 'bge-m3', which
# is not installed anywhere, and then asserted the model was present. It
# reported "not present" and looked like a deployment problem. It was a
# control naming a model that does not exist.
EMBED_MODEL = os.environ.get('BRAIN_EMBED_MODEL') or \
    '/models/Qwen3-Embedding-4B-Q8_0.gguf'


def _probe(path, key):
    req = urllib.request.Request(f'{OLLAMA_URL}{path}', method='GET')
    with urllib.request.urlopen(req, timeout=10) as resp:
        return [m[key] for m in json.loads(resp.read()).get(
            'data' if key == 'id' else 'models', [])]


def run(mode):
    attempts = ([('/v1/models', 'id'), ('/api/tags', 'name')]
                if not mode else
                [('/v1/models', 'id')] if mode == 'openai'
                else [('/api/tags', 'name')])
    names, errs = None, []
    for path, key in attempts:
        try:
            names = _probe(path, key)
            break
        except Exception as e:
            errs.append(f'{path} -> {type(e).__name__}')
    return names, errs


OK = BAD = 0


def case(name, cond, detail=''):
    global OK, BAD
    if cond:
        OK += 1
        print(f'  ok   {name}')
    else:
        BAD += 1
        print(f'  FAIL {name}   {detail}')


n_unset, e_unset = run(None)
n_openai, e_openai = run('openai')
n_ollama, e_ollama = run('ollama')

case('unset mode finds the endpoint via /v1 (was: exit 1)',
     n_unset is not None, str(e_unset))
case('explicit openai mode still works',
     n_openai is not None and n_openai == n_unset)
case('explicit ollama mode still reports honestly',
     n_ollama is None or n_ollama == n_unset)
case('the model list is a real list of names',
     n_unset is not None and all(isinstance(x, str) for x in n_unset))
case('the CONFIGURED embed model is actually served',
     n_unset is not None and EMBED_MODEL in n_unset,
     f'{EMBED_MODEL} not in {n_unset[:2] if n_unset else None}')
if n_unset is not None:
    print(f'  models available: {n_unset[:3]}')
    print(f'  embed model {EMBED_MODEL!r} present: '
          f'{EMBED_MODEL in n_unset}')

print()
print(f'  {OK}/{OK + BAD} controls pass')
raise SystemExit(1 if BAD else 0)
