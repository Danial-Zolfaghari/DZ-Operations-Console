from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class HelperCommand:
    id: str
    category: str
    title: str
    command: str
    description: str


HELPERS = (
    HelperCommand("hostname", "system", "Hostname", "hostname", "Windows host name"),
    HelperCommand("whoami", "system", "Current user", "whoami", "Current Windows user"),
    HelperCommand("systeminfo", "system", "System information", "systeminfo", "Windows version, memory, boot and system information"),
    HelperCommand("env", "system", "Environment", "Get-ChildItem Env: | Sort-Object Name", "Process environment variables"),
    HelperCommand("ipconfig", "network", "IP configuration", "ipconfig /all", "Adapters, IP addresses, DNS and DHCP configuration"),
    HelperCommand("netstat", "network", "Active connections", "netstat -ano", "TCP/UDP connections and owning process IDs"),
    HelperCommand("route", "network", "Routing table", "route print", "System routing table"),
    HelperCommand("dns-cache", "network", "DNS cache", "ipconfig /displaydns", "Windows DNS resolver cache"),
    HelperCommand("arp", "network", "ARP table", "arp -a", "ARP/neighbor table"),
    HelperCommand("tasklist", "process", "Process list", "tasklist", "Currently running processes"),
    HelperCommand("top-cpu", "process", "Top CPU processes", "Get-Process | Sort-Object CPU -Descending | Select-Object -First 20 Name,Id,CPU,WorkingSet", "Processes sorted by CPU time"),
    HelperCommand("top-memory", "process", "Top memory processes", "Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 20 Name,Id,@{N='RAM_MB';E={[math]::Round($_.WorkingSet/1MB,1)}}", "Processes sorted by memory usage"),
    HelperCommand("services-running", "services", "Running services", "Get-Service | Where-Object Status -eq 'Running' | Sort-Object DisplayName", "Currently running Windows services"),
    HelperCommand("services-stopped", "services", "Stopped services", "Get-Service | Where-Object Status -eq 'Stopped' | Sort-Object DisplayName", "Stopped Windows services"),
    HelperCommand("disks", "storage", "Disk volumes", "Get-Volume | Format-Table DriveLetter,FileSystemLabel,FileSystem,HealthStatus,Size,SizeRemaining -AutoSize", "Volumes, file systems and free space"),
    HelperCommand("physical-disks", "storage", "Physical disks", "Get-PhysicalDisk | Format-Table FriendlyName,MediaType,HealthStatus,OperationalStatus,Size -AutoSize", "Physical disk type, health and operational state"),
    HelperCommand("firewall", "security", "Firewall profiles", "Get-NetFirewallProfile | Format-Table Name,Enabled,DefaultInboundAction,DefaultOutboundAction -AutoSize", "Windows Firewall profile state and default policy"),
    HelperCommand("defender", "security", "Defender status", "Get-MpComputerStatus | Select-Object AntivirusEnabled,RealTimeProtectionEnabled,AntispywareEnabled,QuickScanAge,FullScanAge", "Microsoft Defender protection status"),
)

CATEGORIES = (
    {"id": "system", "title": "System", "description": "Host identity and operating environment"},
    {"id": "network", "title": "Network", "description": "IP, routing, DNS and active connections"},
    {"id": "process", "title": "Processes", "description": "Processes and resource utilization"},
    {"id": "services", "title": "Services", "description": "Windows Services"},
    {"id": "storage", "title": "Storage", "description": "Volumes and physical disks"},
    {"id": "security", "title": "Security", "description": "Firewall and Microsoft Defender"},
)


class DiagnosticsService:
    def __init__(self, timeout: int = 15, shell_enabled: bool = False) -> None:
        self.timeout = timeout
        self.shell_enabled = shell_enabled
        self._by_id = {c.id: c for c in HELPERS}

    def catalog(self) -> dict:
        return {
            "categories": list(CATEGORIES),
            "commands": [c.__dict__ for c in HELPERS],
            "shell_enabled": self.shell_enabled,
        }

    def list_commands(self) -> list[dict]:
        return [c.__dict__ for c in HELPERS]

    def execute_helper(self, command_id: str) -> dict:
        helper = self._by_id.get(command_id)
        if not helper:
            raise ValueError("Unknown helper command")
        return self._run_powershell(helper.command, display_command=helper.command)

    def execute_custom(self, command: str) -> dict:
        if not self.shell_enabled:
            raise PermissionError("Custom shell access is disabled. Enable it in Settings and restart the script.")
        command = command.strip()
        if not command:
            raise ValueError("Command cannot be empty")
        if len(command) > 4000:
            raise ValueError("Command is too long")
        return self._run_powershell(command, display_command=command)

    def _run_powershell(self, command: str, *, display_command: str) -> dict:
        if os.name == "nt":
            argv = ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command]
            creationflags = subprocess.CREATE_NO_WINDOW
        else:
            argv = ["sh", "-lc", command]
            creationflags = 0
        proc = subprocess.run(
            argv,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.timeout,
            cwd=os.getcwd(),
            creationflags=creationflags,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        return {"command": display_command, "returncode": proc.returncode, "output": output[-150_000:]}
