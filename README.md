<div align="center">

# ✈️ Radar Terminal Aéronefs

**Suivi en temps réel des aéronefs en vol, directement dans votre terminal.**

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)
[![ADS-B](https://img.shields.io/badge/ADS--B-OpenSky-9333ea?style=for-the-badge)](https://opensky-network.org/)
[![Data](https://img.shields.io/badge/Data-ADS--B_Public-0ea5e9?style=for-the-badge)](https://opensky-network.org/)
[![Terminal](https://img.shields.io/badge/Terminal-ASCII-000000?style=for-the-badge&logo=gnubash&logoColor=white)](https://github.com/gunout/radar-terminal-sat)

<img src="https://img.shields.io/badge/status-active-22c55e?style=flat-square" alt="Status">
<img src="https://img.shields.io/badge/version-2.0-blue?style=flat-square" alt="Version">
<img src="https://img.shields.io/badge/aéronefs-temps_réel-red?style=flat-square" alt="Aéronefs">
<img src="https://img.shields.io/badge/style-tactique_militaire-darkgreen?style=flat-square" alt="Style">

Un radar ASCII haute définition qui affiche en temps réel la position des aéronefs détectés par ADS-B, avec azimut, élévation, distance, altitude et vitesse.

</div>

---

## SCREENSHOTS

<img width="742" height="1008" alt="RADARAERO" src="https://github.com/user-attachments/assets/df622c2a-aa16-48ea-9ab0-cb93f3459b1f" />


---

## 📖 À propos

Ce projet permet de **visualiser en temps réel** les aéronefs en vol, directement depuis un terminal. Il utilise :

- **OpenSky Network** pour les données ADS-B publiques
- **adsb.lol** comme source alternative
- **ASCII art** pour un rendu universel
- **Design tactique militaire** (vert phosphore, style cockpit)

Idéal pour les passionnés d'aviation, les planeurs, les contrôleurs aériens, ou toute personne curieuse de voir ce qui vole au-dessus de sa tête.

---

## ✨ Fonctionnalités

| Fonctionnalité | Description |
|----------------|-------------|
| ✈️ **Radar aérien** | Vue de dessus avec azimut et distance |
| 🎖️ **Design tactique** | Style cockpit de chasse, vert phosphore |
| 📡 **ADS-B temps réel** | Positions mises à jour toutes les 15s |
| 🎯 **Détection militaire** | Par indicatif (RCH, FAF, RRR...) |
| 📊 **Statistiques** | Altitude moyenne, vitesse, contact le plus proche |
| 🔍 **Filtres** | Civils, militaires, altitude |
| 💻 **100% terminal** | Compatible SSH, aucune interface graphique |
| 🌐 **Multi-sites** | Paris, La Réunion, Kourou... |
| 🎨 **4 niveaux d'altitude** | Basse, moyenne, haute, militaire |

---

## 🚀 Installation

### Prérequis

- Python 3.12+
- Terminal 256 couleurs (XFCE4, GNOME, Kitty, Alacritty...)
- Connexion Internet (API OpenSky)

### Étapes

```bash
# 1. Cloner le dépôt
git clone https://github.com/gunout/radar-terminal-aeronefs.git
cd radar-terminal-aeronefs

# 2. Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate

# 3. Aucune dépendance externe requise (urllib inclus dans Python)
# Le script utilise uniquement la bibliothèque standard
```

---

## 🎮 Utilisation

### Radar aérien standard

```bash
# Radar depuis Paris (Europe)
python3 radar_aerien_paris.py

# Radar depuis La Réunion (océan Indien)
python3 radar_aerien_reunion.py
```

### Radar tactique militaire

```bash
# Design tactique depuis Paris
python3 radar_militaire_paris.py

# Design tactique depuis La Réunion
python3 radar_militaire.py
```

### Options en ligne de commande

```bash
# Changer les coordonnées
python3 radar_aerien.py --lat 48.85 --lon 2.35

# Changer le rayon
python3 radar_aerien.py --rayon 500

# Changer l'intervalle
python3 radar_aerien.py --interval 30
```

---

## 📸 Aperçu

### Radar tactique militaire (design vert phosphore)

```
╔════════════════════════════════════════════════════════════════════╗
║          TACTICAL AIR DEFENSE RADAR — PARIS                        ║
║    SOURCE: OPENSKY ADS-B // CLASSIFICATION: UNCLASSIFIED           ║
╠════════════════════════════════════════════════════════════════════╣
║  UTC : 2026-10-09 15:30:00 UTC   LOCAL : 17:30:00 (UTC+2)          ║
║  CONTACTS : 342   │   CIVILS : 340   │   MILITAIRES :   2          ║
║  RAYON : 400 km   │   INTERVALLE : 15s   │   STATUT : ACTIF        ║
╠════════════════════════════════════════════════════════════════════╣

                    ┌─── N (000°) ───┐
                    │  ALT: 40 000 ft │
                    └────────┬────────┘
                    · · · · · · · · · ·
                 · · · · · ● ○ · · · · · ·
               · · · · ● ○ ○ ● · · · · · · ·
             · · · · ○ ● ○ ● ○ · · · · · · · ·
           · · · · ● ● ○ ● ○ ● ● · · · · · · · ·
         · · · · ● ○ ○ ● ● ○ ○ ● · · · · · · · · ·
       · · · · ○ ● ● ○ ○ ● ○ ● ● ○ · · · · · · · · ·
     · · · · · ● ○ ● ○ ● ○ ○ ● ○ ● · · · · · · · · · ·
   · · · · · · ● ○ ○ ● ● ○ ● ○ ● ○ · · · · · · · · · · ·
W 270 ────────────────────────O───────────────────────── 090 E
   · · · · · · ● ○ ○ ● ● ○ ● ○ ● ○ · · · · · · · · · · ·
     · · · · · ● ○ ● ○ ● ○ ○ ● ○ ● · · · · · · · · · ·
       · · · · ○ ● ● ○ ○ ● ○ ● ● ○ · · · · · · · · ·
         · · · · ● ○ ○ ● ● ○ ○ ● · · · · · · · · ·
           · · · · ● ● ○ ● ○ ● ● · · · · · · · ·
             · · · · ○ ● ○ ● ○ · · · · · · · ·
               · · · · ● ○ ○ ● · · · · · · ·
                 · · · · · ● ○ · · · · · ·
                    · · · · · · · · · ·
                    ┌────────┴────────┐
                    │   MODE: TACTIQUE │
                    └─── S (180°) ───┘

  SYMBOLOGIE :  ○ basse alt   ● moyenne   ▲ haute   ✈ militaire

╠════════════════════════════════════════════════════════════════════╣
║  ANALYSE TACTIQUE                                                  ║
╠════════════════════════════════════════════════════════════════════╣
║  ALTITUDE MOYENNE  :      35000 ft                                 ║
║  VITESSE MOYENNE   :        850 km/h                               ║
║  CONTACT LE + PROCHE : AFR1234     à 12.3 km                       ║
║  AZIMUT            :  45.2°   ÉLÉVATION :  12.5°                   ║
╠════════════════════════════════════════════════════════════════════╣
║  PISTE DE CONTACTS (TOP 15)                                        ║
╠════════════════════════════════════════════════════════════════════╣
║  CALLSIGN     ALT ft VIT km/h  DIST km     AZ°                     ║
╠────────────┼────────┼────────┼────────┼────────────────────────────╣
║  AFR1234      35000      850      12.3    45.2                     ║
║  BAW456       37000      920      18.7   120.5                     ║
║  DLH789       33000      780      25.1   230.8                     ║
╚════════════════════════════════════════════════════════════════════╝
  RAFRAÎCHISSEMENT DANS 15s... (CTRL+C POUR QUITTER)
```

---

## 🗂️ Structure du projet

```
radar-terminal-aeronefs/
├── radar_aerien_paris.py        # Radar aérien (Paris)
├── radar_aerien_reunion.py      # Radar aérien (La Réunion)
├── radar_militaire_paris.py     # Radar tactique (Paris)
├── radar_militaire.py           # Radar tactique (La Réunion)
├── requirements.txt             # Aucune dépendance externe
├── .gitignore                   # Fichiers exclus
├── README.md                    # Ce fichier
└── LICENSE                      # MIT
```

---

## 🔧 Configuration

### Changer de site d'observation

Modifiez les coordonnées dans les scripts :

```python
# Paris
OBS_LAT = 48.85
OBS_LON = 2.35

# La Réunion (Saint-Denis)
OBS_LAT = -20.88
OBS_LON = 55.45
```

### Sites prédéfinis

| Site | Latitude | Longitude |
|------|----------|-----------|
| Paris | 48.85 | 2.35 |
| La Réunion | -20.88 | 55.45 |
| Kourou (CSG) | 5.23 | -52.77 |
| Toulouse (CNES) | 43.60 | 1.44 |
| Cologne (ESA) | 50.94 | 6.96 |

### Sources de données

| Source | URL | Couverture |
|--------|-----|------------|
| **OpenSky** | `opensky-network.org` | Europe, USA |
| **adsb.lol** | `api.adsb.lol` | Monde |
| **adsb.fi** | `opendata.adsb.fi` | Europe, USA |

---

## 📦 Dépendances

```txt
# Aucune dépendance externe requise
# Le script utilise uniquement la bibliothèque standard Python :
#   - urllib.request (requêtes HTTP)
#   - json (parsing)
#   - math (calculs)
#   - re (regex)
#   - os, sys, time (système)
```

---

## 🧪 Tests

```bash
# Vérifier la connexion à OpenSky
curl "https://opensky-network.org/api/states/all?lamin=35&lomin=-15&lamax=72&lomax=35" | head -c 200

# Lancer le radar aérien
python3 radar_aerien_paris.py

# Lancer le radar tactique
python3 radar_militaire_paris.py
```

---

## ⚠️ Limites

- **OpenSky Network** : 400 requêtes/jour maximum (anonyme)
- **Intervalle minimum** : 10 secondes
- **La Réunion** : peu de récepteurs ADS-B → trafic aérien quasi-invisible
- **Paris** : des centaines de contacts en temps réel
- **Couverture** : dépend des récepteurs bénévoles

---

## 🎖️ Détection militaire

Les indicatifs suivants sont détectés comme militaires :

| Préfixe | Signification |
|---------|---------------|
| `RCH` / `REACH` | US Air Mobility Command |
| `FAF` | French Air Force |
| `GAF` | German Air Force |
| `IAM` | Italian Air Force |
| `RRR` | Royal Air Force |
| `RFR` | Royal Air Force (Royaume-Uni) |
| `ASCOT` | RAF Transport |
| `DUKE` | US Army |
| `MAGIC` | AWACS |
| `VIPER` | Chasseurs |

**Note** : la détection est basée sur l'indicatif. Beaucoup d'avions militaires volent avec des indicatifs civils ou éteignent leur transpondeur.

---

## 🤝 Contribuer

Les contributions sont les bienvenues !

1. **Fork** le projet
2. **Créer** une branche (`git checkout -b feature/ma-feature`)
3. **Commit** (`git commit -m 'Ajout de ma feature'`)
4. **Push** (`git push origin feature/ma-feature`)
5. **Ouvrir** une Pull Request

---

## 📜 Licence

Ce projet est sous licence **MIT** — voir [LICENSE](LICENSE).

---

## 🙏 Remerciements

- **[OpenSky Network](https://opensky-network.org/)** — Données ADS-B publiques
- **[adsb.lol](https://adsb.lol/)** — Données ADS-B alternatives
- **[adsb.fi](https://adsb.fi/)** — Données ADS-B alternatives
- **[FlightRadar24](https://www.flightradar24.com/)** — Inspiration
- **[AirNav Radar](https://www.airnavradar.com/)** — Inspiration

---

<div align="center">

**⭐ Si ce projet vous plaît, n'hésitez pas à lui donner une étoile !**

Fait avec ❤️ pour la communauté aéronautique francophone

</div>

---

<div align="center">

### 🇫🇷 Gunout · 2026

![Made in France](https://img.shields.io/badge/Made_in-France-002395?style=flat-square&labelColor=FFFFFF&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5MDAgNjAwIj48cmVjdCB3aWR0aD0iOTAwIiBoZWlnaHQ9IjYwMCIgZmlsbD0iIzAwMjM5NSIvPjxyZWN0IHdpZHRoPSI5MDAiIGhlaWdodD0iNDAwIiB5PSIxMDAiIGZpbGw9IiNmZmYiLz48cmVjdCB3aWR0aD0iOTAwIiBoZWlnaHQ9IjIwMCIgeT0iNDAwIiBmaWxsPSIjZWQyOTM5Ii8+PC9zdmc+)
![GitHub](https://img.shields.io/badge/GitHub-gunout-181717?style=flat-square&logo=github&logoColor=white)
![Year](https://img.shields.io/badge/2026-ED2939?style=flat-square&labelColor=FFFFFF)

<sub>© 2026 <strong>Gunout</strong> — Tous droits réservés.</sub>

</div>
