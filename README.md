# 🧊 CPU Temperature Tray Monitor

A lightweight **CPU temperature and frequency monitor** for Linux with a **system tray icon**, alert popups, and optional **automatic frequency throttling** to prevent overheating.

Built with **Python + PyQt5**, designed for minimalism and reliability.

## 💡 Background

I created this tool after experiencing fan control issues on my laptop —
the cooling fan sometimes failed to start, causing the CPU to overheat under load.

To prevent potential thermal damage, I wanted a simple software-based safety layer
that would automatically throttle the CPU frequency if the temperature exceeded a critical threshold.

While the project began as a personal experiment, it evolved into a small educational tool for exploring:

- CPU temperature monitoring via /sys/class/hwmon
- Dynamic frequency scaling
- Safe privilege escalation using sudoers
- PyQt5 tray UI design for system tools

## ⚠️ Disclaimer & Safety Notes

This project is intended for educational and self-experimentation purposes only.
It is not recommended for production environments or long-term hardware management.

- ⚙️ If your laptop’s fan and cooling system work properly,
you should rely on the built-in thermal protection mechanisms provided by your BIOS, OS, and CPU firmware.
Modern CPUs automatically adjust frequency or shut down safely when overheating.
- 🧯 This utility is not a substitute for hardware cooling or proper fan control.
- 💻 Use it at your own risk — the author takes no responsibility for damage caused by misuse.

## 🌟 Features

- 🧠 Real-time CPU temperature monitoring (1s interval)
- 🖥️ Tray icon with live tooltip showing temperature and frequency
- 🔔 Non-blocking popup alerts at custom thresholds
- 🔉 Optional alert sounds per warning level
- ⚙️ Manual CPU frequency control (per core via submenu or popup)
- 🧯 Auto-throttles CPU to the lowest available frequency when temperature exceeds 90°C
- 🪶 Clean and responsive PyQt5 interface
- 🛡️ No root needed at runtime (uses `pkexec` or `sudo -n` when required)

## 🧰 Requirements

- **Python 3.8+**
- **PyQt5**
- **pulseaudio-utils** (for `paplay`)
- Access to `/sys/class/thermal/` and `/sys/devices/system/cpu/` (standard on most Linux distros)

You can install dependencies via:

```bash
sudo apt install python3-pyqt5 pulseaudio-utils
```

## 🚀 Installation

Clone this repository and make the main script executable:

```bash
git clone https://github.com/<your-username>/cpu-temp-tray.git
cd cpu-temp-tray
chmod +x cpu_temp_tray.py set_cpu_freq.sh
```

Optionally, copy the script to a local binary path:

```bash
sudo cp cpu_temp_tray.py /usr/local/bin/cpu_temp_tray
```

## 🔧 Usage

Run from terminal:

```bash
./cpu_temp_tray.py
```

A tray icon will appear in your system panel.
Hover over it to see temperature and CPU frequency in MHz.

Tray Actions

| Action                 | Description                             |
| ---------------------- | --------------------------------------- |
| 🖱️ Left click          | Opens quick frequency control popup     |
| 🖱️ Right click         | Opens main context menu                 |
| ⚙️ *Set CPU Frequency* | Manually set frequency across all cores |
| 🔥 *Auto-throttle*     | Automatically sets lowest freq at 90°C  |
| ❌ *Quit*              | Exit the app                            |


🔊 Alert Levels

| Threshold | Sound        | Message                                 |
| --------- | ------------ | --------------------------------------- |
| 71°C      | `alarm1.wav` | Temperature above 71°C                  |
| 81°C      | `alarm2.wav` | ⚠ CPU Overheating: 81°C                 |
| 86°C      | `alarm3.wav` | ⚠ CPU Overheating: 86°C                 |
| 90°C      | `alarm4.wav` | ⚠ CPU Overheating: 90°C (auto throttle) |

## ⚙️ Frequency Control Script

The app creates and uses /usr/local/bin/set_cpu_freq.sh automatically if missing.
It safely sets all CPU cores to a specific frequency (MHz) and governor mode.

Example generated script:

```bash
#!/bin/bash
for CPUFREQ in /sys/devices/system/cpu/cpu[0-9]*/cpufreq; do
  echo userspace > "$CPUFREQ/scaling_governor"
  echo 1600000 > "$CPUFREQ/scaling_min_freq"
  echo 1600000 > "$CPUFREQ/scaling_max_freq"
done
```

## 🔐 Privileges

For automatic frequency control, the app uses one of:

- `pkexec` (default graphical privilege elevation)
- `sudo -n` (non-interactive mode for emergency throttling)

To avoid repeated password prompts, you can add this to `/etc/sudoers`:

```bash
yourusername ALL=(ALL) NOPASSWD: /usr/local/bin/set_cpu_freq.sh
```

## 🧩 Optional Enhancements

Dynamic tray icon colour (green/yellow/red by temperature)

Cooldown recovery to restore previous frequency

Log to `/tmp/cpu_temp_tray.log`

System notification via `notify-send`

Auto-start option with `.desktop` entry
