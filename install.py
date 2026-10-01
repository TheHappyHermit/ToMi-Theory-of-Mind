#!/usr/bin/env python3
"""
Hermes Brain — Universal Cross-Platform Installer & Setup Script.

Usage:
  python install.py               # Interactive setup (auto-detects Docker / Local)
  python install.py --docker      # Automated Docker Compose deployment
  python install.py --local       # Local native deployment (pip + uvicorn)
  python install.py --link-only   # Link hooks and skills to ~/.hermes/ without running server
"""

import os
import sys
import shutil
import argparse
from typing import Optional
from datetime import datetime, timezone
import subprocess
import secrets
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
MIN_PYTHON = (3, 9)


def print_banner():
    print("""
================================================================================
       __  __                         ____             _       
      / / / /__  _________ ___  ___  / __ )_________ _(_)___   
     / /_/ / _ \\/ ___/ __ `__ \\/ _ \\/ __  / ___/ __ `/ / __ \\  
    / __  /  __/ /  / / / / / /  __/ /_/ / /  / /_/ / / / / /  
   /_/ /_/\\___/_/  /_/ /_/ /_/\\___/_____/_/   \\__,_/_/_/ /_/   
                                                               
   Sovereign Neuro-Cognitive Engine for NousResearch/hermes-agent
================================================================================
""")


def check_python_version():
    if sys.version_info < MIN_PYTHON:
        print(f"[ERROR] Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required. Found Python {sys.version.split()[0]}")
        sys.exit(1)
    print(f"[+] Python version: {sys.version.split()[0]}")


def check_command(cmd: list) -> bool:
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return res.returncode == 0
    except Exception:
        return False


def is_docker_daemon_running() -> bool:
    """True only if the Docker ENGINE is reachable, not just the CLI.

    `docker compose version` succeeds whenever the CLI is on PATH, which
    includes the very common case of Docker Desktop installed but the
    engine stopped. Treating that as "Docker available" made run_docker()
    call `docker compose up` with check=True and abort the entire install
    with a raw CalledProcessError. `docker info` is the check that
    actually distinguishes the two.
    """
    return check_command(["docker", "info"])


def get_docker_compose_cmd() -> list:
    # A compose command without a running daemon is not a usable compose
    # command. Return [] so the caller falls back to local mode instead
    # of discovering the problem via an exception mid-install.
    if not is_docker_daemon_running():
        return []
    if check_command(["docker", "compose", "version"]):
        return ["docker", "compose"]
    elif check_command(["docker-compose", "version"]):
        return ["docker-compose"]
    return []


def setup_env_file(operator_name: str = None):
    env_path = REPO_ROOT / ".env"
    example_path = REPO_ROOT / "example.env"

    if not env_path.exists() and example_path.exists():
        print("[*] Creating .env from example.env...")
        shutil.copy(example_path, env_path)

    # Sync dashboard/.env if missing
    dash_env = REPO_ROOT / "dashboard" / ".env"
    if not dash_env.exists() and env_path.exists():
        shutil.copy(env_path, dash_env)

    # Update OPERATOR_NAME if provided or default to current user.
    # This previously only print()ed the value -- the comment said "Update
    # OPERATOR_NAME" but nothing was ever written, so --operator was a silent
    # no-op. Write it through now, preserving every other line in .env.
    if not operator_name:
        operator_name = os.environ.get("USER") or os.environ.get("USERNAME") or "Operator"

    if env_path.exists():
        try:
            lines = env_path.read_text(encoding="utf-8").splitlines()
            replaced = False
            for i, line in enumerate(lines):
                if line.startswith("HERMES_OPERATOR_NAME="):
                    lines[i] = f"HERMES_OPERATOR_NAME={operator_name}"
                    replaced = True
                    break
            if not replaced:
                lines.append(f"HERMES_OPERATOR_NAME={operator_name}")
            tmp = env_path.with_suffix(".env.tmp")
            tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
            os.replace(tmp, env_path)
            print(f"[+] Operator configured as: {operator_name} (written to .env)")
        except OSError as e:
            print(f"[!] Could not write HERMES_OPERATOR_NAME to .env: {e}")
    else:
        print(f"[!] No .env present; operator name not persisted: {operator_name}")


