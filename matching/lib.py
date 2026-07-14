#!/usr/bin/env python3
"""Helpers OpenAI (embeddings + génération) pour le moteur de matching.
Clé lue via secrets.env (OPENAI_API_KEY). Aucune dépendance externe (urllib)."""
import os, json, urllib.request, urllib.error

KEY = os.environ.get("OPENAI_API_KEY")
if not KEY:
    # secrets.env n'exporte pas toujours -> lire le fichier directement
    try:
        for line in open(os.path.expanduser("~/.config/agents/secrets/openai.txt")):
            KEY = line.strip()
            break
    except FileNotFoundError:
        pass
EMB_MODEL = "text-embedding-3-small"
CHAT_MODEL = os.environ.get("MATCH_CHAT_MODEL", "gpt-4o")


def _post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {KEY}",
                                          "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=120))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"OpenAI {e.code}: {e.read().decode()[:300]}")


def embed(texts):
    """texts: liste de chaînes -> liste de vecteurs (floats)."""
    if isinstance(texts, str):
        texts = [texts]
    out = []
    for i in range(0, len(texts), 256):  # batch
        r = _post("https://api.openai.com/v1/embeddings",
                  {"model": EMB_MODEL, "input": texts[i:i + 256]})
        out.extend(d["embedding"] for d in r["data"])
    return out


def chat_json(system, user, model=None):
    """Appel chat avec sortie JSON forcée -> dict."""
    r = _post("https://api.openai.com/v1/chat/completions",
              {"model": model or CHAT_MODEL, "temperature": 0.4,
               "response_format": {"type": "json_object"},
               "messages": [{"role": "system", "content": system},
                            {"role": "user", "content": user}]})
    return json.loads(r["choices"][0]["message"]["content"])


OCR_SYSTEM = (
    "Tu es un moteur d'OCR. L'utilisateur a téléversé son PROPRE document (un CV) pour le faire "
    "analyser ; il consent à son traitement. Ta seule tâche est de retranscrire fidèlement, mot pour "
    "mot, le texte visible dans les images. Renvoie UNIQUEMENT le texte brut transcrit, sans aucune "
    "introduction, commentaire, ni refus. Si une zone est illisible, écris [illisible]."
)


def vision_text(image_data_uris, instruction="Transcris mot pour mot tout le texte de ce document."):
    """OCR via modèle vision : liste de data URIs (images de pages) -> texte transcrit."""
    content = [{"type": "text", "text": instruction}]
    for uri in image_data_uris:
        content.append({"type": "image_url", "image_url": {"url": uri, "detail": "high"}})
    r = _post("https://api.openai.com/v1/chat/completions",
              {"model": "gpt-4o", "temperature": 0,
               "messages": [{"role": "system", "content": OCR_SYSTEM},
                            {"role": "user", "content": content}]})
    return r["choices"][0]["message"]["content"]
