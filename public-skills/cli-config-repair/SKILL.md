---
name: cli-config-repair
description: Use when CLI config files are corrupted or rejected.
version: 1.0.0
author: Hermes Agent
license: MIT
---

# CLI Config File Repair

Systematic approach to diagnosing and fixing corrupted CLI configuration files, especially when agents have written incompatible data into structured config formats.

## When to Use

- A CLI tool refuses to start with config parsing errors
- An agent accidentally wrote raw API response data or JSON into a YAML config file
- `gh`, `kubectl`, `docker`, `git`, or other CLI tools fail with "failed to read configuration" or "invalid config file"
- Config files contain unexpected data types (JSON objects as YAML keys, raw text in JSON)

---

## 1. Diagnosis

### Step 1: Check the CLI's auth/status
```bash
# For gh
gh auth status

# For kubectl
kubectl config view

# For docker
docker info

# For git
git config --list --show-origin
```

### Step 2: Examine the config file
```bash
# Check the file that the CLI reports
cat /home/user/.config/<tool>/hosts.yml
cat /home/user/.config/<tool>/config.yml
```

### Step 3: Validate the format
- YAML files: should have `key: value` pairs, no raw JSON objects as keys
- JSON files: should be valid JSON
- Check for mixed content (e.g., JSON API response embedded in YAML)

---

## 2. Fix Patterns

### Pattern 1: Completely Corrupted Config (JSON in YAML)

**Symptom**: A JSON API response was written directly into a YAML config file as keys.

Example of corrupted `hosts.yml`:
```yaml
github.com:
    users:
        {
"TheHappyHermit"  # ← JSON object as YAML key
"id": {ID},
...
}:
    oauth_token: ghp_...
```

**Fix**:
```bash
# 1. Back up the corrupted file
cp ~/.config/gh/hosts.yml ~/.config/gh/hosts.yml.corrupted.bak

# 2. Delete the corrupted file (CLI will recreate it on next auth)
rm ~/.config/gh/hosts.yml

# 3. Re-authenticate
gh auth login
```

### Pattern 2: Token Stripped or Invalid

**Symptom**:
```
X Failed to log in to github.com account TheHappyHermit
- The token in ~/.config/gh/hosts.yml is invalid.
```

**Fix**:
```bash
# Write a fresh config with valid token
printf 'github.com:\n    user: TheHappyHermit\n    oauth_token: <valid-token>\n    git_protocol: https\n' > ~/.config/gh/hosts.yml
```

### Pattern 3: Partially Corrupted Config

**Symptom**: Config file has some valid content mixed with garbage.

**Fix**:
```bash
# 1. Extract just the valid portions manually
# 2. Or delete and re-authenticate (safer)
rm ~/.config/gh/hosts.yml
gh auth login
```

---

## 3. Prevention

### Never let agents write raw API responses to config files
- Agents should use structured tools to authenticate, not raw API calls
- Always validate config file format after any automated write
- Use `yq` to validate YAML: `yq eval . ~/.config/gh/hosts.yml`

### Safe token write pattern
```bash
# Use printf with single quotes to prevent shell expansion
printf 'key: value\ntoken: ghp_abc123\n' > ~/.config/gh/hosts.yml

# Or use the CLI's own auth command
gh auth login --with-token
```

### Validation after automated writes
After any agent writes to a CLI config file, always run:
```bash
# Check the CLI recognizes the config
<tool> auth status
# or
<tool> config view
```

## References

See `references/gh-config-corruption.md` for the full transcript of the GitHub hosts.yml JSON-in-YAML corruption incident.
