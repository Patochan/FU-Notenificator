#!/usr/bin/python3
import os, lxml.html, requests, json, configparser, sys, subprocess
from datetime import datetime, timedelta
import logging

LOG_DIR = "/var/log/notenificator"
# Aktuelles Datum und Zeit
today = datetime.now()
log_file = f"{LOG_DIR}/notenificator_{today.strftime('%Y-%m-%d')}.log"
# Logdatei von gestern
yesterday = today - timedelta(days=1)
log_file_yesterday = f"{LOG_DIR}/notenificator_{yesterday.strftime('%Y-%m-%d')}.log"

logger = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.WARNING)

def createKlausurEntry(Modulnummer, Modulname, Semester, Note, Status, ECTS, Punkte, Anrechnung, Versuch, Datum):
    key = "{}_{}".format(Modulnummer, Versuch)

    klausurEintrag = {  "Key": key,
                        "Modulnummer": Modulnummer,
                        "Modulname": (Modulname or "")[1:],
                        "Semester": Semester,
                        "Note": str(Note or "").replace(" ",""),
                        "Status": (Status or "")[1:],
                        "ECTS": str(ECTS or "").replace(" ",""),
                        "Punkte": str(Punkte or "").replace(" ",""),
                        "Anrechnung": str(Anrechnung or "").replace(" ",""),
                        "Versuch": str(Versuch or "").replace(" ",""),
                        "Datum": Datum
                    }
    return(klausurEintrag)

# fetch data from locally stored file.
def getKlausurenStored():
    if not os.path.exists(cacheFile):
        return ( {"klausuren": []} )
    # kaputte Datei: Lauf stoppen, sonst würden alle Noten erneut gemeldet
    try:
        with open(cacheFile, 'r') as infile:
            loadedCacheData = json.load(infile)
            logging.debug(f"loaded data: {loadedCacheData}")
            return(loadedCacheData)
    except Exception as e:
        sys.exit(f"Gespeicherte Noten sind nicht lesbar ({cacheFile}): {e}")

def getKlausurenNew():
    klausurenNew = {"klausuren": []}
    try:
        s = requests.Session()
        res = s.get(cfg["FU"]["posurl"], timeout=30)

        loginForm = lxml.html.fromstring(res.text).xpath(".//a[contains(text(), 'Notenübersicht')]")[0].xpath(".//@href")[0]
        res = s.get("{}{}".format(cfg["FU"]["posurl"],loginForm), timeout=30)

        loginUrl = lxml.html.fromstring(res.text).xpath(".//form/@action")[0]
        loginData = {
                         "asdf": cfg["FU"]["username"],
                         "fdsa": cfg["FU"]["password"],
                         "submit": "Anmelden"
                     }

        res = s.post(url=loginUrl, data=loginData, timeout=30)
        # check if login failed (wrong username or password for example)
        if ("fehlgeschlagen" in res.text):
            notify(f"loggin to POS failed")
            sys.exit("POS Anmeldung fehlgeschlagen")

        pruefungsVerwaltungUrl = lxml.html.fromstring(res.text).xpath(".//a[contains(text(), 'Prüfungsverwaltung')]")[0].xpath(".//@href")[0]
        res = s.get(pruefungsVerwaltungUrl, timeout=30)
        notenUebersichtUrl = lxml.html.fromstring(res.text).xpath(".//a[contains(text(), 'Notenübersicht')]")[0].xpath(".//@href")[0]
        res = s.get(notenUebersichtUrl, timeout=30)
        leistungsUebersichtUrl = lxml.html.fromstring(res.text).xpath(".//a[@title='Leistungen für  Übersicht  über alle Leistungen anzeigen']")[0].xpath(".//@href")[0]
        res = s.get(leistungsUebersichtUrl, timeout=30)

        klausurData = res.text.replace("\t","").replace("\n","").replace("  ","")
        klausuren = lxml.html.fromstring(klausurData).xpath(".//tr")
        for klausur in klausuren:
            klausurDetails = klausur.xpath(".//td")
            if len(klausurDetails) == 10:
                klausurenNew["klausuren"].append( createKlausurEntry (klausurDetails[0].text, klausurDetails[1].text, klausurDetails[2].text, klausurDetails[3].text, klausurDetails[4].text, klausurDetails[5].text, klausurDetails[6].text, klausurDetails[7].text, klausurDetails[8].text, klausurDetails[9].text))
        return(klausurenNew)

    except Exception as e:
        logging.error(e)
        # Fehlermeldungen werden immer gesendet, auch wenn BOT enabled aus ist
        notify("Abruf der Noten fehlgeschlagen, siehe Logdatei")
        sys.exit("Fehler beim Abfragen der Noten")

