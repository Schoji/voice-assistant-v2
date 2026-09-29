"""wi-fi setup: aleksy puts up his own hotspot when he has no network

NetworkManager does the actual work through nmcli, this only decides when to
switch and keeps the state the panel shows. Needs the polkit rule and the
captive portal bits from deploy/client/setup-wifi.sh.
"""
import os
import re
import subprocess
import threading
import time

import config

HOTSPOT = "aleksy-hotspot"
# a new network is tried under this name first, so a typo in the password never touches a profile that works
CANDIDATE = "aleksy-candidate"
# terse nmcli output is translated otherwise
ENV = {**os.environ, "LC_ALL": "C"}

_lock = threading.Lock() # one reconfiguration at a time: the watchdog, a connect or a scan
_state = {"mode": "starting", "connection": None, "ip": None, "busy": None, "error": None, "networks": []}
_offline_since = None
_hotspot_since = 0.0
_last_visit = 0.0
_warned_no_password = False


class NmcliError(RuntimeError):
    pass


def _nmcli(*args, timeout=45):
    r = subprocess.run(["nmcli", *args], capture_output=True, text=True, timeout=timeout, env=ENV)
    if r.returncode != 0:
        raise NmcliError((r.stderr or r.stdout).strip().removeprefix("Error: ") or f"nmcli zwrócił {r.returncode}")
    return r.stdout


def _rows(out):
    """splits terse output, where a ':' inside a value comes escaped as '\\:'"""
    return [[f.replace("\\:", ":") for f in re.split(r"(?<!\\):", line)] for line in out.splitlines() if line]


def _devices():
    return _rows(_nmcli("-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"))


def _online():
    """the connection that puts us on a network (wi-fi or cable), None without one"""
    for _, kind, state, conn in _devices():
        if kind in ("wifi", "ethernet") and state == "connected" and conn != HOTSPOT:
            return conn
    return None


def _hotspot_up():
    return any(conn == HOTSPOT and state == "connected" for _, _, state, conn in _devices())


def _ip():
    out = _nmcli("-g", "IP4.ADDRESS", "device", "show", config.WIFI_IFACE).strip()
    return out.split("|")[0].split("/")[0] or None


def _scan(rescan):
    out = _nmcli("-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list",
                 "ifname", config.WIFI_IFACE, "--rescan", rescan)
    best = {}
    for ssid, signal, security in _rows(out):
        if ssid and ssid != config.HOTSPOT_SSID and (ssid not in best or int(signal) > best[ssid]["signal"]):
            best[ssid] = {"ssid": ssid, "signal": int(signal), "secure": security not in ("", "--")}
    return sorted(best.values(), key=lambda n: -n["signal"])


def _saved():
    saved = []
    for name, kind in _rows(_nmcli("-t", "-f", "NAME,TYPE", "connection", "show")):
        if kind == "802-11-wireless" and name not in (HOTSPOT, CANDIDATE):
            ssid = _nmcli("-g", "802-11-wireless.ssid", "connection", "show", "id", name).strip().replace("\\:", ":")
            saved.append({"name": name, "ssid": ssid})
    return saved


def _delete(name):
    subprocess.run(["nmcli", "connection", "delete", "id", name], capture_output=True, env=ENV)


def _hotspot_password():
    try:
        with open(config.HOTSPOT_PASSWORD_FILE) as f:
            return f.read().strip() or None
    except OSError:
        return None


def _start_hotspot():
    global _hotspot_since
    password = _hotspot_password()
    # scanning barely works once the radio is an access point, so remember what is around now
    try:
        _state["networks"] = _scan("yes")
    except (NmcliError, subprocess.TimeoutExpired):
        pass
    print(f"Wi-Fi: brak sieci, włączam hotspot {config.HOTSPOT_SSID}", flush=True)
    # recreated every time so a changed ssid or password in config takes effect
    _delete(HOTSPOT)
    _nmcli("connection", "add", "type", "wifi", "ifname", config.WIFI_IFACE, "con-name", HOTSPOT,
           "autoconnect", "no", "ssid", config.HOTSPOT_SSID,
           "802-11-wireless.mode", "ap", "802-11-wireless.band", "bg",
           "ipv4.method", "shared", "ipv4.addresses", f"{config.HOTSPOT_IP}/24", "ipv6.method", "disabled",
           # the pi's broadcom chip only brings the AP up with plain WPA2/CCMP
           "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.proto", "rsn",
           "wifi-sec.pairwise", "ccmp", "wifi-sec.group", "ccmp", "wifi-sec.psk", password)
    _nmcli("connection", "up", "id", HOTSPOT)
    _hotspot_since = time.time()


def _leave_hotspot():
    if _hotspot_up():
        _nmcli("connection", "down", "id", HOTSPOT)
        time.sleep(2)
    try:
        _nmcli("device", "wifi", "rescan", "ifname", config.WIFI_IFACE)
        time.sleep(5)
    except NmcliError:
        pass # a scan was already running


