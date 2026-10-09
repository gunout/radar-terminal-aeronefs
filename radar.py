#!/usr/bin/env python3
# radar_militaire_paris.py - Radar tactique militaire — Paris / Europe

import json
import math
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone

# ============================================================
# Configuration — Paris
# ============================================================
OBS_LAT = 48.85
OBS_LON = 2.35
OBS_ALT = 0.035
R_EARTH = 6371.0
INTERVAL = 15
RAYON_KM = 400

OPENSKY_URL = (
    "https://opensky-network.org/api/states/all"
    "?lamin=35&lomin=-15&lamax=72&lomax=35"
)

# ============================================================
# Palette militaire
# ============================================================
VERT = "\033[38;5;46m"
VERT_DIM = "\033[38;5;28m"
VERT_BRIGHT = "\033[38;5;118m"
AMBRE = "\033[38;5;214m"
ROUGE = "\033[38;5;196m"
BLANC = "\033[38;5;255m"
GRIS = "\033[38;5;240m"
BOLD = "\033[1m"
RESET = "\033[0m"


def strip_ansi(s):
    return re.sub(r'\033\[[0-9;]*m', '', s)


def vlen(s):
    return len(strip_ansi(s))


def pad(s, largeur, align="left"):
    manque = max(0, largeur - vlen(s))
    if align == "left":
        return s + " " * manque
    if align == "right":
        return " " * manque + s
    g = manque // 2
    return " " * g + s + " " * (manque - g)


def ligne(contenu="", couleur=VERT):
    return f"{couleur}║{RESET}" + pad(contenu, 68) + f"{couleur}║{RESET}"


