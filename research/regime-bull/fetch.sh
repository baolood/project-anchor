#!/bin/bash
# Binance public archive, spot 1d klines BTCUSDT/ETHUSDT monthly zips, 2017-08 .. 2026-09
cd "$(dirname "$0")/data"
for c in BTC ETH; do for y in 2017 2018 2019 2020 2021 2022 2023 2024 2025 2026; do for m in 01 02 03 04 05 06 07 08 09 10 11 12; do
  [ "$y$m" -gt 202609 ] && continue
  [ "$y$m" -lt 201708 ] && continue
  echo "spot/monthly/klines/${c}USDT/1d/${c}USDT-1d-$y-$m.zip"
done; done; done | xargs -P 16 -I{} sh -c 'f=$(basename {}); [ -s "$f" ] || curl -sf -o "$f" "https://data.binance.vision/data/{}" || rm -f "$f"'
ls | wc -l
