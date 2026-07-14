#!/usr/bin/env python3
"""Convertit le TDR markdown en Google Doc natif via l'API Drive (zuri@, scope drive).
HTML -> application/vnd.google-apps.document. Partage domaine mstudio.vc + leslie@."""
import json, subprocess, urllib.request, urllib.parse, uuid

TOK = json.load(open("/tmp/dc/zuri.json"))
CRED = json.load(open("/home/openclaw/.config/gogcli/credentials.json"))
MD = "/home/openclaw/agents/main/projects/diaspora-emploi-portal/out/tdr_v1.md"
TITLE = "TDR — Portail Intelligence Emploi Diaspora Connect (v1)"

def access_token():
    data = urllib.parse.urlencode({
        "client_id": CRED["client_id"], "client_secret": CRED["client_secret"],
        "refresh_token": TOK["refresh_token"], "grant_type": "refresh_token"}).encode()
    return json.load(urllib.request.urlopen(urllib.request.Request(
        "https://oauth2.googleapis.com/token", data=data)))["access_token"]
AT = access_token()

# md -> html (pandoc, standalone for proper table rendering)
html = subprocess.check_output(["pandoc", MD, "-f", "markdown", "-t", "html", "-s"]).decode()

# Drive multipart upload with conversion to native Google Doc
boundary = "===" + uuid.uuid4().hex + "==="
meta = {"name": TITLE, "mimeType": "application/vnd.google-apps.document"}
body = (
    f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
    + json.dumps(meta) + "\r\n"
    + f"--{boundary}\r\nContent-Type: text/html; charset=UTF-8\r\n\r\n"
    + html + "\r\n" + f"--{boundary}--"
).encode("utf-8")
req = urllib.request.Request(
    "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true",
    data=body, method="POST")
req.add_header("Authorization", "Bearer " + AT)
req.add_header("Content-Type", f"multipart/related; boundary={boundary}")
res = json.load(urllib.request.urlopen(req))
FID = res["id"]
print("DOC_ID", FID)

def share(b):
    r = urllib.request.Request(
        f"https://www.googleapis.com/drive/v3/files/{FID}/permissions?sendNotificationEmail=false&supportsAllDrives=true",
        data=json.dumps(b).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + AT); r.add_header("Content-Type", "application/json")
    try:
        urllib.request.urlopen(r); print("shared", b.get("emailAddress") or b.get("domain"))
    except urllib.error.HTTPError as e:
        print("share fail", e.read().decode()[:200])
share({"type": "domain", "role": "writer", "domain": "mstudio.vc"})
share({"type": "user", "role": "writer", "emailAddress": "leslie@mstudio.vc"})
print("URL", f"https://docs.google.com/document/d/{FID}/edit")
