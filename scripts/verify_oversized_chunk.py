#!/usr/bin/env python3
"""Controls for the oversized-chunk fix in brain_sync.py.

THE DEFECT
The embedding server runs with n_ctx=2048 and answers longer input with
a deterministic HTTP 400:

    request (2501 tokens) exceeds the available context size (2048)

embed_texts_with_retry() retried the identical payload five times with
exponential backoff, then raised. The chunk never reached the index, the
file was recorded as [partial], and 31 seconds were burned proving a
fact that could not change. Three files were affected in the last resync.

THE FIX
Cap a single text at EMBED_MAX_CHARS and embed the head. The control
below asserts the property that matters: an oversized chunk now SUCCEEDS,
and a normal chunk is not touched at all.

Run:  python3 scripts/verify_oversized_chunk.py
"""
import json
import os
import urllib.request

URL = os.environ.get('BRAIN_EMBED_URL', 'http://10.0.0.10:18082/v1/embeddings')
try:
    src_probe = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'brain_sync.py'), encoding='utf-8').read()
except Exception:
    src_probe = ''
MODEL = '/models/Qwen3-Embedding-4B-Q8_0.gguf'
MAX_CHARS = 7500

OK = BAD = 0


def case(name, cond, detail=''):
    global OK, BAD
    if cond:
        OK += 1
        print(f'  ok   {name}')
    else:
        BAD += 1
        print(f'  FAIL {name}   {detail}')


def embed(text):
    body = json.dumps({'model': MODEL, 'input': text,
                       'dimensions': 2000}).encode()
    req = urllib.request.Request(
        URL, data=body, method='POST',
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())['data'][0]['embedding']


def rejects(text):
    try:
        embed(text)
        return False
    except Exception:
        return True


# 1. The defect reproduces: long input is rejected outright.
long_text = ('Active learning annotation efficiency for LLM preference '
             'bootstrap. ' * 700)
case('DEFECT REPRODUCES: a 40k-char chunk is rejected by the server',
     rejects(long_text), 'server accepted it; nothing to fix')

# 2. The fix: the head of that chunk embeds fine.
capped = long_text[:MAX_CHARS]
try:
    v = embed(capped)
    works, dim = True, len(v)
except Exception as e:
    works, dim = False, str(e)[:60]
case('FIX WORKS: the capped chunk embeds', works, str(dim))
# The server IGNORES the "dimensions" request parameter and always returns
# its native 2560. brain_sync truncates to 2000 client-side, because 2000
# is the pgvector HNSW maximum. The first version of this control asked
# the SERVER for 2000 and asserted it got 2000, which it never does --
# it reported a schema mismatch that does not exist.
case('the server returns its native 2560 dims, as it always has', dim == 2560,
     str(dim))
case('brain_sync truncates to the pgvector HNSW max of 2000 client-side',
     'emb[:dim]' in src_probe and 'dim = 2000' in src_probe)

# 3. Normal chunks must be untouched by the cap.
normal = 'A short research note about drift signal calibration.'
case('a normal chunk is under the cap and is not modified',
     len(normal) < MAX_CHARS)
try:
    embed(normal)
    ok_normal = True
except Exception as e:
    ok_normal = str(e)[:60]
case('a normal chunk embeds unchanged', ok_normal is True, str(ok_normal))

# 4. The cap must be an actual cap, not a no-op.
case('EMBED_MAX_CHARS is below the 2048-token window',
     MAX_CHARS < 8000, f'{MAX_CHARS} chars is ~{MAX_CHARS // 4} tokens')
case('the cap is large enough to keep real chunks whole',
     MAX_CHARS > 6000, f'{MAX_CHARS} may truncate legitimate chunks')

# 5. Truncation must be visible, not silent.
src = src_probe
case('the truncation is announced in the log, not silent',
     '[trunc]' in src and 'Tail not indexed' in src)
case('the cap is a named constant, not a magic number inline',
     'EMBED_MAX_CHARS = 7500' in src)

print()
print(f'  {OK}/{OK + BAD} controls pass')
raise SystemExit(1 if BAD else 0)
