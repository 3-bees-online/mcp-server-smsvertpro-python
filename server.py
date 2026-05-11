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
    if not cleaned or not re.match(r'^[\w\-]+$', cleaned):
        raise ValueError(f"Identifiant de campagne invalide : '{campaign_id}'")
    return cleaned


# ─── API Helper ──────────────────────────────────────────────────


def call_api(payload: dict) -> dict:
    """Appelle l'API SMS Vert Pro V2."""
    payload = dict(payload)
    endpoint = payload.pop("request", "")
    url = API_URL.rstrip("/") + "/" + endpoint

    try:
        with httpx.Client(timeout=API_TIMEOUT, verify=True) as client:
            response = client.post(
                url,
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
    except httpx.RequestError:
        return {"status": "REQUEST_ERROR", "error": "API request failed"}
    except json.JSONDecodeError:
        return {"status": "PARSE_ERROR", "error": "Invalid API response"}


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
        payload["message"]["delay"] = delay + ":00"
        payload["message"]["delay_cancel"] = True

    result = call_api(payload)

    if result.get("status") == "SEND_OK":
        return (
            f"SMS envoyé avec succès.\n"
            f"Campagne ID : {result.get('id', '?')}\n"
            f"Crédits restants : {result.get('credits', '?')}\n"
            f"Nombre de SMS : {result.get('nbsms', '?')}\n"
            f"Date : {result.get('date', '?')}"
        )
    return f"Erreur d'envoi : {result.get('status', 'Inconnu')}"


@mcp.tool()
def check_credits() -> str:
    """Consulte le solde de crédits SMS restants sur le compte SMS Vert Pro.
    1 crédit = 1 SMS de 160 caractères."""
    result = call_api({"request": "credits"})
    if "credits" in result:
        return f"Solde : {result['credits']} crédits SMS disponibles."
    return f"Erreur : {result.get('status', 'Inconnu')}"


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
    if not cleaned or not re.match(r'^[\w\-]+$', cleaned):
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
def cancel_sms(campaign_id: str, sms_id: str = "") -> str:
    """Annule un SMS programmé ou une campagne entière.

    Seuls les SMS en attente d'envoi (programmés) peuvent être annulés.
    Les crédits sont automatiquement recrédités sur le compte.
    IMPORTANT : le campaign_id est TOUJOURS requis. Il est retourné dans la
    réponse de send_sms (champ 'id'). Pour annuler un SMS spécifique,
    fournir aussi le sms_id en plus du campaign_id.

    Args:
        campaign_id: L'identifiant de la campagne (retourné par send_sms). OBLIGATOIRE.
        sms_id: L'identifiant d'un SMS spécifique à annuler dans la campagne.
                Si non fourni, toute la campagne est annulée.
    """
    try:
        campaign_id = validate_campaign_id(campaign_id)
    except ValueError as e:
        return f"Erreur de validation : {e}"

    payload = {"request": "cancel", "campaign_id": campaign_id}

    if sms_id:
        sms_id = sms_id.strip()
        if not re.match(r'^[\w\-]+$', sms_id):
            return f"Erreur : identifiant SMS invalide : '{sms_id}'"
        payload["sms_id"] = sms_id

    result = call_api(payload)

    status = result.get("status", "")
    if status == "CANCEL_OK":
        return (
            f"Annulation réussie.\n"
            f"Crédits recrédités. Nouveau solde : {result.get('credits', '?')} crédits."
        )
    if status == "INVALID_SMS":
        return "Erreur : SMS introuvable ou déjà envoyé."
    if status == "NO_SMS_FOUND":
        return "Erreur : aucun SMS en attente trouvé pour cette campagne."
    return f"Erreur d'annulation : {status}"


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
    return f"Erreur OTP : {result.get('status', 'Inconnu')}"


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


# ─── GSM-7 charset (RFC complet) ─────────────────────────────────

_GSM7_CHARS = frozenset(
    "@£$¥èéùìòÇ\nØø\rÅå"
    "Δ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ"
    " !\"#¤%&'()*+,-./"
    "0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNO"
    "PQRSTUVWXYZÄÖÑÜ§"
    "¿abcdefghijklmno"
    "pqrstuvwxyzäöñüà"
    "\f^{}\\[~]|€"
)


# Extension chars: each one costs 2 units (escape \x1B + the char).
_GSM7_EXT = frozenset("\f^{}\\[~]|€")


def _is_gsm7(message: str) -> bool:
    return all(c in _GSM7_CHARS for c in message)


def _gsm7_length(message: str) -> int:
    """Effective billable GSM-7 length: extension chars count as 2."""
    return sum(2 if c in _GSM7_EXT else 1 for c in message)


def _count_sms_parts(message: str) -> int:
    length = _gsm7_length(message)
    if length <= 160:
        return 1
    return -(-length // 153)  # ceil division


@mcp.tool()
def count_sms_parts(message: str) -> str:
    """Calcule localement combien de SMS (parts) un message va consommer.

    100% local, n'envoie rien, ne consomme aucun crédit. Permet à l'agent IA
    d'estimer le coût d'une campagne avant d'appeler send_sms : 1 SMS = 160
    caractères GSM-7 (153 si concaténé en plusieurs parts).

    Par défaut, SMS Vert Pro envoie uniquement en GSM-7. Si le message contient
    des emojis ou des caractères non-GSM (â, ê, î, ô, û, ç minuscule, ï, ë...),
    il sera REJETÉ par l'API au moment de l'envoi (status EMOJI_NOT_ALLOWED).
    Le support Unicode est activable sur demande auprès du support SMS Vert Pro.

    Args:
        message: Texte du SMS à analyser
    """
    if not message:
        return "Message vide : 0 part, 0 caractères."

    chars = len(message)

    if not _is_gsm7(message):
        return (
            f"REJET PRÉVU : le message contient des caractères non-GSM-7. "
            f"SMS Vert Pro rejettera l'envoi avec le code 'EMOJI_NOT_ALLOWED'.\n\n"
            f"Caractères : {chars}\n\n"
            f"Caractères incompatibles à retirer ou remplacer : emojis, "
            f"accents circonflexes (â ê î ô û), ç minuscule (utiliser 'c'), "
            f"ï, ë, ÿ. Les accents GSM-7 acceptés sont : é è à ù É Ç (majuscule).\n\n"
            f"Reprendre la rédaction sans ces caractères, puis rappeler "
            f"count_sms_parts pour estimer le coût final. "
            f"(Le support Unicode est activable sur demande auprès du support SMS Vert Pro.)"
        )

    billing_length = _gsm7_length(message)
    parts = _count_sms_parts(message)
    per_part = 160 if parts == 1 else 153
    extra_count = billing_length - chars
    ext_note = (
        f"\nLongueur facturée : {billing_length} unités GSM-7 "
        f"(présence de {extra_count} caractère(s) d'extension comme € {{ }} [ ] | ~ ^ \\ qui comptent 2)"
        if extra_count > 0
        else ""
    )
    return (
        f"Encodage : GSM-7 (compatible SMS Vert Pro)\n"
        f"Caractères tapés : {chars}{ext_note}\n"
        f"Parts (SMS) : {parts}\n"
        f"Capacité par part : {per_part} caractères\n\n"
        f"Coût pour 1 destinataire : {parts} crédit(s). "
        f"Pour estimer une campagne, multiplier par le nombre de destinataires."
    )


# ─── Démarrage ───────────────────────────────────────────────────

if __name__ == "__main__":
    print("[SMS Vert Pro MCP] Serveur Python démarré.", file=sys.stderr)
    mcp.run(transport="stdio")
