# Backup & Restore

It is highly recommended to regularly backup your WatchMan NIDS database and configuration files.

## What to Backup
1. **Configuration**: `/etc/watchman/watchman.config.json`
2. **Database**: `/var/lib/watchman/alerts.db`
3. **Logs (Optional)**: `/var/log/watchman/`

## Creating a Backup

Create an archive of the critical directories:
```bash
sudo tar -czvf watchman_backup_$(date +%F).tar.gz /etc/watchman /var/lib/watchman
```
Store this archive safely off-server.

## Restoring from a Backup

To restore:
1. Stop the daemon: `sudo systemctl stop watchman`.
2. Extract your backup archive: 
   ```bash
   sudo tar -xzvf watchman_backup_YYYY-MM-DD.tar.gz -C /
   ```
3. Ensure correct permissions:
   ```bash
   sudo chown -R watchman:watchman /etc/watchman /var/lib/watchman
   ```
4. Start the daemon: `sudo systemctl start watchman`.