# ============================================================
# Fetch OpenSky
# ============================================================
def fetch_flights():
    try:
        req = urllib.request.Request(
            OPENSKY_URL,
            headers={"User-Agent": "Tactical-Radar/1.0"}
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
    except Exception as e:
        return []

    states = data.get("states", [])
    if not states:
        return []

    flights = []
    for s in states:
        try:
            icao24 = (s[0] or "").lower()
            callsign = (s[1] or "").strip() or icao24
            lon = s[5]
            lat = s[6]
            baro_alt = s[7]
            geo_alt = s[13]
            vel = s[9]
            heading = s[10]
            on_ground = s[8]
            country = s[2] or "—"

            if lat is None or lon is None or on_ground:
                continue

            alt_m = baro_alt if baro_alt is not None else geo_alt
            alt_ft = round(alt_m * 3.28084) if alt_m is not None else None
            vel_kmh = round(vel * 3.6) if vel is not None else None

            flights.append({
                "icao24": icao24,
                "callsign": callsign,
                "lat": lat,
                "lon": lon,
                "alt_m": alt_m,
                "alt_ft": alt_ft,
                "vel_kmh": vel_kmh,
                "heading": heading,
                "country": country,
            })
        except (IndexError, TypeError):
            continue

    return flights


# ============================================================
# Détection militaire
# ============================================================
MILITARY_PREFIXES = [
    "RCH", "REACH", "DUKE", "MAGIC", "HAWK", "VIPER", "TITAN",
    "SPAR", "EVAC", "MEDEVAC", "ASCOT", "FAF", "GAF", "IAM",
    "CFC", "RAAF", "RNZAF", "RRR", "RFR", "GAM",
]


def est_militaire(f):
    cs = f.get("callsign", "").upper()
    return any(cs.startswith(p) for p in MILITARY_PREFIXES)


# ============================================================
# Azimut / élévation
# ============================================================
def az_el(lat_s, lon_s, alt_km):
    lat_r = math.radians(OBS_LAT)
    lon_r = math.radians(OBS_LON)
    lat_ss = math.radians(lat_s)
    lon_ss = math.radians(lon_s)

    ox = (R_EARTH + OBS_ALT) * math.cos(lat_r) * math.cos(lon_r)
    oy = (R_EARTH + OBS_ALT) * math.cos(lat_r) * math.sin(lon_r)
    oz = (R_EARTH + OBS_ALT) * math.sin(lat_r)

    sx = (R_EARTH + alt_km) * math.cos(lat_ss) * math.cos(lon_ss)
    sy = (R_EARTH + alt_km) * math.cos(lat_ss) * math.sin(lon_ss)
    sz = (R_EARTH + alt_km) * math.sin(lat_ss)

    dx, dy, dz = sx - ox, sy - oy, sz - oz

    sl, cl = math.sin(lat_r), math.cos(lat_r)
    so, co = math.sin(lon_r), math.cos(lon_r)

    s = sl * co * dx + sl * so * dy - cl * dz
    e = -so * dx + co * dy
    z = cl * co * dx + cl * so * dy + sl * dz

    dist = math.sqrt(dx*dx + dy*dy + dz*dz)
    az = math.degrees(math.atan2(e, -s)) % 360
    el = math.degrees(math.asin(z / dist))

    return az, el, dist


# ============================================================
# Radar tactique
# ============================================================
def radar_tactique(avions, sweep_idx):
    size = 51
    c = size // 2
    grid = [[" " for _ in range(size)] for _ in range(size)]

    # Cercle extérieur
    for a_deg in range(0, 360, 2):
        a = math.radians(a_deg)
        x = int(round(c + 24 * math.cos(a)))
        y = int(round(c + 24 * math.sin(a)))
        if 0 <= x < size and 0 <= y < size:
            grid[y][x] = f"{VERT_DIM}·{RESET}"

    # Anneaux intermédiaires
    for r in [18, 12, 6]:
        for a_deg in range(0, 360, 6):
            a = math.radians(a_deg)
            x = int(round(c + r * math.cos(a)))
            y = int(round(c + r * math.sin(a)))
            if 0 <= x < size and 0 <= y < size and grid[y][x] == " ":
                grid[y][x] = f"{VERT_DIM}.{RESET}"

    # Graduations tous les 30°
    for a_deg in range(0, 360, 30):
        a = math.radians(a_deg)
        for r in range(22, 25):
            x = int(round(c + r * math.cos(a)))
            y = int(round(c + r * math.sin(a)))
            if 0 <= x < size and 0 <= y < size:
                grid[y][x] = f"{VERT_BRIGHT}+{RESET}"

    # Axes cardinaux
    for i in range(size):
        if grid[c][i] == " ":
            grid[c][i] = f"{VERT_DIM}-{RESET}"
        if grid[i][c] == " ":
            grid[i][c] = f"{VERT_DIM}|{RESET}"

    # Ligne de balayage
    sweep_angle = sweep_idx * 0.15
    for r in range(2, 24):
        x = int(round(c + r * math.cos(sweep_angle)))
        y = int(round(c + r * math.sin(sweep_angle)))
        if 0 <= x < size and 0 <= y < size:
            if grid[y][x] in [" ", f"{VERT_DIM}.{RESET}", f"{VERT_DIM}·{RESET}"]:
                grid[y][x] = f"{VERT_BRIGHT}·{RESET}"

    # Centre
    grid[c][c] = f"{VERT_BRIGHT}{BOLD}O{RESET}"

    # Avions
    for a in avions:
        az = a["az"]
        dist_km = a["dist"]

        r = int(dist_km / RAYON_KM * 23)
        r = max(1, min(23, r))

        angle = math.radians(90 - az)
        x = int(round(c + r * math.cos(angle)))
        y = int(round(c - r * math.sin(angle)))

        if 0 <= x < size and 0 <= y < size:
            alt_ft = a.get("alt_ft") or 0
            if a.get("militaire"):
                grid[y][x] = f"{ROUGE}{BOLD}✈{RESET}"
            elif alt_ft > 30000:
                grid[y][x] = f"{AMBRE}▲{RESET}"
            elif alt_ft > 10000:
                grid[y][x] = f"{VERT_BRIGHT}●{RESET}"
            else:
                grid[y][x] = f"{VERT}○{RESET}"

    # Affichage
    print(f"{VERT}                    ┌─── N (000°) ───┐{RESET}")
    print(f"{VERT}                    │  ALT: 40 000 ft │{RESET}")
    print(f"{VERT}                    └────────┬────────┘{RESET}")

    for i, row in enumerate(grid):
        line = "".join(row)
        if i == c:
            print(f"{VERT}W 270 ─────────────────{RESET}{line}{VERT}───────────────── 090 E{RESET}")
        else:
            print(f"                          {line}")

    print(f"{VERT}                    ┌────────┴────────┐{RESET}")
    print(f"{VERT}                    │   MODE: TACTIQUE │{RESET}")
    print(f"{VERT}                    └─── S (180°) ───┘{RESET}")


# ============================================================
# Affichage
# ============================================================
def afficher(avions, sweep_idx):
    os.system("clear")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    local = datetime.now().strftime("%H:%M:%S")

    avions.sort(key=lambda a: a["dist"])

    civils = [a for a in avions if not a.get("militaire")]
    milis = [a for a in avions if a.get("militaire")]

    print(f"{VERT}╔" + "═" * 68 + f"╗{RESET}")
    print(f"{VERT}║{RESET}" + f"{BOLD}{VERT_BRIGHT}" + " TACTICAL AIR DEFENSE RADAR — PARIS ".center(68) + f"{RESET}" + f"{VERT}║{RESET}")
    print(f"{VERT}║{RESET}" + f"{GRIS}" + " SOURCE: OPENSKY ADS-B // CLASSIFICATION: UNCLASSIFIED ".center(68) + f"{RESET}" + f"{VERT}║{RESET}")
    print(f"{VERT}╠" + "═" * 68 + f"╣{RESET}")
    print(ligne(f"  UTC : {now}   LOCAL : {local} (UTC+2)"))
    print(ligne(f"  CONTACTS : {len(avions):>3}   │   CIVILS : {len(civils):>3}   │   MILITAIRES : {len(milis):>3}"))
    print(ligne(f"  RAYON : {RAYON_KM} km   │   INTERVALLE : {INTERVAL}s   │   STATUT : ACTIF"))
    print(f"{VERT}╠" + "═" * 68 + f"╣{RESET}")

    print()
    radar_tactique(avions, sweep_idx)
    print()

    print(f"  {GRIS}SYMBOLOGIE :{RESET}  "
          f"{VERT}○{RESET} basse alt   "
          f"{VERT_BRIGHT}●{RESET} moyenne   "
          f"{AMBRE}▲{RESET} haute   "
          f"{ROUGE}{BOLD}✈{RESET} militaire")
    print()

    print(f"{VERT}╠" + "═" * 68 + f"╣{RESET}")
    print(ligne("  ANALYSE TACTIQUE", VERT_BRIGHT))
    print(f"{VERT}╠" + "═" * 68 + f"╣{RESET}")

    if avions:
        en_vol = [a for a in avions if a.get("alt_ft")]
        alt_moy = sum(a["alt_ft"] for a in en_vol) / len(en_vol) if en_vol else 0
        vel_moy = sum(a["vel_kmh"] for a in avions if a["vel_kmh"]) / len(avions) if avions else 0
        plus_proche = avions[0]

        print(ligne(f"  ALTITUDE MOYENNE  : {alt_moy:>10.0f} ft"))
        print(ligne(f"  VITESSE MOYENNE   : {vel_moy:>10.0f} km/h"))
        print(ligne(f"  CONTACT LE + PROCHE : {plus_proche['callsign']:<10} à {plus_proche['dist']:.1f} km"))
        print(ligne(f"  AZIMUT            : {plus_proche['az']:>5.1f}°   ÉLÉVATION : {plus_proche['el']:>5.1f}°"))
    else:
        print(ligne("  AUCUN CONTACT DANS LA ZONE.", AMBRE))

    print(f"{VERT}╠" + "═" * 68 + f"╣{RESET}")
    print(ligne("  PISTE DE CONTACTS (TOP 15)", VERT_BRIGHT))
    print(f"{VERT}╠" + "═" * 68 + f"╣{RESET}")

    W_CS, W_ALT, W_VEL, W_DIST, W_AZ = 10, 8, 8, 8, 7

    header = (f"  {'CALLSIGN':<{W_CS}} {'ALT ft':>{W_ALT}} {'VIT km/h':>{W_VEL}} "
              f"{'DIST km':>{W_DIST}} {'AZ°':>{W_AZ}}")
    print(ligne(header, VERT_BRIGHT))

    positions = []
    p = 2 + W_CS
    positions.append(p)
    p += 1 + W_ALT
    positions.append(p)
    p += 1 + W_VEL
    positions.append(p)
    p += 1 + W_DIST
    positions.append(p)

    parts = []
    prev = 0
    for pos in positions:
        parts.append("─" * (pos - prev))
        parts.append("┼")
        prev = pos + 1
    parts.append("─" * max(0, 68 - prev))
    print(f"{VERT}╠" + "".join(parts) + f"╣{RESET}")

    for a in avions[:15]:
        cs = a["callsign"][:W_CS]
        alt = f"{a['alt_ft']:>{W_ALT}}" if a['alt_ft'] else f"{'—':>{W_ALT}}"
        vel = f"{a['vel_kmh']:>{W_VEL}}" if a['vel_kmh'] else f"{'—':>{W_VEL}}"
        dist = f"{a['dist']:>{W_DIST}.1f}"
        az = f"{a['az']:>{W_AZ}.1f}"

        contenu = f"  {cs:<{W_CS}} {alt} {vel} {dist} {az}"
        couleur = ROUGE if a.get("militaire") else VERT
        print(ligne(contenu, couleur))

    print(f"{VERT}╚" + "═" * 68 + f"╝{RESET}")
    print(f"  {GRIS}RAFRAÎCHISSEMENT DANS {INTERVAL}s... (CTRL+C POUR QUITTER){RESET}")


# ============================================================
# Main
# ============================================================
def main():
    print(f"{VERT}INITIALISATION DU RADAR TACTIQUE — PARIS...{RESET}")
    sweep_idx = 0
    try:
        while True:
            flights = fetch_flights()

            avions = []
            for f in flights:
                alt_km = (f["alt_m"] / 1000) if f["alt_m"] else 10
                az, el, dist = az_el(f["lat"], f["lon"], alt_km)

                if dist > RAYON_KM:
                    continue

                f["az"] = az
                f["el"] = el
                f["dist"] = dist
                f["militaire"] = est_militaire(f)
                avions.append(f)

            afficher(avions, sweep_idx)
            sweep_idx += 1
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print(f"\n{AMBRE}RADAR TACTIQUE ARRÊTÉ.{RESET}")


if __name__ == "__main__":
    main()