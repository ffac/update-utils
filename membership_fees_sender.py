#!/usr/bin/env python

import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo

import pandas as pd

DRY_RUN = True

smtp_host = os.getenv("SMTP_SERVER", "")
smtp_user = os.getenv("SMTP_USER", "")
password = os.getenv("SMTP_PW", "")
sender_name = os.getenv("SENDER_NAME", "Freifunk Aachen")

from_address = f"{sender_name} <{smtp_user}>"
reply_to_address = "vorstand@freifunk-aachen.de"
smtp_server = smtplib.SMTP_SSL(smtp_host)
smtp_server.set_debuglevel(False)
smtp_server.login(smtp_user, password)
smtp_server.set_debuglevel(1)

members_data = pd.read_excel("members.ods", engine="odf", nrows=31)
members_data["Vorname"] = members_data["Vorname"].fillna("")
members_data["offen_von"] = members_data["offen_von"].fillna(0).astype(int)
members_data["offen_bis"] = members_data["offen_bis"].fillna(0).astype(int)

for idx, data in members_data.iterrows():
    # fehlender Vorname ist juristische Person, kriegt keine Mail
    if data["Kontostand"] >= 0 or not data["Vorname"]:
        continue

    if data["offen_von"] != data["offen_bis"]:
        offen_jahre = f"Die Mitgliedsbeiträge  der Jahre {data['offen_von']} bis {data['offen_bis']} sind noch ausstehend."
    else:
        offen_jahre = (
            f"Der Mitgliedsbeitrag des Jahres {data['offen_bis']} ist noch ausstehend."
        )
    content = f"""Hallo {data["Vorname"]} {data["Name"]},

Sie sind Mitglied der Fördervereinigung freie Netzwerke Aachen e.V. (F3N Aachen e.V.)
Sie sind mit Mitgliedsnummer {data["Mitgliedsnummer"]} am {data["Eintrittsdatum"].date()} beigetreten.

Der Mitgliedsbeitrag in Höhe von 60€ (12€ ermäßigt) ist zum 1. März eines jeden Jahres fällig.
{offen_jahre}
Das ergibt in Summe einen ausstehenden Betrag von {-data["Kontostand"]}€.

Bitte überweisen Sie den offenen Betrag zeitnah an folgende Kontoverbindung:

Kontoinhaber:\t\tFördervereinigung freie Netzwerke Aachen
IBAN:\t\t\tDE70 3906 0180 1225 8810 10
Verwendungszweck:\tMitgliedsbeitrag F3N (+ ggf Name, wenn er vom Kontoinhaber abweicht)

Gerne kann dafür auch ein jährlicher Dauerauftrag angelegt werden.
Sollten Sie den Beitrag bereits vor wenigen Tagen gezahlt haben, können sie die Nachricht ignorieren.

Bei Fragen kontaktieren Sie uns gerne unter kontakt@freifunk-aachen.de

Viele Grüße
Ihr Freiwilligen-Team vom Freifunk Aachen
"""
    if DRY_RUN:
        print(content)
        continue

    msg = EmailMessage()
    msg["Subject"] = "Freifunk Aachen - offene Mitgliedsbeiträge"
    msg["From"] = from_address
    msg["To"] = data["Email"]
    msg["Reply-To"] = reply_to_address
    msg["Date"] = datetime.now(tz=ZoneInfo("Europe/Berlin"))
    msg.set_content(content)
    smtp_server.send_message(msg)

smtp_server.quit()
