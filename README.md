<p align="center">
  <h1 align="center">zen-sync</h1>
  <p align="center">Fork of enisbudancamanak/zen-sync, quickly vibecoded to work on macOS and Windows too</p>
  <p align="center">
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
    <img src="https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-yellow.svg" alt="Platform: Linux, macOS, Windows">
    <img src="https://img.shields.io/badge/Zen_Browser-purple.svg" alt="Zen Browser">
  </p>
</p>

<p align="center">
  <a href="#install">Install</a> &bull;
  <a href="#usage">Usage</a> &bull;
  <a href="#sync-modes">Sync modes</a> &bull;
  <a href="#how-it-works">How it works</a> &bull;
  <a href="#limitations">Limitations</a> &bull;
  <a href="LICENSE">License</a>
</p>

---

> Forked from enisbudancamanak/zen-sync and quickly adapted for cross-platform use (Linux, macOS, Windows).

Zen Browser doesn't sync spaces or tabs across devices yet. **zen-sync** fills that gap. Push your entire browsing session from one machine to another in seconds.

Built because I kept switching between my desktop and laptop and wanted my spaces and tabs to follow me. Firefox Sync covers bookmarks and passwords, but not Zen's workspaces. This tool transfers the raw session files, similar to [sharing a profile on a dual-boot system](https://github.com/zen-browser/desktop/discussions/2400).

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/TheBeaconCrafter/zen-sync/main/install.sh | bash
```

Then run the setup wizard:

```bash
zen-sync init
```

## Build and run (macOS / Windows)

There is no compile/build step. `zen-sync` is a Bash script plus Python helpers.

### macOS

1. Install dependencies:
  - Bash
  - Python 3
  - `age` (R2 mode only)
  - `liblz4` (for `merge` and `status`)
2. Run directly from repo:

```bash
chmod +x ./zen-sync
./zen-sync init
```

### Windows

`./zen-sync` is not a native PowerShell executable, so PowerShell may try to open it like a file.

Use one of these:

1. Git Bash:

```bash
./zen-sync init
```

2. PowerShell + Bash:

```powershell
bash .\zen-sync init
```

3. PowerShell wrapper in this repo:

```powershell
.\zen-sync.cmd init
```

If you plan to use SSH mode on Windows, ensure OpenSSH client/server are installed and reachable from your shell.

### Requirements

- Linux, macOS, or Windows
- Zen Browser (same version on both devices)
- `python3` + `liblz4` (for `merge` and `status`)
- **SSH mode.** SSH access between devices (ideally with key-based auth via `ssh-copy-id`)
- **R2 mode.** Cloudflare R2 bucket + `age` for encryption

### Install dependencies (macOS / Windows)

`age` is only required for **R2 mode**. If you only use **SSH mode**, you can skip `age`.

- macOS (Homebrew): `brew install age`
- Windows (winget): `winget install --id FiloSottile.age`

If your package manager does not have `age`, install it from the official releases and ensure the `age` command is available in your shell PATH.

## Sync modes

During `zen-sync init`, you choose how devices communicate:

| Mode           | How it works                                | Best for                                  |
| -------------- | ------------------------------------------- | ----------------------------------------- |
| **SSH**        | Direct device-to-device transfer            | Same network, both devices online         |
| **R2**         | Encrypted upload/download via Cloudflare R2 | Different networks, async sync            |
| **StorageBox** | Encrypted archive over WebDAV               | Hetzner Storage Box / user+password setup |

**SSH** is the simplest. Push and pull files directly between machines. Both devices need to be online and reachable.

**R2** stores your session encrypted (using [age](https://github.com/FiloSottile/age)) in a Cloudflare R2 bucket. Push from one device, pull from another whenever you want. Devices don't need to be online at the same time. Free tier (10GB) is more than enough.

**StorageBox** stores the same encrypted archive via WebDAV (username + password), intended for Hetzner Storage Box style setups.

<details>
<summary><strong>📦 R2 setup guide</strong></summary>
<br>

1. Create a free [Cloudflare](https://dash.cloudflare.com) account
2. Go to **R2 Object Storage** and create a bucket (e.g. `zen-sync`)
3. Go to **R2 > Manage R2 API Tokens > Create API Token** with Read & Write permissions
4. Note your **Account ID** (visible in the dashboard URL), **Access Key ID**, and **Secret Access Key**
5. Install `age` (see "Install dependencies (macOS / Windows)" above)
6. Run `zen-sync init`, select R2 mode, and enter your credentials
7. On the second device, run `zen-sync init` with the same credentials and copy over the age key file

</details>

<details>
<summary><strong>🗄️ StorageBox setup guide (WebDAV)</strong></summary>
<br>

1. Ensure your storage provider supports WebDAV (Hetzner Storage Box does)
2. Run `zen-sync init`, select `Storage Box`
3. Enter:
  - WebDAV URL (example: `https://u12345.your-storagebox.de`)
  - Username
  - Password
  - Remote folder path (default: `zen-sync`)