def _try_saved():
    """drops the hotspot and tries every saved network in range, True once one works"""
    _leave_hotspot()
    visible = {n["ssid"] for n in _scan("no")}
    for profile in _saved():
        if profile["ssid"] in visible:
            try:
                _nmcli("--wait", "30", "connection", "up", "id", profile["name"])
                return True
            except (NmcliError, subprocess.TimeoutExpired) as e:
                print(f"Wi-Fi: {profile['name']} nie działa: {e}", flush=True)
    return False


def _hotspot_in_use():
    if time.time() - _last_visit < config.HOTSPOT_RETRY:
        return True
    try:
        out = subprocess.run(["iw", "dev", config.WIFI_IFACE, "station", "dump"],
                             capture_output=True, text=True, timeout=5).stdout
        return "Station" in out
    except (OSError, subprocess.TimeoutExpired):
        return False


def _tick():
    global _offline_since, _hotspot_since, _warned_no_password
    conn = _online()
    if conn:
        _offline_since = None
        _state.update(mode="client", connection=conn, ip=_ip())
    elif _hotspot_up():
        _hotspot_since = _hotspot_since or time.time() # already up when the client restarted
        _state.update(mode="hotspot", connection=config.HOTSPOT_SSID, ip=config.HOTSPOT_IP)
        # the router may be back after a power cut, but not while someone is setting things up
        if time.time() - _hotspot_since >= config.HOTSPOT_RETRY and not _hotspot_in_use():
            _state["busy"] = "szukam zapisanych sieci"
            if not _try_saved():
                _start_hotspot()
    else:
        _state.update(mode="offline", connection=None, ip=None)
        _offline_since = _offline_since or time.time()
        if time.time() - _offline_since < config.HOTSPOT_AFTER:
            return
        if not _hotspot_password():
            if not _warned_no_password:
                print(f"Wi-Fi: brak {config.HOTSPOT_PASSWORD_FILE}, hotspot wyłączony (deploy/client/setup-wifi.sh)", flush=True)
                _warned_no_password = True
            return
        _start_hotspot()
        _offline_since = None


def _watch():
    while True:
        try:
            with _lock:
                _tick()
        except (NmcliError, subprocess.TimeoutExpired, OSError) as e:
            print(f"Wi-Fi: {e}", flush=True)
        finally:
            _state["busy"] = None
        time.sleep(config.WIFI_CHECK_EVERY)


def _connect(ssid, password):
    with _lock:
        _state.update(busy=f"łączę z {ssid}", error=None)
        try:
            _leave_hotspot()
            _delete(CANDIDATE)
            args = ["connection", "add", "type", "wifi", "ifname", config.WIFI_IFACE,
                    "con-name", CANDIDATE, "ssid", ssid]
            if password:
                args += ["wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password]
            _nmcli(*args)
            _nmcli("--wait", "30", "connection", "up", "id", CANDIDATE)
            # it works, so it replaces whatever was saved for this network before
            for profile in _saved():
                if profile["ssid"] == ssid:
                    _delete(profile["name"])
            _nmcli("connection", "modify", "id", CANDIDATE, "connection.id", ssid)
            print(f"Wi-Fi: połączono z {ssid}", flush=True)
        except (NmcliError, subprocess.TimeoutExpired) as e:
            print(f"Wi-Fi: nie udało się połączyć z {ssid}: {e}", flush=True)
            _state["error"] = f"Nie udało się połączyć z {ssid} (złe hasło albo za słaby sygnał)."
            _delete(CANDIDATE)
            try:
                if not _online() and not _try_saved():
                    _start_hotspot()
            except (NmcliError, subprocess.TimeoutExpired) as e:
                print(f"Wi-Fi: {e}", flush=True)
        finally:
            _state["busy"] = None


def connect(ssid, password):
    """returns straight away: the answer has to reach the phone before the hotspot goes down"""
    _state.update(busy=f"łączę z {ssid}", error=None)

    def later():
        time.sleep(2)
        _connect(ssid, password)
    threading.Thread(target=later, name="wifi-connect", daemon=True).start()


def forget(name):
    with _lock:
        _delete(name)


def scan():
    """a fresh list when the radio is free, otherwise the last one"""
    if _lock.acquire(blocking=False):
        try:
            _state["networks"] = _scan("yes")
        except (NmcliError, subprocess.TimeoutExpired):
            pass
        finally:
            _lock.release()
    return _state["networks"]


def visit():
    global _last_visit
    _last_visit = time.time()


def hotspot_active():
    return _state["mode"] == "hotspot"


def snapshot():
    try:
        saved = _saved()
    except (NmcliError, subprocess.TimeoutExpired):
        saved = []
    return {**_state, "saved": saved, "hotspot_ssid": config.HOTSPOT_SSID}


def start():
    threading.Thread(target=_watch, name="wifi", daemon=True).start()
