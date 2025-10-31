#!/usr/bin/env python3

import sys
import os
import glob
import subprocess
import tempfile
from PyQt5.QtWidgets import (
    QApplication,
    QSystemTrayIcon,
    QMenu,
    QAction,
    QMessageBox,
    QWidget,
    QDialog,
    QVBoxLayout,
    QPushButton,
    QLabel,
)
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtCore import QTimer, Qt


class CpuTempTray:
    def __init__(self):
        self.app = QApplication(sys.argv)

        # Tray Icon
        self.tray = QSystemTrayIcon(
            QIcon.fromTheme("preferences-devices-cpu"), self.app
        )
        self.tray.setToolTip("CPU Temperature Monitor")
        self.tray.setVisible(True)

        # Debug click events
        self.tray.activated.connect(self.on_tray_activated)

        # Tray menu
        self.menu = QMenu()

        alert = None  # Initialize as None
        self.active_alerts = []


        # # Add frequency submenu -- not working
        # freq_menu = QMenu("Set CPU Frequency")
        # for freq in [400, 800, 1600, 2000, 3000, 4000]:
        #     action = QAction(f"Set to {freq}MHz")
        #     action.triggered.connect(
        #         lambda _, f=freq: self.set_cpu_frequency_all_cores(f)
        #     )
        #     freq_menu.addAction(action)
        # self.menu.addMenu(freq_menu)

        # Quit
        self.quit_action = QAction("Quit")
        self.quit_action.triggered.connect(self.app.quit)
        self.menu.addAction(self.quit_action)
        self.tray.setContextMenu(self.menu)

        # Thresholds and sounds
        self.thresholds = [
            (71, "/home/vensder/sounds/alarm1.wav", "Temperature above 71°C"),
            (81, "/home/vensder/sounds/alarm2.wav", "⚠️ CPU Overheating: 81°C!"),
            (86, "/home/vensder/sounds/alarm3.wav", "⚠️ CPU Overheating: 86°C!"),
            (90, "/home/vensder/sounds/alarm4.wav", "⚠️ CPU Overheating: 90°C!"),
        ]

        self.last_triggered_level = 0

        self.last_set_freq_mhz = None

        # Start temp monitoring
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_temp)
        self.timer.start(1000)

    def detect_cpu_temp_sensor(self):
        for path in glob.glob("/sys/class/hwmon/hwmon*"):
            try:
                with open(os.path.join(path, "name")) as f:
                    name = f.read().strip()
                if name == "coretemp":
                    temps = sorted(glob.glob(os.path.join(path, "temp*_input")))
                    if temps:
                        return temps[0]  # use first one (package temperature)
            except FileNotFoundError:
                continue
        return None

    def get_cpu_temp(self):
        TEMP_PATH = self.detect_cpu_temp_sensor() or "/sys/class/hwmon/hwmon4/temp1_input"
        try:
            with open(TEMP_PATH, "r") as f:
                return int(f.read()) // 1000
        except:
            return 0

    def get_current_cpu_freqs(self):
        freqs = []
        for cpu in range(os.cpu_count()):
            path = f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_cur_freq"
            try:
                with open(path, "r") as f:
                    khz = int(f.read().strip())
                    freqs.append(khz // 1000)  # Convert to MHz
            except FileNotFoundError:
                continue  # Some CPUs might not have this file
        return freqs

    def check_temp(self):
        temp = self.get_cpu_temp()
        freqs = self.get_current_cpu_freqs()

        if freqs:
            avg_freq = sum(freqs) // len(freqs)
            self.tray.setToolTip(f"Temp: {temp}°C | Freq: {avg_freq} MHz")
        else:
            self.tray.setToolTip(f"Temp: {temp}°C")

        for threshold, sound_path, message in sorted(self.thresholds):
            if temp >= threshold and self.last_triggered_level < threshold:
                self.last_triggered_level = threshold

                # 🔥 Move this inside the alert condition but BEFORE blocking UI
                if temp >= 90 and (self.last_set_freq_mhz is None or self.last_set_freq_mhz > 400):
                    print("Overheat protection: setting CPU frequency to 400 MHz")
                    # Call the sudo script without prompting
                    subprocess.run(["sudo", "-n", "/usr/local/bin/set_cpu_freq.sh", "400"])

                subprocess.run(["paplay", sound_path])
                # self.tray_icon.showMessage("CPU Alert", message, QSystemTrayIcon.Critical)
                self.show_alert(message)
                break

        # for threshold, sound_path, message in sorted(self.thresholds):
        #     if temp >= threshold and self.last_triggered_level < threshold:
        #         self.last_triggered_level = threshold
        #         subprocess.run(["paplay", sound_path])
        #         self.show_alert(message)
        #         break

        # # Auto-reduce CPU frequency if temperature is dangerously high
        # if temp >= 90 and (self.last_set_freq_mhz is None or self.last_set_freq_mhz > 400):
        #     print("Overheat protection: setting CPU frequency to 400 MHz")
        #     self.set_cpu_frequency_all_cores(400, use_sudo=True)


        if temp < self.thresholds[0][0]:
            self.last_triggered_level = 0


    def show_alert(self, message):
        alert = QMessageBox()
        alert.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        alert.setText(message)
        alert.setWindowTitle("CPU Temperature Warning")
        alert.setIcon(QMessageBox.Warning)
        alert.setStandardButtons(QMessageBox.Ok)
        alert.setModal(False)  # Ensure it's non-modal
        alert.setAttribute(Qt.WA_DeleteOnClose) # Delete the QMessageBox after it is closed

        # Center the dialog on the screen
        screen = self.app.primaryScreen().geometry()
        x = (screen.width() - alert.sizeHint().width()) // 2
        y = (screen.height() - alert.sizeHint().height()) // 2
        alert.move(x, y)

        # Keep reference until closed
        self.active_alerts.append(alert)
        alert.finished.connect(lambda _: self.active_alerts.remove(alert))

        # alert.exec_()
        alert.show()

    def set_cpu_frequency_all_cores(self, freq_mhz, use_sudo=False):
        mhz = freq_mhz * 1000
        self.last_set_freq_mhz = freq_mhz  # Save it for tooltip
        # script_path = "/usr/local/bin/set_cpu_freq.sh"
        # Inside the same directory as the Python script
        SCRIPT_NAME = "set_cpu_freq.sh"
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), SCRIPT_NAME)

        # if not os.path.exists(script_path):
        #     # Create and install the script once if needed
        #     script_lines = [
        #         "#!/bin/bash",
        #         "AVAILABLE=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors)",
        #         'if echo \"$AVAILABLE\" | grep -q userspace; then',
        #         "  GOV=userspace",
        #         "else",
        #         "  GOV=performance",
        #         "fi",
        #         "for CPUFREQ in /sys/devices/system/cpu/cpu[0-9]*/cpufreq; do",
        #         '  echo $GOV > \"$CPUFREQ/scaling_governor\"',
        #         f'  echo {mhz} > \"$CPUFREQ/scaling_min_freq\"',
        #         f'  echo {mhz} > \"$CPUFREQ/scaling_max_freq\"',
        #         "done",
        #     ]

        #     with open(script_path, "w") as f:
        #         f.write("\n".join(script_lines))
        #     os.chmod(script_path, 0o755)

        # Run with appropriate privilege escalation
        if use_sudo:
            result = subprocess.run(["sudo", script_path, str(freq_mhz)])
        else:
            result = subprocess.run(["pkexec", script_path, str(freq_mhz)])

        if result.returncode == 0 and not use_sudo:
            self.tray.showMessage(
                "CPU Frequency Set",
                f"Set to {freq_mhz} MHz on all cores.",
                QSystemTrayIcon.Information,
                3000,
        )

    def set_freq_and_close(self, dialog, freq):
        self.set_cpu_frequency_all_cores(freq)
        dialog.accept()

    def on_tray_activated(self, reason):
        print("Tray icon activated:", reason)
        if reason == QSystemTrayIcon.Trigger:  # Left click
            print("Left click detected — showing fallback popup menu")
            self.show_popup_menu()
        elif reason == QSystemTrayIcon.Context:  # Right click
            print("Right click detected (context menu)")
        elif reason == QSystemTrayIcon.MiddleClick:
            print("Middle click detected")


    def get_available_frequencies(self, step=400):
        """
        Returns a list of available CPU frequencies in MHz.
        Falls back to min/max if scaling_available_frequencies is missing.
        """
        freqs = []
        base = "/sys/devices/system/cpu/cpu0/cpufreq"
        freq_file = os.path.join(base, "scaling_available_frequencies")

        if os.path.exists(freq_file):
            with open(freq_file) as f:
                freqs = sorted(set(int(x) for x in f.read().split()))
        else:
            # # Fallback: use min and max only
            # with open(os.path.join(base, "cpuinfo_min_freq")) as f:
            #     min_freq = int(f.read().strip())
            # with open(os.path.join(base, "cpuinfo_max_freq")) as f:
            #     max_freq = int(f.read().strip())
            # freqs = [min_freq, max_freq]
            try:
                with open(os.path.join(base, "cpuinfo_min_freq")) as f:
                    min_freq = int(f.read().strip())
                with open(os.path.join(base, "cpuinfo_max_freq")) as f:
                    max_freq = int(f.read().strip())
            except FileNotFoundError:
                return [800, 1600, 2400]  # safe fallback

        # # Convert to MHz for display
        # return [f // 1000 for f in freqs]

        # Convert to MHz
        min_mhz = min_freq // 1000
        max_mhz = max_freq // 1000
        
        # Generate frequency list with given step (e.g. 400 MHz)
        freqs = list(range(min_mhz, max_mhz + step, step))
        
        # Ensure min/max are included
        if freqs[-1] != max_mhz:
            freqs[-1] = max_mhz

        # Remove the last (highest) value for safety
        if len(freqs) > 1:
            freqs = freqs[:-1]

        print(freqs)
        return freqs

    # def show_popup_menu(self):
    #     msg = QMessageBox()
    #     msg.setWindowTitle("CPU Tray Menu")
    #     msg.setText("Choose an action:")
    #     msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    #     msg.exec_()

    def show_popup_menu(self):
        dialog = QDialog()
        dialog.setWindowTitle("Set CPU Frequency")
        layout = QVBoxLayout()

        label = QLabel("Select CPU frequency:")
        layout.addWidget(label)
        
        available_freqs = self.get_available_frequencies()

        for freq in available_freqs: # [400, 800, 1600, 2000, 3000, 4000]:
            button = QPushButton(f"{freq} MHz")
            button.clicked.connect(lambda _, f=freq: self.set_freq_and_close(dialog, f))
            layout.addWidget(button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        layout.addWidget(cancel_button)

        dialog.setLayout(layout)
        dialog.exec_()

    def run(self):
        sys.exit(self.app.exec_())


if __name__ == "__main__":
    CpuTempTray().run()
