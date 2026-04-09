#!/usr/bin/env python3
"""
SMS Vert Pro — Serveur MCP (Model Context Protocol) — Python

Permet aux agents IA (Claude, GPT, LangChain, CrewAI, etc.)
d'envoyer des SMS via l'API SMS Vert Pro V2.

Prérequis :
  1. Python 3.10+
  2. pip install mcp httpx
  3. Créez un compte gratuit sur https://www.smsvertpro.com
  4. Générez votre token API Bearer depuis l'API V2
  5. Définissez la variable d'environnement SMSVERTPRO_API_TOKEN

Usage :
  SMSVERTPRO_API_TOKEN=votre_token python server.py

@link https://www.smsvertpro.com/api-smsvertpro/
@link https://www.smsvertpro.com/integration-ia/
"""

import os
import re
import sys
import json
import httpx
from mcp.server.fastmcp import FastMCP

# ─── Configuration ───────────────────────────────────────────────

API_URL = "https://www.smsvertpro.com/api/v2/"
API_TIMEOUT = 30
MAX_MESSAGE_LENGTH = 918  # 6 SMS concaténés max
SENDER_MAX_LENGTH = 11
PHONE_PATTERN = re.compile(r"^\d{10,15}$")
SENDER_PATTERN = re.compile(r"^[a-zA-Z0-9 ]{1,11}$")
DELAY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
OTP_CODE_PATTERN = re.compile(r"^\d{4,8}$")

api_token = os.environ.get("SMSVERTPRO_API_TOKEN", "").strip()
if not api_token:
    print(
        "[ERREUR] Variable d'environnement SMSVERTPRO_API_TOKEN non définie.\n"
        "Créez un compte sur https://www.smsvertpro.com puis générez votre token API.",
        file=sys.stderr,
    )
    sys.exit(1)

mcp = FastMCP("smsvertpro")

# ─── Validation ──────────────────────────────────────────────────


def validate_phone(number: str) -> str:
    """Valide et nettoie un numéro de téléphone."""
    cleaned = number.strip().lstrip("+")
    if not PHONE_PATTERN.match(cleaned):
        raise ValueError(
            f"Numéro invalide : '{number}'. "
            "Format attendu : 10-15 chiffres sans '+' (ex: 33612345678)"
        )
    return cleaned


def validate_sender(sender: str) -> str:
    """Valide le nom d'expéditeur."""
    sender = sender.strip()
    if not sender or not SENDER_PATTERN.match(sender):
        raise ValueError(
            f"Expéditeur invalide : '{sender}'. "
            "11 caractères max, alphanumérique uniquement."
        )
    return sender


def validate_campaign_id(campaign_id: str) -> str:
    """Valide un identifiant de campagne."""
    cleaned = campaign_id.strip()
    if not cleaned or not cleaned.isalnum():
        raise ValueError(f"Identifiant de campagne invalide : '{campaign_id}'")
    return cleaned


# ─── API Helper ──────────────────────────────────────────────────


def call_api(payload: dict) -> dict:
    """Appelle l'API SMS Vert Pro V2 de manière sécurisée."""
    try:
        with httpx.Client(timeout=API_TIMEOUT, verify=True) as client:
            response = client.post(
                API_URL,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_token}",
                },
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        return {"status": "ERROR", "error": "Timeout API (30s)"}
    except httpx.HTTPStatusError as e:
        return {"status": "HTTP_ERROR", "code": e.response.status_code}
    except httpx.RequestError as e:
        return {"status": "REQUEST_ERROR", "error": str(e)}
    except json.JSONDecodeError:
        return {"status": "PARSE_ERROR", "raw": response.text[:500]}


# ─── Tools MCP ───────────────────────────────────────────────────


@mcp.tool()
def send_sms(to: list[str], message: str, sender: str, delay: str = "") -> str:
    """Envoie un SMS à un ou plusieurs destinataires via SMS Vert Pro.

    Les numéros doivent être au format international sans le '+'
    (ex: 33612345678 pour la France). Le message est limité à 160 caractères
    pour 1 SMS (ou 306 pour 2 SMS concaténés).
    IMPORTANT : si le compte est en route marketing, l'expéditeur doit ajouter
    la mention 'STOP 36173' à la fin du message (obligation légale).
    Cette mention n'est PAS ajoutée automatiquement par l'API.

    Args:
        to: Liste des numéros destinataires (ex: ["33612345678"])
        message: Le contenu du SMS à envoyer
        sender: Nom de l'expéditeur affiché (11 car. max, alphanumérique)
        delay: Envoi différé optionnel, format 'YYYY-MM-DD HH:MM'
    """
    if not to:
        return "Erreur : aucun destinataire fourni."

    try:
        recipients = [validate_phone(n) for n in to]
        sender = validate_sender(sender)
    except ValueError as e:
        return f"Erreur de validation : {e}"

    message = message.strip()
    if not message:
        return "Erreur : le message est vide."
    if len(message) > MAX_MESSAGE_LENGTH:
        return f"Erreur : message trop long ({len(message)} car., max {MAX_MESSAGE_LENGTH})."

    payload = {
        "request": "send_sms",
        "message": {"sender": sender, "text": message},
        "recipients": recipients,
    }

    if delay:
        delay = delay.strip()
        if not DELAY_PATTERN.match(delay):
            return "Erreur : format de date invalide. Attendu : 'YYYY-MM-DD HH:MM'"
        payload["message"]["delay"] = delay

    result = call_api(payload)

    if result.get("status") == "SEND_OK":
        return (
            f"SMS envoyé avec succès.\n"
            f"Campagne ID : {result.get('id', '?')}\n"
            f"Crédits restants : {result.get('credits', '?')}\n"
            f"Nombre de SMS : {result.get('nbsms', '?')}\n"
            f"Date : {result.get('date', '?')}"
        )
    return f"Erreur d'envoi : {result.get('status', 'Inconnu')}\n{json.dumps(result)}"


