# Backing up Joplin

Ways to back up your Joplin data depending on how you run it.

---

## When Joplin runs on Fly.io (with this bot)

Your Joplin profile lives in the Fly volume at **`/app/data/joplin`**. Two practical options:

### Option 1: Export notes as Markdown (recommended)

The container has the Joplin CLI. Export all notes to a folder, then download it.

**1. SSH into the app and export:**

```bash
# Create a backup dir and export (format: md or raw)
fly ssh console -C "mkdir -p /tmp/joplin_backup && joplin --profile /app/data/joplin export --format md /tmp/joplin_backup"
```

**2. Copy the backup out** (e.g. with `fly ssh sftp` or by running a one-off machine that tars and serves it). Example using `scp`-style copy via `fly ssh sftp`:

```bash
fly ssh sftp
# Then in the sftp prompt:
# get -r /tmp/joplin_backup ./joplin_backup
# quit
```

If `fly ssh sftp` doesn’t support recursive get easily, use a one-off with a shared volume or run the export to a path under `/app/data` (so it’s on the persistent volume), then use any file-sync or download method you prefer for that volume.

**3. Or: run export into the persistent volume and backup the volume**

```bash
fly ssh console -C "joplin --profile /app/data/joplin export --format md /app/data/joplin_exports/$(date +%Y%m%d)"
```

Then back up the Fly volume using Fly’s volume snapshot/backup (see [Fly.io Volumes](https://fly.io/docs/reference/volumes/)). Exports will be under `/app/data/joplin_exports/`.

### Option 2: Copy the Joplin profile (full backup)

The profile directory contains the SQLite database and resource files. Backing it up gives you a full restore point.

**1. From your machine, stream a tar of the profile to disk:**

```bash
fly ssh console -C "tar -czf - -C /app/data joplin" > joplin_backup_$(date +%Y%m%d).tar.gz
```

**2. Restore** by uploading the tarball and extracting into `/app/data/joplin` (and restarting the app so Joplin uses the restored profile). Stop the app before overwriting the profile.

---

## When you use Joplin Desktop (or any local install)

- **Export:** In the app: **File → Export** and choose format (e.g. **JEX** for full backup, or **Markdown** for readable files).
- **Profile folder:** Copy the profile directory so you have the database and attachments. Locations:
  - **macOS:** `~/Library/Application Support/Joplin/`
  - **Linux:** `~/.config/joplin-desktop/` or `~/.config/joplin/`
  - **Windows:** `%USERPROFILE%\.config\joplin-desktop\`
- **Sync:** If you use Joplin Cloud, Dropbox, or another sync target, the synced copy is an extra backup (not a replacement for periodic exports or profile copies).

---

## Quick reference (Fly.io)

| Goal              | Command |
|-------------------|--------|
| Export to Markdown | `fly ssh console -C "joplin --profile /app/data/joplin export --format md /tmp/joplin_backup"` |
| Full profile tar   | `fly ssh console -C "tar -czf - -C /app/data joplin" > joplin_backup_$(date +%Y%m%d).tar.gz` |
| Export into volume | `fly ssh console -C "mkdir -p /app/data/joplin_exports && joplin --profile /app/data/joplin export --format md /app/data/joplin_exports/$(date +%Y%m%d)"` |

Do a backup before big changes (e.g. before `/reorg_init` or bulk moves).
