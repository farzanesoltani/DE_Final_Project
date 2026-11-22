#!/usr/bin/env bash
set -e

ZIP_URL=$(curl -sL https://api.github.com/repos/grafana/clickhouse-datasource/releases/latest | grep -oE '"browser_download_url": *"[^"]*linux-amd64\.zip"' | head -n1 | cut -d'"' -f4)

if [ -z "$ZIP_URL" ]; then
  echo "لینک از GitHub دریافت نشد؛ مطمئن شوید VPN روشن است و دوباره همین دستور را بزنید."
  exit 1
fi

curl -L -s "$ZIP_URL" -o /tmp/ch_plugin.zip
docker exec -u root grafana_dashboard mkdir -p /var/lib/grafana/plugins/grafana-clickhouse-datasource
docker cp /tmp/ch_plugin.zip grafana_dashboard:/tmp/ch_plugin.zip
docker exec -u root grafana_dashboard sh -c 'rm -rf /var/lib/grafana/plugins/tmp_ch && mkdir -p /var/lib/grafana/plugins/tmp_ch && unzip -q -o /tmp/ch_plugin.zip -d /var/lib/grafana/plugins/tmp_ch && mv /var/lib/grafana/plugins/tmp_ch/*/* /var/lib/grafana/plugins/grafana-clickhouse-datasource/ 2>/dev/null || mv /var/lib/grafana/plugins/tmp_ch/* /var/lib/grafana/plugins/grafana-clickhouse-datasource/ && rm -rf /var/lib/grafana/plugins/tmp_ch /tmp/ch_plugin.zip'
rm -f /tmp/ch_plugin.zip
docker restart grafana_dashboard
echo "DONE! Plugin installed and Grafana restarted."
