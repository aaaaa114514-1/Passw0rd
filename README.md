# P@ssw0rd

A Windows-local password manager with an encrypted vault, a modern Qt desktop interface, light/dark themes, customizable backgrounds, and Chinese/English UI support.

[中文文档](README.zh-CN.md)

## Features

- Encrypted local vault protected by a master password.
- First-run vault creation and master-password unlock on every later launch.
- Unlimited unlock attempts; intentionally no password-reset or recovery flow.
- Create, view, edit, search, filter, sort, and delete entries.
- Store an account name, username, phone number, email address, website, password, category, tags, and notes.
- One-click copy for username, phone number, email, website, and password.
- Category filtering, including an `Uncategorized` filter for entries without a category.
- Clickable table headers: first click sorts ascending; a second click sorts descending.
- Light and dark modes, custom background image support, and Chinese/English switching.
- Adjustable account-list/detail split view and animated top notifications.
- User-supplied application icon in the Windows executable, window, and vault title area.

## Security Model

P@ssw0rd is designed for a local Windows vault. It does not provide cloud sync, a remote service, browser integration, or password recovery.

- The master password is never stored in plaintext.
- A 32-byte random salt and PBKDF2-HMAC-SHA256 with 600,000 iterations derive 64 bytes of key material.
- One derived key authenticates the master password with HMAC-SHA256.
- The other derived key is used for AES-256-GCM encryption.
- Each saved entry is serialized into one encrypted payload with a fresh random 12-byte nonce.
- Sensitive entry content, including name, identity fields, URL, password, category, tags, and notes, is encrypted at rest.
- The SQLite database stores encrypted blobs and timestamps; it does not store plaintext entry fields.
- Changing the master password verifies the current password and re-encrypts every entry with newly derived key material.
- The session key and SQLite connection are released when the vault is locked or the application exits.

> **Important:** There is no master-password recovery mechanism. If the master password is lost, existing vault data cannot be decrypted. Keep a secure backup of the application data directory if the vault is important.

## Data Location

By default, application data is stored under:

```text
%LocalAppData%\P@ssw0rd
```

The directory contains:

- `vault.db`: SQLite database containing encrypted entry payloads.
- `vault_config.json`: salt, PBKDF2 parameters, and password-verification material. It does not contain the master password.
- `ui_preferences.json`: non-sensitive UI preferences such as theme, language, and the path to the selected background image.

Do not commit these files to source control. They are ignored by `.gitignore`.

## Requirements

### Run the packaged application

- Windows 10 or later, 64-bit.
- No separately installed Python or PySide6 runtime is required for the published single-file executable.

### Develop from source

- Windows 10 or later.
- Python 3.12 recommended.
- Git.

## Quick Start

### Use a published executable

Run the built executable after publishing:

```text
publish\P@ssw0rd.exe
```

On the first launch, enter and confirm a non-empty master password. On subsequent launches, enter that master password to unlock the vault.

### Run from source

Create an isolated virtual environment in the repository:

```powershell
python -m venv .venv
python -m pip --python .venv install -r requirements.txt
.\.venv\Scripts\python.exe src\qt_app.py
```

The project keeps its dependencies inside `.venv`; it does not require a system-wide Python package installation.

## Test

Run the test suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .\test-tmp
```

The focused tests cover vault initialization, incorrect-password rejection, encrypted-at-rest entry payloads, entry persistence, master-password rotation, validation, and UI preference persistence.

## Build a Single-File Windows Executable

The release executable embeds the supplied Windows icon and the in-app PNG title icon.

```powershell
.\.venv\Scripts\pyinstaller.exe `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name "P@ssw0rd" `
  --icon "D:\desktop\Code\aaaaa\dsh\P@ssw0rd\icon\favicon.ico" `
  --add-data "D:\desktop\Code\aaaaa\dsh\P@ssw0rd\icon;icon" `
  --distpath publish `
  --workpath build `
  --specpath build `
  src\qt_app.py
```

The output is `publish\P@ssw0rd.exe`. `build/`, `publish/`, and generated PyInstaller spec files are intentionally excluded from Git.

If the repository is cloned to a different directory, update the two absolute icon paths in the command or replace them with equivalent absolute paths for that clone.

## Interface Notes

- Use the sun/moon icon in the title bar to switch between light and dark themes.
- Open **Settings** to change appearance, language, background image, or master password.
- Select a row to reveal account details. The list is single-row selection only.
- Click a table header to sort its visible filtered records.
- Drag the center divider to adjust list and detail panel widths.
- Copy actions display a top-centered, timed confirmation notification.

## Project Layout

```text
.
├── icon/                  # Application ICO and in-app PNG assets
├── src/
│   ├── qt_app.py          # PySide6 desktop UI and packaging resource handling
│   ├── vault.py           # Encrypted SQLite vault and master-password services
│   ├── preferences.py     # Non-sensitive UI preference persistence
│   └── app.py             # Earlier Tk interface retained as historical source
├── tests/
│   ├── test_vault.py      # Vault behavior and encryption tests
│   └── test_preferences.py
├── requirements.txt
├── pyproject.toml
├── WORKLOG.md             # Chronological development log
└── README.zh-CN.md
```

## Scope and Limitations

This project is intended for local Windows use. Before using it as the only copy of important credentials, evaluate whether its local-only design, threat model, and recovery limitations meet your needs. In particular:

- No synchronization, sharing, or multi-device access is implemented.
- No automatic clipboard clearing is implemented.
- No password generator is implemented yet.
- No import/export workflow is implemented.
- The vault is only as secure as the master password and the security of the Windows account/device hosting it.

## License

No license has been selected yet. Add an explicit license before redistributing the project.
