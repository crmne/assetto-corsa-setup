"""Exercise local coach installation without distributing the vendor binary."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "assetto-corsa-setup"
INSTALLER = SCRIPT.read_text().split("<<'PY_COACH'\n", 1)[1].split("\nPY_COACH", 1)[0]
VENDOR_HASH = "9eca51428b1a1d06edbe868f663b763991957c68128af3ee5caee1d187f4b1b7"


class CoachTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.home = self.root / "home with spaces"
        self.prefix = self.root / "prefix"
        self.cache = self.root / "cache"
        self.app = self.prefix / "drive_c/users/steamuser/AppData/Local/Programs/TheTenths"
        self.profile = self.prefix / "drive_c/users/steamuser/AppData/Roaming/TheTenths"
        self.target = self.app / "thetenths-client.exe"
        self.source = self.root / "thetenths-client.exe"
        self.source.write_bytes(b"synthetic coach fixture")
        self.installer = INSTALLER.replace(VENDOR_HASH, hashlib.sha256(self.source.read_bytes()).hexdigest())
        tools = self.root / "tools"
        tools.mkdir()
        for name, data in {
            "pgrep": '#!/bin/sh\nexit "${TEST_RUNNING:-1}"\n',
            "protontricks": '#!/usr/bin/env python3\nimport json,os,sys\nfrom pathlib import Path\nPath(os.environ["TEST_ARGS"]).write_text(json.dumps(sys.argv[1:]))\n',
            "update-desktop-database": '#!/bin/sh\nexit 0\n',
        }.items():
            p = tools / name
            p.write_text(data)
            p.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home), PATH=str(tools)+os.pathsep+os.environ["PATH"],
                        TEST_ARGS=str(self.root / "args.json"))

    def install(self, mode="install", selection="auto", **env):
        return subprocess.run([sys.executable, "-", mode, str(self.source), str(self.prefix),
                               str(self.cache), str(self.root / "Steam"), selection],
                              input=self.installer, text=True, capture_output=True, env=dict(self.env, **env))

    def test_check_validates_before_writing_and_rejects_other_downloads(self):
        self.assertEqual(self.install("check").returncode, 0)
        self.assertFalse(self.app.exists())
        self.source.write_bytes(b"different build")
        self.assertNotEqual(self.install().returncode, 0)
        self.assertFalse(self.app.exists())

    def test_install_keeps_profile_and_identical_running_binary(self):
        self.profile.mkdir(parents=True)
        config = self.profile / "telemetry.json"
        config.write_text('{"token":"synthetic-test-token","settings":{"coach":true}}')
        before = config.read_bytes()
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        mtime = self.target.stat().st_mtime_ns
        self.assertEqual(self.install(TEST_RUNNING="0").returncode, 0)
        self.assertEqual(self.target.stat().st_mtime_ns, mtime)
        self.assertEqual(config.read_bytes(), before)
        self.assertFalse((self.cache / "backups").exists())

    def test_auto_keeps_updated_binary_and_explicit_replacement_backs_up(self):
        self.assertEqual(self.install().returncode, 0)
        self.target.write_bytes(b"vendor update")
        self.assertEqual(self.install(TEST_RUNNING="0").returncode, 0)
        self.assertEqual(self.target.read_bytes(), b"vendor update")
        self.assertNotEqual(self.install(selection="explicit", TEST_RUNNING="0").returncode, 0)
        result = self.install(selection="explicit")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.target.read_bytes(), self.source.read_bytes())
        saved = next((self.cache / "backups").glob("thetenths-*/thetenths-client.exe"))
        self.assertEqual(saved.read_bytes(), b"vendor update")

    def test_destination_symlink_is_rejected(self):
        self.app.parent.mkdir(parents=True)
        outside = self.root / "outside"
        outside.mkdir()
        self.app.symlink_to(outside)
        self.assertNotEqual(self.install().returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])

    def test_launcher_uses_ac_prefix_and_keeps_spaces_quoted(self):
        self.assertEqual(self.install().returncode, 0)
        launcher = self.home / ".local/bin/thetenths"
        result = subprocess.run([str(launcher)], env=self.env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads((self.root / "args.json").read_text())
        self.assertEqual(args[0], "-c")
        self.assertEqual(args[2], "244210")
        command = shlex.split(args[1])
        self.assertEqual(command, ["wine", r"C:\users\steamuser\AppData\Local\Programs\TheTenths\thetenths-client.exe"])
        self.assertNotEqual(subprocess.run([str(launcher), "unexpected"], env=self.env, capture_output=True).returncode, 0)

    def test_fresh_keeps_app_and_account_and_refuses_colliding_backup(self):
        self.assertEqual(self.install().returncode, 0)
        self.profile.mkdir(parents=True)
        config = self.profile / "telemetry.json"
        config.write_text('{"token":"synthetic"}')
        body = SCRIPT.read_text().split("restore_config_backup() {", 1)[1].split(
            "# ------------------------------------------------- Content Manager and CSP", 1)[0]
        program = ('set -eu\nstep() { :; }; warn() { :; }; die() { exit 1; }\n'
                   'restore_config_backup() {' + body)
        backup = self.root / "backup"
        env = dict(self.env, FRESH="1", CONFIG_BACKUP=str(backup), COMPATDATA=str(self.prefix),
                   AC_DOCS=str(self.prefix / "Documents/Assetto Corsa"), CM_DATA=str(self.prefix / "CM"),
                   LFM_DATA=str(self.prefix / "lfm-hub"), LFM_APP=str(self.prefix / "LFM App"),
                   COACH_DATA=str(self.profile), COACH_APP=str(self.app))
        before = config.read_bytes()
        obsolete = self.prefix / "discard-me"
        obsolete.write_text("old prefix")
        result = subprocess.run(["bash", "-c", program], env=env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(config.read_bytes(), before)
        self.assertTrue(self.target.exists())
        self.assertFalse(obsolete.exists())
        (backup / "TheTenths-profile").mkdir(parents=True)
        self.assertNotEqual(subprocess.run(["bash", "-c", program], env=env, capture_output=True).returncode, 0)
        self.assertEqual(config.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
