#!/usr/bin/env python3
"""
RTK Scenario Studio (Édition Monofichier & Pédagogique)
========================================================
Interface graphique autonome pour générer des scripts de provisionnement cloud.

- Les scénarios sont chargés depuis un fichier externe 'scenarios.json'.
- Zéro dépendance externe (bibliothèque standard Python uniquement).

Version : 1.1.0
"""

from __future__ import annotations

import json
import re
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


# ==============================================================================
# 1. CHARGEMENT DES SCÉNARIOS (DEPUIS FICHIER EXTERNE)
# ==============================================================================
def load_scenarios() -> list[dict]:
    """Charge les scénarios depuis le fichier scenarios.json situé dans le même dossier."""
    json_path = Path(__file__).parent / "scenarios.json"

    if not json_path.exists():
        raise FileNotFoundError(
            f"Le fichier 'scenarios.json' est introuvable dans :\n{json_path.parent}\n"
            "Veuillez placer le fichier 'scenarios.json' au même niveau que app.py."
        )

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("scenarios", [])
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Erreur de syntaxe JSON dans scenarios.json "
            f"(ligne {e.lineno}, col {e.colno}) :\n{e.msg}"
        )
    except Exception as e:
        raise RuntimeError(f"Erreur lors de la lecture de scenarios.json : {e}")


# ==============================================================================
# 2. CONSTANTES & CONFIGURATION UI
# ==============================================================================
BG_ROOT = "#0f1420"
BG_PANEL = "#161d2e"
BG_PANEL_ALT = "#1b2338"
BG_CARD = "#202a42"
BG_CARD_HOVER = "#263152"
BG_INPUT = "#111727"
FG_TEXT = "#e7ebf5"
FG_MUTED = "#8793b0"
FG_SUBTLE = "#5f6b8a"
ACCENT = "#5ad1c0"
ACCENT_DARK = "#2f8f82"
ACCENT_SOFT = "#213a3a"
WARN = "#f0a35e"
CRIT = "#e1636e"
BORDER = "#2a3450"

CLOUD_LABELS = {"aws": "AWS", "azure": "Azure", "gcp": "Google Cloud"}

SEVERITY_COLOR = {
    "critical": CRIT,
    "high": "#e8905a",
    "high / critical": "#e8905a",
    "medium": "#e0c158",
    "info/high": "#e0c158",
    "low": FG_MUTED,
}

# 🔧 CORRECTIF N°3 : liste (non exhaustive) des régions valides par cloud.
# Empêche la saisie de régions fantaisistes comme "us-west-3".
KNOWN_REGIONS: dict[str, set[str]] = {
    "aws": {
        # Europe
        "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1",
        "eu-north-1", "eu-south-1",
        # US
        "us-east-1", "us-east-2", "us-west-1", "us-west-2",
        # Asie-Pacifique
        "ap-southeast-1", "ap-southeast-2", "ap-southeast-3",
        "ap-northeast-1", "ap-northeast-2", "ap-northeast-3",
        "ap-south-1",
        # Autres
        "ca-central-1", "sa-east-1", "me-south-1", "af-south-1",
    },
    "azure": {
        "westeurope", "northeurope", "francecentral", "francesouth",
        "eastus", "eastus2", "westus", "westus2", "westus3",
        "centralus", "northcentralus", "southcentralus",
        "uksouth", "ukwest", "germanywestcentral",
        "switzerlandnorth", "switzerlandwest",
        "japaneast", "japanwest", "southeastasia", "eastasia",
    },
    "gcp": {
        "europe-west1", "europe-west2", "europe-west3", "europe-west4",
        "europe-west6", "europe-west8", "europe-west9",
        "europe-north1", "europe-central2", "europe-southwest1",
        "us-central1", "us-east1", "us-east4", "us-west1", "us-west2",
        "us-west3", "us-west4", "northamerica-northeast1",
        "asia-east1", "asia-northeast1", "asia-southeast1",
        "asia-south1", "australia-southeast1",
    },
}


def severity_color(sev: str) -> str:
    return SEVERITY_COLOR.get(sev.lower().strip(), FG_MUTED)


# ==============================================================================
# 3. FONCTIONS UTILITAIRES & MOTEUR DE RENDU
# ==============================================================================
def sanitize_resource_name(value: str) -> str:
    """
    🔧 CORRECTIF N°4a : accepte désormais les majuscules (ex. 'ENG-2026-LAB')
    tout en restant strict sur la longueur et les caractères autorisés.
    """
    if not re.match(r"^[A-Za-z0-9_-]{3,64}$", value):
        raise ValueError(
            "Doit contenir uniquement lettres (a-z/A-Z), chiffres, "
            "tirets et underscores (3-64 car.)"
        )
    return value


