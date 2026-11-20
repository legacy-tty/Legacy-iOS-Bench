#!/usr/bin/env python3
import hashlib
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

BANNER = r"""
  _      ______ _____          _______     __  _  ____   _____ 
 | |    |  ____/ ____|   /\   / ____\ \   / / (_)/ __ \ / ____|
 | |    | |__ | |  __   /  \ | |     \ \_/ /   _| |  | | (___  
 | |    |  __|| | |_ | / /\ \| |      \   /   | | |  | |\___ \ 
 | |____| |___| |__| |/ ____ \ |____   | |    | | |__| |____) |
 |______|______\_____/_/    \_\_____|  |_|    |_|\____/|_____/ 
"""


def run_cmd(cmd, timeout=10):
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out."
    except FileNotFoundError:
        return -1, "", f"Tool not found: {cmd[0]}"


def draw_header():
    console.clear()
    header_text = Text(BANNER, style="bold cyan")
    subtitle = Text(
        "  [ Legacy iOS, Wireless Wi-Fi Sync & Jailbreak Bench v1.0 | Linux Edition ]",
        style="bold green",
    )
    console.print(
        Panel(
            Text.assemble(header_text, "\n", subtitle),
            border_style="bright_blue",
            padding=(0, 1),
        )
    )


def pause():
    console.print("\n[dim]Press Enter to return to Main Menu...[/dim]")
    input()


def parse_ideviceinfo(raw_text):
    info = {}
    for line in raw_text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            info[k.strip()] = v.strip()
    return info


def get_connected_ios():
    if not shutil.which("ideviceinfo"):
        return None, None
    # Try USB first
    code, out, _ = run_cmd(["ideviceinfo"], timeout=5)
    if code == 0 and out:
        return "USB", parse_ideviceinfo(out)
    # Try Wireless Wi-Fi network (-n)
    code_n, out_n, _ = run_cmd(["ideviceinfo", "-n"], timeout=6)
    if code_n == 0 and out_n:
        return "Wi-Fi Network", parse_ideviceinfo(out_n)
    return None, None


def inspect_devices():
    draw_header()
    console.print("[bold yellow]>>> Scanning USB Bus, Wi-Fi Network & Connected iOS Devices...[/bold yellow]\n")

    conn_type, info = get_connected_ios()
    if info:
        table = Table(
            title=f"Connected iOS Device [{conn_type}]",
            border_style="green",
        )
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="bold white")

        fields = [
            ("Connection Mode", None),
            ("Device Name", "DeviceName"),
            ("Product Type", "ProductType"),
            ("iOS Version", "ProductVersion"),
            ("Build Version", "BuildVersion"),
            ("Hardware Model", "HardwareModel"),
            ("ECID (Hex)", "UniqueChipID"),
            ("UDID", "UniqueDeviceID"),
            ("Serial Number", "SerialNumber"),
            ("CPU Architecture", "CPUArchitecture"),
            ("Wi-Fi MAC", "WiFiAddress"),
        ]
        for label, key in fields:
            if label == "Connection Mode":
                style = "bold green" if conn_type == "Wi-Fi Network" else "bold cyan"
                table.add_row(label, f"[{style}]{conn_type}[/{style}]")
            elif key in info:
                table.add_row(label, info[key])

        console.print(table)
    else:
        if not shutil.which("ideviceinfo"):
            console.print(
                "[red]Note: 'libimobiledevice-utils' is not installed. Run: sudo apt install libimobiledevice-utils[/red]\n"
            )
        else:
            console.print(
                Panel(
                    "[yellow]No paired iOS device detected over USB or Wi-Fi.[/yellow]\n"
                    "[dim]Tip: Plug in via USB and tap 'Trust', or enable Wi-Fi Sync in Option 2.[/dim]",
                    border_style="yellow",
                )
            )

    if shutil.which("lsusb"):
        _, usb_out, _ = run_cmd(["lsusb"])
        usb_table = Table(title="USB Bus Devices (lsusb)", border_style="bright_blue")
        usb_table.add_column("Bus / Device ID & Hardware Description", style="white")
        for line in usb_out.splitlines():
            if any(k in line for k in ("Apple", "Recovery", "DFU")):
                usb_table.add_row(f"[bold green]{line}[/bold green]")
            else:
                usb_table.add_row(line)
        console.print(usb_table)

    pause()


