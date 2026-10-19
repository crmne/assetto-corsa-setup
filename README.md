# assetto-corsa-setup

One command that makes Assetto Corsa on Steam playable on Linux, with
[Content Manager](https://acstuff.club/app/) and
[Custom Shaders Patch](https://acstuff.club/patch/) installed and configured.
It asks no questions, and Content Manager opens ready to race: game folder set,
Steam profile picked, plugins in place, readable text at your display's scale.

```sh
curl -fLO https://raw.githubusercontent.com/crmne/assetto-corsa-setup/main/assetto-corsa-setup
chmod +x assetto-corsa-setup
./assetto-corsa-setup
```

Install Assetto Corsa in Steam first. The script is safe to run again at any
time; it only changes what is missing or wrong.

## What it does

1. Finds the game in any of your Steam libraries (native, Flatpak or Snap Steam).
2. Installs GE-Proton (GE-Proton11-7 by default, checksum verified) and sets it
   as Assetto Corsa's compatibility tool in Steam, closing Steam first if it has
   to.
3. Replaces the stock launcher with Content Manager, keeping the original as
   `AssettoCorsa_original.exe`, and installs the fonts Content Manager needs.
4. Installs Custom Shaders Patch 0.2.11.
5. Writes Content Manager's settings: the game folder, your Steam ID, and its
   plugins, so it skips its first-run wizard.
6. Starts the game once and waits while Proton builds the Wine prefix and
   installs .NET and the other components the game needs. This takes several
   minutes and shows nothing, which is why a first launch often looks broken.
7. Installs the Windows core fonts Custom Shaders Patch needs.
8. Fixes Content Manager's look. Proton maps Segoe UI, its interface font, to
   Times New Roman; the script installs [Selawik](https://github.com/microsoft/Selawik),
   Microsoft's open-source Segoe UI stand-in, in its place, and turns on font
   smoothing. It also sets Content Manager's interface scale to your display's
   (see below).
9. If you have a local Pure 3.59 ZIP, installs it and selects a natural SDR
   preset with Pure LCS weather and the matching Pure post-processing filter.
10. If you have a local CMRT Essential or Complete HUD ZIP, installs its apps, flags and
    fuel indicator, and arranges a modern HUD for your resolution.
11. Points the Assetto Corsa desktop entry at Steam and registers it for
   `acmanager://` links.
12. Installs a small CSP background app for accurate MOZA rev lights, using
    the current car's actual RPM limit, including low-revving cars.
13. If you have a local LFM App installer, installs it in AC's Proton prefix,
    sets the game folder, and creates a launcher with Steam login callbacks.
14. If you have the local TheTenths 1.10.98 client, installs it in the same
    prefix so it can read AC's shared-memory telemetry, and creates a launcher.

Then start Assetto Corsa from Steam and it opens Content Manager.

## Options

| Option | |
|---|---|
| `--fresh` | Delete the Wine prefix and rebuild it. Game settings, Content Manager settings, presets and plugins are kept. Try this first if the game stops starting. |
| `--proton TAG` | GE-Proton release to use, such as `GE-Proton11-7`, or `latest`. Switching rebuilds the prefix, keeping settings. |
| `--scale N` | Content Manager's interface scale, such as `1.5`. Overrides whatever is set. |
| `--no-csp` | Skip Custom Shaders Patch. |
| `--pure ZIP` | Install your downloaded Pure 3.59 ZIP and apply the natural SDR preset once. |
| `--no-pure` | Skip automatic Pure detection and installation. |
| `--hud ZIP` | Install your downloaded CMRT Essential 1.0.13 or Complete 2.1.3 ZIP and arrange its apps once. |
| `--no-hud` | Skip automatic HUD detection and installation. |
| `--no-moza-telemetry` | Skip the CSP companion for accurate MOZA rev lights. |
| `--lfm EXE` | Install your downloaded LFM App Setup 1.1.13.exe. |
| `--no-lfm` | Skip automatic LFM detection and installation. |
| `--coach EXE` | Install your downloaded TheTenths client 1.10.98. |
| `--no-coach` | Skip automatic TheTenths detection and installation. |
| `--ac-path DIR` | Path to `steamapps/common/assettocorsa`, if it is not found. |

`CSP_VERSION=0.2.x` installs that Custom Shaders Patch version over the
installed one.

## MOZA rev lights

With CSP installed, the script adds `apps/lua/OmarchyMoza`, a background app
with no HUD window. It sends RPM, limiter and idle RPM from the player's car
to `127.0.0.1:9997` at up to 60 Hz. No telemetry leaves this computer.
Use an updated [Omarchy MOZA panel](https://github.com/crmne/omarchy-moza)
that supports this feed. The app starts with the next driving session.

There is no guessed 7,000 RPM ceiling or minimum engine-speed assumption.
Switching cars or changing the limiter takes effect with the next sample;
over-revving does not raise the limit. Replays and menus send zero RPM, and
the panel clears the lights when telemetry stops. Cars without a reported
limiter do not produce rev-light data. Existing threshold percentages and
colors remain configurable in the panel.

Reruns preserve identical files and back up replaced companion files under
`~/.local/share/assetto-corsa-setup/backups/moza-telemetry-*`. Pass
`--no-moza-telemetry` to skip installation; this does not remove an existing
installation. Remove `apps/lua/OmarchyMoza` to uninstall the companion.

## Pure 3.59

Pure is optional and must be obtained separately. This project does not
distribute Pure, purchase links, or download URLs. If exactly one
`Pure 3.59*.zip` is in your Downloads directory, the script detects it
automatically. Otherwise, select the original archive explicitly:

```sh
./assetto-corsa-setup --pure "$HOME/Downloads/Pure 3.59 Highres.zip"
```

Keep the ZIP intact, including its `Pure 3.59` folder. The installer verifies
the version, checks file integrity before changing the game, and requires
Custom Shaders Patch 0.2.3-preview211 or newer. The default CSP 0.2.11 meets
that requirement. Pure's Windows installer and uninstallers are not run.

The first installation enables Pure LCS, the static Pure controller (which
works with ordinary races and career events), and the matching `pure`
post-processing filter. It uses normal SDR output, exposure 1, 16x anisotropic
filtering, and disables depth of field. New Pure app settings use subtle
photo-realistic and soft-look values of 0.25, exposure uplift 0.10, and no
speed-related depth of field. Existing Pure app preferences are kept.

Resolution, refresh rate, wheel bindings, and other game preferences are
preserved. Later runs keep your graphics adjustments and skip copying the
same Pure archive again. To reinstall missing required components, run the
same command. Use `--no-pure` to skip this step entirely.

Replaced files and configuration are backed up under
`~/.local/share/assetto-corsa-setup/backups/pure-3.59-*` (or
`$XDG_DATA_HOME/assetto-corsa-setup/backups`). Each backup contains `game/`
and `cfg/` files to restore to the game folder and the Assetto Corsa Documents
configuration folder, respectively; `new-files.txt` records added files.
The installer prints the exact backup path. Highres needs about 5 GB for
the installed files plus temporary space for extraction and any backup.

## Modern HUD

Download the free [CMRT Essential HUD](https://www.overtake.gg/downloads/cmrt-essential-hud.69475/)
or purchase [CMRT Complete HUD](https://www.patreon.com/CMRT/shop/cmrt-complete-hud-563983)
from its author separately. The installer detects `CMRT_essential_hud*.zip` and
`CMRT_Complete_hud*.zip` in Downloads, ignoring filename case. If both editions
are present, Complete takes precedence. Multiple ZIPs of the selected edition
require an explicit path:

```sh
./assetto-corsa-setup --hud "$HOME/Downloads/CMRT_essential_hud_v1.0.13.zip"
# Or the purchased edition:
./assetto-corsa-setup --hud "$HOME/Downloads/CMRT_Complete_hud_v2.1.3.zip"
```

Essential 1.0.13 and Complete 2.1.3 are supported, with CSP 0.2.3 or newer. No CMRT files are bundled
or downloaded by this project. Both Pure and CMRT can be installed in the same
run; `--no-hud` skips HUD detection and installation.

On first setup, seven apps are enabled on the current AC desktop: gear/speed/
RPM/fuel, leaderboard, lap and sector timing, delta, circuit map, tyres with
pedal bars, and radar. Complete adds damage and MFD panels, with traction
control, brake bias and lights in a fresh MFD preset. The radar sits low and
centered near the bottom edge, with the MFD above it.
Positions and default app sizes adapt to the configured
resolution, leaving the road view clear. The overlapping stock equivalents
and stock leaderboard strip are hidden, and the virtual mirror is enabled.
Both AC's desktop settings and CSP's separate window-position cache are set.
CMRT settings, separate pedal graphs,
and clocks remain available from the in-game app sidebar.

The archive's matching flags and fuel indicator are installed too. Complete
also installs its starting-light replacement and hides the stock damage panel.
Switching editions backs up and removes the other app folder to avoid duplicate
HUDs. Saved preferences remain in place, and each edition's layout is retained.
Automatic detection never replaces installed Complete with Essential; use
`--hud` explicitly to switch back. That switch restores the starting lights and
damage-display setting this installer replaced, preserving later user edits.

Replaced
files and configuration are backed up under
`~/.local/share/assetto-corsa-setup/backups/cmrt-<edition>-<version>-*`, with the same
`game/`, `cfg/`, and `new-files.txt` structure as Pure backups. Saved CMRT
preferences and existing visible layouts are preserved; later runs keep your
positions and sizes. Default sizes are changed only in the local copy of
CMRT's settings file, and saved preferences take precedence.

## LFM App

Download LFM App separately from Low Fuel Motorsport. If exactly one
`LFM App Setup *.exe` is in Downloads, the script detects it. Version 1.1.13
is supported; select a specific installer with:

```sh
./assetto-corsa-setup --lfm "$HOME/Downloads/LFM App Setup 1.1.13.exe"
```

This needs `7z` and native `protontricks`. The installer checks the archive and
version, then extracts the unmodified application into AC's Proton prefix.
This bypasses the Windows installer's PowerShell process check, which fails
under Wine. No LFM files or account credentials are bundled with this project.

Open **LFM App** from your application launcher and sign in with Steam once.
The script registers `liverytool://` and `lfmhub://` browser callbacks and
sets AC's game folder. Choose your series and content in LFM itself; the setup
script does not register you for races or download every series' mods.

The app lives under `AppData/Local/Programs/LFM App` in AC's prefix, with its
profile in `AppData/Roaming/lfm-hub`. The launcher at `~/.local/bin/lfm-app`
uses that prefix with `--no-sandbox --disable-gpu`, needed for Electron to open
under this Proton configuration. These flags apply only to LFM App.
The desktop entry is `~/.local/share/applications/lfm-app.desktop`.

Reruns preserve login, preferences, and newer app versions installed by LFM's
updater. Close LFM before repairing its application files or using `--fresh`.
Prefix rebuilds keep both the app and its profile. Replaced files and settings
are backed up under `~/.local/share/assetto-corsa-setup/backups/lfm-*`.
`--no-lfm` skips installation without removing an existing app.

LFM races can be selected and registered on the website. Registering directly
inside the desktop app requires LFM+ (with an exception for LMU in app 1.1.13).
Those locks do not mean ordinary website race sign-up requires a subscription.
Follow the event's licence, content, and server-join
instructions. Start the game through Steam as usual. An app login test does
not establish that every game's multiplayer works under Proton.

## TheTenths Coach

Download the Windows client from [TheTenths](https://www.thetenths.com/client)
separately. The setup script detects a single `thetenths-client*.exe` in
Downloads, or accepts an explicit path:

```sh
./assetto-corsa-setup --coach "$HOME/Downloads/thetenths-client.exe"
```

This currently accepts the exact 1.10.98 build tested here, identified by
SHA-256. This identifies the tested file, not a publisher signature. Other
builds require validation; use `--no-coach` to continue setup without them.
No vendor executable is bundled or downloaded by this project.

Open **TheTenths Coach** from the application launcher, or run `thetenths`.
Click **Link this PC** and sign in or create an account in your browser.
Press **Start** if the client has not started automatically, then launch
Assetto Corsa normally. The launcher uses AC's Proton prefix, allowing the
coach to read the same Windows shared-memory telemetry as the game. No game
mod is needed for the coach. Its account link and settings save automatically.

The free client provides live voice coaching and lap telemetry. Generated
AI briefings/analysis use account credits; consult the vendor for current
credit terms. Valid laps and telemetry are sent to TheTenths, and lap pages
are public. This differs from the MOZA companion's local-only telemetry.

The app is installed in `AppData/Local/Programs/TheTenths`, with its account,
preferences and logs in `AppData/Roaming/TheTenths`, inside AC's prefix.
Reruns leave that profile unchanged. Automatic installation preserves a
different installed build, such as a vendor update; `--coach EXE` explicitly
replaces it after backing up the executable. Close the coach before replacing
it or rebuilding the prefix. `--fresh` preserves both directories.
The launcher does not capture application output or authentication data.
`--no-coach` skips installation without removing anything.

## Interface scale

On a HiDPI display Content Manager is tiny, because Wine draws X11 windows at
100%. The script sets Content Manager's own interface scale to your display's
scale, read from Hyprland's focused monitor (when XWayland apps are left
unscaled) or from `Xft.dpi`. It sets it once: if you change the scale in
Content Manager's settings later, running the script again keeps your choice.
Pass `--scale` to override it.

## Content Manager plugins

Content Manager downloads its plugins (7-Zip, CefSharp, VLC,
Magick.NET and others) only from inside the app. The script keeps a copy of
every plugin Content Manager has installed in
`~/.local/share/assetto-corsa-setup/plugins` and puts them back whenever the
prefix is rebuilt. On a machine that has never had them, Content Manager shows
its welcome screen once with everything filled in: click **Install recommended
plugins**, then **OK**, and run the script again to keep them.

Do not create Content Manager's Start Menu shortcut; under Wine it makes
Content Manager crash on startup. The script removes it if it finds one.

## Tested with

Arch Linux (Omarchy), native Steam, NVIDIA RTX 3090, GE-Proton9-20 and
GE-Proton11-7, Content Manager 0.8.2895, Custom Shaders Patch 0.2.11: from a
fresh install to a quick race and a clean exit.

Pure 3.59 Highres with Pure LCS and the SDR preset was also checked in a
running race on this setup. HDR output and other Pure versions are not tested.
CMRT Essential HUD 1.0.13 and Complete 2.1.3 were checked in a 3840×2160 race,
including readable text, live gauges, and matching flag/fuel assets. Complete's
radar and damage display were checked with nearby cars. Other
resolutions have automated layout checks but have not been checked in-game.

LFM App 1.1.13 was opened under GE-Proton11-7 and its Steam sign-in/browser
callback was verified. Series content sync and joining an LFM server have
not yet been tested. This does not imply official Linux support from LFM.

TheTenths 1.10.98 was opened and linked under GE-Proton11-7. It received live
Mazda MX-5 Cup telemetry at Mugello and generated corner-specific coaching
from a downloaded reference lap. Other games and prefixes have not been
tested with this launcher.

## Development checks

```sh
bash -n assetto-corsa-setup
python3 -m unittest discover -s tests -v
```

The Pure and HUD regression tests use synthetic ZIP files and require no mod
assets or game installation. They cover installation, backups, preserving
settings and layouts, repeat runs, unsupported versions, and malformed archives.
LFM tests use synthetic 7z/ASAR packages and require `7z`. They cover preserving
login and preferences, prefix rebuilds, safe callbacks, repairs, and avoiding
downgrades, without running vendor code or contacting LFM.

## Requirements

`curl`, `tar`, `unzip`, `python3`, and `protontricks` for the fonts.

## Credits

Based on [sihawido/assettocorsa-linux-setup](https://github.com/sihawido/assettocorsa-linux-setup),
and licensed under the GPL-2.0 like it.
