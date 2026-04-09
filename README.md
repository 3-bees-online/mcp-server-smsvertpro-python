<p align="center">
  <img src="logo.png" alt="SMS Vert Pro" width="220" />
</p>

# SMS Vert Pro — Serveur MCP Python

Serveur [MCP (Model Context Protocol)](https://modelcontextprotocol.io) en Python pour envoyer des SMS professionnels via [SMS Vert Pro](https://www.smsvertpro.com) depuis n'importe quel agent IA : Claude, ChatGPT, LangChain, CrewAI, AutoGen, etc.

> Version PHP disponible : [mcp-server-smsvertpro-php](https://github.com/3-bees-online/mcp-server-smsvertpro-php)

## Prérequis

1. **Python 3.10+**
2. **Un compte SMS Vert Pro** — [inscription gratuite](https://www.smsvertpro.com/espace-client/?type=1) (10 SMS offerts)
3. **Un token API Bearer** — générez-le depuis l'API V2 de votre compte

## Installation

```bash
git clone https://github.com/3-bees-online/mcp-server-smsvertpro-python.git
cd mcp-server-smsvertpro-python
pip install -r requirements.txt
```

## Configuration

Définissez votre token API en variable d'environnement :

```bash
export SMSVERTPRO_API_TOKEN="votre_token_api_ici"
```

### Claude Desktop

Ajoutez dans votre fichier `claude_desktop_config.json` :

```json
{
  "mcpServers": {
    "smsvertpro": {
      "command": "python",
      "args": ["/chemin/vers/server.py"],
      "env": {
        "SMSVERTPRO_API_TOKEN": "votre_token_api_ici"
      }
    }
  }
}
```

### Claude Code (CLI)

```bash
claude mcp add smsvertpro -- python /chemin/vers/server.py
```

Puis configurez la variable d'environnement `SMSVERTPRO_API_TOKEN`.

### Cursor / Windsurf

Ajoutez la configuration MCP dans les paramètres de votre éditeur en pointant vers `python server.py` avec la variable d'environnement `SMSVERTPRO_API_TOKEN`.

## Outils disponibles

| Outil | Description |
|---|---|
| `send_sms` | Envoyer un SMS (immédiat ou programmé) |
| `check_credits` | Consulter le solde de crédits |
| `get_delivery_report` | Rapport de délivrabilité d'une campagne |
| `get_responses` | Réponses SMS reçues (bidirectionnel) |
| `verify_number` | Vérifier le format d'un numéro (syntaxe) |
| `get_blacklist` | Liste des désabonnements (STOP) |
| `generate_otp` | Envoyer un code OTP par SMS |
| `verify_otp` | Vérifier un code OTP |
| `cancel_sms` | Annuler un SMS programmé ou une campagne |

## Exemples d'utilisation

Une fois le serveur MCP connecté, demandez simplement à votre agent IA :

- *"Envoie un SMS au 33612345678 pour annoncer notre promo de printemps -20%"*
- *"Combien de crédits SMS il me reste ?"*
- *"Vérifie si le SMS de la campagne 12345 a été délivré"*
- *"Envoie un code OTP au 33698765432 pour confirmer l'inscription"*

L'agent IA utilisera automatiquement les bons outils avec les bons paramètres.

## Format des numéros

Les numéros de téléphone doivent être au **format international sans le `+`** :
- France : `33612345678` (pas `0612345678`, pas `+33612345678`)
- Belgique : `32470123456`
- Suisse : `41791234567`

## Sécurité

- Vérification SSL activée sur tous les appels API
- Validation des numéros de téléphone (format, longueur)
- Validation de l'expéditeur (alphanumérique, 11 caractères max)
- Validation des codes OTP (chiffres uniquement)
- Votre token API reste sur votre machine, il n'est jamais partagé avec l'agent IA
- Le serveur communique uniquement avec `https://www.smsvertpro.com/api/v2/`
- Pour les SMS marketing, ajoutez `STOP 36173` à la fin du message (obligation légale)

## Liens

- [SMS Vert Pro](https://www.smsvertpro.com)
- [Documentation API V2](https://www.smsvertpro.com/api-smsvertpro/)
- [Intégration IA](https://www.smsvertpro.com/integration-ia/)
- [Tarifs SMS](https://www.smsvertpro.com/tarifs/)
- [Version PHP](https://github.com/3-bees-online/mcp-server-smsvertpro-php)

## Licence

MIT — Voir [LICENSE](LICENSE)
