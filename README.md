<p align="center">
  <h1 align="center">zen-sync</h1>
  <p align="center">Sync Zen Browser spaces, tabs & sessions across devices via SSH</p>
</p>

<p align="center">
  <a href="#install">Install</a> &bull;
  <a href="#usage">Usage</a> &bull;
  <a href="#how-it-works">How it works</a> &bull;
  <a href="#limitations">Limitations</a> &bull;
  <a href="LICENSE">License</a>
</p>

---

> **Linux only** — tested on Arch Linux with Wayland. May work on other distros but is not tested.

Zen Browser doesn't sync spaces or tabs across devices yet. **zen-sync** fills that gap. Push your entire browsing session from one machine to another in seconds.

Built because I kept switching between my desktop and laptop and wanted my spaces and tabs to follow me. Firefox Sync covers bookmarks and passwords, but not Zen's workspaces. This tool transfers the raw session files over SSH, similar to [sharing a profile on a dual-boot system](https://github.com/zen-browser/desktop/discussions/2400).

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/enisbudancamanak/zen-sync/main/install.sh | bash
```

Then run the setup wizard:

```bash
zen-sync init
```

### Requirements

- Linux (tested on Arch Linux with Wayland/Hyprland)
- Zen Browser (same version on both devices)
- SSH access between devices (ideally with key-based auth via `ssh-copy-id`)
- `python3` + `liblz4` (for `merge` and `status`)

## Usage

> **Zen must be closed on the target device before syncing.**
> The target will overwrite synced files if Zen is still open. Use `--restart` to handle this automatically.
> Zen on the source side can stay open, session files are auto-saved every ~15 seconds.

| Situation | Command |
|-----------|---------|
| Switch to other device | `zen-sync push --restart` |
| Come back from other device | `zen-sync pull --restart` |
| Used both, want to combine | `zen-sync merge --restart` |
| Just check what's where | `zen-sync status` |

### push / pull

Transfers your complete session (spaces, tabs, preferences) to the other device. The target session is fully replaced.

```bash
zen-sync push --restart    # Close Zen on remote, sync, reopen
zen-sync pull --restart    # Close Zen locally, sync, reopen
```

Without `--restart`, close Zen on the target device manually first.

### merge

Adds tabs from the remote device into your local session without removing existing tabs. Deduplicated by URL + workspace. A backup is created automatically before each merge.

```bash
zen-sync merge --restart
```

> Merge is one-directional (remote → local). To get everything on both devices, run `merge` then `push --restart`.

## How it works

Push/pull copies only the essential session files (~10 seconds over LAN):

- `zen-sessions.jsonlz4` — space definitions & tab assignments
- `sessionstore-backups/recovery.jsonlz4` — active session with all open tabs
- `prefs.js` — active workspace & preferences
- `containers.json` — container tab config

Merge reads both `zen-sessions.jsonlz4` files, combines missing spaces and tabs, and updates the sessionstore so Zen loads them on startup.

## Limitations

> Built for a specific setup, may need adjustments for yours.

- **Linux only.** macOS/Windows store Zen profiles in different locations
- **Wayland.** `--restart` reopen uses `WAYLAND_DISPLAY=wayland-1`. X11 or other compositors may need adjustment
- **Single remote.** One remote device per config
- **Push/pull overwrites.** Last push/pull wins, use `merge` to combine
- **Same Zen version.** Both devices should run the same version
- **Does not sync** bookmarks, passwords, history, extensions, cookies (use Firefox Sync for those)

Config: `~/.config/zen-sync/config`. Profile paths are auto-detected during `zen-sync init`.

## License

[MIT](LICENSE)