def sanitize_generic(value: str) -> str:
    """
    🔧 CORRECTIF N°4b : interdit désormais les espaces (qui casseraient les
    arguments shell multi-mots comme --tags Key=...,Value=...).
    """
    if re.search(r"[;&|`$()\s]", value):
        raise ValueError(
            "Contient des caractères shell interdits (&, ;, |, `, $, (), espaces)"
        )
    return value


def sanitize_shell_safe(value: str) -> str:
    """Autorise tout sauf les retours à la ligne (mots de passe, clés API factices)."""
    if "\n" in value or "\r" in value:
        raise ValueError("Ne doit pas contenir de saut de ligne")
    return value


def sanitize_container_image(value: str) -> str:
    """Valide une référence d'image conteneur (registry/name:tag)."""
    if not re.match(r"^[A-Za-z0-9._/:@-]{3,255}$", value):
        raise ValueError(
            "Image conteneur invalide (attendu : registry/name:tag ou name:tag)"
        )
    return value


# 🔧 CORRECTIF N°3 (suite) : validation des régions
def validate_region(cloud: str, region: str) -> str:
    """Vérifie que la région saisie fait partie des régions connues pour ce cloud."""
    if not region:
        return region  # on laisse passer le vide (sera signalé comme "manquant")
    allowed = KNOWN_REGIONS.get(cloud)
    if not allowed:
        return region
    if region not in allowed:
        # Proposer une suggestion par préfixe commun (ex. 'us-west' → 'us-west-2')
        prefix = region.rsplit("-", 1)[0] if "-" in region else region
        suggestions = sorted(r for r in allowed if r.startswith(prefix))
        hint = (
            f" Suggestions proches : {', '.join(suggestions[:3])}."
            if suggestions
            else ""
        )
        raise ValueError(
            f"Région '{region}' inconnue pour {cloud}.{hint}"
        )
    return region


def render_template(text: str, values: dict[str, str]) -> str:
    def repl(m: re.Match) -> str:
        key = m.group(1)
        return str(values.get(key, m.group(0)))

    return re.sub(r"\{\{(\w+)\}\}", repl, text)


def build_didactic_header(scenario: dict, cloud: str, values: dict) -> str:
    """
    🔧 CORRECTIF N°1 : le shebang n'est plus ajouté ici (il est déjà présent
    au début de chaque template de script dans scenarios.json). Cela évite
    la duplication « #!/usr/bin/env bash » en tête de fichier généré.

    🔧 CORRECTIF N°2 : les sections didactiques vides (sans références OWASP,
    sans concept cloud, etc.) sont désormais masquées au lieu d'afficher
    « Non documenté ».
    """
    did = scenario.get("didactique", {})
    owasp = did.get("owasp", [])
    mitre = did.get("mitre_attack", [])
    concept = did.get("concept_cloud")
    faille = did.get("faille_securite")

    lines = [
        "#" + "=" * 78,
        f"# 🛡️  SCÉNARIO RTK : {scenario['name']}",
        f"# 🎯 OBJECTIF PÉDAGOGIQUE : {scenario['description']}",
    ]

    # Section références (OWASP / MITRE) — affichée uniquement si non vide
    if owasp or mitre:
        lines.append("#" + "-" * 78)
        lines.append("# 📚 RÉFÉRENCES :")
        for ref in owasp:
            lines.append(f"#   • OWASP : {ref}")
        for ref in mitre:
            lines.append(f"#   • MITRE ATT&CK : {ref}")

    # Section concept cloud — affichée uniquement si non vide
    if concept:
        lines.append("#" + "-" * 78)
        lines.append("# 💡 CONCEPT CLOUD CLÉ :")
        lines.append(f"#   {concept}")

    # Section faille — affichée uniquement si non vide
    if faille:
        lines.append("#")
        lines.append("# ⚠️ FAILLE DE SÉCURITÉ EXPLOITÉE :")
        lines.append(f"#   {faille}")

    # Section paramètres (toujours affichée)
    lines.append("#")
    lines.append("# 🔧 PARAMÈTRES D'EXÉCUTION :")
    for key, val in values.items():
        lines.append(f"#   {key.upper():<20} = {val}")
    lines.append("#" + "=" * 78)
    return "\n".join(lines)


def md_fenced_block(content: str, lang: str = "") -> str:
    """Renvoie un bloc de code Markdown en calculant le bon nombre de backticks."""
    fence = "```"
    while fence in content:
        fence += "`"
    return f"{fence}{lang}\n{content}\n{fence}"


# ==============================================================================
# 4. WIDGETS PERSONNALISÉS
# ==============================================================================
class Badge(tk.Frame):
    def __init__(self, parent, text, color, **kw):
        super().__init__(parent, bg=color, **kw)
        tk.Label(
            self,
            text=text,
            bg=color,
            fg="#0b0e16",
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=2,
        ).pack()