4. Use the same credentials and age passphrase/key on your other device

</details>

<details>
<summary><strong>🔗 SSH setup guide</strong></summary>
<br>

1. Make sure both devices can reach each other via SSH
2. Set up key-based auth for passwordless access: `ssh-copy-id user@other-device`
3. Run `zen-sync init` on both devices, select SSH mode

</details>

## Usage

> **Before pushing**, close Zen on the other device (or use `--restart`).
> **Before pulling**, close Zen on your device (or use `--restart`).
> Zen writes session files when it closes. If it's still open, it will overwrite your sync.

| Situation                   | Command                    |
| --------------------------- | -------------------------- |
| Switch to other device      | `zen-sync push --restart`  |
| Come back from other device | `zen-sync pull --restart`  |
| Used both, want to combine  | `zen-sync merge --restart` |
| Just check what's where     | `zen-sync status`          |

### push / pull

Transfers your complete session (spaces, tabs, preferences). The target session is fully replaced.

```bash
zen-sync push --restart    # Close Zen on target, sync, reopen
zen-sync pull --restart    # Close Zen locally, sync, reopen
```

Without `--restart`, close Zen on the target device manually first.

> In R2/StorageBox modes, `--restart` only applies locally. There is no remote device to close/reopen.

### merge

Adds tabs from the remote into your local session without removing existing tabs. Deduplicated by URL + workspace. A backup is created automatically before each merge.

```bash
zen-sync merge --restart
```

> Merge is one-directional (remote → local). To get everything on both devices, run `merge` then `push --restart`.

## How it works

Push/pull copies only the essential session files (~10 seconds over LAN, ~15 seconds via R2):

- `zen-sessions.jsonlz4` — space definitions & tab assignments
- `sessionstore-backups/recovery.jsonlz4` — active session with all open tabs
- `prefs.js` — active workspace & preferences
- `containers.json` — container tab config

In R2 mode, files are packed into a tar.gz archive, encrypted with age, and uploaded to your R2 bucket.

Merge reads both `zen-sessions.jsonlz4` files, combines missing spaces and tabs, and updates the sessionstore so Zen loads them on startup.

## What is synced

| Synced                 | Not synced (use Firefox Sync) |
| ---------------------- | ----------------------------- |
| Spaces / Workspaces    | Bookmarks                     |
| Open tabs & tab groups | Passwords                     |
| Pinned tabs            | Browsing history              |
| Active workspace       | Extensions & their data       |
| Container tabs         | Cookies & site storage        |
| Tab folders            | Cached data                   |

## Limitations

> Built for a specific setup, may need adjustments for yours.

- **Cross-platform best effort.** Different Zen install layouts can still require manual profile selection during init
- **Restart behavior differs by OS.** `--restart` uses per-OS launch/close commands and can vary by shell/session manager
- **Single remote.** One remote device per config (SSH mode)
- **Push/pull overwrites.** Last push/pull wins, use `merge` to combine
- **Same Zen version.** Both devices should run the same version

Config: `~/.config/zen-sync/config`. Profile paths are auto-detected during `zen-sync init`.

## License

[MIT](LICENSE)
