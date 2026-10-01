name: disk-io-attribution
description: Use when you need to find what service, process, or container read or wrote a large amount of data to a server's disk drive — attributing a claimed data transfer (e.g. "230 GB today") to the responsible actor.

---

# Disk I/O Attribution

Figure out what touched a server's disk today and how much, then match it to a specific service or container.

## Procedure

### 1. Check for a local mount first

The target drive may already be mounted locally (CIFS/NFS/SSHFS). If it is, you can inspect file timestamps directly without SSH.

```bash
lsblk -o NAME,SIZE,MOUNTPOINT,TRAN,ROTA | grep -v loop
mount | grep -E 'music|media|tv|movies|nas'
find /mnt -maxdepth 1 -type d -ls
```

**Pitfall:** A local mount may be a *different share* than the one you're investigating. `/mnt/agent-nas` here is `//{LAN_IP}/nas` — not `/mnt/music`. Confirm the mount maps to the right physical drive before attributing activity to it.

### 2. SSH to the server

Use the `~/.ssh/config` host alias if one exists — it encodes the right key and user.

```bash
# Prefer the config alias over raw IP + manual key selection
ssh main-server 'echo ok'

# If no alias, try keys from ~/.ssh/config or ~/.ssh/ in order
ssh -i ~/.ssh/{SSH_KEY} {USER}@{LAN_IP} 'echo ok'
```

**Pitfall:** `ssh-add -l` returning "The agent has no identities" does not mean keys are missing — it means the agent is empty. The keys exist on disk; `ssh -i` or the config `IdentityFile` will use them directly. Don't waste rounds trying to `ssh-add` a non-interactive agent.

### 3. Map disks to mounts

```bash
# Physical layout
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,TRAN,ROTA

# Filesystem usage (shows which mounts are actually active)
df -h | grep -E '/mnt/|/media/'

# fstab — what *should* be mounted
cat /etc/fstab | grep -v '^#' | grep -v '^$'
```

### 4. Get boot time — this defines the diskstats window

```bash
who -b
# or
cat /proc/uptime | awk '{print $1/86400 " days"; print $1/3600 " hours"}'
```

**Pitfall:** If the server rebooted mid-day, `/proc/diskstats` since boot will *not* cover the full day. A claimed "230 GB today" that exceeds the since-boot total means either the activity was before boot, or the estimate is wrong. Don't try to close the gap — report the gap.

### 5. Read diskstats for the target drive

```bash
# Single snapshot — fields are cumulative since boot
grep '^ *8' /proc/diskstats | grep -E 'sdc|sdd|sdb|vd'
```

Field layout (space-separated): `major minor name reads_completed reads_merged sectors_read time_reading writes_completed writes_merged sectors_written time_writing ios_in_progress time_doing_ios weighted_time`.

**The two numbers that matter:**
- Field 3 (index 2): sectors *read*
- Field 7 (index 6): sectors *written*

**Sector math:** `sectors × 512 bytes = bytes`. Convert: `sectors × 512 / 1024^3 = GB`.

### 6. Take a delta to get a rate

Wait 30–60 seconds, read diskstats again, subtract. This gives you a live read/write rate in GB/s — useful for confirming active vs. idle.

```bash
# Snapshot 1
grep 'sdc ' /proc/diskstats > /tmp/disk_prev.txt
sleep 60
# Snapshot 2
grep 'sdc ' /proc/diskstats > /tmp/disk_curr.txt
# Delta (Python)
python3 -c "
import re
def read(f):
    with open(f) as fh:
        for line in fh:
            if 'sdc ' in line:
                p = line.split()
                return int(p[2]), int(p[6])  # sectors_read, sectors_written
pr, pw = read('/tmp/disk_prev.txt')
cr, cw = read('/tmp/disk_curr.txt')
print(f'Read delta:  {(cr-pr)*512/1024**3:.2f} GB in 60s = {(cr-pr)*512/1024**3/60:.2f} GB/s')
print(f'Write delta: {(cw-pw)*512/1024**3:.2f} GB in 60s')
"
```

**Pitfall:** `iostat -dx sdc 1 2` gives per-second rates directly and is faster than the manual delta — prefer it when available. But it must be installed (`sysstat` package); if missing, fall back to the diskstats-delta above.

### 7. List containers that could be the actor

```bash
docker ps -a --format '{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}'
```

**Filter for likely candidates:**
```bash
docker ps -a --format '{{.ID}}\t{{.Names}}\t{{.Image}}' | grep -iE 'torrent|sab|nzb|couch|sonarr|radarr|plex|jellyfin|beets|syncthing|transmission|deluge|downloader|arr$'
```

### 8. Map each candidate container to its physical paths

This is the **key technique** — it tells you which disk mounts each container actually writes to.

