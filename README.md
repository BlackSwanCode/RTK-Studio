# RTK Scenario Studio

Interface graphique pour générer des scripts de provisionnement cloud
(**AWS CloudShell / Azure Cloud Shell / Google Cloud Shell**) à partir d'une
bibliothèque de **scénarios de test de sécurité** extraite et généralisée du
framework [RTK — Red Team Toolkit](.).

> ⚠️ **Usage strictement réservé aux engagements autorisés.** Comme le
> rappelle le `README.md` de RTK, chaque scénario déploie des ressources
> **volontairement mal configurées** (bucket public, CORS permissif, rôle IAM
> `Action:*`, service en mode debug, secret commité, serveur MCP sans garde-fou...).
> Ne déployez ces scénarios que dans un compte/abonnement/projet cloud
> **sandbox dédié**, dans le cadre d'un engagement couvert par un `scope.yaml`
> signé, puis **nettoyez systématiquement** à l'aide du script de nettoyage
> fourni pour chaque scénario.

## Ce que fait l'application

1. **Bibliothèque de scénarios** — chargée depuis `templates/scenarios.json`,
   un fichier JSON externe et éditable (ajoutez vos propres scénarios sans
   toucher au code Python).
2. **Personnalisation** — chaque scénario expose un formulaire de paramètres
   (nom du bucket, nom du service/conteneur, image conteneur, nom du dépôt,
   identité factice, ID d'engagement, région/location, mot de passe de lab,
   nom de rôle IAM...). Les valeurs par défaut de région s'adaptent
   automatiquement au cloud choisi.
3. **Choix de l'infrastructure cible** — AWS, Azure ou Google Cloud. Les
   boutons se désactivent automatiquement si un scénario ne couvre pas un
   cloud donné.
4. **Génération du code** — un script de déploiement (bash, compatible
   Cloud Shell : `aws`/`az`/`gcloud` CLI) et un script de nettoyage
   symétrique, à copier ou enregistrer en `.sh`.

## Scénarios inclus (7, couvrant AWS + Azure + GCP)

| Scénario | Module RTK | Catégorie |
|---|---|---|
| Bucket de stockage public oublié | `buckets.enum_buckets` (RTK-04) | Cloud Storage |
| Service conteneurisé CORS permissif + traversée | `buckets.cors_traversal` (RTK-05) | Conteneurs |
| GeoServer WMS/WFS anonyme avec couche sensible | `gis_meteo.ogc_anonymous_access` (RTK-20) | GIS / Météo |
| Secret committé puis supprimé dans un dépôt | `secrets.multi_repo_scan` (RTK-01) | Secrets |
| Service exposant des stack traces (debug actif) | `secrets.error_leakage` (RTK-02) | Secrets |
| Rôle IAM avec wildcard dangereux | `iam.wildcard_policies` (RTK-07) | IAM |
| Serveur MCP exposé (http_get sans allowlist) | `llm_mcp.tool_poisoning_watch` / `exfil_channels` (RTK-13/14) | LLM / MCP |

Chaque scénario correspond à un cas du catalogue `RTK × GCP — Catalogue de
scénarios de test.md` du dépôt, généralisé aux trois clouds.

## Lancer l'application

Aucune dépendance externe : uniquement la bibliothèque standard Python
(`tkinter` est inclus dans la plupart des distributions Python — sous Linux,
installez au besoin le paquet `python3-tk`).

```bash
python3 app.py
```

## Étendre la bibliothèque

Ouvrez `templates/scenarios.json` et ajoutez un objet dans le tableau
`scenarios`. Chaque scénario suit ce schéma :

```json
{
  "id": "identifiant-unique",
  "name": "Nom affiché",
  "rtk_module": "module.rtk (RTK-XX)",
  "category": "Catégorie",
  "severity": "high",
  "description": "Description du scénario.",
  "clouds": ["aws", "azure", "gcp"],
  "parameters": [
    {"key": "mon_param", "label": "Libellé affiché", "default": "valeur"},
    {"key": "region", "label": "Région", "default": "",
     "cloud_defaults": {"aws": "eu-west-3", "azure": "westeurope", "gcp": "europe-west1"}}
  ],
  "scripts": {
    "aws": "#!/usr/bin/env bash\n...{{mon_param}}...",
    "azure": "...",
    "gcp": "..."
  },
  "cleanup": {
    "aws": "...",
    "azure": "...",
    "gcp": "..."
  }
}
```

Les paramètres sont injectés dans les scripts via la syntaxe `{{cle}}`
(simple remplacement de texte — aucune évaluation de code, donc sans risque
d'injection via la bibliothèque de templates elle-même).

## Limites connues / pistes d'amélioration

- Les scripts générés sont des **modèles pédagogiques** : avant exécution en
  conditions réelles, relisez-les et adaptez-les à votre organisation
  (comptes, VPC, politiques de nommage, outillage CI/CD).
- Pas de validation stricte des identifiants cloud saisis (ex. noms de bucket
  S3 doivent être globalement uniques) — le champ reste libre, à vous de
  vérifier avant déploiement.
- La génération reste **un éditeur de texte structuré**, pas un orchestrateur :
  elle ne se connecte à aucun compte cloud et n'exécute rien elle-même.
