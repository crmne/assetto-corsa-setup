"""HUD installation tests use synthetic files, never CMRT's source or assets."""
import configparser
import io
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / "assetto-corsa-setup"
INSTALLER = SCRIPT.read_text().split("<<'PY_HUD'\n", 1)[1].split("\nPY_HUD", 1)[0]
APP = "apps/lua/CMRT-Essential-HUD/"
PAID_APP = "apps/lua/CMRT-Complete-HUD/"
DETECTOR = SCRIPT.read_text().split('detect_hud_archive() {', 1)[1].split('\n}\n', 1)[0]


class HudInstallTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.game = self.root / "game with spaces"
        self.docs = self.root / "documents"
        self.cache = self.root / "cache"
        self.archive = self.root / "CMRT_essential_hud_v1.0.13.zip"
        self.game.mkdir()
        self.files = {p: "-- synthetic fixture\n" for p in (
            "CMRT-Essential-HUD.lua", "common/settings.lua", "common/players.lua",
            "radar/first.lua", "gearbox/first.lua", "leaderboard/first.lua",
            "tires/first.lua", "map/first.lua", "sectors/first.lua", "deltabar/first.lua",
            "auto_resize.ini", "manual_resize.ini", "CHANGELOG.txt")}
        self.files["manifest.ini"] = "[ABOUT]\nNAME=CMRT Essential HUD\nVERSION=1.0.13\n"
        self.files["settings/first.lua"] = "\n".join(
            k + "_scale = 1," for k in ("gearbox", "sectors", "leaderboard", "tyres", "map", "deltabar", "pedals", "radar"))
        self.put(self.game / "dwrite.dll", "fixture")
        self.put(self.game / "extension/config/data_manifest.ini", "[VERSION]\nSHADERS_PATCH=0.2.11\n")
        self.put(self.docs / "cfg/video.ini", "[VIDEO]\nWIDTH=3840\nHEIGHT=2160\n")
        self.make_archive()

    def put(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def make_archive(self, extra=None, nested_extra=None):
        nested = io.BytesIO()
        with zipfile.ZipFile(nested, "w") as z:
            z.writestr("content/gui/flags/blueFlag.png", "synthetic graphic")
            z.writestr("content/gui/flags/blueFlag_backup.png", "not the user's original")
            if nested_extra:
                z.writestr(*nested_extra)
        with zipfile.ZipFile(self.archive, "w") as z:
            for rel, text in self.files.items():
                z.writestr("CMRT_essential_hud/assettocorsa/" + APP + rel, text)
            z.writestr("CMRT_essential_hud/CMRT_flag_and_fuel_replacement.zip", nested.getvalue())
            if extra:
                z.writestr(*extra)

    def use_complete_archive(self, invalid_settings=False):
        self.archive = self.root / "CMRT_Complete_hud_v2.1.3.zip"
        files = dict(self.files)
        files["CMRT-Complete-HUD.lua"] = files.pop("CMRT-Essential-HUD.lua")
        files["manifest.ini"] = "[ABOUT]\nNAME=CMRT Complete HUD\nVERSION=2.1.3\n"
        for rel in ("damagepanel/first.lua", "mfd/first.lua"):
            files[rel] = "-- synthetic paid component\n"
        files["mfd/first.lua"] += "MFD_PRESETS[0].mfd_row1[1] = MFD_Type.ABS\n"
        scales = ("gearbox", "sectors", "leaderboard", "tyres", "map", "deltabar", "pedals", "radar", "damage_panel", "mfd")
        files["settings/first.lua"] = '\n'.join(
            f'{key}_scale = 1,\n{key}_scale = make_setting_storage("fixture_{key}", 1),'
            for key in scales)
        files["settings/first.lua"] += '\nlocal opened = ac.storage("First_Time_Opening_Complete", false)\n'
        if invalid_settings:
            files["settings/first.lua"] = "unsupported format"
        nested = io.BytesIO()
        with zipfile.ZipFile(nested, "w") as z:
            z.writestr("content/texture/off.png", "synthetic transparent starting lights")
            z.writestr("content/texture/off_bkp.png", "bundled stock copy")
        with zipfile.ZipFile(self.archive, "w") as z:
            for rel, text in files.items():
                z.writestr("package/assettocorsa/" + PAID_APP + rel, text)
            z.writestr("package/CMRT_flag_fuel_and_starting_lights_replacement.zip", nested.getvalue())

    def run_installer(self, mode="install", success=True):
        result = subprocess.run([sys.executable, "-", mode, str(self.archive), str(self.game),
                                 str(self.docs), str(self.cache)], input=INSTALLER, text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def cfg(self, rel):
        c = configparser.ConfigParser(interpolation=None)
        c.read(self.docs / "cfg" / rel)
        return c

    def test_install_arranges_current_desktop_and_backs_up_real_originals(self):
        self.put(self.docs / "cfg/acos.ini", "[HEADER]\nDESKTOP_SELECTED=2\n[DESK_0_FORM_AC_ESSENTIALS]\nVISIBLE=1\n[DESK_1_FORM_AC_ESSENTIALS]\nVISIBLE=1\n[DESK_1_FORM_CHAT]\nVISIBLE=1\n")
        self.put(self.docs / "cfg/controls.ini", "keep wheel bindings")
        self.put(self.docs / "cfg/extension/state/imgui_settings.ini", "[theme]\nkeep=1\n")
        self.put(self.docs / "cfg/extension/state/lua/app/CMRT-Essential-HUD.ini", "[VEC2]\noldsize=300,200\n[BOOLEAN]\npreference=1\n")
        self.put(self.game / "content/gui/flags/blueFlag.png", "my original")
        self.run_installer()
        c = self.cfg("acos.ini")
        self.assertEqual(c["DESK_0_FORM_AC_ESSENTIALS"]["VISIBLE"], "1")
        self.assertEqual(c["DESK_1_FORM_AC_ESSENTIALS"]["VISIBLE"], "0")
        self.assertEqual(c["DESK_1_FORM_CHAT"]["VISIBLE"], "1")
        visible = [s for s in c.sections() if "CMRT" in s and c[s]["VISIBLE"] == "1"]
        self.assertEqual(len(visible), 7)
        imgui = self.cfg("extension/state/imgui_settings.ini")
        self.assertEqual(imgui["theme"]["keep"], "1")
        for section in visible:
            key = section.removeprefix("DESK_1_FORM_")
            x, y, w, h = map(int, imgui["IMGUI_APP_POS_SIZE_1"][key].split(","))
            self.assertEqual((x, y), (int(c[section]["POSX"]), int(c[section]["POSY"])))
            self.assertLessEqual(x + w, 3840)
            if key.endswith("WINDOW_7"):
                # Radar's transparent lower window margin may extend below
                # the screen; its center and nearby-car area remain visible.
                self.assertTrue(2160 * .85 < y + h/2 < 2160)
            else:
                self.assertLessEqual(y + h, 2160)
        storage = self.cfg("extension/state/lua/app/CMRT-Essential-HUD.ini")
        self.assertFalse(storage.has_section("VEC2"))
        self.assertEqual(storage["BOOLEAN"]["preference"], "1")
        self.assertEqual(self.cfg("gameplay.ini")["OVERLAY_LEADERBOARD"]["ACTIVE"], "0")
        self.assertEqual((self.docs / "cfg/controls.ini").read_text(), "keep wheel bindings")
        self.assertRegex((self.game / APP / "settings/first.lua").read_text(), r"gearbox_scale = 2(?:\.0)?,")
        self.assertEqual(self.cfg("gameplay.ini")["VIRTUAL_MIRROR"]["ACTIVE"], "1")
        backup = next((self.cache / "backups").iterdir())
        self.assertEqual((backup / "game/content/gui/flags/blueFlag.png").read_text(), "my original")
        self.assertFalse((self.game / "content/gui/flags/blueFlag_backup.png").exists())

    def test_repeat_keeps_layout_and_preferences(self):
        self.run_installer()
        p = self.docs / "cfg/acos.ini"
        p.write_text(p.read_text().replace("POSX=60", "POSX=123"))
        settings = self.game / APP / "settings/first.lua"
        settings.write_text(settings.read_text() + "\n-- user customization\n")
        before = p.read_bytes(), settings.read_bytes()
        self.assertIn("already installed", self.run_installer().stdout)
        self.assertEqual(before, (p.read_bytes(), settings.read_bytes()))

    def test_existing_visible_layout_is_preserved_on_first_install(self):
        p = self.docs / "cfg/acos.ini"
        self.put(p, "[HEADER]\nDESKTOP_SELECTED=1\n[DESK_0_FORM_IMGUI_LUA_CMRT Essential HUD_WINDOW_0]\nVISIBLE=1\nPOSX=222\n")
        before = p.read_bytes()
        self.run_installer()
        self.assertEqual(p.read_bytes(), before)

    def test_layout_stays_within_common_resolutions(self):
        for width, height in ((1920, 1080), (2560, 1440), (3840, 2160), (3440, 1440)):
            with self.subTest(resolution=(width, height)):
                self.put(self.docs / "cfg/video.ini", f"[VIDEO]\nWIDTH={width}\nHEIGHT={height}\n")
                p = self.docs / "cfg/acos.ini"
                p.unlink(missing_ok=True)
                self.run_installer()
                for section in self.cfg("acos.ini").values():
                    if "POSX" in section:
                        self.assertTrue(0 <= int(section["POSX"]) < width)
                        self.assertTrue(0 <= int(section["POSY"]) < height)

    def test_preflight_has_no_writes(self):
        self.run_installer("check")
        self.assertFalse(self.cache.exists())
        self.assertFalse((self.game / "apps").exists())

    def test_invalid_version_missing_components_and_csp_are_rejected(self):
        self.files["manifest.ini"] = self.files["manifest.ini"].replace("1.0.13", "1.0.99")
        self.make_archive()
        self.run_installer(success=False)
        self.assertFalse((self.game / "apps").exists())
        self.files["manifest.ini"] = self.files["manifest.ini"].replace("1.0.99", "1.0.13")
        del self.files["radar/first.lua"]
        self.make_archive()
        self.run_installer(success=False)
        self.files["radar/first.lua"] = "fixture"
        self.make_archive()
        self.put(self.game / "extension/config/data_manifest.ini", "[VERSION]\nSHADERS_PATCH=0.1.79\n")
        self.run_installer(success=False)
        self.assertFalse((self.game / "apps").exists())

    def test_unsafe_paths_and_nested_archives_are_rejected(self):
        self.make_archive(extra=("../escaped", "bad"))
        self.run_installer(success=False)
        self.make_archive(nested_extra=("content/gui/flags/../../../escaped", "bad"))
        self.run_installer(success=False)
        self.assertFalse((self.game / "apps").exists())

    def test_symlinks_and_corrupt_payload_are_rejected(self):
        member = zipfile.ZipInfo("link")
        member.create_system = 3
        member.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.make_archive(extra=(member, "/outside"))
        self.run_installer(success=False)
        self.make_archive()
        self.archive.write_bytes(self.archive.read_bytes().replace(b"synthetic fixture", b"corrupted fixture", 1))
        self.run_installer(success=False)
        self.assertFalse((self.game / "apps").exists())

    def test_complete_layout_scales_and_repeat_preserves_settings(self):
        self.use_complete_archive()
        self.run_installer()
        c = self.cfg("acos.ini")
        visible = {s.rsplit("_", 1)[1] for s in c.sections()
                   if "Complete" in s and c[s]["VISIBLE"] == "1"}
        self.assertEqual(visible, {"0", "1", "2", "3", "4", "7", "8", "10", "12"})
        self.assertEqual(c["DESK_0_FORM_IMGUI_LUA_CMRT Complete HUD_WINDOW_7"]["POSY"], "1640")
        settings = self.game / PAID_APP / "settings/first.lua"
        self.assertIn('First_Time_Opening_Complete", true)', settings.read_text())
        self.assertRegex(settings.read_text(), r'mfd_scale = make_setting_storage\("fixture_mfd", 2(?:\.0)?\)')
        self.assertEqual(self.cfg("gameplay.ini")["DAMAGE_DISPLAYER"]["IS_ACTIVE"], "0")
        mfd = (self.game / PAID_APP / "mfd/first.lua").read_text()
        self.assertIn("MFD_Type.BRAKE_BIAS", mfd)
        self.assertIn("MFD_Type.LIGHTS", mfd)
        self.assertIn("MFD_Row1 = table.clone", mfd)
        self.assertFalse((self.game / "content/texture/off_bkp.png").exists())
        storage = self.docs / "cfg/extension/state/lua/app/CMRT-Complete-HUD.ini"
        self.put(storage, "[NUMBER]\ncustom_layout=2\n")
        before = (self.docs / "cfg/acos.ini").read_bytes(), settings.read_bytes(), storage.read_bytes()
        self.run_installer()
        self.assertEqual(before, ((self.docs / "cfg/acos.ini").read_bytes(), settings.read_bytes(), storage.read_bytes()))

    def test_switch_editions_backs_up_app_and_restores_layout_and_stock_graphics(self):
        self.run_installer()
        essential_archive = self.archive
        acos_path = self.docs / "cfg/acos.ini"
        acos_path.write_text(acos_path.read_text().replace("POSX=3010", "POSX=2800"))
        original_layout = self.cfg("acos.ini")
        self.put(self.game / "content/texture/off.png", "original starting lights")
        self.put(self.docs / "cfg/gameplay.ini", "[DAMAGE_DISPLAYER]\nIS_ACTIVE=1\n")
        self.put(self.game / APP / "my-file.txt", "custom app file")
        self.use_complete_archive()
        self.run_installer()
        self.assertFalse((self.game / APP).exists())
        self.assertTrue((self.game / PAID_APP / "manifest.ini").exists())
        backups = list((self.cache / "backups").glob("*/game/" + APP + "my-file.txt"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), "custom app file")
        self.archive = essential_archive
        self.run_installer()
        self.assertFalse((self.game / PAID_APP).exists())
        self.assertEqual((self.game / "content/texture/off.png").read_text(), "original starting lights")
        self.assertEqual(self.cfg("gameplay.ini")["DAMAGE_DISPLAYER"]["IS_ACTIVE"], "1")
        current = self.cfg("acos.ini")
        for s in original_layout.sections():
            if "Essential" in s:
                self.assertEqual(dict(original_layout[s]), dict(current[s]))
        self.use_complete_archive()
        self.run_installer()
        self.assertEqual(self.cfg("gameplay.ini")["DAMAGE_DISPLAYER"]["IS_ACTIVE"], "0")
        self.assertEqual(self.cfg("acos.ini")["DESK_0_FORM_IMGUI_LUA_CMRT Complete HUD_WINDOW_7"]["VISIBLE"], "1")

    def test_invalid_complete_archive_keeps_essential(self):
        self.run_installer()
        original = (self.docs / "cfg/acos.ini").read_bytes()
        self.use_complete_archive(invalid_settings=True)
        self.run_installer(success=False)
        self.assertTrue((self.game / APP / "manifest.ini").exists())
        self.assertFalse((self.game / PAID_APP).exists())
        self.assertEqual((self.docs / "cfg/acos.ini").read_bytes(), original)

    def test_complete_preflight_does_not_remove_essential(self):
        self.run_installer()
        self.use_complete_archive()
        self.run_installer("check")
        self.assertTrue((self.game / APP / "manifest.ini").exists())
        self.assertFalse((self.game / PAID_APP).exists())

    def test_mfd_update_keeps_custom_radar_and_centers_old_default_mfd(self):
        self.use_complete_archive()
        self.run_installer()
        state_path = next((self.cache / "hud").glob("*.json"))
        state = json.loads(state_path.read_text())
        state["payload_revision"] = 1
        state_path.write_text(json.dumps(state))
        imgui = self.docs / "cfg/extension/state/imgui_settings.ini"
        text = imgui.read_text().replace("IMGUI_LUA_CMRT Complete HUD_WINDOW_7=1617,1640,606,636", "IMGUI_LUA_CMRT Complete HUD_WINDOW_7=1617,1670,606,628")
        text = text.replace("IMGUI_LUA_CMRT Complete HUD_WINDOW_12=1540,1420,760,200", "IMGUI_LUA_CMRT Complete HUD_WINDOW_12=1540,1860,90,112")
        imgui.write_text(text)
        self.run_installer()
        c = self.cfg("extension/state/imgui_settings.ini")["IMGUI_APP_POS_SIZE_0"]
        self.assertEqual(c["IMGUI_LUA_CMRT Complete HUD_WINDOW_7"], "1617,1670,606,628")
        self.assertEqual(c["IMGUI_LUA_CMRT Complete HUD_WINDOW_12"], "1875,1420,90,112")

    def detect(self, success=True):
        shell = 'set -euo pipefail\nHUD_ARCHIVE=""\ninfo() { :; }\ndie() { echo "$*" >&2; exit 1; }\nAC_COMMON="$1"\ndetect_hud_archive() {' + DETECTOR + '\n}\ndetect_hud_archive "$2"\nprintf "%s" "$HUD_ARCHIVE"\n'
        result = subprocess.run(["bash", "-c", shell, "detector", str(self.game), str(self.root)], text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, success, result.stderr)
        return result.stdout

    def test_auto_detection_prefers_complete_case_insensitively(self):
        self.assertEqual(self.detect(), str(self.archive))
        self.use_complete_archive()
        self.assertEqual(self.detect(), str(self.archive))
        duplicate = self.archive.with_name("CMRT_COMPLETE_HUD (1).zip")
        duplicate.write_bytes(self.archive.read_bytes())
        self.detect(success=False)

    def test_auto_detection_never_downgrades_installed_complete(self):
        (self.game / PAID_APP).mkdir(parents=True)
        self.assertEqual(self.detect(), "")


if __name__ == "__main__":
    unittest.main()
