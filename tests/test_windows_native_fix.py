from __future__ import annotations

from pathlib import Path
import tempfile
from unittest import mock

from archive_workbench_ai.bridge import BRIDGE_PROTOCOL, stop_bridge


ROOT = Path(__file__).parents[1]


def test_windows_inno_setup_reads_sibling_vbs() -> None:
    source = (ROOT / "packaging" / "windows" / "ArchiveWorkbenchAI.iss").read_text(
        encoding="utf-8"
    )
    assert 'Source: "setup.vbs"' in source
    assert 'Source: "packaging\\windows\\setup.vbs"' not in source


def test_native_workflow_can_rebuild_windows_without_rebuilding_green_platforms() -> None:
    source = (ROOT / ".github" / "workflows" / "build-native.yml").read_text(
        encoding="utf-8"
    )
    assert "target:" in source
    assert "windows-x64" in source
    assert "inputs.target == 'windows-x64'" in source
    assert '$PSNativeCommandUseErrorActionPreference = $true' in source


def test_stop_bridge_prefers_cooperative_request_over_signal() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "bridge"
        root.mkdir()
        running = {
            "root": str(root),
            "protocol": BRIDGE_PROTOCOL,
            "initialized": True,
            "running": True,
            "pid": 123,
            "pending_jobs": 0,
            "status_file": str(root / "bridge-status.json"),
            "log_file": str(root / "bridge.log"),
        }
        stopped = {**running, "running": False, "pid": None}
        with (
            mock.patch(
                "archive_workbench_ai.bridge.bridge_status",
                side_effect=[running, running, stopped],
            ),
            mock.patch("archive_workbench_ai.bridge.os.kill") as kill,
            mock.patch("archive_workbench_ai.bridge.subprocess.run") as taskkill,
            mock.patch("archive_workbench_ai.bridge.time.sleep"),
        ):
            result = stop_bridge(root, wait_seconds=0.2)

        assert result["status"] == "stopped"
        assert not (root / "stop.request").exists()
        kill.assert_not_called()
        taskkill.assert_not_called()
