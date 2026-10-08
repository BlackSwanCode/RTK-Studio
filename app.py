#!/usr/bin/env python3
"""
RTK Scenario Studio
====================

Interface graphique pour générer des scripts de provisionnement cloud
(AWS CloudShell / Azure Cloud Shell / Google Cloud Shell) à partir d'une
bibliothèque de scénarios de test de sécurité (red team / DevSecOps),
destinés à des environnements de lab sandbox dédiés et explicitement
autorisés (voir scope.yaml du framework RTK).

Les scénarios sont décrits dans templates/scenarios.json. Chaque scénario
propose un script de déploiement et un script de nettoyage pour AWS, Azure
et GCP, paramétrables par l'utilisateur (noms de buckets, de services, de
conteneurs, régions, identifiant d'engagement...).

⚠️  Les scripts générés déploient volontairement des ressources mal
configurées. Ils ne doivent être exécutés que dans un projet / compte /
abonnement cloud sandbox dédié, dans le cadre d'un engagement de test
autorisé, avec nettoyage systématique après usage.

Lancement :
    python3 app.py

Aucune dépendance externe : uniquement la bibliothèque standard
(tkinter, json, pathlib).
"""

from __future__ import annotations

import json
import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_DIR = Path(__file__).resolve().parent
TEMPLATES_PATH = APP_DIR / "templates" / "scenarios.json"

# ---------------------------------------------------------------------------
# Palette & style
# ---------------------------------------------------------------------------

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
CLOUD_BADGE_COLOR = {"aws": "#f0a35e", "azure": "#5ab4f0", "gcp": "#8ad15a"}
SEVERITY_COLOR = {
    "critical": CRIT,
    "high": "#e8905a",
    "high / critical": "#e8905a",
    "medium": "#e0c158",
    "info/high": "#e0c158",
    "low": FG_MUTED,
}


def severity_color(sev: str) -> str:
    return SEVERITY_COLOR.get(sev.lower().strip(), FG_MUTED)


# ---------------------------------------------------------------------------
# Chargement de la bibliothèque de scénarios
# ---------------------------------------------------------------------------