class ScenarioCard(tk.Frame):
    def __init__(self, parent, scenario: dict, on_select):
        super().__init__(parent, bg=BG_CARD, cursor="hand2", padx=12, pady=10)
        self.scenario = scenario
        self.on_select = on_select
        self.selected = False

        tk.Label(
            self,
            text=scenario["name"],
            bg=BG_CARD,
            fg=FG_TEXT,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
            justify="left",
            wraplength=250,
        ).pack(fill="x")

        tk.Label(
            self,
            text=f"{scenario['rtk_module']}",
            bg=BG_CARD,
            fg=ACCENT,
            font=("Consolas", 9),
            anchor="w",
        ).pack(fill="x", pady=(2, 6))

        bottom = tk.Frame(self, bg=BG_CARD)
        bottom.pack(fill="x")
        tk.Label(
            bottom,
            text=scenario["category"],
            bg=BG_CARD,
            fg=FG_MUTED,
            font=("Segoe UI", 8),
        ).pack(side="left")
        tk.Label(
            bottom,
            text=scenario["severity"],
            bg=BG_CARD,
            fg=severity_color(scenario["severity"]),
            font=("Segoe UI", 8, "bold"),
        ).pack(side="right")

        self._children_bg = [self] + list(self.winfo_children())
        for w in self._children_bg:
            w.bind("<Button-1>", lambda _evt=None: self._click())
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)

    def _click(self):
        self.on_select(self.scenario["id"])

    def _enter(self, _evt=None):
        if not self.selected:
            self._set_bg(BG_CARD_HOVER)

    def _leave(self, _evt=None):
        if not self.selected:
            self._set_bg(BG_CARD)

    def set_selected(self, selected: bool):
        self.selected = selected
        self._set_bg(ACCENT_SOFT if selected else BG_CARD)

    def _set_bg(self, color):
        for w in self._children_bg:
            try:
                w.configure(bg=color)
            except tk.TclError:
                pass


class LabeledEntry(tk.Frame):
    def __init__(self, parent, label: str, default: str = ""):
        super().__init__(parent, bg=BG_PANEL_ALT)
        tk.Label(
            self,
            text=label,
            bg=BG_PANEL_ALT,
            fg=FG_MUTED,
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill="x", pady=(0, 3))
        self.var = tk.StringVar(value=default)
        self.entry = tk.Entry(
            self,
            textvariable=self.var,
            bg=BG_INPUT,
            fg=FG_TEXT,
            insertbackground=ACCENT,
            relief="flat",
            font=("Consolas", 10),
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
        )
        self.entry.pack(fill="x", ipady=6)

    def get(self) -> str:
        return self.var.get()

    def set(self, value: str):
        self.var.set(value)


