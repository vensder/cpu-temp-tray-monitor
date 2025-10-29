#!/usr/bin/env python3

import sys
import os
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


        # Add frequency submenu -- not working
        freq_menu = QMenu("Set CPU Frequency")
        for freq in [400, 800, 1600, 2000, 3000, 4000]:
            action = QAction(f"Set to {freq}MHz")
            action.triggered.connect(
                lambda _, f=freq: self.set_cpu_frequency_all_cores(f)
            )
            freq_menu.addAction(action)
        self.menu.addMenu(freq_menu)

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

    def get_cpu_temp(self):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
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
        script_path = "/usr/local/bin/set_cpu_freq.sh"

        if not os.path.exists(script_path):
            # Create and install the script once if needed
            script_lines = [
                "#!/bin/bash",
                "AVAILABLE=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors)",
                'if echo \"$AVAILABLE\" | grep -q userspace; then',
                "  GOV=userspace",
                "else",
                "  GOV=performance",
                "fi",
                "for CPUFREQ in /sys/devices/system/cpu/cpu[0-9]*/cpufreq; do",
                '  echo $GOV > \"$CPUFREQ/scaling_governor\"',
                f'  echo {mhz} > \"$CPUFREQ/scaling_min_freq\"',
                f'  echo {mhz} > \"$CPUFREQ/scaling_max_freq\"',
                "done",
            ]

            with open(script_path, "w") as f:
                f.write("\n".join(script_lines))
            os.chmod(script_path, 0o755)

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

        for freq in [400, 800, 1600, 2000, 3000, 4000]:
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