def wireless_wifi_manager():
    draw_header()
    console.print("[bold yellow]>>> Wireless iOS Connection (Wi-Fi Sync Manager)[/bold yellow]\n")

    if not shutil.which("idevicepair"):
        console.print("[bold red]Missing 'idevicepair'. Install with: sudo apt install libimobiledevice-utils[/bold red]")
        pause()
        return

    action = questionary.select(
        "Select Wireless Operation:",
        choices=[
            "1. Pair USB Device & Enable Wireless Wi-Fi Sync",
            "2. Scan & Test Wireless Wi-Fi Connection (No Cable Needed)",
            "3. Disable Wireless Wi-Fi Sync on Connected Device",
            "4. Back to Main Menu",
        ],
    ).ask()

    if not action or action.startswith("4."):
        return

    if action.startswith("1."):
        console.print("[cyan]Step 1: Pairing device over USB (make sure screen is unlocked & tapped 'Trust')...[/cyan]")
        code, out, err = run_cmd(["idevicepair", "pair"], timeout=10)
        if code == 0:
            console.print(f"[green]✔ {out}[/green]")
            console.print("[cyan]Step 2: Enabling Wi-Fi Sync over network...[/cyan]")
            w_code, w_out, w_err = run_cmd(["idevicepair", "wifi", "on"], timeout=10)
            if w_code == 0:
                console.print(f"[bold green]✔ Wireless Wi-Fi Sync Enabled! {w_out}[/bold green]")
                console.print("[dim]You can now unplug the USB cable as long as both PC and iPhone share the same Wi-Fi.[/dim]")
            else:
                console.print(f"[bold red]✘ Could not enable Wi-Fi Sync:[/bold red] {w_out} {w_err}")
        else:
            console.print(f"[bold red]✘ Pairing failed:[/bold red] {out} {err}")

    elif action.startswith("2."):
        console.print("[cyan]Scanning local Wi-Fi network for paired iOS devices (ideviceinfo -n)...[/cyan]\n")
        code, out, err = run_cmd(["ideviceinfo", "-n"], timeout=8)
        if code == 0 and out:
            info = parse_ideviceinfo(out)
            console.print(
                Panel(
                    f"[bold green]✔ Wireless Connection Active![/bold green]\n"
                    f"Device: [bold white]{info.get('DeviceName', 'Unknown')}[/bold white] ({info.get('ProductType', '?')})\n"
                    f"iOS Version: [cyan]{info.get('ProductVersion', '?')}[/cyan] | UDID: [dim]{info.get('UniqueDeviceID', '?')}[/dim]",
                    border_style="green",
                )
            )
        else:
            console.print(
                "[yellow]No wireless iOS device responded. Ensure Wi-Fi Sync was enabled via USB first and both devices are on the same Wi-Fi.[/yellow]"
            )

    elif action.startswith("3."):
        code, out, err = run_cmd(["idevicepair", "wifi", "off"], timeout=10)
        if code == 0:
            console.print(f"[bold green]✔ Wireless Wi-Fi Sync disabled. {out}[/bold green]")
        else:
            console.print(f"[bold red]✘ Error:[/bold red] {out} {err}")

    pause()


def classify_jailbreak(product_type, ios_ver):
    major = 0
    try:
        major = int(ios_ver.split(".")[0])
    except Exception:
        pass

    checkm8_chips = (
        "iPhone6,", "iPhone7,", "iPhone8,", "iPhone9,", "iPhone10,",
        "iPad4,", "iPad5,", "iPad6,", "iPad7,", "iPod7,", "iPod9,"
    )
    legacy_32bit = ("iPhone1,", "iPhone2,", "iPhone3,", "iPhone4,", "iPhone5,", "iPad1,", "iPad2,", "iPad3,", "iPod1,", "iPod2,", "iPod3,", "iPod4,", "iPod5,")

    if product_type.startswith(legacy_32bit):
        if major <= 6:
            return "Bootrom / Userland Legacy (redsn0w / Absinthe / p0sixspwn) — Untethered possible!"
        elif major in (7, 8, 9):
            return "32-bit Semi-Untethered (Pangu / EtasonJB / Phoenix / Kok3shi9)"
        elif major == 10:
            return "32-bit iOS 10 (h3lix / Socket)"
    elif product_type.startswith(checkm8_chips):
        if 12 <= major <= 14:
            return "checkm8 Bootrom Exploit (checkra1n / odysseyra1n) + Taurine / unc0ver"
        elif major >= 15:
            return "checkm8 Bootrom Exploit (palera1n - rootless or rootful) [Requires DFU Mode]"
        else:
            return "checkm8 Compatible Hardware + Classic Semi-Untethered (Electra / Chimera / unc0ver)"
    else:
        if 15 <= major <= 16:
            return "arm64e Semi-Untethered (Dopamine + TrollStore permanent signing)"
        elif major >= 17:
            return "Modern arm64e (Check TrollStore / NathanLR / Bootstrap compatibility)"
    return "Inspect ProductType & iOS build on ios.cfw.guide for exact exploit path"


