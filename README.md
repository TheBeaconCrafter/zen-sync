<p align="center">
  <h1 align="center">zen-sync</h1>
  <p align="center">Sync Zen Browser spaces, tabs & sessions across devices via SSH</p>
</p>

<p align="center">
  <a href="#install">Install</a> &bull;
  <a href="#when-to-use-what">When to use what</a> &bull;
  <a href="#how-it-works">How it works</a> &bull;
  <a href="#limitations">Limitations</a> &bull;
  <a href="LICENSE">License</a>
</p>

---

> **Linux only** — tested on Arch Linux with Wayland. May work on other distros but is not tested.

Zen Browser doesn't sync spaces or tabs across devices yet. **zen-sync** fills that gap — push your entire browsing session from one machine to another in seconds.

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

## When to use what

### Switching devices

You're done working on one machine and want to continue on the other.

```bash
# On the machine you're leaving:
zen-sync push --restart
```

Your spaces, tabs, and session are now on the other device. This is the most common use case.

### Coming back

You worked on the laptop and now you're back at the desktop.

```bash
# On the desktop:
zen-sync pull --restart
```

Pulls the laptop session to your desktop. Same as push but in reverse.

### You forgot to sync and used both devices

You opened new tabs on both machines. A regular push/pull would overwrite one side.

```bash
# On the machine you want to keep everything:
zen-sync merge --restart
```

This adds tabs from the remote device into your local session without removing your existing tabs. Tabs are deduplicated by URL + workspace.

> **Note:** Merge is one-directional (remote → local). If you want both devices to have everything, run `merge` and then `push --restart`.

### Quick overview

| Situation | Command |
|-----------|---------|
| Switch to other device | `zen-sync push --restart` |
| Come back from other device | `zen-sync pull --restart` |
| Used both, want to combine | `zen-sync merge --restart` |
| Just check what's where | `zen-sync status` |

### All commands

```bash
zen-sync push              # Push session to remote (close Zen on remote first)
zen-sync pull              # Pull session from remote (close Zen locally first)
zen-sync merge             # Merge remote tabs into local session
zen-sync push --restart    # Auto-close Zen on remote, sync, reopen
zen-sync pull --restart    # Auto-close Zen locally, sync, reopen
zen-sync merge --restart   # Auto-close Zen locally, merge, reopen
zen-sync status            # Compare spaces on both devices
zen-sync init              # Setup wizard
```

## How it works

### Push / Pull

Copies only the files that matter:

| File | What it contains |
|------|-----------------|
| `zen-sessions.jsonlz4` | Space definitions & tab-to-space assignments |
| `sessionstore-backups/recovery.jsonlz4` | Active session with all open tabs |
| `sessionstore-backups/recovery.baklz4` | Session backup |
| `sessionstore-backups/previous.jsonlz4` | Previous session |
| `prefs.js` | Active workspace & preferences |
| `containers.json` | Container tab configuration |

This takes ~10 seconds over a local network. The target session is fully replaced.

### Merge

Reads both local and remote `zen-sessions.jsonlz4`, then:

1. Adds missing spaces (by UUID)
2. Adds missing tabs (deduplicated by URL + workspace)
3. Adds missing tab folders and groups
4. Updates the sessionstore so Zen loads the new tabs on startup

A backup is created before every merge (`zen-sessions.jsonlz4.merge-backup-*`).

## Limitations

> This tool was built for a specific setup and may need adjustments for yours.

**Tested environment:**
- Arch Linux on both devices (desktop + laptop)
- Wayland (Hyprland) — the `--restart` flag uses `WAYLAND_DISPLAY=wayland-1`
- Local network (SSH over LAN)

**Known limitations:**
- **Linux only** — macOS and Windows store Zen profiles in different locations
- **Wayland assumption** — `--restart` reopen uses hardcoded `WAYLAND_DISPLAY=wayland-1`. X11 or different compositors may need adjustment
- **Single remote** — one remote device per config
- **Push/pull overwrites** — last push/pull wins. Use `merge` if you need to combine
- **Profile paths are fixed after init** — if Zen creates a new profile, re-run `zen-sync init`

**What is NOT synced (use Firefox Sync for these):**
- Bookmarks, passwords, history
- Extensions and their data
- Cookies and site storage

## Good to know

- Config lives in `~/.config/zen-sync/config`
- Profile paths are auto-detected during `zen-sync init`
- Both devices should run the **same Zen version** to avoid compatibility issues
- Zen stores spaces in `zen-sessions.jsonlz4` (Mozilla LZ4 compressed JSON) and tabs in the sessionstore — both need to be in sync

## Background

Zen Browser (based on Firefox) doesn't offer cross-device sync for its custom features like spaces and workspaces. Firefox Sync handles bookmarks, passwords, and history, but not Zen-specific data.

This tool works similarly to [sharing a profile folder on a dual-boot system](https://github.com/zen-browser/desktop/discussions/2400) — transferring the raw session files between machines.

## License

[MIT](LICENSE)