# ==============================================================================
# 5. APPLICATION PRINCIPALE
# ==============================================================================
class RTKScenarioStudio(tk.Tk):
    # 🔧 CORRECTIF N°4 : ensembles de clés de paramètres pour la validation.
    # - RESOURCE_NAME_KEYS : identifiants de ressources (strict, mais majuscules OK)
    # - SHELL_SAFE_KEYS    : valeurs libres (mots de passe, clés) - tout sauf \n
    # - IMAGE_KEYS         : références d'images conteneur
    RESOURCE_NAME_KEYS = {
        "org", "env", "suffix", "service_name", "repo_name",
        "role_name", "decoy_identity_name", "engagement_id",
    }
    SHELL_SAFE_KEYS = {"admin_password", "fake_api_key"}
    IMAGE_KEYS = {"container_image"}

    def __init__(self):
        super().__init__()
        self.title("RTK Scenario Studio — Générateur Multi-Cloud & Pédagogique")
        self.geometry("1320x850")
        self.minsize(1100, 700)
        self.configure(bg=BG_ROOT)

        # Chargement des scénarios avec gestion d'erreur différée (évite le TclError)
        try:
            self.scenarios = load_scenarios()
        except Exception as exc:
            self.scenarios = []
            self.after(200, lambda: messagebox.showerror("Erreur de chargement", str(exc)))

        self.scenarios_by_id = {s["id"]: s for s in self.scenarios}
        self.current_scenario_id: str | None = None
        self.current_cloud = tk.StringVar(value="aws")
        self.param_widgets: dict[str, LabeledEntry] = {}
        self.cards: dict[str, ScenarioCard] = {}
        self.generated_deploy = ""
        self.generated_cleanup = ""
        self.generated_terraform = ""

        self._build_style()
        self._build_layout()
        if self.scenarios:
            self.select_scenario(self.scenarios[0]["id"])
        self.bind("<F5>", lambda _evt: self._reload_scenarios())

    # ------------------------------------------------------------------ reload
    def _reload_scenarios(self):
        try:
            self.scenarios = load_scenarios()
            self.scenarios_by_id = {s["id"]: s for s in self.scenarios}
            self._refresh_cards()
            if self.current_scenario_id and self.current_scenario_id in self.scenarios_by_id:
                self.select_scenario(self.current_scenario_id)
            messagebox.showinfo("Succès", "Bibliothèque rechargée avec succès.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Échec du rechargement : {e}")

    # ------------------------------------------------------------------- style
    def _build_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(
            "Cloud.TRadiobutton",
            background=BG_PANEL_ALT,
            foreground=FG_TEXT,
            font=("Segoe UI", 10, "bold"),
            padding=(10, 8),
        )
        style.map(
            "Cloud.TRadiobutton",
            background=[("active", BG_CARD_HOVER)],
            foreground=[("selected", ACCENT)],
        )

        style.configure("Dark.TNotebook", background=BG_PANEL, borderwidth=0)
        style.configure(
            "Dark.TNotebook.Tab",
            background=BG_PANEL_ALT,
            foreground=FG_MUTED,
            padding=(16, 10),
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
        )
        style.map(
            "Dark.TNotebook.Tab",
            background=[("selected", BG_PANEL)],
            foreground=[("selected", ACCENT)],
        )

        style.configure(
            "Vertical.TScrollbar",
            background=BG_PANEL,
            troughcolor=BG_ROOT,
            bordercolor=BG_ROOT,
            arrowcolor=FG_MUTED,
            relief="flat",
        )

    def _accent_button(self, parent, text, command, primary=True):
        bg = ACCENT if primary else BG_CARD
        fg = "#0b0e16" if primary else FG_TEXT
        active_bg = ACCENT_DARK if primary else BG_CARD_HOVER
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=16,
            pady=8,
            bd=0,
            cursor="hand2",
        )

    # ------------------------------------------------------------------ layout
    def _build_layout(self):
        header = tk.Frame(self, bg=BG_ROOT, pady=16, padx=20)
        header.pack(fill="x")
        tk.Label(
            header,
            text="RTK Scenario Studio",
            bg=BG_ROOT,
            fg=FG_TEXT,
            font=("Segoe UI", 18, "bold"),
        ).pack(side="left")
        tk.Label(
            header,
            text="  |  Bibliothèque pédagogique de scénarios de test cloud",
            bg=BG_ROOT,
            fg=FG_MUTED,
            font=("Segoe UI", 10),
        ).pack(side="left")

        warn = tk.Frame(self, bg="#2e2412", padx=20, pady=8)
        warn.pack(fill="x")
        tk.Label(
            warn,
            text=(
                "⚠️  Usage réservé aux engagements autorisés, sur comptes/projets cloud "
                "sandbox dédiés. Déployez uniquement dans le périmètre d'un scope.yaml "
                "signé, nettoyez systématiquement après usage."
            ),
            bg="#2e2412",
            fg=WARN,
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill="x")

        body = tk.Frame(self, bg=BG_ROOT)
        body.pack(fill="both", expand=True, padx=20, pady=16)
        body.columnconfigure(0, weight=0, minsize=320)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_sidebar(body)
        self._build_main(body)

    # ----------------------------------------------------------------- sidebar
    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=BG_PANEL)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 16))

        tk.Label(
            sidebar,
            text="BIBLIOTHÈQUE DE SCÉNARIOS",
            bg=BG_PANEL,
            fg=FG_SUBTLE,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
            padx=14,
            pady=12,
        ).pack(fill="x")

        search_frame = tk.Frame(sidebar, bg=BG_PANEL, padx=14)
        search_frame.pack(fill="x", pady=(0, 8))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._refresh_cards())
        search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            bg=BG_INPUT,
            fg=FG_TEXT,
            insertbackground=ACCENT,
            relief="flat",
            font=("Segoe UI", 10),
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
        )
        search_entry.pack(fill="x", ipady=6)
        self._search_placeholder(search_entry)

        canvas = tk.Canvas(sidebar, bg=BG_PANEL, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            sidebar, orient="vertical", command=canvas.yview, style="Vertical.TScrollbar"
        )
        self.cards_frame = tk.Frame(canvas, bg=BG_PANEL)
        self.cards_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.cards_frame, anchor="nw", width=290)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(14, 0))
        scrollbar.pack(side="right", fill="y")

        # Bind du wheel uniquement quand la souris est sur le canvas
        def _on_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_wheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        self._refresh_cards()

    def _search_placeholder(self, entry: tk.Entry):
        placeholder = "Rechercher un scénario…"

        def on_focus_in(_evt):
            if entry.get() == placeholder:
                entry.delete(0, "end")
                entry.configure(fg=FG_TEXT)

        def on_focus_out(_evt):
            if not entry.get():
                entry.insert(0, placeholder)
                entry.configure(fg=FG_SUBTLE)

        entry.insert(0, placeholder)
        entry.configure(fg=FG_SUBTLE)
        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

    def _refresh_cards(self):
        for child in self.cards_frame.winfo_children():
            child.destroy()
        self.cards.clear()

        query = self.search_var.get().strip().lower()
        if query == "rechercher un scénario…":
            query = ""

        for scenario in self.scenarios:
            haystack = " ".join(
                [scenario["name"], scenario["category"], scenario["rtk_module"]]
            ).lower()
            if query and query not in haystack:
                continue
            card = ScenarioCard(self.cards_frame, scenario, self.select_scenario)
            card.pack(fill="x", pady=(0, 8), padx=(0, 14))
            self.cards[scenario["id"]] = card
            if scenario["id"] == self.current_scenario_id:
                card.set_selected(True)

    # -------------------------------------------------------------------- main
    def _build_main(self, parent):
        main = tk.Frame(parent, bg=BG_PANEL)
        main.grid(row=0, column=1, sticky="nsew")
        main.rowconfigure(1, weight=1)
        main.columnconfigure(0, weight=1)

        self.scenario_header = tk.Frame(main, bg=BG_PANEL, padx=20, pady=16)
        self.scenario_header.grid(row=0, column=0, sticky="ew")
        self.title_label = tk.Label(
            self.scenario_header,
            text="",
            bg=BG_PANEL,
            fg=FG_TEXT,
            font=("Segoe UI", 15, "bold"),
            anchor="w",
        )
        self.title_label.pack(fill="x")
        self.desc_label = tk.Label(
            self.scenario_header,
            text="",
            bg=BG_PANEL,
            fg=FG_MUTED,
            font=("Segoe UI", 10),
            anchor="w",
            justify="left",
            wraplength=820,
        )
        self.desc_label.pack(fill="x", pady=(6, 0))
        self.badges_frame = tk.Frame(self.scenario_header, bg=BG_PANEL)
        self.badges_frame.pack(fill="x", pady=(10, 0))

        notebook = ttk.Notebook(main, style="Dark.TNotebook")
        notebook.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))

        self.tab_params = tk.Frame(notebook, bg=BG_PANEL_ALT)
        self.tab_script = tk.Frame(notebook, bg=BG_PANEL_ALT)
        self.tab_cleanup = tk.Frame(notebook, bg=BG_PANEL_ALT)
        self.tab_terraform = tk.Frame(notebook, bg=BG_PANEL_ALT)

        notebook.add(self.tab_params, text="1 · Configuration")
        notebook.add(self.tab_script, text="2 · Script de déploiement (Bash)")
        notebook.add(self.tab_cleanup, text="3 · Script de nettoyage (Bash)")
        notebook.add(self.tab_terraform, text="4 · Infrastructure as Code (Terraform)")
        self.notebook = notebook

        self._build_params_tab()
        self._build_script_tab(self.tab_script, "deploy")
        self._build_script_tab(self.tab_cleanup, "cleanup")
        self._build_script_tab(self.tab_terraform, "terraform")

    # --------------------------------------------------------------- params tab
    def _build_params_tab(self):
        tab = self.tab_params
        tab.columnconfigure(0, weight=1)
        tab.columnconfigure(1, weight=1)

        cloud_card = tk.Frame(tab, bg=BG_PANEL_ALT, padx=20, pady=16)
        cloud_card.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(20, 10))
        tk.Label(
            cloud_card,
            text="INFRASTRUCTURE CLOUD CIBLE",
            bg=BG_PANEL_ALT,
            fg=FG_SUBTLE,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")

        self.cloud_buttons_frame = tk.Frame(cloud_card, bg=BG_PANEL_ALT)
        self.cloud_buttons_frame.pack(fill="x", pady=(10, 0))
        self.cloud_radio_widgets = {}
        for cloud in ("aws", "azure", "gcp"):
            rb = ttk.Radiobutton(
                self.cloud_buttons_frame,
                text=CLOUD_LABELS[cloud],
                value=cloud,
                variable=self.current_cloud,
                style="Cloud.TRadiobutton",
                command=self._on_cloud_change,
            )
            rb.pack(side="left", padx=(0, 10))
            self.cloud_radio_widgets[cloud] = rb

        self.params_container = tk.Frame(tab, bg=BG_PANEL_ALT, padx=20, pady=4)
        self.params_container.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=20)
        tab.rowconfigure(1, weight=1)

        action_row = tk.Frame(tab, bg=BG_PANEL_ALT, padx=20, pady=16)
        action_row.grid(row=2, column=0, columnspan=2, sticky="ew")
        self._accent_button(
            action_row, "⚙  Générer les artefacts", self.generate_artifacts
        ).pack(side="left")
        tk.Label(
            action_row,
            text="Les scripts et le code Terraform sont régénérés avec les en-têtes didactiques.",
            bg=BG_PANEL_ALT,
            fg=FG_SUBTLE,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=12)

    def _on_cloud_change(self):
        scenario = self.scenarios_by_id.get(self.current_scenario_id)
        if not scenario:
            return
        cloud = self.current_cloud.get()
        for p in scenario["parameters"]:
            cloud_defaults = p.get("cloud_defaults")
            if cloud_defaults and p["key"] in self.param_widgets:
                widget = self.param_widgets[p["key"]]
                current = widget.get()
                if current in ("", *cloud_defaults.values()):
                    widget.set(cloud_defaults.get(cloud, ""))
        self._refresh_cloud_buttons_enabled(scenario)

    def _refresh_cloud_buttons_enabled(self, scenario):
        supported = scenario.get("clouds", ["aws", "azure", "gcp"])
        for cloud, rb in self.cloud_radio_widgets.items():
            rb.configure(state="normal" if cloud in supported else "disabled")
        if self.current_cloud.get() not in supported and supported:
            self.current_cloud.set(supported[0])

    # --------------------------------------------------------------- script tab
    def _build_script_tab(self, tab: tk.Frame, kind: str):
        tab.rowconfigure(1, weight=1)
        tab.columnconfigure(0, weight=1)

        toolbar = tk.Frame(tab, bg=BG_PANEL_ALT, padx=16, pady=12)
        toolbar.grid(row=0, column=0, sticky="ew")

        labels = {
            "deploy": "Script de déploiement",
            "cleanup": "Script de nettoyage",
            "terraform": "Code Terraform / OpenTofu",
        }
        tk.Label(
            toolbar,
            text=labels[kind],
            bg=BG_PANEL_ALT,
            fg=FG_TEXT,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")

        self._accent_button(
            toolbar, "📋 Copier", lambda: self._copy_script(kind), primary=False
        ).pack(side="right", padx=(8, 0))

        if kind != "terraform":
            self._accent_button(
                toolbar, "📄 Rapport MD", self.generate_report, primary=False
            ).pack(side="right", padx=(8, 0))

        self._accent_button(
            toolbar, "💾 Enregistrer sous…", lambda: self._save_script(kind), primary=True
        ).pack(side="right")

        text_frame = tk.Frame(tab, bg=BG_PANEL_ALT)
        text_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        fg_color = (
            "#c9f3e8"
            if kind == "deploy"
            else ("#f3d7c9" if kind == "cleanup" else "#d4c9f3")
        )
        text_widget = tk.Text(
            text_frame,
            bg=BG_INPUT,
            fg=fg_color,
            insertbackground=ACCENT,
            relief="flat",
            font=("Consolas", 10),
            wrap="none",
            padx=14,
            pady=14,
            undo=False,
        )
        vsb = ttk.Scrollbar(
            text_frame, orient="vertical", command=text_widget.yview, style="Vertical.TScrollbar"
        )
        hsb = ttk.Scrollbar(
            text_frame, orient="horizontal", command=text_widget.xview, style="Vertical.TScrollbar"
        )
        text_widget.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        text_widget.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        if kind == "deploy":
            self.deploy_text = text_widget
        elif kind == "cleanup":
            self.cleanup_text = text_widget
        else:
            self.terraform_text = text_widget

    # ------------------------------------------------------------------ actions
    def _copy_script(self, kind: str):
        text_map = {
            "deploy": self.generated_deploy,
            "cleanup": self.generated_cleanup,
            "terraform": self.generated_terraform,
        }
        text = text_map.get(kind, "")
        if not text.strip():
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        toast = tk.Label(
            self,
            text="✓ Copié dans le presse-papiers !",
            bg=ACCENT,
            fg="#0b0e16",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=5,
        )
        toast.place(relx=0.5, rely=0.1, anchor="center")
        self.after(1500, toast.destroy)

    def _save_script(self, kind: str):
        text_map = {
            "deploy": self.generated_deploy,
            "cleanup": self.generated_cleanup,
            "terraform": self.generated_terraform,
        }
        text = text_map.get(kind, "")
        if not text.strip():
            messagebox.showinfo(
                "RTK Scenario Studio", "Rien à enregistrer — générez d'abord les artefacts."
            )
            return

        scenario = self.scenarios_by_id.get(self.current_scenario_id, {})
        cloud = self.current_cloud.get()
        ext = ".tf" if kind == "terraform" else ".sh"
        suffix = {"deploy": "deploy", "cleanup": "cleanup", "terraform": "terraform"}[kind]
        default_name = f"{scenario.get('id', 'scenario')}_{cloud}_{suffix}{ext}"

        path = filedialog.asksaveasfilename(
            initialfile=default_name,
            defaultextension=ext,
            filetypes=[("Fichiers texte", f"*{ext}"), ("Tous les fichiers", "*.*")],
        )
        if path:
            Path(path).write_text(text, encoding="utf-8")
            messagebox.showinfo("Succès", f"Artefact enregistré :\n{path}")

    def generate_report(self):
        scenario = self.scenarios_by_id.get(self.current_scenario_id)
        if not scenario:
            return

        cloud = self.current_cloud.get()
        values = {key: widget.get() for key, widget in self.param_widgets.items()}
        did = scenario.get("didactique", {})

        report_lines = [
            "# 🛡️ Rapport de Scénario de Test RTK",
            f"**Date de génération** : {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Scénario** : {scenario['name']} (`{scenario['id']}`)",
            f"**Module RTK** : `{scenario['rtk_module']}`",
            f"**Fournisseur Cloud** : {CLOUD_LABELS.get(cloud, cloud)}",
            f"**ID d'Engagement** : `{values.get('engagement_id', 'NON DÉFINI')}`",
            "---",
            "## 🎯 Objectif du Test",
            scenario["description"],
            "",
            "## 📚 Référentiels de Sécurité",
            f"- **OWASP** : {', '.join(did.get('owasp', ['Non spécifié']))}",
            f"- **MITRE ATT&CK** : {', '.join(did.get('mitre_attack', ['Non spécifié']))}",
            "",
            "## 💡 Analyse Pédagogique",
            "### Concept Cloud Manipulé",
            did.get("concept_cloud", "Non documenté"),
            "",
            "### Faille de Sécurité Exploitée",
            did.get("faille_securite", "Non documentée"),
            "",
            "---",
            "## ⚙️ Paramètres Utilisés",
            "| Paramètre | Valeur |",
            "|-----------|--------|",
        ]
        for key, val in values.items():
            report_lines.append(f"| `{key}` | `{val}` |")

        report_lines.extend(
            [
                "",
                "---",
                "## 📜 Artefacts Générés",
                "### Script de Déploiement",
                md_fenced_block(self.generated_deploy, "bash"),
                "",
                "### Script de Nettoyage",
                md_fenced_block(self.generated_cleanup, "bash"),
                "",
                "### Code Terraform / OpenTofu",
                md_fenced_block(self.generated_terraform, "hcl"),
                "",
                "---",
                "> ⚠️ **Avertissement Légal** : Ce document et les scripts associés "
                "sont strictement réservés à un cadre d'engagement autorisé.",
            ]
        )

        report = "\n".join(report_lines)
        default_name = (
            f"RAPPORT_{scenario['id']}_{cloud}_{values.get('engagement_id', 'LAB')}.md"
        )
        path = filedialog.asksaveasfilename(
            initialfile=default_name,
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Tous les fichiers", "*.*")],
        )
        if path:
            Path(path).write_text(report, encoding="utf-8")
            messagebox.showinfo("Succès", f"Rapport d'engagement généré :\n{path}")

    # ---------------------------------------------------------------- select
    def select_scenario(self, scenario_id: str):
        if self.current_scenario_id and self.current_scenario_id in self.cards:
            self.cards[self.current_scenario_id].set_selected(False)

        self.current_scenario_id = scenario_id
        if scenario_id in self.cards:
            self.cards[scenario_id].set_selected(True)

        scenario = self.scenarios_by_id[scenario_id]
        self.title_label.configure(text=scenario["name"])
        self.desc_label.configure(text=scenario["description"])

        for child in self.badges_frame.winfo_children():
            child.destroy()
        Badge(self.badges_frame, scenario["rtk_module"], ACCENT).pack(side="left", padx=(0, 8))
        Badge(self.badges_frame, scenario["category"], "#3a4568").pack(side="left", padx=(0, 8))
        Badge(
            self.badges_frame,
            f"Sévérité : {scenario['severity']}",
            severity_color(scenario["severity"]),
        ).pack(side="left")

        self._refresh_cloud_buttons_enabled(scenario)
        self._build_param_fields(scenario)

        self.generated_deploy = ""
        self.generated_cleanup = ""
        self.generated_terraform = ""
        self.deploy_text.delete("1.0", "end")
        self.cleanup_text.delete("1.0", "end")
        self.terraform_text.delete("1.0", "end")
        self.notebook.select(self.tab_params)

    def _build_param_fields(self, scenario: dict):
        for child in self.params_container.winfo_children():
            child.destroy()
        self.param_widgets.clear()

        tk.Label(
            self.params_container,
            text="PARAMÈTRES DU SCÉNARIO",
            bg=BG_PANEL_ALT,
            fg=FG_SUBTLE,
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(6, 10))

        cloud = self.current_cloud.get()
        row, col = 1, 0
        for p in scenario["parameters"]:
            default = p.get("default", "")
            cloud_defaults = p.get("cloud_defaults")
            if cloud_defaults:
                default = cloud_defaults.get(cloud, default)

            field = LabeledEntry(self.params_container, p["label"], default)
            field.grid(
                row=row,
                column=col,
                sticky="ew",
                padx=(0, 16) if col == 0 else 0,
                pady=8,
            )
            self.params_container.columnconfigure(col, weight=1)
            self.param_widgets[p["key"]] = field

            col += 1
            if col > 1:
                col = 0
                row += 1

    # ---------------------------------------------------------------- generate
    def _validate_and_collect_values(self, cloud: str) -> dict[str, str] | None:
        """
        🔧 CORRECTIFS N°3 + N°4 : applique la bonne fonction de sanitization
        selon le type de clé, puis valide la région.

        Renvoie None en cas d'erreur (une messagebox a été affichée).
        """
        try:
            values: dict[str, str] = {}
            for key, widget in self.param_widgets.items():
                raw_val = widget.get()

                if key in self.SHELL_SAFE_KEYS:
                    # Mot de passe / clé factice : tout sauf retour à la ligne
                    values[key] = sanitize_shell_safe(raw_val)

                elif key in self.IMAGE_KEYS:
                    # Référence d'image conteneur
                    values[key] = sanitize_container_image(raw_val)

                elif key in self.RESOURCE_NAME_KEYS:
                    # Identifiant de ressource (strict, majuscules autorisées)
                    values[key] = sanitize_resource_name(raw_val)

                else:
                    # Autres champs (region, sensitive_layer_name, etc.)
                    values[key] = sanitize_generic(raw_val)

            # 🔧 CORRECTIF N°3 : validation de la région
            if "region" in values and values["region"]:
                values["region"] = validate_region(cloud, values["region"])

        except ValueError as e:
            messagebox.showerror(
                "Erreur de validation",
                f"Paramètre invalide : {e}\nVeuillez corriger le champ concerné.",
            )
            return None

        return values

    def generate_artifacts(self):
        scenario = self.scenarios_by_id.get(self.current_scenario_id)
        if not scenario:
            return

        cloud = self.current_cloud.get()
        if cloud not in scenario.get("clouds", []):
            messagebox.showwarning(
                "RTK Scenario Studio",
                f"Ce scénario ne propose pas d'artefacts pour {CLOUD_LABELS.get(cloud, cloud)}.",
            )
            return

        values = self._validate_and_collect_values(cloud)
        if values is None:
            return

        # Avertissement sur les champs vides
        missing = [k for k, v in values.items() if not v.strip()]
        if missing and not messagebox.askyesno(
            "Paramètres vides",
            f"Certains paramètres sont vides : {', '.join(missing)}.\nGénérer quand même ?",
        ):
            return

        header = build_didactic_header(scenario, cloud, values)
        deploy_tpl = scenario["scripts"].get(cloud, "")
        cleanup_tpl = scenario["cleanup"].get(cloud, "")
        terraform_tpl = scenario.get("terraform", {}).get(
            cloud, "# 🎓 Code Terraform non disponible pour ce cloud dans ce scénario."
        )

        # 🔧 CORRECTIF N°1 : le shebang vient du template (scenarios.json),
        # plus du header. On retire le shebang résiduel du header s'il existe,
        # et on concatène proprement.
        header_clean = header
        if header_clean.startswith("#!/usr/bin/env bash\n"):
            header_clean = header_clean[len("#!/usr/bin/env bash\n"):]

        deploy_body = render_template(deploy_tpl, values)
        # Si le template ne commence pas par un shebang, on en ajoute un
        if not deploy_body.lstrip().startswith("#!"):
            deploy_body = "#!/usr/bin/env bash\n" + deploy_body

        self.generated_deploy = header_clean + "\n" + deploy_body

        self.generated_cleanup = (
            "#!/usr/bin/env bash\n"
            "# 🧹 Script de nettoyage associé au scénario ci-dessus.\n"
            "# Il est impératif de l'exécuter pour éviter des coûts résiduels "
            "et des failles persistantes.\n"
            + render_template(cleanup_tpl, values)
        )
        self.generated_terraform = render_template(terraform_tpl, values)

        self.deploy_text.delete("1.0", "end")
        self.deploy_text.insert("1.0", self.generated_deploy)
        self.cleanup_text.delete("1.0", "end")
        self.cleanup_text.insert("1.0", self.generated_cleanup)
        self.terraform_text.delete("1.0", "end")
        self.terraform_text.insert("1.0", self.generated_terraform)

        self.notebook.select(self.tab_script)


# ==============================================================================
# 6. POINT D'ENTRÉE
# ==============================================================================
def main():
    app = RTKScenarioStudio()
    app.mainloop()


if __name__ == "__main__":
    main()