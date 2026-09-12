from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .config import Config

StatusCallback = Callable[[str, str, dict], None]


class DeploymentError(RuntimeError):
    pass


class DeploymentRolledBack(DeploymentError):
    pass


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class CommandResult:
    stdout: str
    stderr: str


class Deployer:
    def __init__(self, config: Config, status: StatusCallback):
        self.config = config
        self.status = status
        self.base = config.base_dir
        self.cache = self.base / "cache" / "app.git"
        self.releases = self.base / "releases"
        self.current = self.base / "current"
        self.previous = self.base / "previous"
        self.data = self.base / "data"
        self.state_path = self.data / "state.json"
        self.lock_path = self.data / "update.lock"

    def initialise(self) -> None:
        for path in (self.cache.parent, self.releases, self.data):
            path.mkdir(parents=True, exist_ok=True)

    def run(
        self, args: list[str], cwd: Path | None = None, timeout: int = 300
    ) -> CommandResult:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        result = subprocess.run(
            args,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()[-500:]
            raise DeploymentError(f"{args[0]} failed ({result.returncode}): {detail}")
        return CommandResult(result.stdout.strip(), result.stderr.strip())

    @contextmanager
    def locked(self) -> Iterator[None]:
        import fcntl

        self.initialise()
        with self.lock_path.open("w") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise DeploymentError("Another update is already running") from exc
            yield

    def _ensure_cache(self) -> None:
        if not (self.cache / "HEAD").exists():
            if self.cache.exists():
                shutil.rmtree(self.cache)
            self.run(
                ["git", "clone", "--mirror", self.config.repo_url, str(self.cache)]
            )
        else:
            actual = self.run(
                ["git", "-C", str(self.cache), "remote", "get-url", "origin"]
            ).stdout
            if actual != self.config.repo_url:
                raise DeploymentError(
                    "Configured repository does not match the existing cache"
                )
        self.run(
            [
                "git",
                "-C",
                str(self.cache),
                "fetch",
                "--prune",
                "origin",
                self.config.repo_branch,
            ],
            timeout=120,
        )

    def remote_version(self) -> str:
        self._ensure_cache()
        return self.run(
            ["git", "-C", str(self.cache), "rev-parse", "FETCH_HEAD"]
        ).stdout

    def current_version(self) -> str | None:
        target = self._link_target(self.current)
        return target.name if target else None

    def previous_version(self) -> str | None:
        target = self._link_target(self.previous)
        return target.name if target else None

    def _link_target(self, link: Path) -> Path | None:
        return link.resolve() if link.is_symlink() else None

    def versions(self) -> dict:
        return {
            "installed_version": self.current_version(),
            "previous_version": self.previous_version(),
        }

    def check(self) -> dict:
        with self.locked():
            remote = self.remote_version()
            current = self.current_version()
            state = "up_to_date" if current == remote else "update_available"
            return {"state": state, "available_version": remote, **self.versions()}

    def _make_release(self, commit: str) -> Path:
        release = self.releases / commit
        if release.exists():
            return release
        temporary = self.releases / f".{commit}.staging"
        if temporary.exists():
            shutil.rmtree(temporary)
        self.run(
            ["git", "clone", "--no-checkout", str(self.cache), str(temporary)],
            timeout=120,
        )
        self.run(["git", "checkout", "--detach", commit], cwd=temporary)
        required = (
            temporary / "deploy" / "run.sh",
            temporary / "deploy" / "healthcheck.sh",
        )
        missing = [
            str(path.relative_to(temporary)) for path in required if not path.is_file()
        ]
        if missing:
            shutil.rmtree(temporary)
            raise DeploymentError(
                f"Release is missing required files: {', '.join(missing)}"
            )
        install_hook = temporary / "deploy" / "install.sh"
        if install_hook.is_file():
            self.run(["/bin/bash", str(install_hook)], cwd=temporary, timeout=900)
        temporary.rename(release)
        return release

    def _point(self, link: Path, target: Path) -> None:
        temp_link = link.with_name(f".{link.name}.new")
        temp_link.unlink(missing_ok=True)
        temp_link.symlink_to(target)
        os.replace(temp_link, link)

    def _restart_and_verify(self) -> None:
        self.run(
            ["sudo", "-n", "/usr/local/sbin/managed-pi-service-control", "restart"]
        )
        time.sleep(self.config.health_delay_seconds)
        self.run(
            ["sudo", "-n", "/usr/local/sbin/managed-pi-service-control", "is-active"]
        )
        self.run(
            ["/bin/bash", str(self.current / "deploy" / "healthcheck.sh")],
            cwd=self.current,
        )

    def _write_state(self, state: str, **extra: object) -> None:
        payload = {"state": state, "time": _now(), **self.versions(), **extra}
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, self.state_path)

    def update(self) -> dict:
        with self.locked():
            remote = self.remote_version()
            old = self._link_target(self.current)
            if old and old.name == remote:
                return {
                    "state": "up_to_date",
                    "available_version": remote,
                    **self.versions(),
                }
            self.status(
                "updating", f"Preparing {remote[:12]}", {"available_version": remote}
            )
            release = self._make_release(remote)
            if old:
                self._point(self.previous, old)
            self._point(self.current, release)
            try:
                self._restart_and_verify()
            except Exception as exc:
                if old:
                    self._point(self.current, old)
                    try:
                        self._restart_and_verify()
                    except Exception as rollback_exc:
                        self._write_state(
                            "rollback_failed",
                            error=str(exc),
                            rollback_error=str(rollback_exc),
                        )
                        raise DeploymentError(
                            f"Update and rollback both failed: {exc}; {rollback_exc}"
                        ) from rollback_exc
                    self._write_state(
                        "rolled_back", failed_version=remote, error=str(exc)
                    )
                    raise DeploymentRolledBack(
                        f"Release failed health checks and was rolled back: {exc}"
                    ) from exc
                self.current.unlink(missing_ok=True)
                self._write_state("failed", failed_version=remote, error=str(exc))
                raise
            self._write_state("success", available_version=remote)
            self._cleanup()
            return {"state": "success", "available_version": remote, **self.versions()}

    def rollback(self) -> dict:
        with self.locked():
            target = self._link_target(self.previous)
            if target is None:
                raise DeploymentError("No previous release is available")
            old_current = self._link_target(self.current)
            self._point(self.current, target)
            if old_current:
                self._point(self.previous, old_current)
            try:
                self._restart_and_verify()
            except Exception as exc:
                if old_current:
                    self._point(self.current, old_current)
                    self._restart_and_verify()
                raise DeploymentError(f"Requested rollback failed: {exc}") from exc
            self._write_state("rolled_back_by_request")
            return {"state": "rolled_back_by_request", **self.versions()}

    def restart(self) -> dict:
        with self.locked():
            if self._link_target(self.current) is None:
                raise DeploymentError("No application is installed")
            self._restart_and_verify()
            return {"state": "restarted", **self.versions()}

    def _cleanup(self) -> None:
        protected = {
            target
            for p in (self.current, self.previous)
            if (target := self._link_target(p))
        }
        candidates = sorted(
            (p for p in self.releases.iterdir() if p.is_dir() and p not in protected),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for path in candidates[
            max(0, self.config.release_keep_count - len(protected)) :
        ]:
            shutil.rmtree(path)
