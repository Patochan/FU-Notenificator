#!/usr/bin/python3
import os, urllib, lxml.html, requests, json, configparser, sys
from datetime import datetime, timedelta
import logging

# Aktuelles Datum und Zeit
today=datetime.now()
log_file=f'/var/log/notenificator/notenificator_{today.strftime('%Y-%m-%d')}.log'
# Logdatei von gestern
yesterday = today - timedelta(days=1)
log_file_yesterday = f'/var/log/notenificator/notenificator_{yesterday.strftime("%Y-%m-%d")}.log'


logging.basicConfig(
    # loglevel
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.WARNING)

def createKlausurEntry(Modulnummer, Modulname, Semester, Note, Status, ECTS, Punkte, Anrechnung, Versuch, Datum):
    key = "{}_{}".format(Modulnummer, Versuch)

    klausurEintrag = {  "Key": key,
                        "Modulnummer": Modulnummer,
                        "Modulname": Modulname[1:],
                        "Semester": Semester,
                        "Note": str(Note).replace(" ",""),
                        "Status": Status[1:],
                        "ECTS": str(ECTS).replace(" ",""),
                        "Punkte": str(Punkte).replace(" ",""),
                        "Anrechnung": str(Anrechnung).replace(" ",""),
                        "Versuch": str(Versuch).replace(" ",""),
                        "Datum": Datum
                    }
    return(klausurEintrag)

# fetch data from locally stored file. 
def getKlausurenStored():
    try:
        if os.path.exists(cacheFile):
            with open(cacheFile, 'r') as infile:
                loadedCacheData = json.load(infile)
                logging.debug(f"loaded data: {loadedCacheData}")
                return(loadedCacheData)
        else:
            return ( {"klausuren": []} )
    except Exception as e:
        logging.error(f"error while parsing data from file: {e}")
        return ( {"klausuren": []} )
        
def getKlausurenNew():
    klausurenNew = {"klausuren": []}
    try:
        s = requests.Session() 
        res = s.get(cfg["FU"]["posurl"])

        loginForm = lxml.html.fromstring(res.text).xpath(".//a[contains(text(), 'Notenübersicht')]")[0].xpath(".//@href")[0]
        res = s.get("{}{}".format(cfg["FU"]["posurl"],loginForm) ) 

        loginUrl = lxml.html.fromstring(res.text).xpath(".//form/@action")[0]
        loginData = {
                         "asdf": cfg["FU"]["username"],
                         "fdsa": cfg["FU"]["password"],
                         "submit": "Anmelden"
                     }

        res = s.post(url=loginUrl, data=loginData)
        # check if login failed (wrong username or password for example)
        if ("fehlgeschlagen" in res.text):
            notify(f"loggin to POS failed")
            sys.exit("POS Anmeldung fehlgeschlagen")

        pruefungsVerwaltungUrl = lxml.html.fromstring(res.text).xpath(".//a[contains(text(), 'Prüfungsverwaltung')]")[0].xpath(".//@href")[0]
        res = s.get(pruefungsVerwaltungUrl)
        notenUebersichtUrl = lxml.html.fromstring(res.text).xpath(".//a[contains(text(), 'Notenübersicht')]")[0].xpath(".//@href")[0]
        res = s.get(notenUebersichtUrl)
        leistungsUebersichtUrl = lxml.html.fromstring(res.text).xpath(".//a[@title='Leistungen für  Übersicht  über alle Leistungen anzeigen']")[0].xpath(".//@href")[0]
        res = s.get(leistungsUebersichtUrl)

        klausurData = res.text.replace("\t","").replace("\n","").replace("  ","")
        klausuren = lxml.html.fromstring(klausurData).xpath(".//tr")
        for klausur in klausuren:
            klausurDetails = klausur.xpath(".//td")   
            if len(klausurDetails) == 10: 
                klausurenNew["klausuren"].append( createKlausurEntry (klausurDetails[0].text, klausurDetails[1].text, klausurDetails[2].text, klausurDetails[3].text, klausurDetails[4].text, klausurDetails[5].text, klausurDetails[6].text, klausurDetails[7].text, klausurDetails[8].text, klausurDetails[9].text))
        return(klausurenNew)

    except Exception as e:
        logging.error(e)
        sys.exit("Fehler beim Abfragen der Noten")

def notify(message):
    notifyCmd = f'python /opt/notify/notify.py --app=NOTENIFICATOR --msg="{message}"'
    # send notification
    os.system(notifyCmd)
    logger.debug(f"message forwarded to notify.py: {message}")

def compareKlausurData(klausurenNew, klausurenStored):
    klausurenNotFound = []

    for klausurNew in klausurenNew["klausuren"]:
        found = False
        for klausurCache in klausurenStored["klausuren"]:
            if klausurCache["Key"] == klausurNew["Key"]:
                found = True
        if found == False:
            klausurenNotFound.append(klausurNew)
                        
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
            else:
                message = message + "- Du hast '" + neuesResultat["Modulname"] + "' " + notenText + " " + versuch +" leider nicht bestanden! :(\n"
            message = message.replace("  ", " ")
        if (cfg["BOT"]["enabled"] == "1" or cfg["BOT"]["enabled"] == 1):
            notify(message)
            
    with open( cacheFile, 'w') as outfile:
        try:
            json.dump(klausurenNew, outfile)
            logging.debug(f"Klausuren Cache erneuert")
        except Exception as e:
            logging.error(f"Fehler beim Speichern der Noten:{e}")
            notify(f"Fehler beim Speichern der Noten:{e}")
            sys.exit(1)

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
cfg = configparser.ConfigParser()
cfg.read(os.path.join(ROOT_DIR, "config.ini"))

cacheFile = os.path.join(ROOT_DIR, cfg["STORE"]["filename"])

compareKlausurData(getKlausurenNew(), getKlausurenStored())

#compress logfile from yesterday:
if os.path.exists(log_file_yesterday):
    os.system(f"gzip {log_file_yesterday}")
