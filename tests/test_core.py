"""Tests for mafl-service-discovery core logic.

Covers environment variable substitution, dictionary merging,
and label extraction helpers referenced in docs/REQUIREMENTS.md.
"""

import os
import sys
import importlib
import types
import pytest

# ---------------------------------------------------------------------------
# Import the main module despite the hyphenated filename
# ---------------------------------------------------------------------------

MODULE_PATH = os.path.join(
    os.path.dirname(__file__), os.pardir, "mafl-service-discovery.py"
)


def _load_module():
    """Load mafl-service-discovery.py as a Python module."""
    spec = importlib.util.spec_from_file_location("mafl_service_discovery", MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    mod.__name__ = "mafl_service_discovery"
    spec.loader.exec_module(mod)
    return mod

msd = _load_module()


# ===================================================================
# FR-3 / replace_env_variables
# ===================================================================


class TestReplaceEnvVariables:
    """Verify environment variable substitution in YAML configs."""

    def test_simple_substitution(self, monkeypatch):
        monkeypatch.setenv("DOMAIN", "example.com")
        config = {"link": "https://app.${DOMAIN}/"}
        result = msd.replace_env_variables(config)
        assert result["link"] == "https://app.example.com/"

    def test_missing_env_var_replaced_with_empty(self, monkeypatch):
        monkeypatch.delenv("MISSING_VAR", raising=False)
        config = {"link": "https://${MISSING_VAR}/path"}
        result = msd.replace_env_variables(config)
        assert result["link"] == "https:///path"

    def test_nested_dict_substitution(self, monkeypatch):
        monkeypatch.setenv("HOST", "myhost")
        config = {"outer": {"inner": "http://${HOST}:8080"}}
        result = msd.replace_env_variables(config)
        assert result["outer"]["inner"] == "http://myhost:8080"

    def test_list_substitution(self, monkeypatch):
        monkeypatch.setenv("PORT", "9090")
        config = {"ports": ["${PORT}", "8080"]}
        result = msd.replace_env_variables(config)        assert result["ports"] == ["9090", "8080"]

    def test_no_substitution_needed(self):
        config = {"title": "My Dashboard", "count": 42}
        result = msd.replace_env_variables(config)
        assert result == {"title": "My Dashboard", "count": 42}

    def test_multiple_vars_in_one_string(self, monkeypatch):
        monkeypatch.setenv("PROTO", "https")
        monkeypatch.setenv("DOMAIN", "test.io")
        config = {"url": "${PROTO}://app.${DOMAIN}"}
        result = msd.replace_env_variables(config)
        assert result["url"] == "https://app.test.io"


# ===================================================================
# FR-3 / merge_dicts
# ===================================================================


class TestMergeDicts:
    """Verify recursive dictionary merging behaviour."""

    def test_flat_merge(self):
        a = {"x": 1, "y": 2}
        b = {"y": 3, "z": 4}
        result = msd.merge_dicts(a, b)
        assert result == {"x": 1, "y": 3, "z": 4}

    def test_nested_merge(self):
        a = {"services": {"web": {"port": 80}}}        b = {"services": {"web": {"host": "0.0.0.0"}}}
        result = msd.merge_dicts(a, b)
        assert result == {"services": {"web": {"port": 80, "host": "0.0.0.0"}}}

    def test_list_concatenation(self):
        a = {"items": [1, 2]}
        b = {"items": [3, 4]}
        result = msd.merge_dicts(a, b)
        assert result["items"] == [1, 2, 3, 4]

    def test_does_not_mutate_originals(self):
        a = {"key": "original"}
        b = {"key": "override"}
        msd.merge_dicts(a, b)
        assert a["key"] == "original"

    def test_empty_dicts(self):
        assert msd.merge_dicts({}, {"a": 1}) == {"a": 1}
        assert msd.merge_dicts({"a": 1}, {}) == {"a": 1}
        assert msd.merge_dicts({}, {}) == {}


# ===================================================================
# FR-1 / get_mafl_services (mocked Docker client)
# ===================================================================


class _FakeContainer:
    """Minimal stand-in for a Docker container object."""

    def __init__(self, name, labels, status="running"):        self.name = name
        self.status = status
        self.attrs = {"Config": {"Labels": labels}}


class TestGetMaflServices:
    """Verify Docker label extraction logic using a mocked Docker client."""

    def _patch_docker(self, monkeypatch, containers):
        """Replace docker.from_env() with a fake client returning *containers*."""

        class FakeClient:
            class containers:
                @staticmethod
                def list(all=False):
                    return containers

        monkeypatch.setattr(msd.docker, "from_env", lambda: FakeClient())

    def test_discovers_labelled_container(self, monkeypatch):
        containers = [
            _FakeContainer(
                "myapp",
                {
                    "mafl.enable": "true",
                    "mafl.group": "Apps",
                    "mafl.title": "My App",
                    "mafl.description": "A test app",
                    "mafl.link": "https://app.local",
                    "mafl.icon.name": "mdi:application",
                },            )
        ]
        self._patch_docker(monkeypatch, containers)
        services = msd.get_mafl_services()
        assert "Apps" in services
        assert len(services["Apps"]) == 1
        svc = services["Apps"][0]
        assert svc["title"] == "My App"
        assert svc["description"] == "A test app"
        assert svc["link"] == "https://app.local"

    def test_ignores_container_without_enable(self, monkeypatch):
        containers = [
            _FakeContainer("nolabel", {"mafl.title": "Ghost"})
        ]
        self._patch_docker(monkeypatch, containers)
        services = msd.get_mafl_services()
        assert services == {}

    def test_ignores_stopped_container(self, monkeypatch):
        containers = [
            _FakeContainer(
                "stopped",
                {"mafl.enable": "true", "mafl.group": "X"},
                status="exited",
            )
        ]
        self._patch_docker(monkeypatch, containers)
        services = msd.get_mafl_services()
        assert services == {}
    def test_default_group_is_miscellaneous(self, monkeypatch):
        containers = [
            _FakeContainer("nogroupapp", {"mafl.enable": "true"})
        ]
        self._patch_docker(monkeypatch, containers)
        services = msd.get_mafl_services()
        assert "Miscellaneous" in services

    def test_empty_labels_omitted(self, monkeypatch):
        containers = [
            _FakeContainer(
                "minimal",
                {
                    "mafl.enable": "true",
                    "mafl.group": "Test",
                    "mafl.title": "Minimal",
                },
            )
        ]
        self._patch_docker(monkeypatch, containers)
        services = msd.get_mafl_services()
        svc = services["Test"][0]
        # Empty string fields like description, link should be removed
        assert "description" not in svc or svc.get("description") != ""
        assert "link" not in svc or svc.get("link") != ""

    def test_status_label_parsing(self, monkeypatch):
        containers = [
            _FakeContainer(                "withstatus",
                {
                    "mafl.enable": "true",
                    "mafl.group": "Monitoring",
                    "mafl.title": "StatusApp",
                    "mafl.status.enabled": "true",
                    "mafl.status.interval": "30",
                },
            )
        ]
        self._patch_docker(monkeypatch, containers)
        services = msd.get_mafl_services()
        svc = services["Monitoring"][0]
        assert svc["status"]["enabled"] is True
        assert svc["status"]["interval"] == 30

    def test_icon_color_included(self, monkeypatch):
        containers = [
            _FakeContainer(
                "colorapp",
                {
                    "mafl.enable": "true",
                    "mafl.group": "UI",
                    "mafl.title": "ColorApp",
                    "mafl.icon.name": "mdi:palette",
                    "mafl.icon.color": "#ff5500",
                },
            )
        ]
        self._patch_docker(monkeypatch, containers)        services = msd.get_mafl_services()
        svc = services["UI"][0]
        assert svc["icon"]["color"] == "#ff5500"


# ===================================================================
# Documentation validation
# ===================================================================


class TestRequirementsDocExists:
    """Verify that docs/REQUIREMENTS.md exists and has required sections."""

    REQUIREMENTS_PATH = os.path.join(
        os.path.dirname(__file__), os.pardir, "docs", "REQUIREMENTS.md"
    )

    def test_file_exists(self):
        assert os.path.isfile(self.REQUIREMENTS_PATH), (
            "docs/REQUIREMENTS.md must exist"
        )

    def test_has_required_sections(self):
        with open(self.REQUIREMENTS_PATH) as f:
            content = f.read()
        required = [
            "Project Overview",
            "Core Functional Requirements",
            "Non-Functional Requirements",
            "Integration Requirements",
            "Current Status",
        ]
        for section in required:
            assert section in content, (
                f"docs/REQUIREMENTS.md must contain a '{section}' section"
            )