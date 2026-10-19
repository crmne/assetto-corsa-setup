"""Exercise installation and the actual Lua sender with a mock CSP runtime."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "assetto-corsa-setup"
INSTALLER = SCRIPT.read_text().split("<<'PY_MOZA'\n", 1)[1].split("\nPY_MOZA", 1)[0]


class MozaTelemetryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.game = self.root / "game with spaces"
        self.game.mkdir()
        (self.game / "dwrite.dll").write_text("fixture")
        self.cache = self.root / "cache"
        self.app = self.game / "apps/lua/OmarchyMoza"

    def install(self):
        return subprocess.run([sys.executable, "-", str(self.game), str(self.cache)],
                              input=INSTALLER, text=True, capture_output=True)

    def test_idempotent_and_backs_up_changed_app(self):
        self.assertEqual(self.install().returncode, 0)
        lua = self.app / "OmarchyMoza.lua"
        original = lua.read_text()
        mtime = lua.stat().st_mtime_ns
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(lua.stat().st_mtime_ns, mtime)
        lua.write_text("-- previous version")
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(lua.read_text(), original)
        backups = list((self.cache / "backups").glob("*/OmarchyMoza.lua"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), "-- previous version")

    def test_requires_csp_and_rejects_escaping_destination(self):
        (self.game / "dwrite.dll").unlink()
        self.assertEqual(self.install().returncode, 0)
        self.assertFalse(self.app.exists())
        (self.game / "dwrite.dll").touch()
        self.app.parent.mkdir(parents=True)
        outside = self.root / "outside"
        outside.mkdir()
        self.app.symlink_to(outside)
        self.assertNotEqual(self.install().returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])

    @unittest.skipUnless(shutil.which("luajit"), "LuaJIT required to exercise CSP sender")
    def test_sender_uses_current_car_limit_and_suppresses_replay(self):
        self.assertEqual(self.install().returncode, 0)
        runner = self.root / "runtime.lua"
        runner.write_text('''
local packets = {}
local peer, port
local sender = {
  settimeout = function(_, n) assert(n == 0) end,
  setsockname = function(_, host, n) assert(host == '127.0.0.1' and n == 0) end,
  close = function() end,
  sendto = function(_, data, host, n) packets[#packets + 1] = data; peer = host; port = n end
}
package.preload['shared/socket'] = function() return {udp = function() return sender end} end
local car = {rpm = 6305, rpmLimiter = 6500, rpmMinimum = 1250}
local sim = {}
ac = {getCar = function(index) assert(index == 0); return car end,
  getSim = function() return sim end, onRelease = function() end}
script = {}
dofile(arg[1])
script.update(1/120)
assert(#packets == 0)
script.update(1/120)
assert(packets[1] == '{"protocol":"omarchy-moza-ac/1","rpm":6305,"redline":6500,"idle":1250}')
assert(peer == '127.0.0.1' and port == 9997)
car = {rpm = 485, rpmLimiter = 500, rpmMinimum = -1}
script.update(1/60)
assert(packets[2] == '{"protocol":"omarchy-moza-ac/1","rpm":485,"redline":500,"idle":0}')
car.rpm = 600
script.update(1/60)
assert(packets[3]:find('"redline":500', 1, true))
sim.isReplayActive = true
script.update(1/60)
assert(packets[4]:find('"rpm":0', 1, true))
car.rpmLimiter = 0
script.update(1/60)
assert(#packets == 4)
''')
        result = subprocess.run(["luajit", str(runner), str(self.app / "OmarchyMoza.lua")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
