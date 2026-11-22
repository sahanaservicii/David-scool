#!/bin/bash
# Серия замеров: WAN, правило Block-Cam191-WAN, .191, doctor, хост.
# Только чтение. Запуск: bash state/monitor-wan-cam191.sh
H=/root/workspace/homelab/homelab.py
OUT=/root/workspace/reports/monitor-wan-cam191-2026-11-20.md
cd /root/workspace/homelab || exit 1

{
  echo "# Мониторинг WAN и правила Block-Cam191-WAN — 20.11.2026"
  echo
  echo "Интервал 10 мин, 7 замеров (0..60 мин). Только чтение."
  echo
} > "$OUT"

for i in $(seq 1 7); do
  {
    echo "## Замер $i — $(date '+%Y-%m-%d %H:%M:%S %Z')"
    echo
    echo '### Router status'
    python3 "$H" router status 2>&1
    echo
    echo '### WAN ubus'
    python3 "$H" router exec "ubus call network.interface.wan status" 2>&1
    echo
    echo '### Rule counter'
    python3 "$H" router exec "nft list ruleset | grep -A2 -B1 Block-Cam191-WAN" 2>&1
    echo
    echo '### Cam .191'
    python3 "$H" cam 192.168.1.191 2>&1
    echo
    echo '### Doctor'
    python3 "$H" doctor 2>&1
    echo
    echo '### Xray log tail'
    python3 "$H" router exec "logread -e xray | tail -3" 2>&1
    echo
    echo '### Host'
    uptime 2>&1
    free -h 2>&1 | head -3
    echo
  } >> "$OUT"

  [ "$i" -lt 7 ] && sleep 600
done

echo "ДONE $(date '+%Y-%m-%d %H:%M:%S %Z')" >> "$OUT"
