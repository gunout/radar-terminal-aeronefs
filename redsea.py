#!/usr/bin/env python3
# radar_tout_en_un.py - Radar + CSV + Fusion + Stats + GeoJSON
# Tout-en-un : surveillance, journalisation, analyse, export géographique

import csv
import glob
import json
import math
import os
import re
import sys
import time
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

# ============================================================
# Configuration
# ============================================================
POINTS_SCAN = [
    ("Sanaa (Yémen)",           15.37, 44.19, 3),
    ("Aden (Yémen)",            12.79, 45.03, 3),
    ("Djibouti",                11.55, 43.15, 3),
    ("Bab el-Mandeb",           12.58, 43.33, 3),
    ("Djeddah (Arabie saoudite)",21.49, 39.19, 3),
    ("Riyad (Arabie saoudite)", 24.71, 46.67, 3),
    ("Dubaï (EAU)",             25.25, 55.36, 4),
    ("Abu Dhabi (EAU)",         24.43, 54.65, 4),
    ("Doha (Qatar)",            25.27, 51.60, 3),
    ("Koweït",                  29.22, 47.98, 3),
    ("Mascate (Oman)",          23.59, 58.41, 4),
    ("Détroit d'Ormuz",         26.57, 56.25, 4),
    ("Bahreïn",                 26.07, 50.55, 3),
    ("Téhéran (Iran)",          35.69, 51.39, 3.5),
    ("Bagdad (Irak)",           33.31, 44.36, 3),
    ("Le Caire (Égypte)",       30.04, 31.24, 2),
    ("Khartoum (Soudan)",       15.50, 32.56, 2),
    ("Addis-Abeba (Éthiopie)",   8.98, 38.80, 3),
    ("Karachi (Pakistan)",      24.86, 67.01, 5),
    ("Mumbai (Inde)",           19.09, 72.87, 5.5),
]

RAYON_NM = 250
INTERVAL = 15
RESCAN_PERIOD = 30 * 60
CSV_DIR = "radar_logs"
ROTATION_HORAIRE = True   # True = 1 fichier/heure, False = 1 fichier/jour

# ============================================================
# Palette
# ============================================================
VERT = "\033[38;5;46m"
VERT_DIM = "\033[38;5;28m"
VERT_BRIGHT = "\033[38;5;118m"
AMBRE = "\033[38;5;214m"
ROUGE = "\033[38;5;196m"
BLANC = "\033[38;5;255m"
GRIS = "\033[38;5;240m"
CYAN = "\033[38;5;51m"
MAGENTA = "\033[38;5;201m"
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


# ============================================================
# Détection militaire
# ============================================================
MILITARY_PREFIXES = [
    "RCH", "REACH", "DUKE", "MAGIC", "HAWK", "VIPER", "TITAN",
    "SPAR", "EVAC", "MEDEVAC", "ASCOT", "JAKE", "HOMER", "PYTHON",
    "RRR", "RFR", "TARTAN", "FAF", "COTAM", "CTM",
    "GAF", "GAM", "IAM", "CFC", "CANFORCE",
    "RAAF", "RNZAF", "AUSSIE", "KIWI",
    "SVA", "UAE", "KSA", "RSF", "BAHRAIN", "QAF", "KAF",
    "THK", "TURK", "EGY", "JOR", "RAM",
    "NATO", "AWACS", "SENTRY", "TANKER",
    "UAV", "RQ", "MQ", "FORTE", "GLOBAL",
]

MILITARY_ICAO_PREFIXES = [
    "ae", "43c", "3f", "38", "44", "48", "4b",
    "71", "76", "06", "70", "72", "73", "4d", "45",
]


def detecter_militaire(icao24, callsign):
    cs = (callsign or "").upper()
    for p in MILITARY_PREFIXES:
        if cs.startswith(p):
            return True, "callsign"
    icao = (icao24 or "").lower()
    for p in MILITARY_ICAO_PREFIXES:
        if icao.startswith(p):
            return True, "icao24"
    return False, None


def est_militaire(icao24, callsign):
    return detecter_militaire(icao24, callsign)[0]


# ============================================================
# Gestion CSV
# ============================================================
CSV_HEADER = [
    "timestamp_utc", "timestamp_local", "zone",
    "icao24", "callsign", "lat", "lon",
    "alt_ft", "alt_m", "vel_kmh", "heading",
    "az", "el", "dist_km",
    "militaire", "type_detection",
]


def init_csv_dir():
    if not os.path.exists(CSV_DIR):
        os.makedirs(CSV_DIR)


def csv_filename():
    now = datetime.now()
    if ROTATION_HORAIRE:
        return os.path.join(CSV_DIR, f"radar_contacts_{now.strftime('%Y%m%d_%H')}.csv")
    return os.path.join(CSV_DIR, f"radar_contacts_{now.strftime('%Y%m%d')}.csv")


