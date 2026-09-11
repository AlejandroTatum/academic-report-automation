"""Contract and behavior tests for scripts/sync_skills.sh (Slice 5).

The static tests read the script as data and pin the synced skill set and the
runtime targets, including the Codex target. The behavior tests copy the real
script into an isolated temp repo (so the repo's `.venv` contract-test gate is
not present and the sync cannot recurse) and run it with a controlled HOME and
PATH to prove the optional `gentle-ai skill-registry refresh` step can never
abort the sync under `set -euo pipefail`.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SYNC = ROOT / "scripts" / "sync_skills.sh"
BASH = shutil.which("bash") or "/bin/bash"

# The runtime targets the script is expected to mirror into. Kept here (not
# imported) so a missing target is a test failure, not a silent skip.
RUNTIME_TARGETS = (
    ".config/opencode/skills",
    ".claude/skills",
    ".codex/skills",
)


def _array_entries(script: str, name: str) -> list[str]:
    """Return the unquoted entries of a bash array literal like `SKILLS=(...)`."""
    match = re.search(rf"^{name}=\(\s*\n(.*?)^\)", script, re.MULTILINE | re.DOTALL)
    assert match, f"{name} array not found in scripts/sync_skills.sh"
    return [
        line.strip().strip('"')
        for line in match.group(1).splitlines()
        if line.strip()
    ]


def _path_without_gentle_ai() -> str:
    """A PATH that has the tools the script needs but not the gentle-ai binary."""
    dirs = [d for d in ("/usr/bin", "/bin") if Path(d).is_dir()]
    rsync = shutil.which("rsync")
    if rsync is not None:
        rsync_dir = str(Path(rsync).parent)
        if rsync_dir not in dirs:
            dirs.insert(0, rsync_dir)
    return ":".join(dirs)


def _isolated_repo(tmp_path: Path) -> Path:
    """Copy the real sync script into a temp repo root with a fake skills tree."""
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    shutil.copy2(SYNC, repo / "scripts" / "sync_skills.sh")
    skill = repo / "skills" / "document-workflow"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: document-workflow\n---\n", encoding="utf-8")
    return repo


def _make_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    for target in RUNTIME_TARGETS:
        (home / target).mkdir(parents=True)
    return home


def _write_gentle_ai(bindir: Path, exit_code: int) -> Path:
    """Create a fake `gentle-ai` that records its args and exits with `exit_code`."""
    marker = bindir / "gentle-ai.called"
    binary = bindir / "gentle-ai"
    binary.write_text(
        "#!/usr/bin/env bash\n"
        f'printf "%s\\n" "$*" >> "{marker}"\n'
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    binary.chmod(0o755)
    return marker


def _run_sync(repo: Path, home: Path, path: str, args: tuple[str, ...] = ()):
    env = {
        "HOME": str(home),
        "PATH": path,
        "LANG": os.environ.get("LANG", "C.UTF-8"),
    }
    return subprocess.run(
        [BASH, str(repo / "scripts" / "sync_skills.sh"), *args],
        env=env,
        capture_output=True,
        text=True,
    )


def test_document_workflow_and_codex_target_present():
    script = SYNC.read_text(encoding="utf-8")
    skills = _array_entries(script, "SKILLS")
    targets = _array_entries(script, "TARGETS")
    assert "document-workflow" in skills
    assert "$HOME/.codex/skills" in targets


def test_sync_exits_zero_without_gentle_ai_binary(tmp_path):
    script = SYNC.read_text(encoding="utf-8")
    assert "command -v gentle-ai" in script, "refresh step must probe for the binary"

    repo = _isolated_repo(tmp_path)
    home = _make_home(tmp_path)
    path = _path_without_gentle_ai()
    assert shutil.which("gentle-ai", path=path) is None

    result = _run_sync(repo, home, path, args=("--apply",))

    assert result.returncode == 0, result.stderr
    for target in RUNTIME_TARGETS:
        assert (home / target / "document-workflow" / "SKILL.md").is_file()
    assert "skill-registry refresh failed" not in result.stderr


def test_sync_exits_zero_when_refresh_fails(tmp_path):
    repo = _isolated_repo(tmp_path)
    home = _make_home(tmp_path)
    bindir = tmp_path / "fakebin"
    bindir.mkdir()
    marker = _write_gentle_ai(bindir, exit_code=1)
    path = f"{bindir}:{_path_without_gentle_ai()}"

    result = _run_sync(repo, home, path, args=("--apply",))

    assert result.returncode == 0, result.stderr
    assert marker.is_file(), "gentle-ai was never invoked"
    assert "skill-registry refresh" in marker.read_text(encoding="utf-8")
    assert "non-fatal" in result.stderr


def test_dry_run_exits_zero_without_gentle_ai_binary(tmp_path):
    repo = _isolated_repo(tmp_path)
    home = _make_home(tmp_path)
    path = _path_without_gentle_ai()

    result = _run_sync(repo, home, path)

    assert result.returncode == 0, result.stderr
    for target in RUNTIME_TARGETS:
        assert not (home / target / "document-workflow").exists()