```bash
docker inspect <container-name> --format '{{range .Mounts}}{{.Destination}} -> {{.Source}}\n{{end}}'
```

Do this for every candidate. Look for mounts that point to the target drive (e.g. `/mnt/music`, `/mnt/nas/downloads`).

**Pitfall:** A downloader container (qbittorrent, sabnzbd) may map to `/mnt/nas/downloads` — *not* the music drive. But post-processors (beets, lidarr, sonobarr, radarr) that watch that download directory may then copy/move files *to* `/mnt/music`. The downloader and the post-processor are separate containers; attribute to the one whose volume map includes the target mount.

### 9. Check container logs for the activity window

```bash
# Activity since start of the claimed day
docker logs <container> --since '2026-09-12T00:00:00' 2>/dev/null \
  | grep -iE 'complete|import|move|copy|download|save|post.?proc|unpack|scan|/mnt/music|music' \
  | tail -30
```

Check each candidate container. Look for:
- **SABnzbd:** `Download Completed`, `Post-Processing`, `DirectUnpacked`, `Queue finished`
- **qBittorrent:** save path events, torrent completion (may be sparse in logs)
- **beets:** `import`, `copy`, `move` (config may say `move: no`)
- **lidarr/sonarr/radarr:** `ImportApprovedTracks`, `Post-Process`, `Duplicate`
- **jellyfin/plex:** `scan`, `metadata`, `ffmpeg`, `transcode` (reads, not writes)
- **syncthing:** `sent`, `received`, `pull`, `push`, folder names

**Pitfall:** Container logs may be sparse or show only Web UI startup messages if the service logs to a file inside the container rather than stdout. If `docker logs` is unhelpful, check the config volume for log files:
```bash
docker inspect <container> --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}\n{{end}}' | grep config
# Then read the log file from the host path
```

### 10. Check system/journal logs for I/O errors or service mentions

```bash
journalctl --since '2026-09-12T00:00:00' --until '2026-09-13T00:00:00' 2>/dev/null \
  | grep -iE 'sdc|I/O|block|sabnzbd|qbittorrent|beets|music|scan|import' \
  | grep -vi 'dns.*timeout' | head -30
```

**Pitfall:** `journalctl` output is dominated by Docker DNS resolver timeouts when the VPN (gluetun) is active. Always `grep -vi 'dns.*timeout'` or `grep -vi 'resolver.*failed'` to see the signal.

### 11. Find today's large files on the target drive (if feasible)

```bash
# Files modified today, larger than 100 MB, sorted by size
find /mnt/music -type f -newermt '2026-09-12' ! -newermt '2026-09-13' \
  -printf '%s %p\n' 2>/dev/null | awk '$1>100000000' | sort -rn | head -20
```

**Pitfall:** `find -newermt` on a multi-terabyte drive with millions of files **times out**. If it doesn't return within 30 seconds, kill it and fall back to:
- Narrow the scope: `find /mnt/music/music -type f ...` (one subdirectory at a time)
- Use diskstats + log attribution instead (steps 5–9)
- Check `du -sh` on candidate subdirectories to find where bulk data lives

### 12. Synthesize

Combine everything:
- **Diskstats totals** (since boot) tell you the *scale* — does the user's claim match reality?
- **Container volume maps** tell you *who can touch* the target mount
- **Container logs** tell you *who was active* during the window
- **Today's file timestamps** (when feasible) tell you *what changed*

Report:
- The actual read/write volume from diskstats (with boot-time caveat)
- Which containers map to the target mount
- Which of those had log activity in the window
- The most likely actor, with the evidence chain
- Anything you *couldn't* determine (timestamp gaps, find timeouts, missing logs)

---

## Quick decision table

| What you see | Likely source | Confirm with |
|---|---|---|
| Large reads, small writes on music drive | Media server scanning (jellyfin/plex/navidrome) | `docker logs jellyfin --since ... | grep ffmpeg/scan/metadata` |
| Large writes to `/mnt/nas/downloads/incomplete` | qbittorrent or sabnzbd downloading | `docker logs qbittorrent --since ...` + `docker logs sabnzbd --since ...` |
| Writes to `/mnt/music/music/<artist>/<album>/` after a download completes | Post-processor (beets/lidarr/sonobarr) copied/moved it | Check downloader logs for completion timestamp, then post-processor logs for import at same time |
| Syncthing folder sync activity | Syncthing pushing/pulling a folder | `docker logs syncthing --since ... | grep -i 'sent\|received\|pull\|push'` |
| No container maps to the target mount | Activity is from a bare-metal service or direct shell action | `systemctl list-units --type=service --state=running | grep -iE 'sab|torrent|beets'` |

---

## References

- `references/diskstats-and-boot-time.md` — sector math, field layout, boot-time window interpretation
