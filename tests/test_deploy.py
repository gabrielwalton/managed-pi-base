from contextlib import contextmanager
from pathlib import Path

import pytest

from managed_pi_agent.config import Config
from managed_pi_agent.deploy import Deployer, DeploymentError, DeploymentRolledBack


def config(tmp_path: Path) -> Config:
    return Config(
        device_id="test-pi",
        device_name="Test Pi",
        mqtt_host="mqtt.local",
        mqtt_port=1883,
        mqtt_username=None,
        mqtt_password=None,
        mqtt_discovery_prefix="homeassistant",
        repo_url="https://example.invalid/app.git",
        repo_branch="main",
        base_dir=tmp_path,
        service_name="managed-pi-app.service",
        health_delay_seconds=0,
        release_keep_count=3,
    )


class FakeDeployer(Deployer):
    def __init__(self, cfg, status, remote="b" * 40, fail_health=False):
        super().__init__(cfg, status)
        self.remote = remote
        self.fail_health = fail_health
        self.restart_count = 0
        self.pointers = {}

    @contextmanager
    def locked(self):
        self.initialise()
        yield

    def remote_version(self):
        return self.remote

    def _make_release(self, commit):
        release = self.releases / commit
        (release / "deploy").mkdir(parents=True, exist_ok=True)
        (release / "deploy" / "run.sh").write_text("#!/bin/sh\n")
        (release / "deploy" / "healthcheck.sh").write_text("#!/bin/sh\n")
        return release

    def _restart_and_verify(self):
        self.restart_count += 1
        if self.fail_health:
            self.fail_health = False
            raise DeploymentError("unhealthy")

    def _point(self, link, target):
        self.pointers[str(link)] = target

    def _link_target(self, link):
        return self.pointers.get(str(link))


def seed_current(deployer: Deployer, commit="a" * 40):
    release = deployer.releases / commit
    (release / "deploy").mkdir(parents=True)
    deployer._point(deployer.current, release)
    return release


def test_successful_update_switches_release_and_keeps_previous(tmp_path):
    deployer = FakeDeployer(config(tmp_path), lambda *args: None)
    old = seed_current(deployer)
    result = deployer.update()
    assert deployer._link_target(deployer.current).name == "b" * 40
    assert deployer._link_target(deployer.previous) == old
    assert result["state"] == "success"


def test_failed_health_check_restores_previous_release(tmp_path):
    deployer = FakeDeployer(config(tmp_path), lambda *args: None, fail_health=True)
    old = seed_current(deployer)
    with pytest.raises(DeploymentRolledBack, match="rolled back"):
        deployer.update()
    assert deployer._link_target(deployer.current) == old
    assert deployer.restart_count == 2


def test_retains_only_configured_number_of_releases(tmp_path):
    deployer = FakeDeployer(config(tmp_path), lambda *args: None)
    for index in range(6):
        release = deployer.releases / (str(index) * 40)
        release.mkdir(parents=True)
    deployer._point(deployer.current, deployer.releases / ("5" * 40))
    deployer._point(deployer.previous, deployer.releases / ("4" * 40))
    deployer._cleanup()
    assert len(list(deployer.releases.iterdir())) == 3
