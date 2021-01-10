# FU-Notenificator
Abfragescript für die Notenverwaltung der FernUni Hagen.
Sendet eine Notification via Telegram Bot an den gewünschten User

# Anforderungen
- python3 mit den Modulen urllib, lxml.html, requests, json & configparser
- Telegram Account

# Konfiguration
1. Erstelle einen TelegramBot => https://core.telegram.org/bots
2. config.ini
  [BOT]
  
  token = Token des TelegramBots (wird bei der Erstellung des Bots generiert)
	
  notify = Telegram UserId 
	Diese kann mittels Nachricht an deinen Bot und dem anschliessenden Aufruf 
	von https://api.telegram.org/bot<BOTID>/getUpdates (wobei <BOTID> der zuvor generierte Token ist)
  
  [FU]
  posurl = URL des POS der FernUni 
	
  username = FernUni Benutzername (qXXXXXXXX)
	
  password = FernUni Passwort (Achtung, Passwort wird Klartext gespeichert!)
	

  [STORE]
  
  filename = lokales File, in welchen die Klausuren für den Vergleich abgespeichert werden.