@mcp.tool()
def check_credits() -> str:
    """Consulte le solde de crédits SMS restants sur le compte SMS Vert Pro.
    1 crédit = 1 SMS de 160 caractères."""
    result = call_api({"request": "credits"})
    if "credits" in result:
        return f"Solde : {result['credits']} crédits SMS disponibles."
    return f"Erreur : {json.dumps(result)}"


@mcp.tool()
def get_delivery_report(campaign_id: str) -> str:
    """Récupère le rapport de délivrabilité d'une campagne SMS envoyée.

    Args:
        campaign_id: L'identifiant de la campagne retourné lors de l'envoi
    """
    try:
        campaign_id = validate_campaign_id(campaign_id)
    except ValueError as e:
        return f"Erreur de validation : {e}"

    result = call_api({"request": "reports", "campaign_id": campaign_id})
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def get_responses(campaign_id: str) -> str:
    """Récupère les réponses SMS reçues pour une campagne (SMS bidirectionnel).

    Args:
        campaign_id: L'identifiant de la campagne
    """
    try:
        campaign_id = validate_campaign_id(campaign_id)
    except ValueError as e:
        return f"Erreur de validation : {e}"

    result = call_api({"request": "responses", "campaign_id": campaign_id})
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def verify_number(list_id: str) -> str:
    """Vérifie le format des numéros de téléphone d'une liste de contacts.

    Args:
        list_id: L'identifiant de la liste de contacts à vérifier
    """
    cleaned = list_id.strip()
    if not cleaned or not cleaned.isalnum():
        return f"Erreur : identifiant de liste invalide : '{list_id}'"

    result = call_api(
        {"request": "verify_numbers", "liste_id": cleaned, "action": "check"}
    )
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def get_blacklist() -> str:
    """Récupère la liste des numéros ayant envoyé STOP (désabonnements).
    Ces numéros ne recevront plus de SMS marketing."""
    result = call_api({"request": "blacklist"})
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def generate_otp(to: str, sender: str) -> str:
    """Génère et envoie un code OTP par SMS pour l'authentification 2FA.

    Args:
        to: Numéro du destinataire au format international (ex: '33612345678')
        sender: Nom de l'expéditeur
    """
    try:
        to = validate_phone(to)
        sender = validate_sender(sender)
    except ValueError as e:
        return f"Erreur de validation : {e}"

    result = call_api({"request": "generate_otp", "gsm": to, "sender": sender})

    if result.get("status") == "OTP_SENT":
        return (
            f"Code OTP envoyé par SMS au {to}. "
            "Demandez à l'utilisateur de saisir le code reçu."
        )
    return f"Erreur OTP : {json.dumps(result)}"


@mcp.tool()
def verify_otp(to: str, code: str) -> str:
    """Vérifie un code OTP saisi par l'utilisateur.

    Args:
        to: Numéro du destinataire utilisé lors de la génération
        code: Le code OTP saisi par l'utilisateur
    """
    try:
        to = validate_phone(to)
    except ValueError as e:
        return f"Erreur de validation : {e}"

    code = code.strip()
    if not OTP_CODE_PATTERN.match(code):
        return "Erreur : code OTP invalide. Attendu : 4-8 chiffres."

    result = call_api({"request": "verify_otp", "gsm": to, "code": code})

    status = result.get("status", "")
    if status in ("OK", "OTP_TRUE"):
        return "Code OTP valide. Identité confirmée."
    if status == "OTP_VERIFIED":
        return f"Ce code OTP a déjà été vérifié le {result.get('verified_at', '?')}."
    return f"Code OTP invalide ou expiré. Statut : {status}"


# ─── Démarrage ───────────────────────────────────────────────────

if __name__ == "__main__":
    print("[SMS Vert Pro MCP] Serveur Python démarré.", file=sys.stderr)
    mcp.run(transport="stdio")
