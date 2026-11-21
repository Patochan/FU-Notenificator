# FU-Notenificator

Fragt das Prüfungsportal (POS) der FernUni Hagen ab und meldet neue Prüfungsergebnisse.

Das Skript loggt sich mit deinen Zugangsdaten ins POS ein, liest alle Prüfungsergebnisse aus und vergleicht sie mit dem lokal gespeicherten Stand. Nur neue oder geänderte Ergebnisse werden gemeldet. Die Meldung wird über das Skript `/opt/notify/notify.py` verschickt (gedacht für einen Telegram-Bot, siehe [Benachrichtigung](#benachrichtigung)).

## Voraussetzungen

- Python 3
- Die Pakete `requests` und `lxml`:

  ```sh
  pip install requests lxml
  ```

- Zugang zum POS der FernUni (Benutzername und Passwort)
- Auf dem Server: das Benachrichtigungsskript unter `/opt/notify/notify.py`

## Einrichtung

1. Konfigurationsdatei anlegen:

   ```sh
   cp config.ini.template config.ini
   ```

2. `config.ini` ausfüllen (siehe [Konfiguration](#konfiguration)).

3. Skript einmal starten und die Ausgabe prüfen:

   ```sh
   python FU_Notenificator.py
   ```

`config.ini` muss im selben Ordner liegen wie `FU_Notenificator.py`.

## Konfiguration

| Abschnitt | Schlüssel | Bedeutung |
|-----------|-----------|-----------|
| `[BOT]` | `enabled` | `1` = Meldungen über neue Ergebnisse senden, `0` = aus. Fehlermeldungen werden immer gesendet. |
| `[BOT]` | `token`, `notify` | Stehen in der Vorlage, werden von diesem Skript **nicht** gelesen (siehe [Benachrichtigung](#benachrichtigung)). |
| `[FU]` | `posurl` | Adresse des POS der FernUni |
| `[FU]` | `username` | FernUni-Benutzername (Format `qXXXXXXXX`) |
| `[FU]` | `password` | FernUni-Passwort. **Wird im Klartext gespeichert.** |
| `[STORE]` | `filename` | Datei für den gespeicherten Stand, z. B. `klausuren.json`. Relativ zum Skriptordner. |

Die Datei `config.ini` enthält dein Passwort. Sie steht in `.gitignore` und darf nicht ins Repository. Auf dem Server sollte nur dein Benutzer sie lesen können (`chmod 600 config.ini`).

## Benachrichtigung

Das Skript ruft `/opt/notify/notify.py --app=NOTENIFICATOR --msg="..."` auf. Dieses Skript gehört nicht zu diesem Repository. Die Telegram-Zugangsdaten (Bot-Token und Nutzer-ID) müssen dort eingerichtet werden.

Zur Einrichtung eines Telegram-Bots: <https://core.telegram.org/bots>. Deine Nutzer-ID bekommst du, indem du deinem Bot eine Nachricht schickst und danach `https://api.telegram.org/bot<TOKEN>/getUpdates` aufrufst.

## Ablauf

1. Das POS abrufen und die Prüfungsergebnisse lesen.
2. Mit dem gespeicherten Stand vergleichen. Ein Ergebnis gilt als neu, wenn die Kombination aus Modulnummer, Versuch und Status vorher nicht gespeichert war.
3. Bei neuen Ergebnissen die Meldung senden. Gelingt das nicht, wird der Stand **nicht** gespeichert und der nächste Lauf versucht es erneut.
4. Den neuen Stand in die Datei aus `[STORE]` schreiben.

**Achtung beim ersten Lauf:** Fehlt die Datei aus `[STORE]`, gelten alle Ergebnisse als neu, und du bekommst eine Meldung für jedes davon.

Schutzmechanismen:
- Ist die gespeicherte Datei kaputt, stoppt der Lauf. Er überschreibt sie nicht.
- Liefert das POS gar keine Ergebnisse, obwohl welche gespeichert sind, stoppt der Lauf. Der gespeicherte Stand bleibt erhalten.
- Schlägt der Abruf fehl (z. B. Login, geänderte Seite, Zeitüberschreitung), wird eine Fehlermeldung gesendet.

## Automatisch ausführen

Beispiel für cron (zweimal täglich, um 7:00 und 19:00 Uhr):

```cron
0 7,19 * * * cd /pfad/zum/FU-Notenificator && python3 FU_Notenificator.py
```

## Logs

Das Skript schreibt täglich eine Logdatei nach `/var/log/notenificator/` (z. B. `notenificator_2026-01-31.log`). Der Ordner wird bei Bedarf angelegt. Die Logdatei von gestern wird beim nächsten Lauf mit `gzip` gepackt.

## Fehlersuche

| Meldung | Bedeutung und Abhilfe |
|---------|-----------------------|
| `POS Anmeldung fehlgeschlagen` | Benutzername oder Passwort sind falsch. |
| `Fehler beim Abfragen der Noten` | Die Seite des POS hat sich geändert oder ist nicht erreichbar. Details stehen in der Logdatei. |
| `Keine Noten gefunden, obwohl gespeicherte Noten vorhanden sind` | Das POS hat keine Ergebnisse geliefert. Der gespeicherte Stand bleibt unverändert. |
| `Gespeicherte Noten sind nicht lesbar` | Die Datei aus `[STORE]` ist beschädigt. Sichern oder löschen und neu anfangen (dann werden alle Ergebnisse erneut gemeldet). |
| `Benachrichtigung fehlgeschlagen, Noten nicht gespeichert` | `notify.py` konnte die Meldung nicht senden. Der nächste Lauf versucht es erneut. |

## Tests

Die Tests brauchen keinen Zugang zum POS und keine Benachrichtigung:

```sh
python -m unittest test_FU_Notenificator -v
```