def jailbreak_toolkit():
    draw_header()
    console.print("[bold yellow]>>> Jailbreak, Bootrom Exploit & DFU/Recovery Toolkit[/bold yellow]\n")

    action = questionary.select(
        "Select Jailbreak / Low-Level Operation:",
        choices=[
            "1. Exploit & Jailbreak Compatibility Advisor (Auto-Detect Device)",
            "2. Scan Installed Jailbreak Loaders & Sideloaded Apps (Sileo / Cydia / TrollStore)",
            "3. Enter Recovery Mode (Prep for checkm8 / DFU / IPSW Restore)",
            "4. Exit Recovery Mode (Kick Stuck Device Back to Normal Boot)",
            "5. Back to Main Menu",
        ],
    ).ask()

    if not action or action.startswith("5."):
        return

    if action.startswith("1."):
        conn_type, info = get_connected_ios()
        if info:
            ptype = info.get("ProductType", "Unknown")
            iver = info.get("ProductVersion", "Unknown")
            arch = info.get("CPUArchitecture", "Unknown")
            advice = classify_jailbreak(ptype, iver)
            console.print(
                Panel(
                    f"[bold cyan]Detected Hardware:[/bold cyan] {info.get('DeviceName', '?')} ([bold white]{ptype}[/bold white])\n"
                    f"[bold cyan]iOS Version:[/bold cyan] {iver} ({info.get('BuildVersion', '?')}) | [bold cyan]Arch:[/bold cyan] {arch}\n"
                    f"[bold cyan]Connection:[/bold cyan] {conn_type}\n\n"
                    f"[bold green]Recommended Exploit / Jailbreak Path:[/bold green]\n"
                    f"  >> [bold yellow]{advice}[/bold yellow]\n\n"
                    f"[dim]Reference Guide: https://ios.cfw.guide[/dim]",
                    title="Bootrom & Exploit Analysis",
                    border_style="bright_green",
                )
            )
        else:
            console.print("[yellow]No device detected over USB/Wi-Fi. Connect a device or check Option 4 for IPSW status.[/yellow]")

    elif action.startswith("2."):
        if not shutil.which("ideviceinstaller"):
            console.print("[bold red]Missing 'ideviceinstaller'. Install with: sudo apt install ideviceinstaller[/bold red]")
            pause()
            return
        console.print("[cyan]Scanning installed user packages & jailbreak utilities...[/cyan]\n")
        code, out, err = run_cmd(["ideviceinstaller", "-l"], timeout=15)
        if code != 0:
            code, out, err = run_cmd(["ideviceinstaller", "-n", "-l"], timeout=15)
        if code == 0 and out:
            jb_keywords = ("cydia", "sileo", "zebra", "trollstore", "palera1n", "dopamine", "altstore", "sidestore", "filza", "unc0ver", "taurine", "checkra1n")
            found_jb = []
            lines = out.splitlines()
            for line in lines[1:]:
                if any(k in line.lower() for k in jb_keywords):
                    found_jb.append(line)

            if found_jb:
                table = Table(title="Detected Jailbreak / Sideload Apps", border_style="green")
                table.add_column("Bundle ID & App Name", style="bold green")
                for item in found_jb:
                    table.add_row(item)
                console.print(table)
            else:
                console.print("[yellow]No known jailbreak loaders or package managers found among user apps.[/yellow]")
            console.print(f"\n[dim]Total user apps scanned: {max(0, len(lines) - 1)}[/dim]")
        else:
            console.print(f"[bold red]Could not list apps:[/bold red] {err}")

    elif action.startswith("3."):
        if not shutil.which("ideviceenterrecovery"):
            console.print("[bold red]Missing 'ideviceenterrecovery' (part of libimobiledevice-utils).[/bold red]")
            pause()
            return
        _, info = get_connected_ios()
        udid = info.get("UniqueDeviceID") if info else questionary.text("Enter device UDID:").ask()
        if udid and udid.strip():
            if questionary.confirm(f"Send device {udid.strip()} into Recovery Mode?").ask():
                code, out, err = run_cmd(["ideviceenterrecovery", udid.strip()], timeout=10)
                if code == 0:
                    console.print("[bold green]✔ Device is rebooting into Recovery Mode![/bold green]")
                    console.print("[dim]From Recovery Mode, you can follow button prompts for DFU (checkm8/palera1n).[/dim]")
                else:
                    console.print(f"[bold red]✘ Failed:[/bold red] {out} {err}")

    elif action.startswith("4."):
        if shutil.which("irecovery"):
            console.print("[cyan]Sending autoboot & reset command via irecovery...[/cyan]")
            run_cmd(["irecovery", "-c", "setenv auto-boot true"], timeout=5)
            run_cmd(["irecovery", "-c", "saveenv"], timeout=5)
            code, out, err = run_cmd(["irecovery", "-c", "reboot"], timeout=5)
            if code == 0:
                console.print("[bold green]✔ Reboot command sent to Recovery device![/bold green]")
            else:
                console.print(f"[yellow]irecovery output:[/yellow] {out} {err}")
        else:
            console.print(
                "[yellow]'irecovery' (libirecovery-utils) not installed.[/yellow]\n"
                "Install it on Linux Mint with: [cyan]sudo apt install libirecovery-utils[/cyan]"
            )

    pause()