def exporter_csv(zone_nom, avions):
    if not avions:
        return
    init_csv_dir()
    chemin = csv_filename()
    nouveau = not os.path.exists(chemin)
    try:
        with open(chemin, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if nouveau:
                writer.writerow(CSV_HEADER)
            now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            now_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for a in avions:
                writer.writerow([
                    now_utc, now_local, zone_nom,
                    a.get("icao24", ""), a.get("callsign", ""),
                    f"{a.get('lat', 0):.6f}", f"{a.get('lon', 0):.6f}",
                    a.get("alt_ft", ""), a.get("alt_m", ""),
                    a.get("vel_kmh", ""),
                    f"{a.get('heading', 0):.1f}" if a.get("heading") is not None else "",
                    f"{a.get('az', 0):.1f}", f"{a.get('el', 0):.2f}",
                    f"{a.get('dist', 0):.2f}",
                    "OUI" if a.get("militaire") else "NON",
                    a.get("type_detection") or "",
                ])
    except Exception as e:
        print(f"{ROUGE}Erreur écriture CSV: {e}{RESET}")


# ============================================================
# Fetch adsb.lol
# ============================================================
def fetch_point(nom, lat, lon, tz):
    url = f"https://api.adsb.lol/v2/point/{lat}/{lon}/{RAYON_NM}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Tactical-Radar/4.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        aircraft = data.get("ac") or []
        nb_milis = sum(
            1 for a in aircraft
            if est_militaire(a.get("hex", ""), (a.get("flight") or "").strip())
        )
        return {
            "nom": nom, "lat": lat, "lon": lon, "tz": tz,
            "total": len(aircraft), "militaires": nb_milis,
            "aircraft": aircraft, "erreur": None,
        }
    except Exception as e:
        return {
            "nom": nom, "lat": lat, "lon": lon, "tz": tz,
            "total": 0, "militaires": 0, "aircraft": [], "erreur": str(e)[:40],
        }


# ============================================================
# Azimut / élévation
# ============================================================
def az_el(obs_lat, obs_lon, obs_alt, lat_s, lon_s, alt_km):
    R_EARTH = 6371.0
    lat_r = math.radians(obs_lat); lon_r = math.radians(obs_lon)
    lat_ss = math.radians(lat_s); lon_ss = math.radians(lon_s)
    ox = (R_EARTH + obs_alt) * math.cos(lat_r) * math.cos(lon_r)
    oy = (R_EARTH + obs_alt) * math.cos(lat_r) * math.sin(lon_r)
    oz = (R_EARTH + obs_alt) * math.sin(lat_r)
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
# Transformation
# ============================================================
def transformer_avions(aircraft_list, obs_lat, obs_lon, obs_alt, rayon_km):
    avions = []
    for a in aircraft_list:
        try:
            icao24 = (a.get("hex") or "").lower()
            callsign = (a.get("flight") or "").strip() or icao24
            lat = a.get("lat"); lon = a.get("lon")
            alt_baro = a.get("alt_baro")
            gs = a.get("gs"); track = a.get("track")
            if lat is None or lon is None:
                continue
            if alt_baro == "ground" or alt_baro is None:
                alt_ft = 0
            else:
                try:
                    alt_ft = int(alt_baro)
                except (ValueError, TypeError):
                    alt_ft = 0
            alt_m = round(alt_ft * 0.3048) if alt_ft else 0
            vel_kmh = round(gs * 1.852) if gs is not None else None
            alt_km = (alt_m / 1000) if alt_m else 0.1
            az, el, dist = az_el(obs_lat, obs_lon, obs_alt, lat, lon, alt_km)
            if dist > rayon_km:
                continue
            mil, type_det = detecter_militaire(icao24, callsign)
            avions.append({
                "icao24": icao24, "callsign": callsign,
                "lat": lat, "lon": lon,
                "alt_m": alt_m, "alt_ft": alt_ft,
                "vel_kmh": vel_kmh, "heading": track,
                "az": az, "el": el, "dist": dist,
                "militaire": mil, "type_detection": type_det,
            })
        except Exception:
            continue
    return avions


# ============================================================
# Radar tactique
# ============================================================
def radar_tactique(avions, sweep_idx, rayon_km):
    size = 51; c = size // 2
    grid = [[" " for _ in range(size)] for _ in range(size)]
    for a_deg in range(0, 360, 2):
        a = math.radians(a_deg)
        x = int(round(c + 24 * math.cos(a)))
        y = int(round(c + 24 * math.sin(a)))
        if 0 <= x < size and 0 <= y < size:
            grid[y][x] = f"{VERT_DIM}·{RESET}"
    for r in [18, 12, 6]:
        for a_deg in range(0, 360, 6):
            a = math.radians(a_deg)
            x = int(round(c + r * math.cos(a)))
            y = int(round(c + r * math.sin(a)))
            if 0 <= x < size and 0 <= y < size and grid[y][x] == " ":
                grid[y][x] = f"{VERT_DIM}.{RESET}"
    for a_deg in range(0, 360, 30):
        a = math.radians(a_deg)
        for r in range(22, 25):
            x = int(round(c + r * math.cos(a)))
            y = int(round(c + r * math.sin(a)))
            if 0 <= x < size and 0 <= y < size:
                grid[y][x] = f"{VERT_BRIGHT}+{RESET}"
    for i in range(size):
        if grid[c][i] == " ": grid[c][i] = f"{VERT_DIM}-{RESET}"
        if grid[i][c] == " ": grid[i][c] = f"{VERT_DIM}|{RESET}"
    sweep_angle = sweep_idx * 0.15
    for r in range(2, 24):
        x = int(round(c + r * math.cos(sweep_angle)))
        y = int(round(c + r * math.sin(sweep_angle)))
        if 0 <= x < size and 0 <= y < size:
            if grid[y][x] in [" ", f"{VERT_DIM}.{RESET}", f"{VERT_DIM}·{RESET}"]:
                grid[y][x] = f"{VERT_BRIGHT}·{RESET}"
    grid[c][c] = f"{VERT_BRIGHT}{BOLD}O{RESET}"
    for a in avions:
        az = a["az"]; dist_km = a["dist"]
        r = int(dist_km / rayon_km * 23)
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
# Affichage radar principal
# ============================================================
def afficher_radar(point, avions, sweep_idx, rayon_km, mode_label=""):
    os.system("clear")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    local = datetime.now().strftime("%H:%M:%S")
    avions.sort(key=lambda a: a["dist"])
    civils = [a for a in avions if not a.get("militaire")]
    milis = [a for a in avions if a.get("militaire")]
    print(f"{VERT}╔" + "═" * 68 + f"╗{RESET}")
    titre = f" TACTICAL AIR DEFENSE RADAR — {point['nom'].upper()} "
    print(f"{VERT}║{RESET}" + f"{BOLD}{VERT_BRIGHT}" + titre.center(68) + f"{RESET}" + f"{VERT}║{RESET}")
    sous_titre = f" SOURCE: ADSB.LOL // POS: {point['lat']:.2f}°N {point['lon']:.2f}°E {mode_label}"
    print(f"{VERT}║{RESET}" + f"{GRIS}" + sous_titre.center(68) + f"{RESET}" + f"{VERT}║{RESET}")
    print(f"{VERT}╠" + "═" * 68 + f"╣{RESET}")
    print(f"{VERT}║{RESET}" + pad(f"  UTC : {now}   LOCAL : {local}", 68) + f"{VERT}║{RESET}")
    print(f"{VERT}║{RESET}" + pad(f"  CONTACTS : {len(avions):>3}   │   CIVILS : {len(civils):>3}   │   MILITAIRES : {len(milis):>3}", 68) + f"{VERT}║{RESET}")
    rot = "HORAIRE" if ROTATION_HORAIRE else "JOURNALIÈRE"
    print(f"{VERT}║{RESET}" + pad(f"  RAYON : {rayon_km:.0f} km ({RAYON_NM} nm)   │   CSV : {rot}", 68) + f"{VERT}║{RESET}")
    print(f"{VERT}╠" + "═" * 68 + f"╣{RESET}")
    print()
    radar_tactique(avions, sweep_idx, rayon_km)
    print()
    print(f"  {GRIS}SYMBOLOGIE :{RESET}  "
          f"{VERT}○{RESET} basse alt   "
          f"{VERT_BRIGHT}●{RESET} moyenne   "
          f"{AMBRE}▲{RESET} haute   "
          f"{ROUGE}{BOLD}✈{RESET} militaire")
    print()
    print(f"{VERT}╠" + "═" * 68 + f"╣{RESET}")
    print(f"{VERT}║{RESET}" + f"{VERT_BRIGHT}  ANALYSE TACTIQUE{RESET}".ljust(76) + f"{VERT}║{RESET}")
    print(f"{VERT}╠" + "═" * 68 + f"╣{RESET}")
    if avions:
        en_vol = [a for a in avions if a.get("alt_ft")]
        alt_moy = sum(a["alt_ft"] for a in en_vol) / len(en_vol) if en_vol else 0
        vel_moy = sum(a["vel_kmh"] for a in avions if a["vel_kmh"]) / len(avions) if avions else 0
        pp = avions[0]
        print(f"{VERT}║{RESET}" + pad(f"  ALTITUDE MOYENNE  : {alt_moy:>10.0f} ft", 68) + f"{VERT}║{RESET}")
        print(f"{VERT}║{RESET}" + pad(f"  VITESSE MOYENNE   : {vel_moy:>10.0f} km/h", 68) + f"{VERT}║{RESET}")
        print(f"{VERT}║{RESET}" + pad(f"  CONTACT LE + PROCHE : {pp['callsign']:<10} à {pp['dist']:.1f} km", 68) + f"{VERT}║{RESET}")
        print(f"{VERT}║{RESET}" + pad(f"  AZIMUT            : {pp['az']:>5.1f}°   ÉLÉVATION : {pp['el']:>5.1f}°", 68) + f"{VERT}║{RESET}")
    else:
        print(f"{VERT}║{RESET}" + pad("  AUCUN CONTACT DANS LA ZONE.", 68) + f"{VERT}║{RESET}")
    print(f"{VERT}╠" + "═" * 68 + f"╣{RESET}")
    print(f"{VERT}║{RESET}" + f"{VERT_BRIGHT}  PISTE DE CONTACTS (TOP 15){RESET}".ljust(76) + f"{VERT}║{RESET}")
    print(f"{VERT}╠" + "═" * 68 + f"╣{RESET}")
    W_CS, W_ALT, W_VEL, W_DIST, W_AZ = 10, 8, 8, 8, 7
    header = (f"  {'CALLSIGN':<{W_CS}} {'ALT ft':>{W_ALT}} {'VIT km/h':>{W_VEL}} "
              f"{'DIST km':>{W_DIST}} {'AZ°':>{W_AZ}}")
    print(f"{VERT}║{RESET}" + pad(header, 68, "left") + f"{VERT}║{RESET}")
    for a in avions[:15]:
        cs = a["callsign"][:W_CS]
        alt = f"{a['alt_ft']:>{W_ALT}}" if a['alt_ft'] else f"{'—':>{W_ALT}}"
        vel = f"{a['vel_kmh']:>{W_VEL}}" if a['vel_kmh'] else f"{'—':>{W_VEL}}"
        dist = f"{a['dist']:>{W_DIST}.1f}"
        az = f"{a['az']:>{W_AZ}.1f}"
        marqueur = ""
        if a.get("type_detection") == "icao24":
            marqueur = " [I]"
        elif a.get("type_detection") == "callsign":
            marqueur = " [C]"
        contenu = f"  {cs:<{W_CS}} {alt} {vel} {dist} {az}{marqueur}"
        couleur = ROUGE if a.get("militaire") else VERT
        print(f"{couleur}║{RESET}" + pad(contenu, 68) + f"{couleur}║{RESET}")
    print(f"{VERT}╚" + "═" * 68 + f"╝{RESET}")
    print(f"  {GRIS}RAFRAÎCHISSEMENT DANS {INTERVAL}s... (CTRL+C POUR QUITTER){RESET}")


# ============================================================
# Menu
# ============================================================
def menu():
    os.system("clear")
    print(f"{VERT_BRIGHT}{BOLD}")
    print("╔" + "═" * 68 + "╗")
    print("║" + "  RADAR TACTIQUE TOUT-EN-UN — MENU".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print(f"{RESET}")
    print(f"  {GRIS}Modes de surveillance :{RESET}\n")
    print(f"  {VERT_BRIGHT}[1]{RESET} {VERT}Auto — plus grand nombre de contacts{RESET}")
    print(f"  {VERT_BRIGHT}[2]{RESET} {VERT}Militaire — priorité aux avions militaires{RESET}")
    print(f"  {VERT_BRIGHT}[3]{RESET} {VERT}Manuel — vous choisissez la zone{RESET}")
    print(f"  {VERT_BRIGHT}[4]{RESET} {VERT}Re-scan périodique — bascule auto toutes les 30 min{RESET}")
    print()
    print(f"  {GRIS}Outils d'analyse :{RESET}\n")
    print(f"  {VERT_BRIGHT}[5]{RESET} {VERT}Fusionner tous les CSV + statistiques{RESET}")
    print(f"  {VERT_BRIGHT}[6]{RESET} {VERT}Exporter les trajectoires en GeoJSON{RESET}")
    print(f"  {VERT_BRIGHT}[7]{RESET} {VERT}Fusion + GeoJSON + stats (complet){RESET}")
    print(f"  {VERT_BRIGHT}[8]{RESET} {VERT}Filtrer par date (fusion partielle){RESET}")
    print(f"  {VERT_BRIGHT}[9]{RESET} {VERT}Exporter par zone (1 CSV par zone){RESET}")
    print()
    print(f"  {GRIS}CSV dans ./{CSV_DIR}/ — rotation {'horaire' if ROTATION_HORAIRE else 'journalière'}{RESET}")
    print()
    choix = input(f"  {AMBRE}Votre choix [1-9] (défaut 1) : {RESET}").strip() or "1"
    if choix not in [str(i) for i in range(1, 10)]:
        choix = "1"
    return int(choix)


# ============================================================
# Scan
# ============================================================
def scanner_points():
    os.system("clear")
    print(f"{VERT_BRIGHT}{BOLD}")
    print("╔" + "═" * 68 + "╗")
    print("║" + "  SCAN AUTOMATIQUE — MOYEN-ORIENT / GOLFE / MER ROUGE".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print(f"{RESET}")
    print(f"  {GRIS}Interrogation en parallèle...{RESET}\n")
    resultats = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {
            ex.submit(fetch_point, nom, lat, lon, tz): (nom, lat, lon, tz)
            for nom, lat, lon, tz in POINTS_SCAN
        }
        for i, fut in enumerate(as_completed(futures), 1):
            res = fut.result()
            resultats.append(res)
            statut = f"{VERT}OK {RESET}" if not res["erreur"] else f"{ROUGE}ERR{RESET}"
            mil = f"{ROUGE}{res['militaires']:>2} mil{RESET}" if res["militaires"] else f"{GRIS} 0 mil{RESET}"
            print(f"  [{i:>2}/{len(POINTS_SCAN)}] {statut}  "
                  f"{res['nom']:<28} {res['total']:>4} av  {mil}")
    print()
    return resultats


# ============================================================
# Classement
# ============================================================
def score_auto(r): return r["total"]
def score_militaire(r): return r["militaires"] * 3 + r["total"]


def afficher_classement(resultats, mode, top_n=10):
    if mode == 2:
        score_fn = score_militaire
        titre = "  CLASSEMENT — PRIORITÉ MILITAIRE (3×mil + civils)"
    else:
        score_fn = score_auto
        titre = "  CLASSEMENT — TRAFIC TOTAL"
    resultats_tries = sorted(resultats, key=score_fn, reverse=True)
    print(f"{VERT_BRIGHT}{BOLD}")
    print("╔" + "═" * 68 + "╗")
    print("║" + titre.center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print(f"{RESET}")
    print(f"  {GRIS}{'#':<4}{'ZONE':<28}{'AVIONS':>8}{'MIL':>6}{'SCORE':>8}{RESET}")
    print(f"  {VERT_DIM}" + "─" * 58 + f"{RESET}")
    for i, r in enumerate(resultats_tries[:top_n], 1):
        score = score_fn(r)
        if i == 1:
            couleur = VERT_BRIGHT + BOLD; marqueur = " ★"
        elif i <= 3:
            couleur = VERT_BRIGHT; marqueur = " "
        elif r["total"] > 0:
            couleur = VERT; marqueur = " "
        else:
            couleur = GRIS; marqueur = " "
        mil_couleur = ROUGE if r["militaires"] > 0 else GRIS
        print(f"  {couleur}{i:<4}{r['nom']:<28}{r['total']:>8}{marqueur}"
              f"{mil_couleur}{r['militaires']:>6}{RESET}"
              f"{couleur}{score:>8}{RESET}")
    print()
    return resultats_tries


# ============================================================
# Fusion CSV
# ============================================================
def lister_csv():
    pattern = os.path.join(CSV_DIR, "radar_contacts_*.csv")
    fichiers = [f for f in glob.glob(pattern)
                if "FUSION" not in f and "zone_" not in f]
    return sorted(fichiers)


def lire_csv(chemin):
    lignes = []
    try:
        with open(chemin, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                lignes.append(row)
    except Exception as e:
        print(f"  ERREUR lecture {chemin}: {e}")
    return lignes


def deduplication(lignes):
    vus = set(); uniques = []
    for l in lignes:
        ts = l.get("timestamp_utc", "")[:16]
        cle = (l.get("icao24", ""), ts)
        if cle not in vus:
            vus.add(cle); uniques.append(l)
    return uniques


def fusionner_csv(dedup=True, date_debut=None, date_fin=None):
    if not os.path.exists(CSV_DIR):
        print(f"  Dossier {CSV_DIR}/ introuvable.")
        return []
    fichiers = lister_csv()
    if not fichiers:
        print(f"  Aucun CSV trouvé.")
        return []
    print(f"\n{'═' * 68}")
    print(f"  FUSION DES CSV RADAR")
    if date_debut or date_fin:
        print(f"  Filtre : du {date_debut or '...'} au {date_fin or '...'}")
    print(f"{'═' * 68}\n")
    toutes = []
    for i, f in enumerate(fichiers, 1):
        lignes = lire_csv(f)
        # Filtre temporel
        if date_debut:
            lignes = [l for l in lignes if l.get("timestamp_utc", "") >= date_debut]
        if date_fin:
            lignes = [l for l in lignes if l.get("timestamp_utc", "") <= date_fin + " 23:59:59"]
        taille = os.path.getsize(f) / 1024
        print(f"  [{i:>2}/{len(fichiers)}] {os.path.basename(f):<42} "
              f"{len(lignes):>6} lignes  ({taille:.1f} Ko)")
        toutes.extend(lignes)
    print(f"\n  Total brut : {len(toutes)} lignes")
    if dedup:
        avant = len(toutes)
        toutes = deduplication(toutes)
        print(f"  Après déduplication : {len(toutes)} lignes "
              f"({avant - len(toutes)} doublons)")
    toutes.sort(key=lambda l: l.get("timestamp_utc", ""))
    return toutes


def ecrire_fusion(lignes):
    if not lignes:
        return
    chemin = os.path.join(CSV_DIR, "radar_contacts_FUSION.csv")
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=lignes[0].keys())
        writer.writeheader()
        writer.writerows(lignes)
    taille = os.path.getsize(chemin) / 1024
    print(f"\n  Fichier fusion : {chemin}")
    print(f"  {len(lignes)} lignes — {taille:.1f} Ko")


def statistiques(lignes):
    if not lignes:
        return
    print(f"\n{'═' * 68}")
    print(f"  STATISTIQUES")
    print(f"{'═' * 68}\n")
    icaos = set(l.get("icao24", "") for l in lignes)
    print(f"  Contacts uniques (ICAO24)  : {len(icaos):>8}")
    milis = [l for l in lignes if l.get("militaire") == "OUI"]
    civils = [l for l in lignes if l.get("militaire") != "OUI"]
    print(f"  Lignes militaires          : {len(milis):>8} ({100*len(milis)/len(lignes):.1f}%)")
    print(f"  Lignes civiles             : {len(civils):>8} ({100*len(civils)/len(lignes):.1f}%)")
    det_cs = [l for l in lignes if l.get("type_detection") == "callsign"]
    det_ic = [l for l in lignes if l.get("type_detection") == "icao24"]
    print(f"  Militaires détectés callsign: {len(det_cs):>7}")
    print(f"  Militaires détectés ICAO24 : {len(det_ic):>7}")
    zones = defaultdict(int)
    for l in lignes:
        zones[l.get("zone", "?")] += 1
    print(f"\n  Top 10 zones :")
    for zone, count in sorted(zones.items(), key=lambda x: -x[1])[:10]:
        print(f"    {zone:<35} {count:>8}")
    callsigns = defaultdict(int)
    for l in lignes:
        cs = l.get("callsign", "").strip()
        if cs:
            callsigns[cs] += 1
    print(f"\n  Top 15 callsigns :")
    for cs, count in sorted(callsigns.items(), key=lambda x: -x[1])[:15]:
        print(f"    {cs:<15} {count:>8}")
    mil_icaos = defaultdict(int)
    for l in milis:
        mil_icaos[l.get("icao24", "")] += 1
    print(f"\n  Top 10 ICAO24 militaires :")
    for icao, count in sorted(mil_icaos.items(), key=lambda x: -x[1])[:10]:
        print(f"    {icao:<12} {count:>8}")
    if lignes:
        print(f"\n  Période :")
        print(f"    Du  : {lignes[0].get('timestamp_utc', '?')}")
        print(f"    Au  : {lignes[-1].get('timestamp_utc', '?')}")
    alts = [int(l["alt_ft"]) for l in lignes if l.get("alt_ft", "").isdigit()]
    vels = [int(l["vel_kmh"]) for l in lignes if l.get("vel_kmh", "").isdigit()]
    if alts:
        print(f"\n  Altitude moyenne : {sum(alts)/len(alts):>8.0f} ft")
    if vels:
        print(f"  Vitesse moyenne  : {sum(vels)/len(vels):>8.0f} km/h")
    print(f"\n{'═' * 68}\n")


def sauvegarder_stats(lignes):
    import io
    old = sys.stdout
    sys.stdout = buffer = io.StringIO()
    statistiques(lignes)
    sys.stdout = old
    chemin = os.path.join(CSV_DIR, "radar_stats.txt")
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(buffer.getvalue())
    print(f"  Stats sauvegardées : {chemin}")


# ============================================================
# Export GeoJSON
# ============================================================
def exporter_geojson(lignes):
    if not lignes:
        print("  Aucune ligne à exporter.")
        return
    print(f"\n{'═' * 68}")
    print(f"  EXPORT GEOJSON")
    print(f"{'═' * 68}\n")

    # Grouper par icao24 pour reconstituer les trajectoires
    trajectoires = defaultdict(list)
    for l in lignes:
        try:
            lat = float(l["lat"]); lon = float(l["lon"])
        except (ValueError, KeyError):
            continue
        trajectoires[l["icao24"]].append({
            "lat": lat, "lon": lon,
            "alt_ft": l.get("alt_ft", ""),
            "vel_kmh": l.get("vel_kmh", ""),
            "timestamp": l.get("timestamp_utc", ""),
            "callsign": l.get("callsign", ""),
            "militaire": l.get("militaire", "NON"),
            "type_detection": l.get("type_detection", ""),
        })

    # Trier chaque trajectoire par timestamp
    for icao in trajectoires:
        trajectoires[icao].sort(key=lambda p: p["timestamp"])

    features = []
    for icao, points in trajectoires.items():
        if len(points) < 2:
            # Un seul point : marqueur ponctuel
            p = points[0]
            features.append({
                "type": "Feature",
                "properties": {
                    "icao24": icao,
                    "callsign": p["callsign"],
                    "militaire": p["militaire"],
                    "type_detection": p["type_detection"],
                    "nb_points": 1,
                    "alt_ft": p["alt_ft"],
                    "timestamp": p["timestamp"],
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [p["lon"], p["lat"]],
                },
            })
        else:
            # Ligne complète
            coords = [[p["lon"], p["lat"]] for p in points]
            alt_moy = 0
            try:
                alts = [int(p["alt_ft"]) for p in points if p["alt_ft"]]
                alt_moy = sum(alts) / len(alts) if alts else 0
            except ValueError:
                pass
            features.append({
                "type": "Feature",
                "properties": {
                    "icao24": icao,
                    "callsign": points[0]["callsign"],
                    "militaire": points[0]["militaire"],
                    "type_detection": points[0]["type_detection"],
                    "nb_points": len(points),
                    "alt_ft_moy": round(alt_moy),
                    "debut": points[0]["timestamp"],
                    "fin": points[-1]["timestamp"],
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords,
                },
            })

    geojson = {
        "type": "FeatureCollection",
        "metadata": {
            "genere_le": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "nb_trajectoires": len(features),
            "source": "adsb.lol",
        },
        "features": features,
    }

    chemin = os.path.join(CSV_DIR, "radar_trajectoires.geojson")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)

    taille = os.path.getsize(chemin) / 1024
    print(f"  Trajectoires exportées : {len(features)}")
    print(f"  Fichier : {chemin} ({taille:.1f} Ko)")
    print(f"\n  Visualisation :")
    print(f"    - QGIS : ouvrir directement le .geojson")
    print(f"    - geojson.io : glisser-déposer le fichier")
    print(f"    - GitHub : support natif des .geojson")


# ============================================================
# Export par zone
# ============================================================
def exporter_par_zone(lignes):
    if not lignes:
        return
    print(f"\n{'═' * 68}")
    print(f"  EXPORT PAR ZONE")
    print(f"{'═' * 68}\n")
    zones = defaultdict(list)
    for l in lignes:
        zones[l.get("zone", "inconnu")].append(l)
    for zone, sous_lignes in zones.items():
        nom_propre = re.sub(r'[^a-zA-Z0-9]+', '_', zone).strip('_')
        chemin = os.path.join(CSV_DIR, f"zone_{nom_propre}.csv")
        with open(chemin, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=sous_lignes[0].keys())
            writer.writeheader()
            writer.writerows(sous_lignes)
        print(f"  {zone:<35} → {len(sous_lignes):>6} lignes  ({os.path.basename(chemin)})")


# ============================================================
# Menu outils (post-scan)
# ============================================================
def menu_outils():
    while True:
        os.system("clear")
        print(f"{VERT_BRIGHT}{BOLD}")
        print("╔" + "═" * 68 + "╗")
        print("║" + "  OUTILS D'ANALYSE POST-SCAN".center(68) + "║")
        print("╚" + "═" * 68 + "╝")
        print(f"{RESET}")
        print(f"  {VERT_BRIGHT}[1]{RESET} Fusionner tous les CSV + stats")
        print(f"  {VERT_BRIGHT}[2]{RESET} Fusion + export GeoJSON")
        print(f"  {VERT_BRIGHT}[3]{RESET} Export par zone (1 CSV/zone)")
        print(f"  {VERT_BRIGHT}[4]{RESET} Fusion filtrée par date")
        print(f"  {VERT_BRIGHT}[5]{RESET} Tout (fusion + stats + GeoJSON + zones)")
        print(f"  {VERT_BRIGHT}[0]{RESET} Retour au menu principal")
        print()
        choix = input(f"  {AMBRE}Votre choix [0-5] : {RESET}").strip()
        if choix == "0":
            return
        elif choix == "1":
            lignes = fusionner_csv(dedup=True)
            if lignes:
                ecrire_fusion(lignes); statistiques(lignes); sauvegarder_stats(lignes)
        elif choix == "2":
            lignes = fusionner_csv(dedup=True)
            if lignes:
                exporter_geojson(lignes)
        elif choix == "3":
            lignes = fusionner_csv(dedup=True)
            if lignes:
                exporter_par_zone(lignes)
        elif choix == "4":
            print(f"\n  Format : YYYY-MM-DD (ex: 2026-10-09)")
            d1 = input(f"  Date début (vide = pas de filtre) : ").strip() or None
            d2 = input(f"  Date fin   (vide = pas de filtre) : ").strip() or None
            lignes = fusionner_csv(dedup=True, date_debut=d1, date_fin=d2)
            if lignes:
                ecrire_fusion(lignes); statistiques(lignes); sauvegarder_stats(lignes)
        elif choix == "5":
            lignes = fusionner_csv(dedup=True)
            if lignes:
                ecrire_fusion(lignes)
                statistiques(lignes)
                sauvegarder_stats(lignes)
                exporter_geojson(lignes)
                exporter_par_zone(lignes)
        if choix in ("1", "2", "3", "4", "5"):
            input(f"\n  {AMBRE}Appuyez sur Entrée pour continuer...{RESET}")


# ============================================================
# Boucle radar
# ============================================================
def boucle_radar(point, rayon_km, mode_label="", duree_max=None):
    debut = time.time()
    sweep_idx = 0
    try:
        while True:
            if duree_max and (time.time() - debut) > duree_max:
                return
            url = f"https://api.adsb.lol/v2/point/{point['lat']}/{point['lon']}/{RAYON_NM}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Tactical-Radar/4.0"})
                with urllib.request.urlopen(req, timeout=15) as r:
                    data = json.loads(r.read().decode())
                aircraft = data.get("ac") or []
            except Exception:
                aircraft = []
            avions = transformer_avions(
                aircraft, point["lat"], point["lon"], 0.015, rayon_km
            )
            exporter_csv(point["nom"], avions)
            afficher_radar(point, avions, sweep_idx, rayon_km, mode_label)
            sweep_idx += 1
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        raise


# ============================================================
# Main
# ============================================================
def main():
    try:
        mode = menu()

        # Outils d'analyse sans scan
        if mode in (5, 6, 7, 8, 9):
            if mode == 5:
                lignes = fusionner_csv(dedup=True)
                if lignes:
                    ecrire_fusion(lignes); statistiques(lignes); sauvegarder_stats(lignes)
            elif mode == 6:
                lignes = fusionner_csv(dedup=True)
                if lignes:
                    exporter_geojson(lignes)
            elif mode == 7:
                lignes = fusionner_csv(dedup=True)
                if lignes:
                    ecrire_fusion(lignes); statistiques(lignes)
                    sauvegarder_stats(lignes); exporter_geojson(lignes)
            elif mode == 8:
                print(f"\n  Format : YYYY-MM-DD")
                d1 = input(f"  Date début : ").strip() or None
                d2 = input(f"  Date fin   : ").strip() or None
                lignes = fusionner_csv(dedup=True, date_debut=d1, date_fin=d2)
                if lignes:
                    ecrire_fusion(lignes); statistiques(lignes)
            elif mode == 9:
                lignes = fusionner_csv(dedup=True)
                if lignes:
                    exporter_par_zone(lignes)
            input(f"\n  {AMBRE}Appuyez sur Entrée pour continuer...{RESET}")
            return

        # Mode radar
        resultats = scanner_points()
        classement = afficher_classement(resultats, mode, top_n=10)
        if not classement or classement[0]["total"] == 0:
            print(f"{ROUGE}AUCUN POINT AVEC DU TRAFIC. ARRÊT.{RESET}")
            return

        if mode == 2:
            score_fn = score_militaire
            mode_label = "// MODE: MILITAIRE"
        else:
            score_fn = score_auto
            mode_label = "// MODE: AUTO"

        classement_score = sorted(resultats, key=score_fn, reverse=True)

        if mode == 3:
            print(f"  {AMBRE}Sélectionnez le numéro du point à surveiller (1-{len(classement_score)}):{RESET}")
            for i, r in enumerate(classement_score, 1):
                print(f"    {i:>2}. {r['nom']:<28} ({r['total']} avions, {r['militaires']} mil)")
            try:
                choix = int(input(f"  {AMBRE}Votre choix : {RESET}").strip())
                meilleur = classement_score[choix - 1]
            except (ValueError, IndexError):
                meilleur = classement_score[0]
        else:
            meilleur = classement_score[0]

        print(f"\n  {VERT_BRIGHT}{BOLD}★ POINT SÉLECTIONNÉ : {meilleur['nom']} "
              f"({meilleur['total']} avions, {meilleur['militaires']} militaires){RESET}")
        print(f"  {GRIS}Démarrage dans 3s...{RESET}")
        time.sleep(3)

        rayon_km = RAYON_NM * 1.852

        if mode == 4:
            while True:
                resultats = scanner_points()
                classement_score = sorted(resultats, key=score_fn, reverse=True)
                nouveau = classement_score[0]
                if nouveau["nom"] != meilleur["nom"]:
                    print(f"\n  {AMBRE}★ BASCULE : {meilleur['nom']} → {nouveau['nom']}{RESET}")
                    time.sleep(2)
                    meilleur = nouveau
                boucle_radar(meilleur, rayon_km, mode_label, duree_max=RESCAN_PERIOD)
        else:
            boucle_radar(meilleur, rayon_km, mode_label)

    except KeyboardInterrupt:
        print(f"\n{AMBRE}RADAR TACTIQUE ARRÊTÉ.{RESET}")


if __name__ == "__main__":
    main()