def setup_cron_jobs(selected: Optional[set] = None):
    cron_script = REPO_ROOT / "scripts" / "setup_cron_jobs.py"
    if selected is not None and "cron" not in selected:
        print("[*] Skipping cron setup (not selected).")
        return
    if cron_script.exists():
        print("[*] Checking autonomous cron schedules...")
        res = subprocess.run([sys.executable, str(cron_script)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(res.stdout.strip() or "[+] Cron jobs initialized.")


def _result_word(result: str) -> str:
    """Past-tense label for a provisioning result ('linked' -> 'Linked')."""
    return {"linked": "Linked", "copied": "Copied"}.get(result, result.capitalize())


def _backup_existing(dest: Path, backups_root: Path) -> Optional[Path]:
    """
    Move an existing destination aside instead of deleting it.

    The previous installer called shutil.rmtree() unconditionally on any
    pre-existing destination, so re-running install.py destroyed hand-written
    skills, hooks, plugins, and profiles with no backup and no prompt. Anything
    we are about to replace is now moved under ~/.hermes/backups/install-<ts>/
    first, so a mistaken install is always recoverable.
    """
    if not dest.exists() and not dest.is_symlink():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = backups_root / f"install-{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / dest.name
    suffix = 1
    while target.exists() or target.is_symlink():
        target = backup_dir / f"{dest.name}.{suffix}"
        suffix += 1
    shutil.move(str(dest), str(target))
    return target


def _provision_component(dest: Path, source: Path, label: str,
                         backups_root: Path, force: bool = False) -> str:
    """
    Idempotently place one component, preserving anything we do not own.

    Returns one of: "unchanged", "linked", "copied", "skipped".

    Rules:
      * destination already a symlink to this exact source -> unchanged (no churn)
      * destination is a symlink to somewhere else          -> replace, after backup
      * destination is a real directory                     -> BACK IT UP, then
        replace. With force=False we still replace (that is the point of an
        installer) but the old copy is preserved under backups/.
      * symlink unsupported (Windows without Developer Mode) -> copy, after backup
    """
    if dest.is_symlink():
        try:
            if dest.resolve() == source.resolve():
                return "unchanged"
        except OSError:
            pass

    backup = _backup_existing(dest, backups_root)
    if backup is not None:
        print(f"  [~] Backed up existing {label}: {backup}")

    if force:
        try:
            dest.symlink_to(source, target_is_directory=True)
            return "linked"
        except (OSError, NotImplementedError, AttributeError):
            pass
    try:
        dest.symlink_to(source, target_is_directory=True)
        return "linked"
    except (OSError, NotImplementedError, AttributeError):
        shutil.copytree(source, dest)
        return "copied"


def preflight_check_hermes_agent(hermes_dir: Path, args) -> None:
    """Confirm a Hermes Agent harness is actually present before provisioning.

    The components this repo ships (hooks, skills, profiles, plugins) are
    only read by a Hermes Agent installation. That harness is a separate
    upstream install and is not vendored here, so on a machine without it
    every provisioning step still succeeds: ~/.hermes/ fills with components
    that nothing loads, and the installer reports success. That is the worst
    possible outcome for a new user — an install that looks clean and does
    nothing.

    So check first, and fail loudly with the install command. --local is
    exempt: that path installs the runtime from PyPI rather than expecting an
    existing harness, so the check does not apply to it.
    """
    if args.local:
        return

    agent_dir = hermes_dir / "hermes-agent"
    if agent_dir.is_dir() and (agent_dir / "cli.py").exists():
        return

    # Also accept a harness already on PATH, installed system-wide rather
    # than into this data directory.
    if shutil.which("hermes"):
        return

    print()
    print("[ERROR] No Hermes Agent installation found.")
    print(f"        Looked for: {agent_dir}")
    print("        Also checked the `hermes` command on PATH.")
    print()
    print("  This repo provides the components a Hermes Agent reads (hooks,")
    print("  skills, profiles, plugins). Without the agent itself, installing")
    print("  them has no effect: nothing will load what was just written.")
    print()
    print("  Install the agent first, then re-run this installer:")
    print("      pip install hermes-agent")
    print("  Or point this installer at an existing data directory:")
    print("      python install.py --hermes-home /path/to/.hermes")
    print()
    print("  To install just the runtime and skip agent provisioning, use:")
    print("      python install.py --local")
    sys.exit(1)


def install_hermes_hooks_and_skills(hermes_dir: Optional[Path] = None,
                                      selected: Optional[set] = None):
    """Link or copy hooks, skills, plugins, profiles, and scripts into ~/.hermes/ (or $HERMES_HOME).

    `selected` is None for a full install, or a set of component names from
    customize_install(); a stage whose name is absent is skipped entirely.
    """
    if not hermes_dir:
        hermes_home = os.environ.get("HERMES_HOME") or os.environ.get("HERMES_DATA_DIR")
        if hermes_home:
            hermes_dir = Path(hermes_home)
        elif sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
            hermes_dir = Path(os.environ["LOCALAPPDATA"]) / "hermes"
        else:
            hermes_dir = Path.home() / ".hermes"

    def want(name: str) -> bool:
        return selected is None or name in selected

    if selected:
        print(f"[*] Selected components: {', '.join(sorted(selected))}")
    print(f"[*] Provisioning Hermes Agent components in: {hermes_dir}")
    # Anything we replace is moved here first (see _backup_existing).
    backups_root = Path(os.environ.get("BACKUP_ROOT_DIR") or (hermes_dir / "backups"))
    backups_root.mkdir(parents=True, exist_ok=True)
    hermes_hooks = hermes_dir / "hooks"
    hermes_skills = hermes_dir / "skills"
    hermes_plugins = hermes_dir / "plugins"
    hermes_profiles = hermes_dir / "profiles"
    hermes_scripts = hermes_dir / "scripts"

    hermes_hooks.mkdir(parents=True, exist_ok=True)
    hermes_skills.mkdir(parents=True, exist_ok=True)
    hermes_plugins.mkdir(parents=True, exist_ok=True)
    hermes_profiles.mkdir(parents=True, exist_ok=True)
    hermes_scripts.mkdir(parents=True, exist_ok=True)

    # 1. Provision Hooks
    repo_hooks = REPO_ROOT / "hooks"
    if want("hooks") and repo_hooks.exists():
        for hook_dir in repo_hooks.iterdir():
            if hook_dir.is_dir() and (hook_dir / "HOOK.yaml").exists():
                dest = hermes_hooks / hook_dir.name
                result = _provision_component(dest, hook_dir, f"hook:{hook_dir.name}",
                                              backups_root)
                if result != "unchanged":
                    print(f"  [+] {_result_word(result)} hook: {hook_dir.name}")

    # 2. Provision Skills
    # 2. Provision Skills (both top-level and nested protocol categories)
    repo_skills = REPO_ROOT / "skills"
    if want("skills") and repo_skills.exists():
        seen_skills = set()
        for skill_file in sorted(repo_skills.rglob("SKILL.md")):
            skill_dir = skill_file.parent
            if skill_dir == repo_skills:
                continue
            skill_name = skill_dir.name
            if skill_name in seen_skills:
                continue
            seen_skills.add(skill_name)
            dest = hermes_skills / skill_name
            result = _provision_component(dest, skill_dir, f"skill:{skill_name}",
                                          backups_root)
            if result != "unchanged":
                print(f"  [+] {_result_word(result)} skill: {skill_name}")

    # 3. Provision Plugins
    hermes_plugins = hermes_dir / "plugins"
    hermes_plugins.mkdir(parents=True, exist_ok=True)
    repo_plugins = REPO_ROOT / "plugins"
    if want("plugins") and repo_plugins.exists():
        for plugin_dir in repo_plugins.iterdir():
            if plugin_dir.is_dir() and (plugin_dir / "plugin.yaml").exists():
                dest = hermes_plugins / plugin_dir.name
                result = _provision_component(dest, plugin_dir,
                                              f"plugin:{plugin_dir.name}", backups_root)
                if result != "unchanged":
                    print(f"  [+] {_result_word(result)} plugin: {plugin_dir.name}")

    # 4. Provision Profiles
    hermes_profiles = hermes_dir / "profiles"
    hermes_profiles.mkdir(parents=True, exist_ok=True)
    repo_profiles = REPO_ROOT / "profiles"
    if want("profiles") and repo_profiles.exists():
        for profile_dir in repo_profiles.iterdir():
            if profile_dir.is_dir():
                dest = hermes_profiles / profile_dir.name
                result = _provision_component(dest, profile_dir,
                                              f"profile:{profile_dir.name}", backups_root)
                if result != "unchanged":
                    print(f"  [+] {_result_word(result)} profile: {profile_dir.name}")

        # Ensure default SOUL.md is linked to ~/.hermes/SOUL.md
        hermes_soul = hermes_dir / "SOUL.md"
        default_soul = repo_profiles / "default" / "SOUL.md"
        root_soul = REPO_ROOT / "SOUL.md"
        source_soul = default_soul if default_soul.exists() else root_soul
        if source_soul.exists() and not hermes_soul.exists():
            try:
                hermes_soul.symlink_to(source_soul)
                print(f"  [+] Linked SOUL.md -> {hermes_soul}")
            except (OSError, NotImplementedError):
                shutil.copy(source_soul, hermes_soul)
                print(f"  [+] Copied SOUL.md -> {hermes_soul}")

    # 5. Provision Scripts (Required for Hermes Agent cron containment)
    repo_scripts = REPO_ROOT / "scripts"
    if want("scripts") and repo_scripts.exists():
        for script_file in repo_scripts.iterdir():
            if script_file.is_file() and script_file.suffix in (".py", ".sh", ".sql"):
                dest = hermes_scripts / script_file.name
                if dest.exists():
                    if dest.is_symlink() or dest.is_file():
                        dest.unlink()
                try:
                    dest.symlink_to(script_file)
                    print(f"  [+] Linked script: {script_file.name} -> {dest}")
                except (OSError, NotImplementedError):
                    shutil.copy2(script_file, dest)
                    print(f"  [+] Copied script: {script_file.name} -> {dest}")


def init_hermes_database(selected: Optional[set] = None):
    """Ensure organizer and experience databases are created with full schema."""
    if selected is not None and "databases" not in selected:
        print("[*] Skipping database initialization (not selected).")
        return
    init_db_script = REPO_ROOT / "scripts" / "init_db.py"
    if init_db_script.exists():
        print("[*] Initializing Personal Organizer database schema...")
        res = subprocess.run([sys.executable, str(init_db_script), "--yes"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            print("[+] Personal Organizer database schema successfully verified & initialized.")
        else:
            print(f"[!] Warning initializing Personal Organizer schema: {res.stderr.strip() or res.stdout.strip()}")

    init_exp_script = REPO_ROOT / "scripts" / "init_experience_db.py"
    if init_exp_script.exists():
        print("[*] Initializing Cortex Experience Index database schema...")
        res = subprocess.run([sys.executable, str(init_exp_script), "--yes"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            print("[+] Experience Index database schema successfully verified & initialized.")
        else:
            print(f"[!] Warning initializing Experience Index schema: {res.stderr.strip() or res.stdout.strip()}")


def setup_companion_apps(selected: Optional[set] = None):
    """Detect and configure upstream companion applications (ai-visualizer and barehands)."""
    if selected is not None and "companions" not in selected:
        print("[*] Skipping companion apps (not selected).")
        return
    try:
        from plugins.adapters.visualizer import VisualizerAdapter
        from plugins.adapters.barehands import BarehandsAdapter
        vis = VisualizerAdapter()
        bh = BarehandsAdapter()

        print("[*] Checking companion applications...")
        if vis.is_installed:
            vis.ensure_config(name="HERMES", face="board", badge="BRAIN", port=8790)
            print(f"  [+] Configured ai-visualizer at: {vis.visualizer_dir}")
        else:
            print("  [-] ai-visualizer not found (clone to ../ai-visualizer to enable)")

        if bh.is_installed:
            bh.ensure_config(name="HERMES", port=8794)
            print(f"  [+] Configured barehands at: {bh.barehands_dir}")
        else:
            print("  [-] barehands not found (clone to ../barehands to enable)")

        if not (vis.is_installed and bh.is_installed):
            print("  [i] Guide: See docs/COMPANION_APPS.md to clone and link upstream companions.")
    except Exception as e:
        print(f"  [!] Companion setup note: {e}")


# Companion stacks that ship in docker/ but were never started by the old
# installer, which ran `docker compose up` against the repo root only. The
# acceptance test in tests/run_tests.sh asserts Honcho :8000 and Personal
# Organizer :8001 are healthy, so on a clean machine that test could never pass
# and the installer failed silently. Each entry is (compose file, required?).
COMPANION_STACKS = [
    ("docker/docker-compose.honcho.yml", True),
    ("docker/docker-compose.personal-organizer.yml", True),
    ("docker/docker-compose.searxng.yml", False),
    ("docker/docker-compose.firecrawl.yml", False),
]


def ensure_env_file() -> Path:
    """
    Return the single .env the container stacks interpolate from, creating it and
    generating the credentials compose REQUIRES if they are absent.

    One file, not one per stack. The companion compose files under docker/ used
    to read docker/.env, which meant the Control Panel -- which writes the root
    .env through sync_env_file() -- could not reach them, and the two drifted.
    Every stack now reads this one file via --env-file.

    HONCHO_PG_PASSWORD is the only variable marked required
    (${HONCHO_PG_PASSWORD:?...}) in docker/docker-compose.honcho.yml. Without it
    `docker compose config` aborts, so a fresh clone could not deploy Honcho at
    all, and the error named a credential that appeared in no tracked file. It
    is generated here so a first install just works. An operator who wants their
    own value edits this file, or sets it in the Control Panel, which writes back
    to the same place.

    The value is never printed and never committed: the file is gitignored.
    """
    env_path = REPO_ROOT / ".env"
    env_path.touch(exist_ok=True)
    try:
        env_path.chmod(0o600)
    except OSError:
        pass  # a filesystem that cannot do this is not a reason to abort

    try:
        env_path.read_text(encoding="utf-8")
    except OSError:
        env_path.write_text("", encoding="utf-8")

    existing = {}
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, v = stripped.split("=", 1)
            existing[k.strip()] = v.strip()

    # Credentials compose requires. Generated once, then left alone: a
    # regenerated password would orphan the data already in the volume, because
    # Postgres keys its data directory on the password it was initialised with.
    generated = []
    for key, gen in (
        ("HONCHO_PG_PASSWORD", lambda: secrets.token_urlsafe(32)),
        ("SEARXNG_SECRET", lambda: secrets.token_urlsafe(32)),
    ):
        if not existing.get(key):
            with env_path.open("a", encoding="utf-8") as fh:
                if not env_path.read_text(encoding="utf-8", errors="ignore").endswith("\n"):
                    fh.write("\n")
                fh.write(f"{key}={gen()}\n")
            generated.append(key)

    if generated:
        print(f"[*] Generated {', '.join(generated)} in .env (mode 600, gitignored).")
        print(f"    Change any of them by editing .env or the Control Panel Settings page.")
    return env_path


def compose_env_args(env_path: Path) -> list:
    """--env-file for a compose invocation, but only for CLIs that accept it."""
    # `docker compose` (v2) accepts --env-file. Legacy `docker-compose` (v1)
    # does not, and passing it anyway makes the whole command fail -- so the
    # legacy path keeps the historical cwd-relative ./.env lookup.
    return ["--env-file", str(env_path)]


def start_companion_stacks(compose_cmd: list, only_required: bool = False,
                           env_path: Path | None = None) -> list:
    """
    Start the compose stacks under docker/ that the root compose does not include.

    Non-fatal: a missing optional stack is reported and skipped, because
    Firecrawl/Camofox needs a browser stack most installs do not want. A missing
    *required* stack (Honcho = autobiographical memory, Personal Organizer) is
    reported loudly, because the memory tier silently not existing is exactly
    the failure this whole project exists to avoid.
    """
    started, problems = [], []
    env_args = compose_env_args(env_path) if env_path is not None else []
    if env_path is not None and not env_args:
        print("    (legacy docker-compose: relying on ./.env in the compose directory)")
    for rel, required in COMPANION_STACKS:
        if only_required and not required:
            continue
        cf = REPO_ROOT / rel
        if not cf.exists():
            problems.append((rel, "compose file missing"))
            continue
        print(f"[*] Starting {rel}...")
        r = subprocess.run(compose_cmd + ["-f", str(cf)] + env_args + ["up", "-d"],
                           cwd=str(REPO_ROOT))
        if r.returncode == 0:
            started.append(rel)
        else:
            problems.append((rel, f"exit {r.returncode}"))
    if problems:
        print("\n[!] Companion stack issues:")
        for rel, why in problems:
            print(f"      - {rel}: {why}")
    return started


def run_docker(compose_cmd: list):
    # One .env for every stack, created before any compose call. The companion
    # stacks interpolate ${HONCHO_PG_PASSWORD:?...}, so this has to happen
    # first: without it the first `up` aborts on a missing credential rather
    # than on a missing service.
    env_path = ensure_env_file()
    env_args = compose_env_args(env_path)

    print("[*] Launching Hermes Brain via Docker Compose...")
    cmd = compose_cmd + env_args + ["up", "-d", "--build"]
    subprocess.run(cmd, cwd=str(REPO_ROOT), check=True)

    print("\n[*] Starting companion stacks (Honcho, Personal Organizer, ...)...")
    start_companion_stacks(compose_cmd, env_path=env_path)

    print("\n[+] Hermes Brain Docker containers are up and running!")
    print("    Dashboard:     http://localhost:8088")
    print("    Cognitive:     http://localhost:8088/api/brain/status")
    print("    SearXNG:       http://localhost:8080")
    print("    AI Visualizer: http://localhost:8790 (cd ../ai-visualizer && python server.py)")
    print("    Barehands 3D:  http://localhost:8794/stage.html (cd ../barehands && python server.py)")
    print("    Unified Start: python scripts/start_all.py\n")


def _wait_for_health(url: str, timeout: float = 15.0) -> bool:
    """Poll a URL until it answers or the timeout expires.

    Returns True on success. A failure here is reported, never raised:
    the caller still wants to run verification and print a useful summary
    rather than abort mid-install.
    """
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def run_local():
    print("[*] Installing Python requirements locally...")
    req_file = REPO_ROOT / "requirements.txt"
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req_file)], check=True)

    print("\n[*] Launching Hermes Brain Command Deck Server locally...")
    server_script = REPO_ROOT / "dashboard" / "dashboard_server.py"

    # This MUST be detached. dashboard_server.py runs uvicorn in the
    # foreground and never returns, so a plain subprocess.run() blocks
    # here forever: run_verification() is never reached, the installer
    # never exits, and any automated agent driving it hits a process
    # timeout with no diagnostic. start_new_session also detaches the
    # child from this process group, so Ctrl-C on the installer does not
    # take the server down with it.
    proc = subprocess.Popen(
        [sys.executable, str(server_script)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    if _wait_for_health("http://127.0.0.1:8088/health"):
        print(f"[+] Command Deck is serving on http://127.0.0.1:8088 (pid {proc.pid})")
    else:
        # Not fatal. The server may still be binding, or may have exited
        # on a missing dependency. Say so plainly and let verification
        # report the detail rather than guessing here.
        print(f"[!] Command Deck did not answer /health within 15s (pid {proc.pid}).")
        print("    It may still be starting. Check with: curl -s http://127.0.0.1:8088/health")
        if proc.poll() is not None:
            print(f"    The process has exited with code {proc.returncode}.")


def run_verification(check_services: bool = True) -> bool:
    """
    Run scripts/verify_stack.py and honour its exit code.

    Previously the installer ran verification *before* starting any container
    (install.py called it at line ~303, run_docker at ~315) and discarded the
    result -- no check=, no returncode inspection. On a fresh machine every
    service probe necessarily failed, the verdict was thrown away, and the
    install continued to print success. That is a check that cannot fail and a
    result nobody reads.

    Now: verification runs AFTER services are started, waits briefly for
    containers to become healthy, and returns the verifier's verdict so main()
    can exit non-zero on a broken install.
    """
    verify_script = REPO_ROOT / "scripts" / "verify_stack.py"
    if not verify_script.exists():
        print("[!] scripts/verify_stack.py not found; skipping verification.")
        return True

    if check_services:
        print("\n[*] Waiting for containers to report healthy (up to 60s)...")
        compose_cmd = get_docker_compose_cmd()
        if compose_cmd:
            subprocess.run(compose_cmd + ["up", "-d", "--wait"],
                           cwd=str(REPO_ROOT),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            time.sleep(5)

    print("[*] Verifying stack configuration...")
    result = subprocess.run([sys.executable, str(verify_script)])
    if result.returncode == 0:
        print("[+] Stack verification passed.")
        return True

    print("\n[!] Stack verification FAILED (exit %d)." % result.returncode)
    print("    The install did not fully succeed. Re-run after starting services,")
    print("    or inspect scripts/verify_stack.py output above for the failing check.")
    return False


def check_vault_config():
    """
    Report whether the graph and arena have anything to work on.

    The brain itself runs fine with no vault: every subsystem degrades to an
    empty-but-valid state, and the scripts exit 0. That is the problem. An
    unconfigured graph returns nothing and reports nothing, so a fresh install
    looks identical to a working one -- and the natural conclusion is "the
    graph is broken" rather than "the graph was never fed".

    README.md documents this properly (see the Graphify section). This does not
    duplicate that documentation. It only says, out loud, what state the install
    actually finished in, because a user should not have to go looking to find
    out.

    Never fails the install. A missing vault is a legitimate starting state --
    someone may not have a wiki yet -- so this informs and does not obstruct.
    """
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        print("[!] No .env present; cannot determine vault configuration.")
        print("    See README.md -> 'Graphify: Derived Relationship Connectivity'.")
        return None

    try:
        values = {}
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            values[k.strip()] = v.strip().strip('"').strip("'")
    except OSError as e:
        print(f"[!] Could not read .env: {e}")
        return None

    unset, missing, ready = [], [], []
    for var, label in (("ORACLE_BRAIN_PATH", "Oracle brain"),
                       ("ACTIVE_WIKI_PATH", "Active Wiki")):
        raw = values.get(var, "")
        if not raw:
            unset.append((var, label))
            continue
        p = Path(raw).expanduser()
        if p.is_dir():
            ready.append((var, label, p))
        elif p.exists():
            missing.append((var, label, p, "it is a file, not a directory"))
        else:
            missing.append((var, label, p, "no such directory on this machine"))

    if ready:
        print(f"[*] Vaults configured: {len(ready)}/2")
        for var, label, p in ready:
            try:
                n = sum(1 for _ in p.rglob("*.md"))
            except OSError:
                n = 0
            graph = p / "graphify-out" / "graph.json"
            tag = "graph built" if graph.exists() else "no graph built yet"
            print(f"    {label:14s} {p}  ({n} markdown files, {tag})")
            if not graph.exists():
                print(f"        -> run Graphify over {p} to index it; see README.md")

    if unset:
        print(f"\n[!] {len(unset)} vault path(s) not set in .env. The graph and the")
        print("    cognition arena will run but stay EMPTY -- they will not error,")
        print("    and they will return nothing. That is easy to mistake for a bug.")
        for var, label in unset:
            print(f"      {var}=<path to your {label} markdown directory>")
        print("    Then index it with Graphify. See README.md -> 'Graphify: Derived")
        print("    Relationship Connectivity', and scripts/graphify_health.py to check.")

    for var, label, p, why in missing:
        print(f"\n[!] {var} points at {p}, but {why}.")
        print(f"    {label} will be treated as unavailable until this is corrected.")

    return {"unset": unset, "missing": missing, "ready": ready}


def ask_soul_question(hermes_dir: Path):
    """
    Ask about SOUL.md BEFORE anything writes to it.

    An installer that symlinks a repo SOUL.md over a user's own would destroy
    it silently, so the file is never touched without an explicit answer. The
    operational-facts block is shown in full before the prompt rather than
    described, so nobody appends text they have not seen.
    """
    hermes_soul = hermes_dir / "SOUL.md"
    soul_facts = """
## Operational Facts (auto-appended by install.py)
- Data directory: ~/.hermes  (override with HERMES_HOME)
- Experience DB: ~/.hermes/experience.db
- Command Deck: http://localhost:8088
"""

    if hermes_soul.exists() or hermes_soul.is_symlink():
        # A symlink pointing at the repo's own SOUL.md is ours, not the user's,
        # so there is nothing to protect and nothing to confirm.
        if hermes_soul.is_symlink() and hermes_soul.resolve().is_relative_to(REPO_ROOT):
            print(f"\n[*] SOUL.md is already linked to the repo copy; leaving it as is.")
            return

        print(f"\n[?] SOUL.md already exists at {hermes_soul}")
        print("    What would you like to do?")
        print("    1) Append operational facts to the existing file (Recommended)")
        print("    2) Replace it with the repo's default SOUL.md")
        print("    3) Leave it untouched")
        choice = _prompt("    Enter choice [1/2/3] (default: 1): ") or "1"

        if choice == "1":
            print("\n    The following will be appended:")
            print("    " + "-" * 60)
            for line in soul_facts.strip().split("\n"):
                print(f"    {line}")
            print("    " + "-" * 60)
            if _confirm("    Append? [Y/n] (default: Y): ", default_yes=True):
                with open(hermes_soul, "a") as fh:
                    fh.write(soul_facts)
                print("    [+] SOUL.md updated.")
            else:
                print("    [-] Skipped.")
        elif choice == "2":
            print("\n    WARNING: this replaces the current contents. The old file is")
            print("    moved into backups/ first, not deleted.")
            default_soul = REPO_ROOT / "SOUL.md"
            if not default_soul.exists():
                print("    [-] No default SOUL.md in the repo; skipping.")
            elif _confirm("    Replace? [y/N] (default: N): ", default_yes=False):
                backups_root = hermes_dir / "backups" / f"install-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                backups_root.mkdir(parents=True, exist_ok=True)
                if hermes_soul.is_symlink():
                    hermes_soul.unlink()
                else:
                    shutil.move(str(hermes_soul), str(backups_root / "SOUL.md"))
                    print(f"    [i] Previous SOUL.md saved to {backups_root / 'SOUL.md'}")
                shutil.copy(default_soul, hermes_soul)
                print("    [+] SOUL.md replaced.")
            else:
                print("    [-] Skipped.")
        else:
            print("    [-] Skipped.")
        return

    print(f"\n[?] No SOUL.md found at {hermes_soul}")
    print("    1) Create one with the operational facts (Recommended)")
    print("    2) Skip")
    choice = _prompt("    Enter choice [1/2] (default: 1): ") or "1"
    if choice == "1":
        hermes_soul.parent.mkdir(parents=True, exist_ok=True)
        default_soul = REPO_ROOT / "SOUL.md"
        if default_soul.exists():
            shutil.copy(default_soul, hermes_soul)
        else:
            hermes_soul.write_text("# SOUL.md — System Operating Instructions\n")
        with open(hermes_soul, "a") as fh:
            fh.write(soul_facts)
        print(f"    [+] Created {hermes_soul}")
    else:
        print("    [-] Skipped.")


def ask_install_scope() -> bool:
    """Ask whether to install everything or pick components. True = customize."""
    print("\n[?] Install everything, or choose components?")
    print("    1) Install everything (Recommended)")
    print("    2) Choose components")
    return (_prompt("    Enter choice [1/2] (default: 1): ") or "1") == "2"


# Components offered by customize_install. The availability lambda decides
# whether the item can be installed at all on this machine; a False here means
# "not offered", never "installed and failed".
INSTALL_COMPONENTS = [
    ("hooks",        True,  lambda: True),
    ("skills",       True,  lambda: True),
    ("plugins",      True,  lambda: (REPO_ROOT / "plugins").exists()),
    ("profiles",     True,  lambda: (REPO_ROOT / "profiles").exists()),
    ("scripts",      True,  lambda: True),
    ("databases",    True,  lambda: (REPO_ROOT / "scripts" / "init_db.py").exists()),
    ("cron",         True,  lambda: (REPO_ROOT / "scripts" / "setup_cron_jobs.py").exists()),
    ("companions",   False, lambda: True),
    ("docker stack", True,  lambda: bool(get_docker_compose_cmd())),
]


def customize_install() -> set:
    """
    Present the component checklist and return the selected names.

    Returns a set, and main() passes it to each stage, which skips itself when
    its name is absent. The previous branch version collected this list and
    never read it, so every answer was discarded and the checklist was theatre.
    """
    available = [(n, d) for n, d, ok in INSTALL_COMPONENTS if ok()]
    unavailable = [n for n, d, ok in INSTALL_COMPONENTS if not ok()]

    print("\n[?] Choose the components to install:")
    selected = set()
    for name, default in available:
        hint = "[Y/n]" if default else "[y/N]"
        choice = _prompt(f"    {name}? {hint}: ")
        if choice == "" or choice == "y":
            selected.add(name)
        else:
            print(f"        [-] {name} skipped")

    for name in unavailable:
        print(f"    [-] {name} (not available: Docker/Compose not found)")

    if not selected:
        print("\n    [!] Nothing selected. Falling back to a full install.")
        return {n for n, d in available}
    return selected


def _prompt(message: str) -> str:
    """input() that returns a safe default instead of raising on a closed stdin."""
    try:
        return input(message).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


def _confirm(message: str, default_yes: bool = True) -> bool:
    """Y/n prompt honouring an explicit default when the user just hits enter."""
    answer = _prompt(message)
    if answer == "":
        return default_yes
    return answer.lower().startswith("y")


def main():
    print_banner()
    parser = argparse.ArgumentParser(description="Hermes Brain Setup & Installer")
    parser.add_argument("--docker", action="store_true", help="Deploy via Docker Compose")
    parser.add_argument("--local", action="store_true", help="Install & run locally with Python")
    parser.add_argument("--link-only", action="store_true", help="Only link hooks, skills, plugins & profiles to ~/.hermes/")
    parser.add_argument("--auto", "-y", "--yes", action="store_true", help="Non-interactive automatic setup (defaults to Docker if available, else local)")
    parser.add_argument("--operator", type=str, default="", help="Custom Operator name")
    parser.add_argument("--hermes-home", type=str, default="", help="Custom Hermes Agent home directory")
    args = parser.parse_args()

    check_python_version()
    setup_env_file(args.operator)

    hermes_dir = Path(args.hermes_home) if args.hermes_home else None
    if hermes_dir is None:
        env_home = os.environ.get("HERMES_HOME") or os.environ.get("HERMES_DATA_DIR")
        hermes_dir = Path(env_home) if env_home else Path.home() / ".hermes"

    # Before writing anything: confirm something exists that will read it.
    preflight_check_hermes_agent(hermes_dir, args)

    # SOUL.md is settled before anything can write to it, and before the
    # provisioning stage links or copies over it.
    if not args.auto and sys.stdin.isatty():
        ask_soul_question(hermes_dir)

    # Full install, or pick components. Only offered on a real terminal: with
    # piped/closed stdin every prompt would take the default anyway, and
    # --auto must stay fully non-interactive.
    selected = None
    if not args.auto and sys.stdin.isatty() and not args.link_only:
        if ask_install_scope():
            selected = customize_install()

    init_hermes_database(selected)
    install_hermes_hooks_and_skills(hermes_dir, selected)
    setup_cron_jobs(selected)
    setup_companion_apps(selected)

    if args.link_only:
        run_verification(check_services=False)
        print("\n[+] Hooks, skills, profiles, plugins, and scripts provisioned successfully. Exiting.")
        return

    compose_cmd = get_docker_compose_cmd()

    started_services = False

    if args.docker:
        if not compose_cmd:
            # Two different failures produce the same empty list, and the
            # remedy is different for each: a user with Docker Desktop
            # closed needs to START it, not install it.
            if check_command(["docker", "--version"]):
                print("[ERROR] Docker is installed but the engine is not running.")
                print("       Start Docker Desktop (or `sudo systemctl start docker`) and re-run.")
            else:
                print("[ERROR] Docker or Docker Compose is not installed or not in PATH.")
                print("       Install Docker, or re-run with --local to deploy without containers.")
            sys.exit(1)
        run_docker(compose_cmd)
        started_services = True
    elif args.local:
        run_local()
        started_services = True
    elif args.auto or not sys.stdin.isatty():
        if compose_cmd:
            print("\n[*] Non-interactive / Auto mode: Deploying via Docker Compose...")
            run_docker(compose_cmd)
            started_services = True
        else:
            print("\n[*] Non-interactive / Auto mode: Docker not found. Deploying locally...")
            run_local()
            started_services = True
    else:
        # Auto-detect or prompt
        if compose_cmd:
            print("\n[?] Docker Compose detected. How would you like to run Hermes Brain?")
            print("    1) Docker Compose (Recommended: includes pgvector & SearXNG)")
            print("    2) Local Native Python (uvicorn on port 8088)")
            print("    3) Exit after hooks/skills/profiles setup")
            try:
                choice = input("Enter choice [1/2/3] (default: 1): ").strip() or "1"
            except (EOFError, KeyboardInterrupt):
                choice = "1"
            if choice == "1":
                run_docker(compose_cmd)
                started_services = True
            elif choice == "2":
                run_local()
                started_services = True
            else:
                print("[+] Setup completed.")
        else:
            print("\n[*] Docker not found. Defaulting to local Python execution.")
            run_local()
            started_services = True

    # Verification happens LAST, after services exist, and its verdict decides
    # the process exit code.
    if not run_verification(check_services=started_services):
        sys.exit(1)

    # Vault state is reported, never enforced. A brain with no vault is a valid
    # brain; it just has nothing to retrieve or distil yet, and says so.
    print("\n" + "=" * 60)
    print("Vault configuration")
    print("=" * 60)
    check_vault_config()


if __name__ == "__main__":
    main()
