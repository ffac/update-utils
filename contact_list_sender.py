#!/usr/bin/env python

import smtplib
import json
import os
from email.message import EmailMessage

with open("contact_addresses_multi.json", "r") as f:
    multi_addresses = json.load(f)

with open("contact_addresses_single.json", "r") as f:
    single_addresses = json.load(f)

smtp_host = os.getenv("SMTP_SERVER")
smtp_user = os.getenv("SMTP_USER")
password = os.getenv("SMTP_PW")
sender_name = os.getenv("SENDER_NAME", "Freifunk Aachen")

from_address = f"{sender_name} <{smtp_user}>"
reply_to_address = "router-ersetzen@freifunk-aachen.de"
smtp_server = smtplib.SMTP_SSL(smtp_host)
smtp_server.set_debuglevel(False)
smtp_server.login(smtp_user, password)
smtp_server.set_debuglevel(1)

for address, nodes in single_addresses[:1]:
    model, name, routerid = nodes[0]

    content = f"""Hallo zusammen,

der von Ihnen eingesetzte {model} Freifunk-Router mit dem Namen {name} ist veraltet und muss ersetzt werden.
Ihre Mail-Adresse ist auf diesem Router als Kontakt-Adresse eingetragen.

Wie Sie unserer Karte entnehmen können
https://map.aachen.freifunk.net/#!/en/map/{routerid}
ist dieses Gerät nun seit mehreren Jahren veraltet, erhält keine Sicherheits-Updates und sollte in den nächsten Wochen ersetzt werden, um Freifunk flächendeckend schnell und aktuell zu halten.

Sinnvolle Ersatzrouter empfehlen wir hier:
https://wiki.freifunk.net/Freifunk_Aachen/Hardware

Weitere Informationen zur Veralterung des Geräts erhalten Sie hier:
https://freifunk-aachen.de/2022/11/23/ausmusterung-altgeraete/

Bei Fragen kontaktieren Sie uns gerne unter kontakt@freifunk-aachen.de

Viele Grüße
Ihr Freiwilligen-Team vom Freifunk Aachen
"""

    msg = EmailMessage()
    msg["Subject"] = "Freifunk Aachen - veralteten Router ersetzen"
    msg["From"] = from_address
    msg["To"] = address
    msg["Reply-To"] = reply_to_address
    msg.set_content(content)
    smtp_server.send_message(msg)

for address, nodes in multi_addresses[:1]:
    router_string = ""
    for node in nodes:
        model, name, routerid = node
        router_string += f"""{name}
{model}
https://map.aachen.freifunk.net/#!/en/map/{routerid}

"""

    content = f"""Hallo zusammen,

Sie setzen einige veraltete Freifunk-Router ein.
Ihre Mail-Adresse ist auf diesen Routern als Kontakt-Adresse eingetragen.

Diese Geräte sind nun seit mehreren Jahren veraltet, erhalten keine Sicherheits-Updates und sollten in den nächsten Wochen ersetzt werden,um Freifunk flächendeckend schnell und aktuell zu halten.

Die betroffenen Router sind:

{router_string}
Sinnvolle Ersatzrouter empfehlen wir hier:
https://wiki.freifunk.net/Freifunk_Aachen/Hardware

Weitere Informationen zur Veralterung des Geräts erhalten Sie hier:
https://freifunk-aachen.de/2022/11/23/ausmusterung-altgeraete/

Bei Fragen kontaktieren Sie uns gerne unter kontakt@freifunk-aachen.de

Viele Grüße
Ihr Freiwilligen-Team vom Freifunk Aachen
"""

    msg = EmailMessage()
    msg["Subject"] = "Freifunk Aachen - veraltete Router ersetzen"
    msg["From"] = from_address
    msg["To"] = address
    msg["Reply-To"] = reply_to_address

    msg.set_content(content)
    smtp_server.send_message(msg)


smtp_server.quit()
