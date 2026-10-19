"""Exercise the embedded installer against synthetic archives, never paid assets."""
import configparser
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / "assetto-corsa-setup"
INSTALLER = SCRIPT.read_text().split("<<'PY_PURE'\n", 1)[1].split("\nPY_PURE", 1)[0]


class PureInstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.game = self.root / "game with spaces"
        self.docs = self.root / "documents"
        self.cache = self.root / "cache"
        self.game.mkdir()
        self.archive = self.root / "Pure 3.59 Highres.zip"
        self.files = {
            "extension/weather/Pure LCS/manifest.ini": "[ABOUT]\nVERSION=3.59\n",
            "extension/weather/pure/manifest.ini": "[ABOUT]\nVERSION=3.59\n",
            "extension/weather/Pure LCS/weather.lua": "__PURE_version = 3.59\n",
            "extension/weather-controllers/pureCtrl static/controller.lua": "-- test fixture\n",
            "system/cfg/ppfilters/pure.ini": "[ABOUT]\nVERSION=fixture\n",
            "system/cfg/ppfilters/purelcs_scripts/pure.lua": "-- test fixture\n",
            "apps/lua/PureConfig/manifest.ini": "[ABOUT]\nNAME=fixture\n",
            "extension/config-ext/Pure/textures/test.dds": "test texture",
        }
        self.write("extension/config/data_manifest.ini", "[VERSION]\nSHADERS_PATCH_BUILD=3465\n")
        self.write("dwrite.dll", "fixture")
        self.make_archive()

    def write(self, relative, content):
        path = self.game / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def make_archive(self, extra=None):
        with zipfile.ZipFile(self.archive, "w") as bundle:
            for name, content in self.files.items():
                bundle.writestr("Pure 3.59/" + name, content)
            # Installers supplied with Pure must never be executed or copied.
            bundle.writestr("Pure 3.59/uninstall_pure.bat", "DO NOT RUN")
            if extra:
                bundle.writestr(*extra)

    def run_installer(self, mode="install", success=True):
        result = subprocess.run(
            [sys.executable, "-", mode, str(self.archive), str(self.game), str(self.docs), str(self.cache)],
            input=INSTALLER, text=True, capture_output=True,
        )
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def test_install_configures_preset_and_preserves_controls_with_backups(self):
        original = self.write("system/cfg/ppfilters/pure.ini", "original")
        cfg = self.docs / "cfg"
        cfg.mkdir(parents=True)
        (cfg / "controls.ini").write_text("wheel bindings")
        (cfg / "video.ini").write_text("[VIDEO]\nWIDTH=3840\nHEIGHT=2160\n[POST_PROCESS]\nFILTER=default\n")
        self.run_installer()
        self.assertEqual(original.read_text(), self.files["system/cfg/ppfilters/pure.ini"])
        self.assertEqual((cfg / "controls.ini").read_text(), "wheel bindings")
        settings = configparser.ConfigParser()
        settings.read(cfg / "video.ini")
        self.assertEqual(settings["VIDEO"]["WIDTH"], "3840")
        self.assertEqual(settings["POST_PROCESS"]["FILTER"], "pure")
        self.assertEqual(settings["POST_PROCESS"]["DOF"], "0")
        self.assertIn("CONTROLLER=pureCtrl static", (cfg / "extension/weather_fx.ini").read_text())
        backup = next((self.cache / "backups").iterdir())
        self.assertEqual((backup / "game/system/cfg/ppfilters/pure.ini").read_text(), "original")
        self.assertIn("FILTER=default", (backup / "cfg/video.ini").read_text())
        self.assertFalse((self.game / "uninstall_pure.bat").exists())
        self.assertFalse(list(self.cache.glob("pure-stage-*")))

    def test_repeat_preserves_adjustments_and_is_idempotent(self):
        self.run_installer()
        video = self.docs / "cfg/video.ini"
        video.write_text(video.read_text().replace("DOF=0", "DOF=3").replace("FILTER=pure", "FILTER=custom"))
        preset = self.game / "extension/config-ext/Pure LCS/scriptsettings/pure_ScriptSettings.ini"
        preset.write_text(preset.read_text().replace("photo-realistic=0.25", "photo-realistic=0.4"))
        before = {p: p.read_bytes() for p in [video, preset]}
        result = self.run_installer()
        self.assertIn("already installed", result.stdout)
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        self.assertEqual(len(list((self.cache / "backups").iterdir())), 1)

    def test_existing_pure_app_preferences_are_kept(self):
        preset = self.write("extension/config-ext/Pure LCS/scriptsettings/pure_ScriptSettings.ini",
                            "[PureScriptSettings]\nphoto-realistic=0.7\ncustom=keep\n")
        self.run_installer()
        self.assertIn("photo-realistic=0.7", preset.read_text())
        self.assertIn("custom=keep", preset.read_text())
        self.assertIn("exposure-uplift=0.10", preset.read_text())

    def test_check_is_read_only(self):
        self.run_installer("check")
        self.assertFalse(self.docs.exists())
        self.assertFalse(self.cache.exists())
        self.assertFalse((self.game / "apps").exists())

    def test_wrong_version_is_rejected_before_changes(self):
        self.files["extension/weather/Pure LCS/manifest.ini"] = "[ABOUT]\nVERSION=3.60\n"
        self.make_archive()
        self.run_installer(success=False)
        self.assertFalse((self.game / "apps").exists())

    def test_missing_component_is_rejected(self):
        del self.files["system/cfg/ppfilters/purelcs_scripts/pure.lua"]
        self.make_archive()
        self.run_installer(success=False)

    def test_traversal_and_duplicate_paths_are_rejected(self):
        for extra in [("Pure 3.59/apps/../../../escaped", "bad"),
                      ("Pure 3.59/SYSTEM/cfg/ppfilters/PURE.ini", "duplicate"),
                      ("/absolute", "bad")]:
            with self.subTest(extra=extra[0]):
                self.make_archive(extra)
                self.run_installer(success=False)
                self.assertFalse((self.game / "apps").exists())

    def test_symlink_members_are_rejected(self):
        member = zipfile.ZipInfo("Pure 3.59/apps/link")
        member.create_system = 3
        member.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.make_archive((member, "../../outside"))
        self.run_installer(success=False)

    def test_symlink_destination_escape_is_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.game / "apps").symlink_to(outside, target_is_directory=True)
        self.run_installer(success=False)
        self.assertEqual(list(outside.iterdir()), [])

    def test_corrupt_payload_changes_no_game_files(self):
        payload = self.archive.read_bytes()
        self.archive.write_bytes(payload.replace(b"test texture", b"bad! texture", 1))
        self.run_installer(success=False)
        self.assertFalse((self.game / "apps").exists())
        self.assertFalse(list(self.cache.glob("pure-stage-*")))

    def test_old_csp_is_rejected(self):
        self.write("extension/config/data_manifest.ini", "[VERSION]\nSHADERS_PATCH_BUILD=2000\n")
        self.run_installer(success=False)
        self.assertFalse((self.game / "apps").exists())


if __name__ == "__main__":
    unittest.main()