def notify(message):
    # ohne Shell: Anführungszeichen in message bleiben normaler Text
    try:
        result = subprocess.run([sys.executable, "/opt/notify/notify.py", "--app=NOTENIFICATOR", f"--msg={message}"])
    except OSError as e:
        logger.error(f"notify konnte nicht gestartet werden: {e}")
        return False
    logger.debug(f"message forwarded to notify.py: {message}")
    return result.returncode == 0

def compareKlausurData(klausurenNew, klausurenStored):
    # leere Abfrage darf den gespeicherten Stand nicht überschreiben
    if len(klausurenNew["klausuren"]) == 0 and len(klausurenStored["klausuren"]) > 0:
        notify("Keine Noten gefunden, obwohl gespeicherte Noten vorhanden sind")
        sys.exit("Keine Noten gefunden; gespeicherte Noten bleiben unverändert")

    # ein Ergebnis gilt als neu, wenn Key oder Status vorher nicht gespeichert war
    known = {(k["Key"], k["Status"]) for k in klausurenStored["klausuren"]}
    klausurenNotFound = [k for k in klausurenNew["klausuren"] if (k["Key"], k["Status"]) not in known]

    if (len(klausurenNotFound) == 0):
        logging.info("Keine neuen Einträge gefunden")
    else:
        message = "NEUE RESULTATE GEFUNDEN\n-------------------\n"
        for neuesResultat in klausurenNotFound:
            notenText = ""
            versuch = "im " + neuesResultat["Versuch"] +". Versuch "
            if (neuesResultat["Note"] != ""):
                notenText = "mit {}".format(neuesResultat["Note"])
            if neuesResultat["Status"] == "bestanden":
                message = message + "- Gratuliere, du hast '" + neuesResultat["Modulname"] + "' " + notenText + " " + versuch +" bestanden! :)\n"
            elif neuesResultat["Status"] == "nicht bestanden":
                message = message + "- Du hast '" + neuesResultat["Modulname"] + "' " + notenText + " " + versuch +" leider nicht bestanden! :(\n"
            else:
                message = message + "- Neues Ergebnis für '" + neuesResultat["Modulname"] + "': " + neuesResultat["Status"] + ", " + versuch + "\n"
            message = message.replace("  ", " ")
        # erst senden, dann speichern: scheitert der Versand, wird beim nächsten Lauf erneut gemeldet
        if (cfg["BOT"]["enabled"] == "1") and not notify(message):
            sys.exit("Benachrichtigung fehlgeschlagen, Noten nicht gespeichert")

    with open( cacheFile, 'w') as outfile:
        try:
            json.dump(klausurenNew, outfile)
            logging.debug(f"Klausuren Cache erneuert")
        except Exception as e:
            logging.error(f"Fehler beim Speichern der Noten:{e}")
            notify(f"Fehler beim Speichern der Noten:{e}")
            sys.exit(1)

if __name__ == "__main__":
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        # loglevel
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    cfg = configparser.ConfigParser()
    cfg.read(os.path.join(ROOT_DIR, "config.ini"))

    cacheFile = os.path.join(ROOT_DIR, cfg["STORE"]["filename"])

    compareKlausurData(getKlausurenNew(), getKlausurenStored())

    #compress logfile from yesterday:
    if os.path.exists(log_file_yesterday):
        os.system(f"gzip {log_file_yesterday}")