def check_ipsw_signing():
    draw_header()
    console.print("[bold yellow]>>> Apple TSS / IPSW Signing Status Lookup[/bold yellow]\n")

    preset = questionary.select(
        "Choose a device or enter a custom identifier:",
        choices=[
            "iPhone4,1 (iPhone 4S - Classic Legacy)",
            "iPhone5,2 (iPhone 5)",
            "iPhone6,1 (iPhone 5s - First 64-bit / checkm8)",
            "iPhone8,1 (iPhone 6s - checkm8)",
            "iPhone10,6 (iPhone X - checkm8)",
            "iPhone14,2 (iPhone 13 Pro)",
            "iPhone16,1 (iPhone 15 Pro)",
            "Enter custom identifier (e.g., iPad4,1)...",
        ],
    ).ask()

    if not preset:
        return

    if "Enter custom" in preset:
        identifier = questionary.text("Enter Apple Device Identifier:").ask()
        if not identifier:
            return
        identifier = identifier.strip()
    else:
        identifier = preset.split(" ")[0]

    url = f"https://api.ipsw.me/v4/device/{identifier}?type=ipsw"
    console.print(f"\n[cyan]Querying Apple TSS status for [bold]{identifier}[/bold]...[/cyan]\n")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LegacyiOSBench/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        table = Table(
            title=f"{data.get('name', identifier)} ({identifier}) Firmware Status",
            border_style="bright_blue",
        )
        table.add_column("iOS Version", style="bold white")
        table.add_column("Build ID", style="cyan")
        table.add_column("Signing Status", justify="center")
        table.add_column("Size", justify="right", style="dim")

        for fw in data.get("firmwares", [])[:15]:
            signed = fw.get("signed", False)
            status = "[bold green][ SIGNED ][/bold green]" if signed else "[red][ UNSIGNED ][/red]"
            size_gb = f"{fw.get('filesize', 0) / (1024**3):.2f} GB"
            table.add_row(fw.get("version", "?"), fw.get("buildid", "?"), status, size_gb)

        console.print(table)
        console.print("[dim]Showing latest 15 firmware builds from ipsw.me API.[/dim]")

    except urllib.error.HTTPError:
        console.print(f"[bold red]Device '{identifier}' not found in IPSW database.[/bold red]")
    except Exception as e:
        console.print(f"[bold red]Network error: {e}[/bold red]")

    pause()


