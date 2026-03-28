# zen-sync

Sync Zen Browser spaces, tabs, and sessions across devices via SSH.

## Quick Start

```bash
# Install
git clone https://github.com/officiallyeno/zen-sync
sudo ln -s "$(pwd)/zen-sync/zen-sync" /usr/local/bin/zen-sync

# Setup
zen-sync init

# Push your session to another device
zen-sync push

# Pull session from another device
zen-sync pull
```

## Requirements

- Zen Browser (same version on both devices)
- SSH access between devices
- Python 3 with system `liblz4` (for `zen-sync status`)

## Commands

| Command | Description |
|---------|-------------|
| `zen-sync init` | Interactive setup - detects profiles automatically |
| `zen-sync push` | Push local spaces & tabs to remote (light, ~10s) |
| `zen-sync pull` | Pull remote spaces & tabs to local (light, ~10s) |
| `zen-sync push --full` | Full profile sync via rsync (slower, more complete) |
| `zen-sync pull --full` | Full profile pull via rsync |
| `zen-sync status` | Compare spaces on both devices |

## How it works

### Light sync (default)
Copies only the essential session files:
- `zen-sessions.jsonlz4` — Space definitions and tab assignments
- `sessionstore-backups/recovery.jsonlz4` — Active session with all tabs
- `sessionstore-backups/recovery.baklz4` — Session backup
- `sessionstore-backups/previous.jsonlz4` — Previous session
- `prefs.js` — Active workspace and preferences
- `containers.json` — Container tab configuration

### Full sync (`--full`)
Uses `rsync` to sync the entire profile directory, excluding caches. Useful for first-time setup or when light sync misses something.

## Important

- **Close Zen Browser** on the target device before syncing
- Both devices should run the **same Zen version** to avoid compatibility issues
- Config is stored in `~/.config/zen-sync/config`

## How Zen stores data

Zen Browser stores workspaces/spaces in `zen-sessions.jsonlz4` (Mozilla's LZ4 compressed JSON). The actual tab session lives in `sessionstore-backups/recovery.jsonlz4`. Both files need to be in sync for spaces and tabs to transfer correctly.

Unlike Firefox Sync, this tool transfers the raw profile data, similar to sharing a profile folder across dual-boot systems.

## License

MIT
