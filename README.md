# assetto-corsa-setup

One command that makes Assetto Corsa on Steam playable on Linux, with
[Content Manager](https://acstuff.club/app/) and
[Custom Shaders Patch](https://acstuff.club/patch/) installed and configured.
It asks no questions, and Content Manager opens ready to race: game folder set,
Steam profile picked, plugins in place.

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
8. Points the Assetto Corsa desktop entry at Steam and registers it for
   `acmanager://` links.

Then start Assetto Corsa from Steam and it opens Content Manager.

## Options

| Option | |
|---|---|
| `--fresh` | Delete the Wine prefix and rebuild it. Game settings, Content Manager settings, presets and plugins are kept. Try this first if the game stops starting. |
| `--proton TAG` | GE-Proton release to use, such as `GE-Proton11-7`, or `latest`. Switching rebuilds the prefix, keeping settings. |
| `--no-csp` | Skip Custom Shaders Patch. |
| `--ac-path DIR` | Path to `steamapps/common/assettocorsa`, if it is not found. |

`CSP_VERSION=0.2.x` installs that Custom Shaders Patch version over the
installed one.

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

## Requirements

`curl`, `tar`, `unzip`, `python3`, and `protontricks` for the fonts.

## Credits

Based on [sihawido/assettocorsa-linux-setup](https://github.com/sihawido/assettocorsa-linux-setup),
and licensed under the GPL-2.0 like it.