def verify_checksum():
    draw_header()
    console.print("[bold yellow]>>> Firmware / IPSW Hash Verifier (SHA-1 & SHA-256)[/bold yellow]\n")

    file_path = questionary.path("Select or enter path to .ipsw / .iso file:").ask()
    if not file_path:
        return

    file_path = os.path.expanduser(file_path.strip())
    if not os.path.isfile(file_path):
        console.print(f"[bold red]File not found: {file_path}[/bold red]")
        pause()
        return

    console.print("\n[cyan]Hashing file (this may take a few seconds for large IPSWs)...[/cyan]")
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            sha1.update(chunk)
            sha256.update(chunk)

    table = Table(title=f"Hashes for {os.path.basename(file_path)}", border_style="green")
    table.add_column("Algorithm", style="bold cyan")
    table.add_column("Digest", style="white")
    table.add_row("SHA-1", sha1.hexdigest())
    table.add_row("SHA-256", sha256.hexdigest())
    console.print(table)

    expected = questionary.text("Paste expected hash to compare (or press Enter to skip):").ask()
    if expected and expected.strip():
        clean_exp = expected.strip().lower()
        if clean_exp in (sha1.hexdigest(), sha256.hexdigest()):
            console.print("\n[bold green]✔ MATCH! File integrity verified.[/bold green]")
        else:
            console.print("\n[bold red]✘ MISMATCH! File may be corrupted or modified.[/bold red]")

    pause()


def logs_viewer():
    draw_header()
    console.print("[bold yellow]>>> Live iOS Syslog & Linux Kernel USB Events[/bold yellow]\n")

    mode = questionary.select(
        "Select Log Stream:",
        choices=[
            "1. Stream Live iOS Device Syslog (USB or Wireless Wi-Fi) [Ctrl+C to Stop]",
            "2. View Last 20 Linux Kernel USB / DFU Events (dmesg)",
            "3. Back to Main Menu",
        ],
    ).ask()

    if not mode or mode.startswith("3."):
        return

    if mode.startswith("1."):
        if not shutil.which("idevicesyslog"):
            console.print("[bold red]Missing 'idevicesyslog'. Install libimobiledevice-utils first.[/bold red]")
            pause()
            return
        console.print("[bold cyan]>>> Streaming iOS Syslog (Press Ctrl+C to Stop)...[/bold cyan]\n")
        time.sleep(1)
        try:
            # Try USB first, fallback to network (-n)
            res = subprocess.run(["idevicesyslog"], timeout=2)
        except subprocess.TimeoutExpired:
            pass
        except KeyboardInterrupt:
            console.print("\n[cyan]Syslog stream stopped.[/cyan]")
        else:
            try:
                subprocess.run(["idevicesyslog", "-n"])
            except KeyboardInterrupt:
                console.print("\n[cyan]Wireless syslog stream stopped.[/cyan]")

    elif mode.startswith("2."):
        _, out, err = run_cmd(["dmesg", "-T"])
        if out:
            usb_lines = [
                line for line in out.splitlines()
                if any(k in line.lower() for k in ("usb", "apple", "dfu", "recovery", "serial"))
            ][-20:]
            if usb_lines:
                console.print(Panel("\n".join(usb_lines), title="Last 20 USB / Apple Kernel Logs", border_style="cyan"))
            else:
                console.print("[yellow]No recent USB/Apple kernel events found.[/yellow]")
        else:
            console.print(f"[yellow]Could not read dmesg (sudo may be required on your kernel): {err}[/yellow]")

    pause()


def main():
    while True:
        draw_header()
        choice = questionary.select(
            "Select iOS Operation:",
            choices=[
                "1. Inspect Connected iOS Devices (USB, Wi-Fi Network & DFU)",
                "2. Wireless Wi-Fi Sync & Pairing Manager (Cable-Free Connection)",
                "3. Jailbreak, Bootrom Exploit & Recovery/DFU Toolkit",
                "4. Check Live Apple IPSW Firmware Signing Status (TSS / ipsw.me)",
                "5. Verify IPSW / ISO Firmware Checksum (SHA-1 & SHA-256)",
                "6. Live iOS Syslog (USB/Wi-Fi) & Kernel USB Logs",
                "7. Exit Bench",
            ],
            qmark="[*]",
            pointer=">>",
        ).ask()

        if choice is None or choice.startswith("7."):
            console.print("\n[bold cyan]Exiting Legacy iOS Bench. Happy jailbreaking![/bold cyan]")
            break
        elif choice.startswith("1."):
            inspect_devices()
        elif choice.startswith("2."):
            wireless_wifi_manager()
        elif choice.startswith("3."):
            jailbreak_toolkit()
        elif choice.startswith("4."):
            check_ipsw_signing()
        elif choice.startswith("5."):
            verify_checksum()
        elif choice.startswith("6."):
            logs_viewer()


if __name__ == "__main__":
    main()
