#!/usr/bin/env bash
# Simple helper to set CPU frequency across all cores

if [ -z "$1" ]; then
  echo "Usage: $0 <freq_mhz>"
  exit 1
fi

FREQ=$1
KHZ=$((FREQ * 1000))

AVAILABLE=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors)
if echo "$AVAILABLE" | grep -q userspace; then
  GOV=userspace
else
  GOV=performance
fi

for CPUFREQ in /sys/devices/system/cpu/cpu[0-9]*/cpufreq; do
  echo "$GOV" | sudo tee "$CPUFREQ/scaling_governor" >/dev/null
  echo "$KHZ" | sudo tee "$CPUFREQ/scaling_min_freq" >/dev/null
  echo "$KHZ" | sudo tee "$CPUFREQ/scaling_max_freq" >/dev/null
done

echo "CPU frequency set to ${FREQ} MHz for all cores."
