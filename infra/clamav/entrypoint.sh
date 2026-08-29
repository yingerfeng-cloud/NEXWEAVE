#!/bin/sh
set -eu

install -d -o clamav -g clamav /run/clamav /var/lib/clamav
chown -R clamav:clamav /var/lib/clamav

freshclam --stdout --config-file=/etc/clamav/freshclam.conf
exec clamd --foreground=true --config-file=/etc/clamav/clamd.conf
