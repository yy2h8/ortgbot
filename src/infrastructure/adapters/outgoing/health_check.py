import os
import time


def _read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except (FileNotFoundError, PermissionError):
        return None


def _read_lines(path):
    try:
        with open(path) as f:
            return f.readlines()
    except (FileNotFoundError, PermissionError):
        return []


def _cpu_percent(interval=0.5):
    lines = _read_lines("/proc/stat")
    if not lines:
        return None
    fields = lines[0].split()
    t1_total = sum(int(x) for x in fields[1:])
    t1_idle = int(fields[4])
    time.sleep(interval)
    lines = _read_lines("/proc/stat")
    if not lines:
        return None
    fields = lines[0].split()
    t2_total = sum(int(x) for x in fields[1:])
    t2_idle = int(fields[4])
    diff_total = t2_total - t1_total
    diff_idle = t2_idle - t1_idle
    if diff_total == 0:
        return 0.0
    return round((1 - diff_idle / diff_total) * 100, 1)


def _cpu_temp():
    raw = _read("/sys/class/thermal/thermal_zone0/temp")
    if raw is None:
        return None
    try:
        return round(int(raw) / 1000, 1)
    except ValueError:
        return None


def _uptime():
    raw = _read("/proc/uptime")
    if raw is None:
        return None
    seconds = int(float(raw.split()[0]))
    d, s = divmod(seconds, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    parts = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    parts.append(f"{s}s")
    return "".join(parts)


def _memory():
    info = {}
    for line in _read_lines("/proc/meminfo"):
        parts = line.split()
        if len(parts) >= 2:
            info[parts[0].rstrip(":")] = int(parts[1])
    total = info.get("MemTotal", 0)
    available = info.get("MemAvailable", 0)
    used = total - available
    return round(total / 1024, 1), round(used / 1024, 1)


def _process_rss():
    for line in _read_lines(f"/proc/{os.getpid()}/status"):
        if line.startswith("VmRSS:"):
            return round(int(line.split()[1]) / 1024, 1)
    return None


def get_health() -> str:
    up = _uptime()
    cpu = _cpu_percent()
    temp = _cpu_temp()
    total_mb, used_mb = _memory()
    rss = _process_rss()

    cpu_str = f"CPU: {cpu}%" if cpu is not None else "CPU: N/A"
    temp_str = f"Temp: {temp}\u00b0C" if temp is not None else "Temp: N/A"
    rss_str = f"{rss} MB" if rss is not None else "N/A"

    return (
        f"Uptime: {up or 'N/A'}\n"
        f"{cpu_str}\t{temp_str}\n"
        f"RAM: {rss_str} ({used_mb}/{total_mb} total)"
    )
