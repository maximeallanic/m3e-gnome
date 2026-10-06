#!/usr/bin/env python3
"""Private, throw-away SYSTEM bus for the screenshot session, populated with fake demo hardware.

A nested Shell talks to the system bus given by DBUS_SYSTEM_BUS_ADDRESS. Left alone, that is the real one:
NetworkManager, UPower and BlueZ would hand the Wi-Fi network, the VPNs and the paired devices of the machine to
the quick settings. This script starts its own dbus-daemon and fills it with python-dbusmock services (fake
Wi-Fi networks, a battery, Bluetooth devices, power profiles), so the capture shows the full quick settings and no
real data. The real system bus is never contacted.

Usage: sysbus.py --dir DIR      (runs until SIGTERM/SIGINT; writes DIR/address once the services are up)
Needs python-dbusmock (and dbus-python, from the system) in the interpreter that runs it: see README.md.
"""
import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

CONFIG = """<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <type>session</type>
  <listen>unix:path={socket}</listen>
  <auth>EXTERNAL</auth>
  <policy context="default">
    <allow send_destination="*" eavesdrop="true"/>
    <allow eavesdrop="true"/>
    <allow own="*"/>
  </policy>
</busconfig>
"""

MOCK = "org.freedesktop.DBus.Mock"

# Demo data, all invented.
WIFI_NETWORKS = [("Aurora", 92), ("CafeWifi", 64), ("LibraryGuest", 41)]
BLUETOOTH_DEVICES = [("00:11:22:33:44:55", "Demo Headphones"), ("00:11:22:33:44:66", "Demo Speaker")]
BATTERY_PERCENT, BATTERY_SECONDS = 78, 19800


def populate():
    import dbus
    from dbusmock import SpawnedMock

    mocks = [SpawnedMock.spawn_with_template(name).process
             for name in ("logind", "polkitd", "upower", "networkmanager", "bluez5", "upower_power_profiles_daemon")]
    bus = dbus.SystemBus()

    def iface(name, path, interface):
        return dbus.Interface(bus.get_object(name, path), interface)

    # The Shell and its applications expect a login session for the current uid; the user is the demo one.
    login = iface("org.freedesktop.login1", "/org/freedesktop/login1", MOCK)
    # python-dbusmock's GetUser concatenates a str and the uint32 argument (TypeError): redefined with str().
    login.AddMethod("org.freedesktop.login1.Manager", "GetUser", "u", "o",
                    'ret = "/org/freedesktop/login1/user/" + str(args[0])')
    login.AddSeat("seat0")
    login.AddUser(os.getuid(), "demo", True)
    login.AddSession("c1", "seat0", os.getuid(), "demo", True)

    iface("org.freedesktop.UPower", "/org/freedesktop/UPower", MOCK) \
        .AddDischargingBattery("BAT0", "Demo battery", float(BATTERY_PERCENT), BATTERY_SECONDS)
    # The Shell reads the aggregated DisplayDevice: type 2 = battery, state 2 = discharging, warning level 1 = none.
    iface("org.freedesktop.UPower", "/org/freedesktop/UPower", MOCK).SetupDisplayDevice(
        2, 2, float(BATTERY_PERCENT), 40.0, 51.0, 8.0, BATTERY_SECONDS, 0, True, "battery-good-symbolic", 1)

    nm = iface("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager",
               MOCK)
    device = nm.AddWiFiDevice("mock_wifi", "wlan0", 100)
    points = [nm.AddAccessPoint(device, f"mock_ap{index}", ssid, f"00:23:F8:7E:12:{index:02X}", 2, 2412, 5400,
                                strength, 0x100 if index == 0 else 0x0)
              for index, (ssid, strength) in enumerate(WIFI_NETWORKS)]
    connection = nm.AddWiFiConnection(device, "mock_conn", WIFI_NETWORKS[0][0], "wpa-psk")
    active = nm.AddActiveConnection([device], connection, points[0], WIFI_NETWORKS[0][0], 2)
    # The mock does not define the manager-level properties the Shell reads for the top bar icon.
    manager = dbus.Interface(bus.get_object("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager"), MOCK)
    manager.AddProperty("org.freedesktop.NetworkManager", "PrimaryConnection", dbus.ObjectPath(active))
    manager.AddProperty("org.freedesktop.NetworkManager", "PrimaryConnectionType", "802-11-wireless")
    dbus.Interface(bus.get_object("org.freedesktop.NetworkManager", device), MOCK).AddProperty(
        "org.freedesktop.NetworkManager.Device.Wireless", "ActiveAccessPoint", dbus.ObjectPath(points[0]))

    bluez = iface("org.bluez", "/", "org.bluez.Mock")
    bluez.AddAdapter("hci0", "demo-laptop")
    for address, alias in BLUETOOTH_DEVICES:
        bluez.AddDevice("hci0", address, alias)
    bluez.PairDevice("hci0", BLUETOOTH_DEVICES[0][0])
    bluez.ConnectDevice("hci0", BLUETOOTH_DEVICES[0][0])
    return mocks


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--dir", required=True)
    a = p.parse_args()
    work = Path(a.dir).resolve()
    work.mkdir(parents=True, exist_ok=True)
    sock = work / "system_bus_socket"
    (work / "bus.conf").write_text(CONFIG.format(socket=sock), encoding="utf-8")
    daemon = subprocess.Popen(["dbus-daemon", "--config-file", str(work / "bus.conf"), "--nofork"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    for _ in range(100):
        if sock.exists():
            break
        time.sleep(0.05)
    else:
        daemon.kill()
        sys.exit("sysbus: the private bus did not start")
    os.environ["DBUS_SYSTEM_BUS_ADDRESS"] = f"unix:path={sock}"
    os.environ.pop("DBUS_STARTER_ADDRESS", None)
    stop = []
    for s in (signal.SIGTERM, signal.SIGINT):
        signal.signal(s, lambda *_: stop.append(1))
    mocks = []
    try:
        mocks = populate()
        (work / "address").write_text(os.environ["DBUS_SYSTEM_BUS_ADDRESS"], encoding="utf-8")
        while not stop and daemon.poll() is None:
            time.sleep(0.2)
    finally:
        for m in mocks:
            m.terminate()
        daemon.terminate()
        daemon.wait()
    return 0


if __name__ == "__main__":
    sys.exit(main())
