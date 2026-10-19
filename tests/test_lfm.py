"""LFM install tests use synthetic 7z/ASAR packages, never vendor assets."""
import json
import os
from pathlib import Path
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "assetto-corsa-setup"
INSTALLER = SCRIPT.read_text().split("<<'PY_LFM'\n", 1)[1].split("\nPY_LFM", 1)[0]


@unittest.skipUnless(shutil.which("7z"), "7z required for archive integration tests")
class LfmTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.home = self.root / "home with spaces"
        self.prefix = self.root / "prefix"
        self.game = self.root / "game with spaces"
        self.cache = self.root / "cache"
        self.steam = self.root / "Steam"
        self.app = self.prefix / "drive_c/users/steamuser/AppData/Local/Programs/LFM App"
        self.config = self.prefix / "drive_c/users/steamuser/AppData/Roaming/lfm-hub/config.json"
        self.tools = self.root / "tools"
        self.tools.mkdir()
        for name, text in {
            "xdg-mime": "#!/bin/sh\nexit 0\n",
            "update-desktop-database": "#!/bin/sh\nexit 0\n",
            "pgrep": '#!/bin/sh\nexit "${TEST_PGREP_EXIT:-1}"\n',
            "protontricks": '#!/usr/bin/env python3\nimport os,sys,json\nfrom pathlib import Path\nPath(os.environ["TEST_ARGS"]).write_text(json.dumps(sys.argv[1:]))\n',
        }.items():
            p = self.tools / name
            p.write_text(text)
            p.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home), XDG_STATE_HOME=str(self.home / "state"),
                        PATH=str(self.tools) + os.pathsep + os.environ["PATH"],
                        TEST_ARGS=str(self.root / "args.json"))
        self.make_installer()

    def make_installer(self, version="1.1.13", symlink=False):
        stage = self.root / "stage"
        shutil.rmtree(stage, ignore_errors=True)
        (stage / "resources/assets").mkdir(parents=True)
        (stage / "LFM App.exe").write_bytes(b"MZ synthetic executable")
        (stage / "resources/assets/icon.png").write_text("synthetic icon")
        meta = json.dumps(dict(name="lfm-hub", version=version)).encode()
        header = json.dumps({"files": {"package.json": {"offset": "0", "size": len(meta)}}}).encode()
        header_size = len(header) + 8
        (stage / "resources/app.asar").write_bytes(struct.pack("<4I", 4, header_size, header_size - 4, len(header)) + header + meta)
        if symlink:
            outside = self.root / "outside"
            outside.write_text("outside")
            (stage / "link").symlink_to(outside)
        nested = self.root / "outer/$PLUGINSDIR/app-64.7z"
        nested.parent.mkdir(parents=True, exist_ok=True)
        nested.unlink(missing_ok=True)
        subprocess.run(["7z", "a", "-snl", str(nested), "."], cwd=stage, check=True, capture_output=True)
        self.archive = self.root / "LFM App Setup 1.1.13.exe"
        self.archive.unlink(missing_ok=True)
        subprocess.run(["7z", "a", "-t7z", str(self.archive), "$PLUGINSDIR"], cwd=nested.parent.parent,
                       check=True, capture_output=True)

    def install(self, mode="install", **env):
        return subprocess.run([sys.executable, "-", mode, str(self.archive), str(self.game),
                               str(self.prefix), str(self.cache), str(self.steam)],
                              input=INSTALLER, text=True, capture_output=True, env=dict(self.env, **env))

    def test_install_preserves_login_and_preferences_and_is_repeatable(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text(json.dumps({"apiKey": "synthetic-test-value", "settings": {"language": "DE"}}))
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        cfg = json.loads(self.config.read_text())
        self.assertEqual(cfg["apiKey"], "synthetic-test-value")
        self.assertEqual(cfg["settings"], {"language": "DE"})
        self.assertEqual(cfg["acSteamPath"], "Z:" + str(self.game).replace("/", "\\"))
        self.assertTrue(cfg["acSteamPathLocked"])
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
        mtime = (self.app / "LFM App.exe").stat().st_mtime_ns
        result = self.install(TEST_PGREP_EXIT="0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.app / "LFM App.exe").stat().st_mtime_ns, mtime)
        self.assertEqual(len(list((self.cache / "backups").glob("*/config.json"))), 1)

    def test_preflight_and_wrong_version_leave_install_untouched(self):
        self.assertEqual(self.install("check").returncode, 0)
        self.assertFalse(self.app.exists())
        self.assertFalse((self.home / ".local/bin/lfm-app").exists())
        self.make_installer(version="9.0.0")
        self.assertNotEqual(self.install().returncode, 0)
        self.assertFalse(self.app.exists())

    def test_repair_waits_for_running_app_and_backs_up_original(self):
        self.assertEqual(self.install().returncode, 0)
        (self.app / "LFM App.exe").write_text("old executable")
        self.assertNotEqual(self.install(TEST_PGREP_EXIT="0").returncode, 0)
        self.assertEqual((self.app / "LFM App.exe").read_text(), "old executable")
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        backup = next((self.cache / "backups").glob("*/app/LFM App.exe"))
        self.assertEqual(backup.read_text(), "old executable")

    def test_rerun_keeps_a_newer_vendor_update(self):
        self.assertEqual(self.install().returncode, 0)
        self.make_installer(version="1.2.0")
        asar = self.app / "resources/app.asar"
        shutil.copyfile(self.root / "stage/resources/app.asar", asar)
        updated = asar.read_bytes()
        self.make_installer()
        result = self.install(TEST_PGREP_EXIT="0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(asar.read_bytes(), updated)
        self.assertIn("newer installed", result.stdout)

    def test_invalid_settings_abort_before_installation(self):
        self.config.parent.mkdir(parents=True)
        for invalid in ["{", "[]", "null"]:
            self.config.write_text(invalid)
            result = self.install()
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.config.read_text(), invalid)
            self.assertFalse(self.app.exists())

    def test_fresh_prefix_preserves_lfm_and_refuses_backup_collisions(self):
        self.assertEqual(self.install().returncode, 0)
        body = SCRIPT.read_text().split("restore_config_backup() {", 1)[1].split(
            "# ------------------------------------------------- Content Manager and CSP", 1)[0]
        program = ('set -e\nstep() { :; }; warn() { :; }; die() { exit 1; }\n'
                   'restore_config_backup() {' + body)
        backup = self.root / "previous-settings"
        env = dict(self.env, FRESH="1", CONFIG_BACKUP=str(backup), COMPATDATA=str(self.prefix),
                   AC_DOCS=str(self.prefix / "Documents/Assetto Corsa"),
                   CM_DATA=str(self.prefix / "CM"), LFM_DATA=str(self.config.parent), LFM_APP=str(self.app))
        original = self.config.read_bytes()
        obsolete = self.prefix / "obsolete-prefix-file"
        obsolete.write_text("discard on rebuild")
        result = subprocess.run(["bash", "-c", program], env=env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.config.read_bytes(), original)
        self.assertTrue((self.app / "LFM App.exe").exists())
        self.assertFalse(obsolete.exists())
        (backup / "lfm-hub").mkdir(parents=True)
        result = subprocess.run(["bash", "-c", program], env=env, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.config.read_bytes(), original)
        self.assertTrue((self.app / "LFM App.exe").exists())

    def test_rejects_archive_links_and_destination_escape(self):
        self.make_installer(symlink=True)
        self.assertNotEqual(self.install().returncode, 0)
        self.assertFalse(self.app.exists())
        self.make_installer()
        self.app.parent.mkdir(parents=True)
        outside = self.root / "outside-directory"
        outside.mkdir()
        self.app.symlink_to(outside)
        self.assertNotEqual(self.install().returncode, 0)
        self.assertFalse(list(outside.iterdir()))

    def test_callback_remains_one_quoted_argument_and_rejects_other_schemes(self):
        self.assertEqual(self.install().returncode, 0)
        launcher = self.home / ".local/bin/lfm-app"
        url = "lfmhub://auth?token=synthetic'; touch /should-not-run; $(false)"
        result = subprocess.run([str(launcher), url], env=self.env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads((self.root / "args.json").read_text())
        self.assertEqual(args[0], "-c")
        self.assertEqual(args[2], "244210")
        command = shlex.split(args[1])
        self.assertEqual(command[-1], url)
        self.assertEqual(len(command), 5)
        self.assertIn("--disable-gpu", command)
        self.assertFalse((self.home / "state/assetto-corsa-setup/lfm-launch.log").exists())
        (self.root / "args.json").unlink()
        result = subprocess.run([str(launcher), "https://example.com"], env=self.env, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "args.json").exists())


if __name__ == "__main__":
    unittest.main()
