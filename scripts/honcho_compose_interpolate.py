#!/usr/bin/env python3
"""
Convert the deriver's hardcoded model values to ${...} interpolation.

The compose currently hardcodes the model name and base URL as literals, so
editing .env cannot change a running stack -- a new install gets whatever
the commit happened to contain. This replaces the literals with
interpolations that fall back to the current working values, so:

  - behaviour is identical when the vars are unset (defaults preserved)
  - a new install only has to put the vars in .env
  - the docker change is additive: no Honcho source is touched
"""
import re

P = "/home/operator/docker/docker-compose.honcho.yml"
s = open(P).read()

OLD_MODEL = "/models/Qwen3.5-4B-UD-Q4_K_XL.gguf"
OLD_URL = "http://10.0.0.10:18081/v1"
OLD_KEY = "sk-local"

NEW_MODEL = "${HONCHO_DERIVATION_MODEL:-" + OLD_MODEL + "}"
NEW_URL = "${HONCHO_DERIVATION_BASE_URL:-" + OLD_URL + "}"
NEW_KEY = "${HONCHO_DERIVATION_API_KEY:-" + OLD_KEY + "}"

before_model = s.count(OLD_MODEL)
before_url = s.count(OLD_URL)

# Only touch the model-config lines, not the image or unrelated settings.
s = s.replace(
    f"- DIALECTIC_LEVELS__minimal__MODEL_CONFIG__MODEL={OLD_MODEL}",
    f"- DIALECTIC_LEVELS__minimal__MODEL_CONFIG__MODEL={NEW_MODEL}")
s = s.replace(
    f"- DIALECTIC_LEVELS__low__MODEL_CONFIG__MODEL={OLD_MODEL}",
    f"- DIALECTIC_LEVELS__low__MODEL_CONFIG__MODEL={NEW_MODEL}")
s = s.replace(
    f"- DIALECTIC_LEVELS__medium__MODEL_CONFIG__MODEL={OLD_MODEL}",
    f"- DIALECTIC_LEVELS__medium__MODEL_CONFIG__MODEL={NEW_MODEL}")
s = s.replace(
    f"- DIALECTIC_LEVELS__high__MODEL_CONFIG__MODEL={OLD_MODEL}",
    f"- DIALECTIC_LEVELS__high__MODEL_CONFIG__MODEL={NEW_MODEL}")
s = s.replace(
    f"- DIALECTIC_LEVELS__max__MODEL_CONFIG__MODEL={OLD_MODEL}",
    f"- DIALECTIC_LEVELS__max__MODEL_CONFIG__MODEL={NEW_MODEL}")
s = s.replace(
    f"- DERIVER_MODEL_CONFIG__MODEL={OLD_MODEL}",
    f"- DERIVER_MODEL_CONFIG__MODEL={NEW_MODEL}")
s = s.replace(
    f"- SUMMARY_MODEL_CONFIG__MODEL={OLD_MODEL}",
    f"- SUMMARY_MODEL_CONFIG__MODEL={NEW_MODEL}")
s = s.replace(
    f"- DREAM_DEDUCTION_MODEL_CONFIG__MODEL={OLD_MODEL}",
    f"- DREAM_DEDUCTION_MODEL_CONFIG__MODEL={NEW_MODEL}")
s = s.replace(
    f"- DREAM_INDUCTION_MODEL_CONFIG__MODEL={OLD_MODEL}",
    f"- DREAM_INDUCTION_MODEL_CONFIG__MODEL={NEW_MODEL}")

# URLs and keys: only on lines that are a model-config override.
out = []
url_n = key_n = 0
for ln in s.split("\n"):
    if re.match(r"^\s*-\s*(DIALECTIC_LEVELS__\w+__|DERIVER_|SUMMARY_|DREAM_)",
                ln) and f"__OVERRIDES__BASE_URL={OLD_URL}" in ln:
        ln = ln.replace(f"__OVERRIDES__BASE_URL={OLD_URL}",
                        f"__OVERRIDES__BASE_URL={NEW_URL}")
        url_n += 1
    elif re.match(r"^\s*-\s*(DIALECTIC_LEVELS__\w+__|DERIVER_|SUMMARY_|DREAM_)",
                  ln) and f"__OVERRIDES__API_KEY={OLD_KEY}" in ln:
        ln = ln.replace(f"__OVERRIDES__API_KEY={OLD_KEY}",
                        f"__OVERRIDES__API_KEY={NEW_KEY}")
        key_n += 1
    out.append(ln)
s = "\n".join(out)

open(P, "w").write(s)
print(f"  model literals remaining: {s.count(OLD_MODEL)} (was {before_model})")
print(f"  url literals replaced   : {url_n}")
print(f"  key literals replaced   : {key_n}")
