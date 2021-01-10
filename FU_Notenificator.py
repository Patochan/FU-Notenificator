import os, urllib, lxml.html, requests, json, configparser, sys



def createKlausurEntry(Modulnummer, Modulname, Semester, Note, Status, ECTS, Punkte, Anrechnung, Versuch, Datum):
    if Note == None:
        Note = ""
    if Punkte == None:
        Punkte = ""
    
    key = "{}_{}".format(Modulnummer, Versuch)

    klausurEintrag = {  "Key": key,
                        "Modulnummer": Modulnummer,
                        "Modulname": Modulname[1:],
                        "Semester": Semester,
                        "Note": Note.replace(" ",""),
                        "Status": Status[1:],
                        "ECTS": ECTS.replace(" ",""),
                        "Punkte": Punkte.replace(" ",""),
                        "Anrechnung": Anrechnung.replace(" ",""),
                        "Versuch": Versuch.replace(" ",""),
                        "Datum": Datum
                    }
    return(klausurEintrag)

# fetch data from locally stored file. 
def getKlausurenStored():
    try:
        with open(os.path.join(ROOT_DIR, cfg["STORE"]["filename"]), 'r') as infile:
            return(json.load(infile))
    except Exception as e:
        print("error while parsing data from file", e)
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
        if ("fehlgeschlagen" in res.text) :
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
        print(e)
        sys.exit("Fehler beim Abfragen der Noten")

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
        print("nix neues")
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
        print (message)
        if (cfg["BOT"]["enabled"] == "1" or cfg["BOT"]["enabled"] == 1):
            print("Sende notification via Telegram")
            url = 'https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s' % (
                    cfg["BOT"]["token"], cfg["BOT"]["notify"], urllib.parse.quote_plus(message))
            res = requests.get(url, timeout=10)
    with open(  os.path.join(ROOT_DIR, cfg["STORE"]["filename"]), 'w') as outfile:
        json.dump(klausurenNew, outfile)


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
cfg = configparser.ConfigParser()
cfg.read(os.path.join(ROOT_DIR, "config.ini"))

compareKlausurData(getKlausurenNew(), getKlausurenStored())