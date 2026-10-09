# RTK Scenario Studio

Interface graphique de bureau (Tkinter) pour générer, à partir d'une
bibliothèque de **scénarios de test de sécurité cloud**, des artefacts
pédagogiques prêts à l'emploi : script de déploiement, script de nettoyage
symétrique, squelette **Terraform/OpenTofu**, et rapport d'engagement au
format Markdown.

Les scénarios sont une extraction et une généralisation multi-cloud
(**AWS / Azure / Google Cloud**) de cas issus du framework
[RTK — Red Team Toolkit](.).

> ⚠️ **Usage strictement réservé aux engagements autorisés.** Chaque
> scénario déploie des ressources **volontairement mal configurées**
> (bucket public, CORS permissif, rôle IAM `Action:*`, service en mode
> debug, secret committé, serveur MCP sans garde-fou...). Ne déployez ces
> scénarios que dans un compte/abonnement/projet cloud **sandbox dédié**,
> dans le cadre d'un engagement couvert par un `scope.yaml` signé, puis
> **nettoyez systématiquement** à l'aide du script de nettoyage généré
> pour chaque scénario.

## Sommaire

- [Aperçu](#aperçu)
- [Fonctionnalités](#fonctionnalités)
- [Scénarios inclus](#scénarios-inclus-7--aws--azure--gcp)
- [Installation & lancement](#installation--lancement)
- [Prise en main](#prise-en-main)
- [Architecture du projet](#architecture-du-projet)
- [Format `scenarios.json`](#format-scenariosjson)
- [Validation & sécurité des entrées](#validation--sécurité-des-entrées)
- [Étendre la bibliothèque](#étendre-la-bibliothèque)
- [Raccourcis clavier](#raccourcis-clavier)
- [Limites connues / pistes d'amélioration](#limites-connues--pistes-damélioration)
- [Licence & avertissement](#licence--avertissement)

## Aperçu

RTK Scenario Studio est une application **monofichier** (`app.py`) et
**sans dépendance externe** (bibliothèque standard Python uniquement) qui
sert d'éditeur de texte structuré pour préparer des démonstrations ou des
exercices de test d'intrusion cloud. Elle ne se connecte à aucun compte
cloud et n'exécute rien elle-même : elle produit du texte (scripts shell,
code Terraform, rapport Markdown) que l'opérateur relit et exécute
lui-même, en toute connaissance de cause, dans son propre environnement
sandbox.

## Fonctionnalités

- **Bibliothèque de scénarios externalisée** — chargée depuis
  `scenarios.json` (fichier JSON à la racine du projet, au même niveau que
  `app.py`), modifiable sans toucher au code Python.
- **Recherche** — un champ de recherche dans la barre latérale filtre les
  scénarios par nom, catégorie ou module RTK en temps réel.
- **Fiche didactique par scénario** — nom, module RTK, catégorie, badge de
  sévérité colorisé (`low` → `critical`), description, références
  **OWASP** et **MITRE ATT&CK**, concept cloud manipulé et faille de
  sécurité exploitée.
- **Personnalisation par formulaire** — chaque scénario expose ses propres
  paramètres (nom du bucket, nom du service/conteneur, image conteneur,
  nom du dépôt, identité factice, ID d'engagement, mot de passe de lab,
  nom de rôle IAM, région...). Les valeurs par défaut de région s'adaptent
  automatiquement au cloud sélectionné.
- **Choix de l'infrastructure cible** — AWS, Azure ou Google Cloud ; les
  boutons radio se désactivent automatiquement si le scénario sélectionné
  ne couvre pas un cloud donné, avec bascule automatique vers un cloud
  supporté.
- **Génération multi-artefacts**, répartie en 4 onglets :
  1. **Configuration** — choix du cloud cible et des paramètres.
  2. **Script de déploiement (Bash)** — compatible Cloud Shell
     (`aws`/`az`/`gcloud` CLI), précédé d'un en-tête didactique généré
     automatiquement (objectif, références, concept cloud, faille
     exploitée, paramètres utilisés).
  3. **Script de nettoyage (Bash)** — symétrique au script de déploiement,
     pour supprimer systématiquement les ressources créées.
  4. **Infrastructure as Code (Terraform/OpenTofu)** — squelette `.tf`
     généré à partir d'un gabarit optionnel par scénario/cloud (affiche un
     message pédagogique si aucun gabarit Terraform n'est encore défini
     pour le scénario/cloud choisi — voir
     [Limites connues](#limites-connues--pistes-damélioration)).
- **Rapport d'engagement en Markdown** — bouton « 📄 Rapport MD » qui
  compile objectif, référentiels de sécurité, analyse pédagogique,
  paramètres utilisés et les trois artefacts générés (déploiement,
  nettoyage, Terraform) dans un unique document Markdown horodaté, prêt à
  être archivé ou annexé à un rapport de pentest.
- **Copier / Enregistrer sous…** — chaque artefact (déploiement, nettoyage,
  Terraform) peut être copié dans le presse-papiers ou enregistré dans un
  fichier (`.sh` ou `.tf`) via une boîte de dialogue native, avec un nom de
  fichier par défaut construit à partir de l'ID du scénario, du cloud et du
  type d'artefact.
- **Rechargement à chaud de la bibliothèque** (`F5`) — relit
  `scenarios.json` sans redémarrer l'application, pratique en cours
  d'édition des scénarios.
- **Validation des paramètres avant génération** — chaque champ est
  sanitisé selon son rôle (voir
  [Validation & sécurité des entrées](#validation--sécurité-des-entrées)),
  avec confirmation explicite si des champs sont laissés vides.
- **Interface sombre** sur mesure (Tkinter/ttk stylé), cartes de scénarios
  cliquables avec recherche, surlignage de sélection, badges de sévérité.

## Scénarios inclus (7, couvrant AWS + Azure + GCP)

| Scénario | Module RTK | Catégorie | Sévérité |
|---|---|---|---|
| Bucket de stockage public oublié | `buckets.enum_buckets` (RTK-04) | Cloud Storage | high |
| Service conteneurisé CORS permissif + traversée de chemin | `buckets.cors_traversal` (RTK-05) | Applications conteneurisées | high / critical |
| Serveur GeoServer (WMS/WFS) anonyme avec couche sensible | `gis_meteo.ogc_anonymous_access` (RTK-20) | GIS / Météo | high |
| Clé de service account committée puis supprimée dans un dépôt | `secrets.multi_repo_scan` (RTK-01) | Secrets | critical |
| Service exposant des stack traces (mode debug actif) | `secrets.error_leakage` (RTK-02) | Secrets | high |
| Rôle IAM personnalisé avec wildcard dangereux | `iam.wildcard_policies` (RTK-07) | IAM | high |
| Serveur MCP exposé (outil `http_get` sans allowlist de sortie) | `llm_mcp.tool_poisoning_watch` (RTK-13) / `llm_mcp.exfil_channels` (RTK-14) | LLM / MCP | critical |

Chaque scénario couvre les trois clouds (AWS, Azure, GCP) et correspond à
un cas du catalogue `RTK × GCP — Catalogue de scénarios de test.md` du
dépôt RTK, généralisé aux trois fournisseurs.

## Installation & lancement

Aucune dépendance externe : uniquement la bibliothèque standard Python.
`tkinter` est inclus dans la plupart des distributions Python — sous
Linux, installez au besoin le paquet système correspondant
(`python3-tk` sur Debian/Ubuntu, `python3-tkinter` sur Fedora, etc.).

```bash
# Python 3.10+ recommandé (utilisation de `list[dict]`, `str | None`, etc.)
python3 app.py
```

Les deux fichiers `app.py` et `scenarios.json` doivent rester au même
niveau : l'application lève une erreur explicite (boîte de dialogue) si
`scenarios.json` est introuvable ou mal formé.

## Prise en main

1. Lancez `python3 app.py`. Le premier scénario de la bibliothèque est
   sélectionné automatiquement.
2. Dans la barre latérale, utilisez la recherche ou cliquez sur une carte
   pour choisir un scénario.
3. Onglet **1 · Configuration** : choisissez le cloud cible (les clouds
   non supportés par le scénario sont grisés) et ajustez les paramètres du
   formulaire (valeurs par défaut pré-remplies, y compris la région selon
   le cloud choisi).
4. Cliquez sur **⚙ Générer les artefacts** : les trois scripts/gabarits
   sont produits et l'application bascule sur l'onglet **2**.
5. Parcourez les onglets **2 · Script de déploiement**,
   **3 · Script de nettoyage** et **4 · Infrastructure as Code** pour
   relire, copier ou enregistrer chaque artefact.
6. Optionnel : cliquez sur **📄 Rapport MD** pour exporter un rapport
   d'engagement Markdown regroupant contexte, référentiels et artefacts.
7. **Avant toute exécution réelle**, relisez chaque script généré,
   adaptez-le à votre organisation, et assurez-vous d'opérer dans le
   périmètre exact d'un engagement autorisé.
8. Une fois le test terminé, exécutez systématiquement le script de
   nettoyage correspondant.

## Architecture du projet

```
RTK-Studio-main/
├── app.py            # Application Tkinter monofichier (point d'entrée)
└── scenarios.json     # Bibliothèque de scénarios (données, éditable)
```

`app.py` est organisé en six sections commentées :

1. **Chargement des scénarios** (`load_scenarios`) — lecture et validation
   de `scenarios.json`, avec messages d'erreur explicites (JSON invalide,
   fichier manquant).
2. **Constantes & configuration UI** — palette de couleurs du thème sombre,
   libellés des clouds, couleurs de sévérité, et `KNOWN_REGIONS` (listes de
   régions valides par cloud, utilisées pour la validation).
3. **Fonctions utilitaires & moteur de rendu** — fonctions de
   sanitization (`sanitize_resource_name`, `sanitize_generic`,
   `sanitize_shell_safe`, `sanitize_container_image`), validation de
   région (`validate_region`), moteur de templating (`render_template`),
   génération de l'en-tête didactique (`build_didactic_header`) et des
   blocs de code Markdown (`md_fenced_block`).
4. **Widgets personnalisés** — `Badge` (étiquette colorée), `ScenarioCard`
   (carte cliquable de la bibliothèque), `LabeledEntry` (champ de
   formulaire étiqueté).
5. **Application principale** (`RTKScenarioStudio`) — fenêtre Tkinter :
   construction du layout (en-tête, bandeau d'avertissement, barre
   latérale avec recherche, zone principale à onglets), sélection de
   scénario, construction dynamique des champs de paramètres, validation
   et génération des artefacts, copie/enregistrement, génération du
   rapport, rechargement à chaud.
6. **Point d'entrée** (`main`) — instancie et lance l'application.

## Format `scenarios.json`

Le fichier contient un objet avec une clé `scenarios`, tableau d'objets
suivant ce schéma :

```json
{
  "scenarios": [
    {
      "id": "identifiant-unique",
      "name": "Nom affiché",
      "rtk_module": "module.rtk (RTK-XX)",
      "category": "Catégorie",
      "severity": "high",
      "description": "Description du scénario.",
      "didactique": {
        "owasp": ["A05:2021 – Security Misconfiguration"],
        "mitre_attack": ["T1530: Data from Cloud Storage Object"],
        "concept_cloud": "Explication du concept cloud manipulé.",
        "faille_securite": "Explication de la faille exploitée."
      },
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
      },
      "terraform": {
        "aws": "resource \"aws_s3_bucket\" \"...\" { ... }",
        "azure": "...",
        "gcp": "..."
      }
    }
  ]
}
```

Notes sur le schéma :

- `didactique` est optionnel ; les sous-sections vides (sans référence
  OWASP/MITRE, sans concept cloud ou sans faille documentée) sont
  automatiquement masquées dans l'en-tête didactique généré, plutôt que
  d'afficher une mention « non documenté ».
- `terraform` est **optionnel** par scénario et par cloud. S'il est absent
  pour le cloud sélectionné, l'onglet Terraform affiche un message de
  substitution pédagogique au lieu d'un gabarit vide. Aucun des 7
  scénarios livrés par défaut n'inclut encore de gabarit Terraform (voir
  [Limites connues](#limites-connues--pistes-damélioration)).
- `parameters[].cloud_defaults` permet de faire varier la valeur par
  défaut d'un champ selon le cloud sélectionné (typiquement la région) ;
  la valeur est réappliquée automatiquement lors d'un changement de cloud
  tant que le champ n'a pas été modifié manuellement par l'utilisateur.
- Les paramètres sont injectés dans les scripts (`scripts`, `cleanup`,
  `terraform`) via la syntaxe `{{cle}}` — simple remplacement de texte par
  expression régulière, sans évaluation de code, donc sans risque
  d'injection via le moteur de templating lui-même.

## Validation & sécurité des entrées

Avant génération, chaque champ de paramètre est sanitisé selon sa
catégorie :

| Catégorie de clé | Clés concernées | Règle |
|---|---|---|
| Nom de ressource | `org`, `env`, `suffix`, `service_name`, `repo_name`, `role_name`, `decoy_identity_name`, `engagement_id` | `^[A-Za-z0-9_-]{3,64}$` (lettres, chiffres, tirets, underscores — majuscules autorisées) |
| Valeur libre | `admin_password`, `fake_api_key` | Tout caractère autorisé sauf retour à la ligne |
| Image conteneur | `container_image` | `^[A-Za-z0-9._/:@-]{3,255}$` (format `registry/name:tag`) |
| Région | `region` | Doit appartenir à la liste `KNOWN_REGIONS` du cloud sélectionné ; en cas d'erreur, des suggestions par préfixe commun sont proposées (ex. `us-west` → `us-west-2`) |
| Autres champs | tout le reste (ex. `sensitive_layer_name`) | Rejet des métacaractères shell dangereux (`;`, `&`, `|`, `` ` ``, `$`, `(`, `)`, espaces) |

Si un ou plusieurs champs sont laissés vides, une confirmation explicite
est demandée avant de poursuivre la génération. Ces contrôles réduisent le
risque d'arguments shell malformés ou d'injection accidentelle dans les
scripts générés, mais **ne remplacent pas une relecture humaine** avant
exécution.

## Étendre la bibliothèque

1. Ouvrez `scenarios.json` et ajoutez un objet au tableau `scenarios` en
   suivant le [schéma ci-dessus](#format-scenariosjson).
2. Si l'application est déjà lancée, appuyez sur **F5** pour recharger la
   bibliothèque sans redémarrer.
3. Pensez à renseigner `didactique.owasp` / `didactique.mitre_attack` pour
   que le scénario s'intègre correctement au rapport d'engagement
   Markdown.
4. Ajoutez un gabarit `terraform` par cloud si vous souhaitez que l'onglet
   Infrastructure as Code produise du code plutôt que le message de
   substitution par défaut.

## Raccourcis clavier

| Raccourci | Action |
|---|---|
| `F5` | Recharge la bibliothèque de scénarios depuis `scenarios.json` |

## Limites connues / pistes d'amélioration

- Les scripts générés sont des **modèles pédagogiques** : avant exécution
  en conditions réelles, relisez-les et adaptez-les à votre organisation
  (comptes, VPC, politiques de nommage, outillage CI/CD).
- La validation des identifiants cloud reste une **liste blanche de
  régions connues** (`KNOWN_REGIONS`) plutôt qu'une vérification en temps
  réel auprès des fournisseurs ; les noms de ressources globalement
  uniques (ex. bucket S3) ne sont pas vérifiés pour disponibilité.
- **Aucun des 7 scénarios livrés n'inclut encore de gabarit Terraform** :
  l'onglet « Infrastructure as Code » est fonctionnel et affiche un
  message pédagogique tant que le champ `terraform` n'est pas renseigné
  pour le scénario/cloud choisi dans `scenarios.json`.
- La génération reste **un éditeur de texte structuré**, pas un
  orchestrateur : l'application ne se connecte à aucun compte cloud et
  n'exécute rien elle-même.
- Interface Tkinter mono-fenêtre, non testée en-dehors de Windows/Linux
  avec un environnement graphique standard.

## Licence & avertissement

Projet pédagogique destiné à la formation et à la préparation
d'engagements de test d'intrusion cloud **autorisés**. L'utilisateur reste
seul responsable de l'usage fait des scripts et gabarits générés, de leur
conformité au périmètre d'engagement signé, et du nettoyage systématique
des ressources déployées.
