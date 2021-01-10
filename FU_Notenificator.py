import http.client, urllib, lxml.html, requests, json, configparser


def erstelleKlausurEintrag(Modulnummer, Modulname, Semester, Note, Status, ECTS, Punkte, Anrechnung, Versuch, Datum):
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


# lade gespeichertes json aus dem file
def getKlausurenCached():
    klausurenCached = {"klausuren": []}
    try:
        with open(cfg["CACHE"]["filename"], 'r') as infile:
            klausurenCached = json.load(infile)
    except Exception as e:
        print(e)

    return(klausurenCached)


def getKlausurenNew():
    klausurenNew = {"klausuren": []}

    username = cfg["FU"]["username"]
    password = cfg["FU"]["password"]
    body = "asdf={}&fdsa={}&submit=Anmelden".format(username, password)
    headers = {"Connection": "keep-alive"}
    connection = http.client.HTTPSConnection("pos.fernuni-hagen.de")
    connection.request("GET", "/qisserver/rds?state=user&type=1&category=auth.login&startpage=portal.vm&breadCrumbSource=portal")
    response = connection.getresponse()

    if response.status == 200:
        response.read()
        session_id = response.getheader("Set-Cookie")[:43]
        cookie = session_id
        headers = {"Cookie": cookie, "Connection": "keep-alive", "Content-Type": "application/x-www-form-urlencoded"}

        connection.request("POST", "/qisserver/rds;{}?state=user&type=1&category=auth.login&startpage=portal.vm&breadCrumbSource=portal".format(session_id), body=body, headers=headers)
        response = connection.getresponse()
        prev_session_id = session_id

        if response.status != 302:
            print("Something went wrong:")
            print("Status", response.status, "instead of 302")
        else:
            session_id = response.getheader("Set-Cookie")[:43]
            location = response.getheader("Location")[28:]
            cookie = "{};{}".format(session_id, prev_session_id)
            headers = {"Cookie": cookie, "Connection": "keep-alive"}
            response.read()

            connection.request("GET", location, headers=headers)
            response = connection.getresponse()

            prev_session_id = session_id
            response.read()

            path = "https://pos.fernuni-hagen.de/qisserver/rds?state=change&type=1&moduleParameter=studyPOSMenu&nextdir=change&next=menu.vm&subdir=applications&xml=menu&purge=y&navigationPosition=functions%2CstudyPOSMenu&breadcrumb=studyPOSMenu&topitem=functions&subitem=studyPOSMenu"
            connection.request("GET", path, headers=headers)
            response = connection.getresponse()
            data = response.read()
            lines = data.split(b"<a href=\"")

            for line in lines:
                line = line[:line.find(b"\"")]
                if line.find(b"notenspiegelStudent") != -1:
                    location = line.decode("utf-8")[28:].replace("&amp;", "&")
                    connection.request("GET", location, headers=headers)
                    response = connection.getresponse()
                    data = response.read()

                    lines = data.split(b"<a href=\"")
                    for line in lines:
                        if line.find(b"Leistungen f\xc3\xbcr  \xc3\x9cbersicht  \xc3\xbcber alle Leistungen anzeigen")!= -1:
                            line = line[:line.find(b"\"")]
                            location = line.decode("utf-8")[28:].replace("&amp;", "&")
                            connection.request("GET", location, headers=headers)
                            response = connection.getresponse()
                            data = response.read().decode("utf-8").replace("\t","").replace("\n","").replace("  ","")
                            data = lxml.html.fromstring(data)
                    
                            trs = data.findall(".//tr")
                            for tr in trs: 
                                    tds = tr.findall(".//td")
                                    # Klausuren enthalten 10 td-Elemente
                                    if len(tds) == 10: 
                                        klausur = erstelleKlausurEintrag( tds[0].text , tds[1].text, tds[2].text, tds[3].text, tds[4].text, tds[5].text, tds[6].text, tds[7].text, tds[8].text, tds[9].text)
                                        klausurenNew["klausuren"].append(klausur)
                            return(klausurenNew)


def compareKlausurData(klausurenNew,klausurenCached):
    klausurenNotFound = []
    for klausurNew in klausurenNew["klausuren"]:
        found = False
        for klausurCache in klausurenCached["klausuren"]:
            if klausurCache["Key"] == klausurNew["Key"]:
                found = True
        if found == False:
            klausurenNotFound.append(klausurNew)
                        
    if (len(klausurenNotFound) == 0):
        print("nix neues")
    else:
        message = "NEUE RESULTATE GEFUNDEN\n-------------------\n"
        for neuesResultat in klausurenNotFound:
            notenText = " "
            versuch = " im " + neuesResultat["Versuch"] +". Versuch "
            if (neuesResultat["Note"] != ""):
                notenText = " mit {} ".format(neuesResultat["Note"])
            if neuesResultat["Status"] == "bestanden":
                message = message + "Gratuliere, du hast '" + neuesResultat["Modulname"] + "'"+notenText+versuch+"bestanden! :)\n"
            else:
                message = message + "Du hast '" + neuesResultat["Modulname"] + "'"+notenText+versuch+"leider nicht bestanden! :(\n"
            message = message.replace("  ", " ")

        if (cfg["TELEGRAMBOT"]["enabled"] == 1):
            url = 'https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s' % (
                    cfg["TELEGRAMBOT"]["token"], cfg["TELEGRAMBOT"]["notify"], urllib.parse.quote_plus(message))
            res = requests.get(url, timeout=10)
    with open(cfg["CACHE"]["filename"], 'w') as outfile:
        json.dump(klausurenNew, outfile)





cfg = configparser.ConfigParser()
cfg.read("config.ini")

compareKlausurData(getKlausurenNew(), getKlausurenCached())