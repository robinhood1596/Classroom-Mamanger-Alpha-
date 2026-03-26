# Classroom-Mamanger-Alpha-
Python-Classroom-Manager Overlay für Windows und Linux

Downloaden, overlay.pyw oder overlay.py starten und ab dafür.
# Classroom Overlay Tool

Ein transparentes, immer-im-Vordergrund Desktop-Overlay fuer den Unterricht. Gebaut mit PyQt6.
<img width="3783" height="1912" alt="grafik" src="https://github.com/user-attachments/assets/8f2473ba-a232-4540-b425-098766ae7778" />


<!-- Screenshot: Overlay mit Toolbar und geoeffneten Panels ueber dem Desktop -->

---

## Features

### Texteditor
Vollwertiger Rich-Text-Editor mit ein-/ausklappbarer Formatierungsleiste. Unterstuetzt Schriftgroessen (10-72pt), Text- und Markierungsfarben, Fett/Kursiv/Unterstrichen sowie eine Blink-Funktion mit einstellbarer Geschwindigkeit (Rechtsklick auf den Blinken-Button).


### Schuelerliste & Notizen
Zeigt die geladene Klassenliste an. Per Rechtsklick auf einen Namen koennen Notizen mit Ablaufdatum (in Unterrichtsstunden) erstellt werden. Abgelaufene Notizen werden automatisch entfernt.



### Ampelsystem
Zwei Modi:
- **Klick-Modus**: Farbpunkt klicken wechselt die Farbe, Name klicken zaehlt den Counter hoch
- **Sortier-Modus**: Schueler per Drag & Drop zwischen Rot/Gelb/Gruen verschieben

Optionale Countdown-Timer pro Farbzone. Notizen erscheinen nach 3 Sekunden Hover ueber einem Namen.


### Timer & Stoppuhr
Countdown-Timer oder Stoppuhr mit Start/Pause-Toggle und schneller Zeitanpassung ueber +/- Buttons. Konfigurierbarer Alarmton bei Ablauf.


### Zufallsgenerator & Gruppenbildung
Zieht zufaellige Namen aus der Klasse oder erstellt ausgewogene Gruppen (2-10).



### Lautstaerke-Monitor
Ueberwacht die Umgebungslautstaerke per Mikrofon in Echtzeit. Einstellbare Schwelle, Karenzzeit und Gelb/Rot-Zaehlung. Optionale dB-Anzeige.



### Arbeitssymbole
Grosse, gut sichtbare Symbole fuer Arbeitsformen: Lesen, Schreiben, Leise, Gruppenarbeit, Partnerarbeit, Einzelarbeit, Melden, Zuhoeren, Diskussion, Pause.



### QR-Code Generator
URL oder Text eingeben, QR-Code wird direkt im Panel generiert und skaliert.


### Aufraumen & Ordnungsdienst
Vollbild-Overlay mit Aufraeum-Anweisungen (per Rechtsklick editierbar). Zeigt automatisch 2 zufaellig gezogene Schueler als Ordnungsdienst an. Neues Ziehen per Button moeglich.

### Pause
Vollbild-Pause-Overlay mit 5-Minuten-Countdown. Stoppt automatisch alle laufenden Timer und setzt sie nach Ablauf fort.


### Smartboard-Modus
Verschiebt das gesamte Overlay auf den sekundaeren Bildschirm (Beamer/Smartboard). Beim Zurueckschalten wird der Bildschirm automatisch wieder auf Duplizieren gesetzt (Windows).

### Hintergrund
Weisser oder farbiger Hintergrund (Rechtsklick fuer Farbwahl) blendet den Desktop aus. Umschaltbar per Button oder `Ctrl+Shift+W`.

### Zeichnen
Transparente Vollbild-Zeichenflaeche mit 6 Farben, 3 Stiftstaerken und Radierer.


### Layout-System
Panels, Positionen, Groessen und Texteditor-Inhalt werden automatisch gespeichert und beim naechsten Start wiederhergestellt. Pro Klasse wird ein eigenes Layout verwaltet.

---

## Tastenkuerzel

| Kuerzel | Aktion |
|---|---|
| `Esc` / `Ctrl+Q` | Overlay beenden |
| `Ctrl+B` | Fett (im Texteditor) |
| `Ctrl+I` | Kursiv (im Texteditor) |
| `Ctrl+U` | Unterstrichen (im Texteditor) |
| `Ctrl+Shift+W` | Hintergrund ein/aus |

---

## Installation

### Voraussetzungen
- Python 3.10+
- Betriebssystem: Windows 10/11 oder Linux (Fedora/KDE getestet)

### Einrichtung

```bash
# Repository klonen
git clone https://github.com/BENUTZERNAME/classroom-overlay.git
cd classroom-overlay

# Abhaengigkeiten installieren
pip install -r requirements.txt
```

### Starten

```bash
# Mit Konsolenfenster (Debug)
python overlay.py

# Ohne Konsolenfenster (Windows)
pythonw overlay.pyw
```

---

## Abhaengigkeiten

| Bibliothek | Zweck |
|---|---|
| PyQt6 >= 6.5 | GUI-Framework |
| qrcode[pil] | QR-Code Generierung |
| python-xlib | Globale Hotkeys (nur Linux) |

---

## Ordnerstruktur

```
overlay/
  overlay.py          # Hauptanwendung
  requirements.txt    # Python-Abhaengigkeiten
  classes/            # Klassendateien (JSON)
    5a.json
    7b.json
  layouts/            # Gespeicherte Layouts pro Klasse
    layout_5a.json
    notes_5a.json     # Schueler-Notizen pro Klasse
  sounds/             # Audio-Dateien (Alarm, etc.)
  symbols/            # Eigene Symbol-Bilder
  screenshots/        # Screenshots fuer README
```

### Klassendatei-Format

```json
{
  "class_name": "5a",
  "students": [
    {"first_name": "Max", "last_name": "Mustermann"},
    {"first_name": "Erika", "last_name": "Musterfrau"}
  ]
}
```

---

## Plattform-Hinweise

- **Windows**: Smartboard-Modus nutzt `DisplaySwitch.exe` fuer Bildschirm-Duplizierung. Audio ueber `winsound`.
- **Linux**: Globale Hotkeys ueber `python-xlib` (X11). Audio ueber PulseAudio (`paplay`). Wayland wird nicht unterstuetzt.

---

## Lizenz

