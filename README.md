# Writy

Writy is a lightweight Windows notes app with rich-text formatting, light and dark themes, and a sidebar for saved notes.

![Writy logo](writy.svg)

## Install on Windows

Download and run the [Writy Windows installer](https://github.com/GauravDahalCodes/writy-/releases/latest/download/WritySetup.exe) from the latest GitHub Release. The per-user installer creates a Start Menu shortcut, so you can search for **Writy** after installation. No administrator access is required.

The app's download page is `index.html`. Enable GitHub Pages for the repository root, then attach `WritySetup.exe` to a GitHub Release. The page links to the latest release automatically.

## Features

- Save and switch notes in one window.
- Rich text formatting, including keyboard shortcuts.
- Light and dark themes.
- Note deletion and current-note highlighting.
- Notes stored in per-user app data and available again after updates.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| Ctrl+B | Bold |
| Ctrl+I | Italic |
| Ctrl+U | Underline |

## Build from source

Use Python 3.11 on Windows. Install the Python dependencies and Inno Setup 6, then run these commands from the project folder in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

$root = (Get-Location).Path
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name Writy --icon "$root\writy.ico" --add-data "$root\writy.svg;." --distpath "$root\build\release-dist" --workpath "$root\build\pyinstaller" --specpath "$root\build\spec" "$root\main.py"

& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" .\Writy.iss
```

The installer is written to `dist\WritySetup.exe`. The SVG is used by the app and download page; the matching ICO supplies the Windows executable and installer icons.

## Publish with GitHub Pages

1. Push the repository to GitHub.
2. Build `dist\WritySetup.exe` and create a GitHub Release with that file attached.
3. In **Settings > Pages**, publish from the repository's default branch and the root folder.

The download button on `index.html` resolves the repository from the standard `username.github.io/repository` Pages address and downloads `WritySetup.exe` from the latest release.