def load_scenarios() -> list[dict]:
    if not TEMPLATES_PATH.exists():
        raise FileNotFoundError(
            f"Bibliothèque de scénarios introuvable : {TEMPLATES_PATH}"
        )
    with open(TEMPLATES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("scenarios", [])


PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")


def render_template(text: str, values: dict[str, str]) -> str:
    def repl(m: re.Match) -> str:
        key = m.group(1)
        return str(values.get(key, m.group(0)))

    return PLACEHOLDER_RE.sub(repl, text)


# ---------------------------------------------------------------------------
# Widgets utilitaires
# ---------------------------------------------------------------------------


class Badge(tk.Frame):
    """Petite étiquette colorée (ex : AWS, severity=high)."""

    def __init__(self, parent, text, color, **kw):
        super().__init__(parent, bg=color, **kw)
        lbl = tk.Label(
            self,
            text=text,
            bg=color,
            fg="#0b0e16",
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=2,
        )
        lbl.pack()


class ScenarioCard(tk.Frame):
    """Carte cliquable représentant un scénario dans la liste de gauche."""

    def __init__(self, parent, scenario: dict, on_select):
        super().__init__(parent, bg=BG_CARD, cursor="hand2", padx=12, pady=10)
        self.scenario = scenario
        self.on_select = on_select
        self.selected = False

        name = tk.Label(
            self,
            text=scenario["name"],
            bg=BG_CARD,
            fg=FG_TEXT,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
            justify="left",
            wraplength=250,
        )
        name.pack(fill="x")

        meta = tk.Label(
            self,
            text=f"{scenario['rtk_module']}",
            bg=BG_CARD,
            fg=ACCENT,
            font=("Consolas", 9),
            anchor="w",
        )
        meta.pack(fill="x", pady=(2, 6))

        bottom = tk.Frame(self, bg=BG_CARD)
        bottom.pack(fill="x")
        cat = tk.Label(
            bottom,
            text=scenario["category"],
            bg=BG_CARD,
            fg=FG_MUTED,
            font=("Segoe UI", 8),
        )
        cat.pack(side="left")
        sev = tk.Label(
            bottom,
            text=scenario["severity"],
            bg=BG_CARD,
            fg=severity_color(scenario["severity"]),
            font=("Segoe UI", 8, "bold"),
        )
        sev.pack(side="right")

        for w in (self, name, meta, bottom, cat, sev):
            w.bind("<Button-1>", self._click)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self._children_bg = [self, name, meta, bottom, cat, sev]

    def _click(self, _evt=None):
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
            w.configure(bg=color)


class LabeledEntry(tk.Frame):
    """Champ de paramètre : label + entry stylés."""

    def __init__(self, parent, label: str, default: str = ""):
        super().__init__(parent, bg=BG_PANEL_ALT)
        lbl = tk.Label(
            self,
            text=label,
            bg=BG_PANEL_ALT,
            fg=FG_MUTED,
            font=("Segoe UI", 9),
            anchor="w",
        )
        lbl.pack(fill="x", pady=(0, 3))

        self.var = tk.StringVar(value=default)
        entry = tk.Entry(
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
        entry.pack(fill="x", ipady=6)

    def get(self) -> str:
        return self.var.get()

    def set(self, value: str):
        self.var.set(value)


# ---------------------------------------------------------------------------
# Application principale
# ---------------------------------------------------------------------------


class RTKScenarioStudio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RTK Scenario Studio — Générateur multi-cloud de scénarios de test")
        self.geometry("1280x800")
        self.minsize(1040, 640)
        self.configure(bg=BG_ROOT)

        try:
            self.scenarios = load_scenarios()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Erreur de chargement", str(exc))
            self.scenarios = []

        self.scenarios_by_id = {s["id"]: s for s in self.scenarios}
        self.current_scenario_id: str | None = None
        self.current_cloud = tk.StringVar(value="gcp")
        self.param_widgets: dict[str, LabeledEntry] = {}
        self.cards: dict[str, ScenarioCard] = {}
        self.generated_deploy = ""
        self.generated_cleanup = ""

        self._build_style()
        self._build_layout()

        if self.scenarios:
            self.select_scenario(self.scenarios[0]["id"])

    # -- style ---------------------------------------------------------

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

        style.configure(
            "Dark.TNotebook",
            background=BG_PANEL,
            borderwidth=0,
        )
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
        btn = tk.Button(
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
        return btn

    # -- layout ----------------------------------------------------------

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
            text="  bibliothèque de scénarios de test  →  provisioning AWS / Azure / GCP",
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
                "sandbox dédiés. Déployez uniquement dans le périmètre d'un scope.yaml signé, "
                "nettoyez systématiquement après usage."
            ),
            bg="#2e2412",
            fg=WARN,
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill="x")

        body = tk.Frame(self, bg=BG_ROOT)
        body.pack(fill="both", expand=True, padx=20, pady=16)
        body.columnconfigure(0, weight=0, minsize=300)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_sidebar(body)
        self._build_main(body)

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
        )
        search_entry.insert(0, "")
        search_entry.pack(fill="x", ipady=6)
        search_entry.configure(
            highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT
        )
        self._search_placeholder(search_entry)

        canvas = tk.Canvas(sidebar, bg=BG_PANEL, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            sidebar, orient="vertical", command=canvas.yview, style="Vertical.TScrollbar"
        )
        self.cards_frame = tk.Frame(canvas, bg=BG_PANEL)
        self.cards_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.cards_frame, anchor="nw", width=272)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(14, 0))
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

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

    def _build_main(self, parent):
        main = tk.Frame(parent, bg=BG_PANEL)
        main.grid(row=0, column=1, sticky="nsew")
        main.rowconfigure(1, weight=1)
        main.columnconfigure(0, weight=1)

        # -- scenario header --
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

        # -- notebook --
        notebook = ttk.Notebook(main, style="Dark.TNotebook")
        notebook.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))

        self.tab_params = tk.Frame(notebook, bg=BG_PANEL_ALT)
        self.tab_script = tk.Frame(notebook, bg=BG_PANEL_ALT)
        self.tab_cleanup = tk.Frame(notebook, bg=BG_PANEL_ALT)
        notebook.add(self.tab_params, text="1 · Configuration")
        notebook.add(self.tab_script, text="2 · Script de déploiement")
        notebook.add(self.tab_cleanup, text="3 · Script de nettoyage")
        self.notebook = notebook

        self._build_params_tab()
        self._build_script_tab(self.tab_script, "deploy")
        self._build_script_tab(self.tab_cleanup, "cleanup")

    # -- tab: paramètres --------------------------------------------------

    def _build_params_tab(self):
        tab = self.tab_params
        tab.columnconfigure(0, weight=1)
        tab.columnconfigure(1, weight=1)

        # Cloud selector
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

        # Params grid
        self.params_container = tk.Frame(tab, bg=BG_PANEL_ALT, padx=20, pady=4)
        self.params_container.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=20)
        tab.rowconfigure(1, weight=1)

        # Generate button
        action_row = tk.Frame(tab, bg=BG_PANEL_ALT, padx=20, pady=16)
        action_row.grid(row=2, column=0, columnspan=2, sticky="ew")
        self._accent_button(
            action_row, "⚙  Générer le script", self.generate_script
        ).pack(side="left")
        tk.Label(
            action_row,
            text="Le script de déploiement et le script de nettoyage sont régénérés.",
            bg=BG_PANEL_ALT,
            fg=FG_SUBTLE,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=12)

    def _on_cloud_change(self):
        """Quand le cloud change, met à jour les valeurs par défaut dépendantes du cloud."""
        scenario = self.scenarios_by_id.get(self.current_scenario_id)
        if not scenario:
            return
        cloud = self.current_cloud.get()
        for p in scenario["parameters"]:
            cloud_defaults = p.get("cloud_defaults")
            if cloud_defaults and p["key"] in self.param_widgets:
                widget = self.param_widgets[p["key"]]
                current = widget.get()
                # ne remplace que si le champ est vide ou contient encore une ancienne valeur par défaut
                if current in ("", *cloud_defaults.values()):
                    widget.set(cloud_defaults.get(cloud, ""))
        self._refresh_cloud_buttons_enabled(scenario)

    def _refresh_cloud_buttons_enabled(self, scenario):
        supported = scenario.get("clouds", ["aws", "azure", "gcp"])
        for cloud, rb in self.cloud_radio_widgets.items():
            state = "normal" if cloud in supported else "disabled"
            rb.configure(state=state)
        if self.current_cloud.get() not in supported and supported:
            self.current_cloud.set(supported[0])

    # -- tab: script (déploiement / nettoyage) -----------------------------

    def _build_script_tab(self, tab: tk.Frame, kind: str):
        tab.rowconfigure(1, weight=1)
        tab.columnconfigure(0, weight=1)

        toolbar = tk.Frame(tab, bg=BG_PANEL_ALT, padx=16, pady=12)
        toolbar.grid(row=0, column=0, sticky="ew")

        label = "Script de déploiement" if kind == "deploy" else "Script de nettoyage"
        tk.Label(
            toolbar,
            text=label,
            bg=BG_PANEL_ALT,
            fg=FG_TEXT,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")

        btn_copy = self._accent_button(
            toolbar, "📋 Copier", lambda: self._copy_script(kind), primary=False
        )
        btn_copy.pack(side="right", padx=(8, 0))
        btn_save = self._accent_button(
            toolbar, "💾 Enregistrer sous…", lambda: self._save_script(kind), primary=True
        )
        btn_save.pack(side="right")

        text_frame = tk.Frame(tab, bg=BG_PANEL_ALT)
        text_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        text_widget = tk.Text(
            text_frame,
            bg=BG_INPUT,
            fg="#c9f3e8" if kind == "deploy" else "#f3d7c9",
            insertbackground=ACCENT,
            relief="flat",
            font=("Consolas", 10),
            wrap="none",
            padx=14,
            pady=14,
            undo=False,
        )
        vsb = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview, style="Vertical.TScrollbar")
        hsb = ttk.Scrollbar(text_frame, orient="horizontal", command=text_widget.xview, style="Vertical.TScrollbar")
        text_widget.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        text_widget.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        if kind == "deploy":
            self.deploy_text = text_widget
        else:
            self.cleanup_text = text_widget

    def _copy_script(self, kind: str):
        text = self.generated_deploy if kind == "deploy" else self.generated_cleanup
        if not text.strip():
            messagebox.showinfo("RTK Scenario Studio", "Rien à copier — générez d'abord le script.")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("RTK Scenario Studio", "Script copié dans le presse-papiers.")

    def _save_script(self, kind: str):
        text = self.generated_deploy if kind == "deploy" else self.generated_cleanup
        if not text.strip():
            messagebox.showinfo("RTK Scenario Studio", "Rien à enregistrer — générez d'abord le script.")
            return
        scenario = self.scenarios_by_id.get(self.current_scenario_id, {})
        cloud = self.current_cloud.get()
        suffix = "deploy" if kind == "deploy" else "cleanup"
        default_name = f"{scenario.get('id', 'scenario')}_{cloud}_{suffix}.sh"
        path = filedialog.asksaveasfilename(
            initialfile=default_name,
            defaultextension=".sh",
            filetypes=[("Script shell", "*.sh"), ("Tous les fichiers", "*.*")],
        )
        if not path:
            return
        Path(path).write_text(text, encoding="utf-8")
        messagebox.showinfo("RTK Scenario Studio", f"Script enregistré :\n{path}")

    # -- sélection / génération --------------------------------------------

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
            self.badges_frame, f"Sévérité : {scenario['severity']}", severity_color(scenario["severity"])
        ).pack(side="left")

        self._refresh_cloud_buttons_enabled(scenario)
        self._build_param_fields(scenario)
        self.generated_deploy = ""
        self.generated_cleanup = ""
        self.deploy_text.delete("1.0", "end")
        self.cleanup_text.delete("1.0", "end")
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
        row = 1
        col = 0
        for p in scenario["parameters"]:
            default = p.get("default", "")
            cloud_defaults = p.get("cloud_defaults")
            if cloud_defaults:
                default = cloud_defaults.get(cloud, default)
            field = LabeledEntry(self.params_container, p["label"], default)
            field.grid(row=row, column=col, sticky="ew", padx=(0, 16) if col == 0 else 0, pady=8)
            self.params_container.columnconfigure(col, weight=1)
            self.param_widgets[p["key"]] = field
            col += 1
            if col > 1:
                col = 0
                row += 1

    def generate_script(self):
        scenario = self.scenarios_by_id.get(self.current_scenario_id)
        if not scenario:
            return
        cloud = self.current_cloud.get()
        if cloud not in scenario.get("clouds", []):
            messagebox.showwarning(
                "RTK Scenario Studio",
                f"Ce scénario ne propose pas de script pour {CLOUD_LABELS.get(cloud, cloud)}.",
            )
            return

        values = {key: widget.get() for key, widget in self.param_widgets.items()}
        missing = [k for k, v in values.items() if not v.strip()]
        if missing:
            if not messagebox.askyesno(
                "RTK Scenario Studio",
                "Certains paramètres sont vides : " + ", ".join(missing) + ".\nGénérer quand même ?",
            ):
                return

        deploy_tpl = scenario["scripts"].get(cloud, "")
        cleanup_tpl = scenario["cleanup"].get(cloud, "")
        self.generated_deploy = render_template(deploy_tpl, values)
        self.generated_cleanup = render_template(cleanup_tpl, values)

        self.deploy_text.delete("1.0", "end")
        self.deploy_text.insert("1.0", self.generated_deploy)
        self.cleanup_text.delete("1.0", "end")
        self.cleanup_text.insert("1.0", self.generated_cleanup)

        self.notebook.select(self.tab_script)


def main():
    app = RTKScenarioStudio()
    app.mainloop()


if __name__ == "__main__":
    main()
