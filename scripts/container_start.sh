#!/bin/sh
# Container-Startbefehl (PID 1): Webroot verlinken, Apache im Vordergrund.
# Idempotent — läuft bei jedem Containerstart erneut (Restart-Policy:
# unless-stopped); ersetzt den manuellen Aufruf von start_server.sh.
set -e
cd "$(dirname "$0")/.."
sudo rm -rf /var/www/html
sudo ln -sfn "$(pwd)/www" /var/www/html
grep -q '^ServerName' /etc/apache2/apache2.conf || \
  sudo sh -c 'echo "ServerName paraglidable.com" >> /etc/apache2/apache2.conf'
exec sudo apachectl -D FOREGROUND
