#!/usr/bin/env python3
"""Buffer Logger - Lab buffer management and calculation tool."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import copy

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "buffers.json")

CONC_UNITS = ["M", "mM", "µM", "nM", "pM", "%", "mg/mL", "µg/mL"]
VOL_UNITS = ["L", "mL", "µL"]

CONC_TO_BASE = {
    "M": ("molar", 1), "mM": ("molar", 1e-3), "µM": ("molar", 1e-6),
    "uM": ("molar", 1e-6), "nM": ("molar", 1e-9), "pM": ("molar", 1e-12),
    "%": ("percent", 1),
    "mg/mL": ("mass", 1), "µg/mL": ("mass", 1e-3), "ug/mL": ("mass", 1e-3),
}
VOL_TO_UL = {"L": 1e6, "mL": 1e3, "µL": 1, "uL": 1}

TIER_COLORS = {
    "stock":    {"bg": "#1565C0", "fg": "white", "light": "#E3F2FD", "mid": "#90CAF9"},
    "simple":   {"bg": "#2E7D32", "fg": "white", "light": "#E8F5E9", "mid": "#A5D6A7"},
    "compound": {"bg": "#E65100", "fg": "white", "light": "#FFF3E0", "mid": "#FFCC80"},
}
TIER_LABELS = {"stock": "Stock Solutions", "simple": "Simple Buffers", "compound": "Compound Buffers"}


def to_base_conc(value, unit):
    cat, factor = CONC_TO_BASE.get(unit, ("molar", 1))
    return value * factor, cat


def from_base_conc(value, category):
    if category == "percent":
        return value, "%"
    if category == "mass":
        return (value, "mg/mL") if value >= 1 else (value * 1e3, "µg/mL")
    for thresh, unit in [(1, "M"), (1e-3, "mM"), (1e-6, "µM"), (1e-9, "nM")]:
        if value >= thresh * 0.99:
            return value / thresh, unit
    return value / 1e-12, "pM"


def to_ul(value, unit):
    return value * VOL_TO_UL.get(unit, 1)


def smart_vol(ul, ref_unit="µL"):
    if ul >= 1e6:
        return ul / 1e6, "L"
    if ul >= 1e3:
        return ul / 1e3, "mL"
    return ul, "µL"


def fmt(val):
    if val == 0:
        return "0"
    if abs(val) >= 100:
        return f"{val:.1f}"
    if abs(val) >= 1:
        return f"{val:.2f}"
    return f"{val:.4g}"


# ── Default buffers ─────────────────────────────────────────────────────────

DEFAULT_BUFFERS = {
    # ── Pure stock solutions ────────────────────────────────────────────
    "BSA 10%": {
        "type": "stock", "pH": None,
        "components": [{"name": "BSA", "concentration": 10, "unit": "%"}],
    },
    "MC 10%": {
        "type": "stock", "pH": None,
        "components": [{"name": "Methylcellulose", "concentration": 10, "unit": "%"}],
    },
    "GTP 0.1M": {
        "type": "stock", "pH": None,
        "components": [{"name": "GTP", "concentration": 100, "unit": "mM"}],
    },
    "DTT 0.9M": {
        "type": "stock", "pH": None,
        "components": [{"name": "DTT", "concentration": 900, "unit": "mM"}],
    },
    "GMPCPP 0.5mM": {
        "type": "stock", "pH": None,
        "components": [{"name": "GMPCPP", "concentration": 0.5, "unit": "mM"}],
    },
    "Neutravidin 1mg/mL": {
        "type": "stock", "pH": None,
        "components": [{"name": "Neutravidin", "concentration": 1, "unit": "mg/mL"}],
    },
    "Glucose 150mg/mL": {
        "type": "stock", "pH": None,
        "components": [{"name": "Glucose", "concentration": 150, "unit": "mg/mL"}],
    },
    "Glucose Oxidase 5mg/mL": {
        "type": "stock", "pH": None,
        "components": [{"name": "Glucose Oxidase", "concentration": 5, "unit": "mg/mL"}],
    },
    "Catalase 1mg/mL": {
        "type": "stock", "pH": None,
        "components": [{"name": "Catalase", "concentration": 1, "unit": "mg/mL"}],
    },
    "Tubulin black 220\u00b5M": {
        "type": "stock", "pH": None,
        "components": [{"name": "Tubulin (unlabelled)", "concentration": 220, "unit": "\u00b5M"}],
    },
    "Tubulin 488/565 143\u00b5M": {
        "type": "stock", "pH": None,
        "components": [{"name": "Tubulin (488/565)", "concentration": 143, "unit": "\u00b5M"}],
    },
    "MAP 20.5\u00b5M": {
        "type": "stock", "pH": None,
        "components": [{"name": "MAP", "concentration": 20.5, "unit": "\u00b5M"}],
    },
    # ── Concentrated buffers ────────────────────────────────────────────
    "20x BRB": {
        "type": "stock", "pH": 6.8,
        "components": [
            {"name": "PIPES", "concentration": 1.6, "unit": "M"},
            {"name": "EGTA", "concentration": 20, "unit": "mM"},
            {"name": "MgCl\u2082", "concentration": 20, "unit": "mM"},
        ],
    },
    "10x MAP Buffer": {
        "type": "stock", "pH": 7.7,
        "components": [
            {"name": "KCl", "concentration": 1000, "unit": "mM"},
            {"name": "Phosphate buffer", "concentration": 500, "unit": "mM"},
            {"name": "DTT", "concentration": 10, "unit": "mM"},
        ],
    },
    "15x HKEM": {
        "type": "stock", "pH": 7.4,
        "components": [
            {"name": "HEPES", "concentration": 150, "unit": "mM"},
            {"name": "KCl", "concentration": 750, "unit": "mM"},
            {"name": "MgCl\u2082", "concentration": 750, "unit": "mM"},
            {"name": "EDTA", "concentration": 15, "unit": "mM"},
        ],
    },
    # ── Simple buffers (working buffers) ─────────────────────────────────
    "1x BRB": {
        "type": "simple", "pH": 6.8,
        "components": [
            {"name": "PIPES", "concentration": 80, "unit": "mM"},
            {"name": "EGTA", "concentration": 1, "unit": "mM"},
            {"name": "MgCl\u2082", "concentration": 1, "unit": "mM"},
        ],
    },
    "BRB/BSA": {
        "type": "simple", "pH": None,
        "components": [
            {"name": "PIPES", "concentration": 80, "unit": "mM"},
            {"name": "EGTA", "concentration": 1, "unit": "mM"},
            {"name": "MgCl\u2082", "concentration": 1, "unit": "mM"},
            {"name": "BSA", "concentration": 1, "unit": "%"},
        ],
    },
    "BRB/MAP": {
        "type": "simple", "pH": None,
        "components": [
            {"name": "PIPES", "concentration": 80, "unit": "mM"},
            {"name": "EGTA", "concentration": 1, "unit": "mM"},
            {"name": "MgCl\u2082", "concentration": 1, "unit": "mM"},
            {"name": "KCl", "concentration": 50, "unit": "mM"},
            {"name": "Phosphate buffer", "concentration": 25, "unit": "mM"},
            {"name": "DTT", "concentration": 0.5, "unit": "mM"},
        ],
    },
    "BRB/MC": {
        "type": "simple", "pH": None,
        "components": [
            {"name": "PIPES", "concentration": 80, "unit": "mM"},
            {"name": "EGTA", "concentration": 1, "unit": "mM"},
            {"name": "MgCl\u2082", "concentration": 1, "unit": "mM"},
            {"name": "Methylcellulose", "concentration": 1, "unit": "%"},
            {"name": "KCl", "concentration": 50, "unit": "mM"},
            {"name": "Phosphate buffer", "concentration": 25, "unit": "mM"},
            {"name": "DTT", "concentration": 0.5, "unit": "mM"},
        ],
    },
    "Neutravidin 50\u00b5g/mL": {
        "type": "simple", "pH": None,
        "components": [
            {"name": "PIPES", "concentration": 76, "unit": "mM"},
            {"name": "EGTA", "concentration": 0.95, "unit": "mM"},
            {"name": "MgCl\u2082", "concentration": 0.95, "unit": "mM"},
            {"name": "Neutravidin", "concentration": 50, "unit": "\u00b5g/mL"},
        ],
    },
    "Antifading": {
        "type": "simple", "pH": None,
        "components": [
            {"name": "KCl", "concentration": 300, "unit": "mM"},
            {"name": "Phosphate buffer", "concentration": 150, "unit": "mM"},
            {"name": "DTT", "concentration": 201, "unit": "mM"},
            {"name": "Glucose", "concentration": 12, "unit": "mg/mL"},
            {"name": "Glucose Oxidase", "concentration": 0.4, "unit": "mg/mL"},
            {"name": "Catalase", "concentration": 0.08, "unit": "mg/mL"},
        ],
    },
    "GTP 10mM": {
        "type": "simple", "pH": None,
        "components": [{"name": "GTP", "concentration": 10, "unit": "mM"}],
    },
    # ── Compound buffers (assay mixes) ──────────────────────────────────
    "Polymerization mix": {
        "type": "compound", "pH": None,
        "total_volume": 60, "total_volume_unit": "\u00b5L",
        "sources": [
            {"buffer": "BRB/BSA", "volume": 29.2, "volume_unit": "\u00b5L"},
            {"buffer": "BRB/MC", "volume": 10, "volume_unit": "\u00b5L"},
            {"buffer": "Antifading", "volume": 6, "volume_unit": "\u00b5L"},
            {"buffer": "BSA 10%", "volume": 6, "volume_unit": "\u00b5L"},
            {"buffer": "GTP 10mM", "volume": 6, "volume_unit": "\u00b5L"},
            {"buffer": "Tubulin black 220\u00b5M", "volume": 2.59, "volume_unit": "\u00b5L"},
            {"buffer": "Tubulin 488/565 143\u00b5M", "volume": 0.21, "volume_unit": "\u00b5L"},
        ],
    },
    "Capping mix": {
        "type": "compound", "pH": None,
        "total_volume": 60, "total_volume_unit": "\u00b5L",
        "sources": [
            {"buffer": "BRB/BSA", "volume": 33.74, "volume_unit": "\u00b5L"},
            {"buffer": "BRB/MC", "volume": 10, "volume_unit": "\u00b5L"},
            {"buffer": "Antifading", "volume": 6, "volume_unit": "\u00b5L"},
            {"buffer": "BSA 10%", "volume": 6, "volume_unit": "\u00b5L"},
            {"buffer": "GMPCPP 0.5mM", "volume": 3, "volume_unit": "\u00b5L"},
            {"buffer": "Tubulin 488/565 143\u00b5M", "volume": 1.26, "volume_unit": "\u00b5L"},
        ],
    },
    "Incorporation mix": {
        "type": "compound", "pH": None,
        "total_volume": 60, "total_volume_unit": "\u00b5L",
        "sources": [
            {"buffer": "BRB/BSA", "volume": 28.35, "volume_unit": "\u00b5L"},
            {"buffer": "BRB/MC", "volume": 10, "volume_unit": "\u00b5L"},
            {"buffer": "Antifading", "volume": 6, "volume_unit": "\u00b5L"},
            {"buffer": "BSA 10%", "volume": 6, "volume_unit": "\u00b5L"},
            {"buffer": "GTP 10mM", "volume": 6, "volume_unit": "\u00b5L"},
            {"buffer": "MAP 20.5\u00b5M", "volume": 0.29, "volume_unit": "\u00b5L"},
            {"buffer": "Tubulin 488/565 143\u00b5M", "volume": 3.36, "volume_unit": "\u00b5L"},
        ],
    },
    "Wash Buffer": {
        "type": "compound", "pH": None,
        "total_volume": 100, "total_volume_unit": "\u00b5L",
        "sources": [
            {"buffer": "BRB/BSA", "volume": 51.97, "volume_unit": "\u00b5L"},
            {"buffer": "BRB/MC", "volume": 16.67, "volume_unit": "\u00b5L"},
            {"buffer": "Antifading", "volume": 10, "volume_unit": "\u00b5L"},
            {"buffer": "BSA 10%", "volume": 10, "volume_unit": "\u00b5L"},
            {"buffer": "GTP 10mM", "volume": 10, "volume_unit": "\u00b5L"},
            {"buffer": "Tubulin black 220\u00b5M", "volume": 1.36, "volume_unit": "\u00b5L"},
        ],
    },
}


# ── Data layer ──────────────────────────────────────────────────────────────


class BufferManager:
    def __init__(self):
        self.buffers = {}
        self.categories = {"stock": [], "simple": [], "compound": []}
        self.load()

    def load(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if "buffers" in raw and "categories" in raw:
                self.buffers = raw["buffers"]
                self.categories = raw["categories"]
            else:
                # legacy format: flat dict of buffers
                self.buffers = raw
                self.categories = {"stock": [], "simple": [], "compound": []}
            for buf in self.buffers.values():
                if buf["type"] == "composite":
                    if "sources" in buf:
                        buf["type"] = "compound"
                    else:
                        buf["type"] = "stock"
        else:
            self.buffers = copy.deepcopy(DEFAULT_BUFFERS)
            self.categories = {"stock": [], "simple": [], "compound": []}
        self.save()

    def save(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"buffers": self.buffers, "categories": self.categories},
                      f, indent=2, ensure_ascii=False)

    def names(self, tier=None):
        if tier:
            return sorted(k for k, v in self.buffers.items() if v["type"] == tier)
        return sorted(self.buffers.keys())

    def names_grouped(self, tier):
        """Return list of (category, [buffer_names]) tuples, sorted."""
        all_names = self.names(tier)
        cats = self.categories.get(tier, [])
        groups = []
        for cat in cats:
            members = sorted(n for n in all_names
                             if self.buffers[n].get("category") == cat)
            groups.append((cat, members))
        # uncategorized
        categorized = {n for n in all_names if self.buffers[n].get("category")}
        uncategorized = sorted(n for n in all_names if n not in categorized)
        if uncategorized:
            groups.insert(0, (None, uncategorized))
        return groups

    def add_category(self, tier, name):
        cats = self.categories.setdefault(tier, [])
        if name not in cats:
            cats.append(name)
            self.save()

    def remove_category(self, tier, name):
        cats = self.categories.get(tier, [])
        if name in cats:
            cats.remove(name)
            # unset category on affected buffers
            for buf in self.buffers.values():
                if buf.get("category") == name and buf["type"] == tier:
                    buf.pop("category", None)
            self.save()

    def rename_category(self, tier, old, new):
        cats = self.categories.get(tier, [])
        if old in cats:
            cats[cats.index(old)] = new
            for buf in self.buffers.values():
                if buf.get("category") == old and buf["type"] == tier:
                    buf["category"] = new
            self.save()

    def get(self, name):
        return self.buffers.get(name)

    def add(self, name, data):
        self.buffers[name] = data
        self.save()

    def rename(self, old, new):
        if old == new or old not in self.buffers:
            return
        self.buffers[new] = self.buffers.pop(old)
        for buf in self.buffers.values():
            if buf["type"] == "compound":
                for src in buf.get("sources", []):
                    if src["buffer"] == old:
                        src["buffer"] = new
        self.save()

    def delete(self, name):
        deps = [
            k for k, v in self.buffers.items()
            if v["type"] == "compound"
            and any(s["buffer"] == name for s in v.get("sources", []))
        ]
        if deps:
            return False, deps
        self.buffers.pop(name, None)
        self.save()
        return True, []

    def final_conc(self, name, _visited=None):
        if _visited is None:
            _visited = set()
        if name in _visited:
            return []
        _visited.add(name)
        buf = self.buffers.get(name)
        if not buf:
            return []
        if buf["type"] in ("stock", "simple"):
            return [dict(c) for c in buf.get("components", [])]

        total_ul = to_ul(buf.get("total_volume", 0), buf.get("total_volume_unit", "mL"))
        if total_ul <= 0:
            return []

        ingredients = {}
        for src in buf.get("sources", []):
            dilution = to_ul(src["volume"], src["volume_unit"]) / total_ul
            for comp in self.final_conc(src["buffer"], _visited.copy()):
                bv, cat = to_base_conc(comp["concentration"], comp["unit"])
                key = comp["name"]
                if key in ingredients:
                    ingredients[key]["value"] += bv * dilution
                else:
                    ingredients[key] = {"value": bv * dilution, "category": cat}

        return [
            {"name": n,
             "concentration": from_base_conc(d["value"], d["category"])[0],
             "unit": from_base_conc(d["value"], d["category"])[1]}
            for n, d in ingredients.items()
        ]

    def calc_volumes(self, name, target_vol, target_unit):
        buf = self.buffers.get(name)
        if not buf or buf["type"] != "compound":
            return None
        orig_ul = to_ul(buf["total_volume"], buf["total_volume_unit"])
        if orig_ul == 0:
            return None
        scale = to_ul(target_vol, target_unit) / orig_ul
        vols = []
        total_src = 0
        for src in buf.get("sources", []):
            v = to_ul(src["volume"], src["volume_unit"]) * scale
            total_src += v
            dv, du = smart_vol(v, target_unit)
            vols.append({"buffer": src["buffer"], "volume": dv, "unit": du})
        water = to_ul(target_vol, target_unit) - total_src
        if water > 0.01:
            dv, du = smart_vol(water, target_unit)
            vols.append({"buffer": "H\u2082O", "volume": dv, "unit": du})
        return vols


# (ScrollableFrame removed – detail panel uses direct canvas embed)


# ── Application ─────────────────────────────────────────────────────────────


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Buffer Logger")
        self.geometry("1350x720")
        self.minsize(1050, 550)
        self.configure(bg="#F5F5F5")

        self.mgr = BufferManager()
        self._sel_name = None
        self._sel_tier = None
        self._recalc_job = None
        self._comp_rows = []
        self._cat_indices = {"stock": set(), "simple": set(), "compound": set()}

        self._build_styles()
        self._build_ui()
        self._refresh_all()

    # ── Styles ──────────────────────────────────────────────────────────

    def _build_styles(self):
        s = ttk.Style(self)
        try:
            s.theme_use("vista")
        except Exception:
            try:
                s.theme_use("clam")
            except Exception:
                pass

        s.configure("Big.TButton", font=("Segoe UI", 11), padding=(14, 6))
        s.configure("Save.TButton", font=("Segoe UI", 11, "bold"), padding=(20, 8))
        s.configure("Section.TLabel", font=("Segoe UI", 11, "bold"))
        s.configure("Conc.Treeview", font=("Segoe UI", 10), rowheight=26)
        s.configure("Conc.Treeview.Heading", font=("Segoe UI", 10, "bold"))

    # ── Main layout ────────────────────────────────────────────────────

    def _build_ui(self):
        # toolbar
        toolbar = tk.Frame(self, bg="#37474F", height=48)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)
        tk.Label(toolbar, text="Buffer Logger", font=("Segoe UI", 16, "bold"),
                 bg="#37474F", fg="white").pack(side="left", padx=16)
        tk.Button(
            toolbar, text="Volume Calculator", font=("Segoe UI", 10),
            bg="#546E7A", fg="white", activebackground="#607D8B", bd=0,
            padx=14, pady=4, cursor="hand2", command=self._open_calc
        ).pack(side="right", padx=(8, 16), pady=8)
        tk.Button(
            toolbar, text="Export Image", font=("Segoe UI", 10),
            bg="#546E7A", fg="white", activebackground="#607D8B", bd=0,
            padx=14, pady=4, cursor="hand2", command=self._open_export
        ).pack(side="right", pady=8)

        # main area using grid: 3 list columns with arrow buttons between them + detail
        body = tk.Frame(self, bg="#F5F5F5")
        body.pack(fill="both", expand=True, padx=8, pady=8)

        #  col:  0=stock  1=simple  2=compound  3=detail
        body.columnconfigure(0, weight=1, minsize=110)
        body.columnconfigure(1, weight=1, minsize=110)
        body.columnconfigure(2, weight=1, minsize=110)
        body.columnconfigure(3, weight=10, minsize=520)
        body.rowconfigure(0, weight=1)

        self._lists = {}
        self._list_frames = {}

        self._build_tier_column(body, "stock", 0)
        self._build_tier_column(body, "simple", 1)
        self._build_tier_column(body, "compound", 2)

        # right: detail panel with canvas scrolling
        detail_border = tk.Frame(body, bg="#CCCCCC", bd=0)
        detail_border.grid(row=0, column=3, sticky="nsew", padx=(6, 0))

        self._detail_canvas = tk.Canvas(detail_border, highlightthickness=0, bg="#FAFAFA", bd=0)
        self._detail_vsb = ttk.Scrollbar(detail_border, orient="vertical",
                                          command=self._detail_canvas.yview)
        self._detail_canvas.configure(yscrollcommand=self._detail_vsb.set)
        self._detail_vsb.pack(side="right", fill="y")
        self._detail_canvas.pack(side="left", fill="both", expand=True)

        self._detail = tk.Frame(self._detail_canvas, bg="#FAFAFA")
        self._detail_win = self._detail_canvas.create_window((0, 0), window=self._detail,
                                                              anchor="nw")

        def _on_detail_cfg(e):
            self._detail_canvas.configure(scrollregion=self._detail_canvas.bbox("all"))
        def _on_canvas_cfg(e):
            self._detail_canvas.itemconfigure(self._detail_win, width=e.width)
        def _on_wheel(e):
            self._detail_canvas.yview_scroll(-1 * (e.delta // 120), "units")

        self._detail.bind("<Configure>", _on_detail_cfg)
        self._detail_canvas.bind("<Configure>", _on_canvas_cfg)
        self._detail_canvas.bind("<Enter>",
            lambda e: self._detail_canvas.bind_all("<MouseWheel>", _on_wheel))
        self._detail_canvas.bind("<Leave>",
            lambda e: self._detail_canvas.unbind_all("<MouseWheel>"))

        self._show_empty_detail()

    # ── Tier columns ───────────────────────────────────────────────────

    def _build_tier_column(self, parent, tier, col):
        colors = TIER_COLORS[tier]

        outer = tk.Frame(parent, bg="#E0E0E0", bd=0)
        outer.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 4, 0))
        self._list_frames[tier] = outer

        # header
        header = tk.Frame(outer, bg=colors["bg"], height=32)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=TIER_LABELS[tier], font=("Segoe UI", 9, "bold"),
                 bg=colors["bg"], fg=colors["fg"]).pack(side="left", padx=8, pady=4)

        # listbox
        lb_frame = tk.Frame(outer, bg=colors["light"])
        lb_frame.pack(fill="both", expand=True)

        lb = tk.Listbox(lb_frame, font=("Segoe UI", 9), bd=0, highlightthickness=0,
                        selectbackground=colors["mid"], selectforeground="black",
                        bg=colors["light"], activestyle="none", exportselection=False)
        lb.pack(fill="both", expand=True, padx=2, pady=2)

        lb.bind("<<ListboxSelect>>", lambda e, t=tier: self._on_list_select(t))

        self._lists[tier] = lb

        # buttons
        btn_frame = tk.Frame(outer, bg=colors["light"])
        btn_frame.pack(fill="x", padx=4, pady=4)

        tk.Button(
            btn_frame, text="+", font=("Segoe UI", 9, "bold"),
            bg=colors["bg"], fg=colors["fg"], activebackground=colors["mid"],
            bd=0, padx=10, pady=2, cursor="hand2",
            command=lambda t=tier: self._new_buffer(t)
        ).pack(side="left", padx=(0, 4))

        tk.Button(
            btn_frame, text="\u2715", font=("Segoe UI", 9),
            bg="#C62828", fg="white", activebackground="#E53935",
            bd=0, padx=10, pady=2, cursor="hand2",
            command=lambda t=tier: self._delete_buffer(t)
        ).pack(side="left")

        tk.Button(
            btn_frame, text="\u2630", font=("Segoe UI", 9),
            bg="#78909C", fg="white", activebackground="#90A4AE",
            bd=0, padx=8, pady=2, cursor="hand2",
            command=lambda t=tier: self._manage_categories(t)
        ).pack(side="right")

    # ── List management ────────────────────────────────────────────────

    def _refresh_all(self):
        for tier in ("stock", "simple", "compound"):
            lb = self._lists[tier]
            lb.delete(0, "end")
            self._cat_indices[tier] = set()
            groups = self.mgr.names_grouped(tier)
            for cat, members in groups:
                if cat is not None:
                    idx = lb.size()
                    lb.insert("end", f"\u25b8 {cat}")
                    lb.itemconfigure(idx, fg=TIER_COLORS[tier]["bg"],
                                     selectbackground=TIER_COLORS[tier]["light"],
                                     selectforeground=TIER_COLORS[tier]["bg"])
                    self._cat_indices[tier].add(idx)
                for name in members:
                    prefix = "    " if cat is not None else ""
                    lb.insert("end", f"{prefix}{name}")

    def _select_item(self, name, tier):
        for t, other_lb in self._lists.items():
            other_lb.selection_clear(0, "end")
        lb = self._lists[tier]
        items = list(lb.get(0, "end"))
        for idx, item in enumerate(items):
            if item.strip() == name:
                lb.selection_set(idx)
                lb.see(idx)
                break
        self._sel_name = name
        self._sel_tier = tier
        self._show_detail()

    def _on_list_select(self, tier):
        lb = self._lists[tier]
        sel = lb.curselection()
        if not sel:
            return
        idx = sel[0]
        # skip category headers
        if idx in self._cat_indices.get(tier, set()):
            lb.selection_clear(idx)
            return
        # deselect other lists
        for t, other_lb in self._lists.items():
            if t != tier:
                other_lb.selection_clear(0, "end")
        self._sel_name = lb.get(idx).strip()
        self._sel_tier = tier
        self._show_detail()

    # ── Detail panel ───────────────────────────────────────────────────

    def _clear_detail(self):
        self._comp_rows = []
        if self._recalc_job:
            self.after_cancel(self._recalc_job)
            self._recalc_job = None
        for w in self._detail.winfo_children():
            w.destroy()

    def _show_empty_detail(self):
        self._clear_detail()
        ttk.Label(self._detail, text="Select a buffer to view details",
                  font=("Segoe UI", 14), foreground="#999").pack(pady=80, padx=20)

    def _show_detail(self):
        self._clear_detail()
        buf = self.mgr.get(self._sel_name)
        if not buf:
            self._show_empty_detail()
            return

        tier = buf["type"]
        colors = TIER_COLORS[tier]

        # title bar
        title_bar = tk.Frame(self._detail, bg=colors["bg"])
        title_bar.pack(fill="x", ipady=4)

        tk.Label(title_bar, text=TIER_LABELS[tier],
                 font=("Segoe UI", 9), bg=colors["bg"], fg=colors["fg"]
                 ).pack(side="right", padx=10)

        self._name_var = tk.StringVar(value=self._sel_name)
        tk.Entry(title_bar, textvariable=self._name_var,
                 font=("Segoe UI", 13, "bold"), bg=colors["bg"], fg=colors["fg"],
                 bd=0, insertbackground=colors["fg"], highlightthickness=0
                 ).pack(side="left", padx=10, pady=4, fill="x", expand=True)

        # pH + category + save on same row
        top_row = ttk.Frame(self._detail)
        top_row.pack(fill="x", padx=12, pady=(6, 2))
        ttk.Label(top_row, text="pH:", font=("Segoe UI", 10)).pack(side="left")
        self._ph_var = tk.StringVar(value=str(buf["pH"]) if buf.get("pH") else "")
        ttk.Entry(top_row, textvariable=self._ph_var, width=6,
                  font=("Segoe UI", 10)).pack(side="left", padx=(6, 0))

        # category dropdown
        cats = self.mgr.categories.get(tier, [])
        cat_values = ["(none)"] + cats
        current_cat = buf.get("category", "") or "(none)"
        ttk.Label(top_row, text="Category:", font=("Segoe UI", 10)).pack(side="left", padx=(12, 0))
        self._cat_var = tk.StringVar(value=current_cat)
        ttk.Combobox(top_row, textvariable=self._cat_var, values=cat_values,
                     width=14, font=("Segoe UI", 9)).pack(side="left", padx=(4, 0))

        # save button in top row
        if tier == "compound":
            tk.Button(top_row, text="Vol. Calc", font=("Segoe UI", 9),
                      bg="#546E7A", fg="white", activebackground="#607D8B", bd=0,
                      padx=8, pady=2, cursor="hand2",
                      command=lambda: self._open_calc(self._sel_name)).pack(side="right", padx=(4, 0))
        tk.Button(top_row, text="Save", font=("Segoe UI", 10, "bold"),
                  bg="#2E7D32", fg="white", activebackground="#388E3C", bd=0,
                  padx=14, pady=2, cursor="hand2",
                  command=self._save_current).pack(side="right", padx=(8, 0))

        if tier in ("stock", "simple"):
            self._build_component_editor(buf)
        else:
            self._build_compound_editor(buf)

        self._detail_canvas.yview_moveto(0)

    # ── Component editor (stock) ─────────────────────────────────────

    def _build_component_editor(self, buf):
        ttk.Label(self._detail, text="Components", font=("Segoe UI", 10, "bold")
                  ).pack(anchor="w", padx=12, pady=(8, 2))

        # column headers
        hdr = ttk.Frame(self._detail)
        hdr.pack(fill="x", padx=12, pady=(0, 2))
        ttk.Label(hdr, text="Ingredient", font=("Segoe UI", 8), foreground="#666",
                  width=18).pack(side="left")
        ttk.Label(hdr, text="Conc.", font=("Segoe UI", 8), foreground="#666",
                  width=10).pack(side="left", padx=(4, 0))
        ttk.Label(hdr, text="Unit", font=("Segoe UI", 8), foreground="#666",
                  width=8).pack(side="left", padx=(4, 0))

        self._comp_rows = []
        self._comp_container = ttk.Frame(self._detail)
        self._comp_container.pack(fill="x", padx=12)

        for comp in buf.get("components", []):
            self._add_component_row(comp["name"], comp["concentration"], comp["unit"])

        tk.Button(
            self._detail, text="+ Add Component", font=("Segoe UI", 9),
            bg="#E0E0E0", fg="#333", activebackground="#BDBDBD", bd=0,
            padx=10, pady=3, cursor="hand2", command=self._add_component_row
        ).pack(anchor="w", padx=12, pady=(6, 0))

    def _add_component_row(self, name="", conc="", unit="mM"):
        row = ttk.Frame(self._comp_container)
        row.pack(fill="x", pady=1)

        name_var = tk.StringVar(value=name)
        conc_var = tk.StringVar(value=str(conc) if conc != "" else "")
        unit_var = tk.StringVar(value=unit)

        ttk.Entry(row, textvariable=name_var, width=18,
                  font=("Segoe UI", 10)).pack(side="left", padx=(0, 4))
        ttk.Entry(row, textvariable=conc_var, width=10,
                  font=("Segoe UI", 10)).pack(side="left", padx=(0, 4))
        ttk.Combobox(row, textvariable=unit_var, values=CONC_UNITS,
                     width=6, state="readonly", font=("Segoe UI", 9)
                     ).pack(side="left", padx=(0, 4))

        entry = {"name": name_var, "conc": conc_var, "unit": unit_var, "frame": row}

        def remove():
            self._comp_rows.remove(entry)
            row.destroy()

        tk.Button(row, text="\u2715", font=("Segoe UI", 9, "bold"),
                  bg="#EF5350", fg="white", activebackground="#C62828",
                  bd=0, width=2, cursor="hand2", command=remove).pack(side="left")

        self._comp_rows.append(entry)

    # ── Compound editor ────────────────────────────────────────────────

    def _build_compound_editor(self, buf):
        # total volume row
        vol_frame = ttk.Frame(self._detail)
        vol_frame.pack(fill="x", padx=12, pady=(6, 4))
        ttk.Label(vol_frame, text="Total Volume:", font=("Segoe UI", 10)).pack(side="left")
        self._total_vol_var = tk.StringVar(value=str(buf.get("total_volume", "")))
        self._total_vol_var.trace_add("write", self._schedule_recalc)
        ttk.Entry(vol_frame, textvariable=self._total_vol_var, width=8,
                  font=("Segoe UI", 10)).pack(side="left", padx=(6, 4))
        self._total_unit_var = tk.StringVar(value=buf.get("total_volume_unit", "mL"))
        self._total_unit_var.trace_add("write", self._schedule_recalc)
        ttk.Combobox(vol_frame, textvariable=self._total_unit_var, values=VOL_UNITS,
                     width=5, state="readonly", font=("Segoe UI", 9)).pack(side="left")

        self._water_label = ttk.Label(vol_frame, text="", font=("Segoe UI", 10, "bold"))
        self._water_label.pack(side="right", padx=(12, 0))

        # side-by-side: sources (left) | concentrations (right)
        split = tk.Frame(self._detail, bg="#FAFAFA")
        split.pack(fill="both", expand=True, padx=4, pady=(2, 0))
        split.columnconfigure(0, weight=2)
        split.columnconfigure(1, weight=3)
        split.rowconfigure(1, weight=1)

        # ── Left: source buffers ──
        ttk.Label(split, text="Source Buffers", font=("Segoe UI", 10, "bold")
                  ).grid(row=0, column=0, sticky="w", padx=8, pady=(4, 2))

        src_frame = tk.Frame(split, bg="#FAFAFA")
        src_frame.grid(row=1, column=0, sticky="nsew", padx=(8, 4))

        # column headers
        hdr = ttk.Frame(src_frame)
        hdr.pack(fill="x", pady=(0, 2))
        ttk.Label(hdr, text="Fill", font=("Segoe UI", 8), foreground="#666",
                  width=3).pack(side="left")
        ttk.Label(hdr, text="Buffer", font=("Segoe UI", 8), foreground="#666",
                  width=18).pack(side="left")
        ttk.Label(hdr, text="Vol", font=("Segoe UI", 8), foreground="#666",
                  width=7).pack(side="left", padx=(2, 0))
        ttk.Label(hdr, text="Unit", font=("Segoe UI", 8), foreground="#666",
                  width=5).pack(side="left", padx=(2, 0))

        self._src_container = ttk.Frame(src_frame)
        self._src_container.pack(fill="x")

        self._fill_var = tk.IntVar(value=-1)
        self._fill_var.trace_add("write", self._schedule_recalc)

        self._comp_rows = []
        for src in buf.get("sources", []):
            self._add_source_row(src["buffer"], src["volume"], src["volume_unit"])

        tk.Button(
            src_frame, text="+ Add Source", font=("Segoe UI", 9),
            bg="#E0E0E0", fg="#333", activebackground="#BDBDBD", bd=0,
            padx=10, pady=3, cursor="hand2", command=self._add_source_row
        ).pack(anchor="w", pady=(6, 0))

        # ── Right: final concentrations ──
        ttk.Label(split, text="Final Concentrations", font=("Segoe UI", 10, "bold")
                  ).grid(row=0, column=1, sticky="w", padx=8, pady=(4, 2))

        conc_frame = tk.Frame(split, bg="#FAFAFA")
        conc_frame.grid(row=1, column=1, sticky="nsew", padx=(4, 8))

        cols = ("ingredient", "concentration", "unit")
        self._conc_tree = ttk.Treeview(conc_frame, columns=cols, show="headings",
                                       style="Conc.Treeview")
        self._conc_tree.heading("ingredient", text="Ingredient")
        self._conc_tree.heading("concentration", text="Concentration")
        self._conc_tree.heading("unit", text="Unit")
        self._conc_tree.column("ingredient", width=140, anchor="w")
        self._conc_tree.column("concentration", width=90, anchor="e")
        self._conc_tree.column("unit", width=70, anchor="w")
        conc_vsb = ttk.Scrollbar(conc_frame, orient="vertical", command=self._conc_tree.yview)
        self._conc_tree.configure(yscrollcommand=conc_vsb.set)
        conc_vsb.pack(side="right", fill="y")
        self._conc_tree.pack(side="left", fill="both", expand=True)
        self._conc_tree.tag_configure("even", background="#F5F5F5")
        self._conc_tree.tag_configure("odd", background="white")

        self._recalc_compound()

    def _add_source_row(self, buf_name="", vol="", vol_unit="µL"):
        idx = len(self._comp_rows)
        row = ttk.Frame(self._src_container)
        row.pack(fill="x", pady=1)

        tk.Radiobutton(row, variable=self._fill_var, value=idx,
                       bg="#FAFAFA", activebackground="#FAFAFA",
                       highlightthickness=0).pack(side="left", padx=(0, 1))

        buf_var = tk.StringVar(value=buf_name)
        vol_var = tk.StringVar(value=str(vol) if vol != "" else "")
        unit_var = tk.StringVar(value=vol_unit)

        available = sorted(
            n for n in self.mgr.names()
            if n != self._sel_name
        )

        ttk.Combobox(row, textvariable=buf_var, values=available,
                     width=17, font=("Segoe UI", 9)
                     ).pack(side="left", padx=(0, 2))
        buf_var.trace_add("write", self._schedule_recalc)

        vol_entry = ttk.Entry(row, textvariable=vol_var, width=7,
                              font=("Segoe UI", 9))
        vol_entry.pack(side="left", padx=(0, 2))
        vol_var.trace_add("write", self._schedule_recalc)

        ttk.Combobox(row, textvariable=unit_var, values=VOL_UNITS,
                     width=4, state="readonly", font=("Segoe UI", 9)
                     ).pack(side="left", padx=(0, 4))
        unit_var.trace_add("write", self._schedule_recalc)

        entry = {"buffer": buf_var, "volume": vol_var, "unit": unit_var,
                 "frame": row, "vol_entry": vol_entry}

        def remove():
            try:
                was_fill = self._fill_var.get() == self._comp_rows.index(entry)
            except ValueError:
                was_fill = False
            if entry in self._comp_rows:
                self._comp_rows.remove(entry)
            row.destroy()
            if was_fill:
                self._fill_var.set(-1)
            self._schedule_recalc()

        tk.Button(row, text="\u2715", font=("Segoe UI", 9, "bold"),
                  bg="#EF5350", fg="white", activebackground="#C62828",
                  bd=0, width=2, cursor="hand2", command=remove).pack(side="left")

        self._comp_rows.append(entry)

    def _schedule_recalc(self, *_):
        if self._recalc_job:
            self.after_cancel(self._recalc_job)
        self._recalc_job = self.after(120, self._recalc_compound)

    def _recalc_compound(self):
        self._recalc_job = None
        if not hasattr(self, "_conc_tree") or not self._conc_tree.winfo_exists():
            return

        for item in self._conc_tree.get_children():
            self._conc_tree.delete(item)
        self._water_label.config(text="")

        try:
            total_vol = float(self._total_vol_var.get())
        except (ValueError, AttributeError):
            return
        total_unit = self._total_unit_var.get()
        total_ul = to_ul(total_vol, total_unit)
        if total_ul <= 0:
            return

        # auto-fill: adjust the selected fill buffer's volume
        fill_idx = self._fill_var.get()
        if 0 <= fill_idx < len(self._comp_rows):
            other_ul = 0
            for i, row in enumerate(self._comp_rows):
                if i == fill_idx:
                    continue
                try:
                    vol = float(row["volume"].get())
                except ValueError:
                    continue
                other_ul += to_ul(vol, row["unit"].get())
            fill_unit = self._comp_rows[fill_idx]["unit"].get()
            fill_ul = max(0, total_ul - other_ul)
            fill_vol_factor = VOL_TO_UL.get(fill_unit, 1)
            fill_display = fill_ul / fill_vol_factor
            fill_var = self._comp_rows[fill_idx]["volume"]
            current = fill_var.get()
            new_val = fmt(fill_display)
            if current != new_val:
                traces = fill_var.trace_info()
                for mode, cbname in traces:
                    if "write" in mode:
                        fill_var.trace_remove("write", cbname)
                fill_var.set(new_val)
                fill_var.trace_add("write", self._schedule_recalc)

        ingredients = {}
        src_ul_total = 0

        for row in self._comp_rows:
            bname = row["buffer"].get().strip()
            try:
                vol = float(row["volume"].get())
            except ValueError:
                continue
            unit = row["unit"].get()
            if not bname or bname not in self.mgr.buffers:
                continue

            src_ul = to_ul(vol, unit)
            src_ul_total += src_ul
            dilution = src_ul / total_ul

            for comp in self.mgr.final_conc(bname):
                bv, cat = to_base_conc(comp["concentration"], comp["unit"])
                key = comp["name"]
                if key in ingredients:
                    ingredients[key]["value"] += bv * dilution
                else:
                    ingredients[key] = {"value": bv * dilution, "category": cat}

        for i, (n, d) in enumerate(ingredients.items()):
            dv, du = from_base_conc(d["value"], d["category"])
            tag = "even" if i % 2 == 0 else "odd"
            self._conc_tree.insert("", "end", values=(n, fmt(dv), du), tags=(tag,))

        water = total_ul - src_ul_total
        if water > 0.01:
            wv, wu = smart_vol(water, total_unit)
            self._water_label.config(
                text=f"H\u2082O to fill:  {fmt(wv)} {wu}", foreground="#1565C0")
        elif water < -0.01:
            self._water_label.config(
                text="\u26a0  Source volumes exceed total volume!", foreground="#C62828")
        else:
            self._water_label.config(text="No water needed (exact fill)", foreground="#666")

    # ── CRUD ───────────────────────────────────────────────────────────

    def _new_buffer(self, tier):
        base = TIER_LABELS[tier].rstrip("s")
        name = f"New {base}"
        i = 1
        while name in self.mgr.buffers:
            i += 1
            name = f"New {base} {i}"

        if tier in ("stock", "simple"):
            self.mgr.add(name, {"type": tier, "pH": None, "components": []})
        else:
            self.mgr.add(name, {"type": "compound", "pH": None,
                                "total_volume": 1, "total_volume_unit": "mL", "sources": []})

        self._refresh_all()
        self._select_item(name, tier)

    def _delete_buffer(self, tier):
        lb = self._lists[tier]
        sel = lb.curselection()
        if not sel:
            messagebox.showinfo("Info", "Select a buffer to delete.", parent=self)
            return
        name = lb.get(sel[0]).strip()
        if not messagebox.askyesno("Delete?", f"Delete '{name}'?", parent=self):
            return
        ok, deps = self.mgr.delete(name)
        if not ok:
            messagebox.showerror(
                "Error",
                f"Cannot delete '{name}'.\nUsed by:\n" + "\n".join(f"  - {d}" for d in deps),
                parent=self)
            return
        self._sel_name = None
        self._sel_tier = None
        self._refresh_all()
        self._show_empty_detail()

    def _save_current(self):
        if not self._sel_name or not self._sel_tier:
            return

        new_name = self._name_var.get().strip()
        if not new_name:
            messagebox.showerror("Error", "Buffer name is required.", parent=self)
            return

        ph = None
        ph_s = self._ph_var.get().strip()
        if ph_s:
            try:
                ph = float(ph_s)
            except ValueError:
                messagebox.showerror("Error", "Invalid pH value.", parent=self)
                return

        tier = self._sel_tier

        if tier in ("stock", "simple"):
            components = []
            for r in self._comp_rows:
                ing = r["name"].get().strip()
                cs = r["conc"].get().strip()
                if not ing and not cs:
                    continue
                if not ing:
                    messagebox.showerror("Error", "Component name missing.", parent=self)
                    return
                try:
                    conc = float(cs)
                except ValueError:
                    messagebox.showerror("Error", f"Invalid concentration for '{ing}'.", parent=self)
                    return
                components.append({"name": ing, "concentration": conc, "unit": r["unit"].get()})

            data = {"type": tier, "pH": ph, "components": components}
            cat = self._cat_var.get().strip()
            if cat and cat != "(none)":
                data["category"] = cat

        else:
            try:
                total_vol = float(self._total_vol_var.get())
            except ValueError:
                messagebox.showerror("Error", "Invalid total volume.", parent=self)
                return

            sources = []
            for r in self._comp_rows:
                bname = r["buffer"].get().strip()
                vs = r["volume"].get().strip()
                if not bname and not vs:
                    continue
                if not bname:
                    continue
                if bname not in self.mgr.buffers:
                    messagebox.showerror("Error", f"Source '{bname}' does not exist.", parent=self)
                    return
                try:
                    vol = float(vs)
                except ValueError:
                    messagebox.showerror("Error", f"Invalid volume for '{bname}'.", parent=self)
                    return
                sources.append({"buffer": bname, "volume": vol, "volume_unit": r["unit"].get()})

            data = {"type": "compound", "pH": ph,
                    "total_volume": total_vol, "total_volume_unit": self._total_unit_var.get(),
                    "sources": sources}
            cat = self._cat_var.get().strip()
            if cat and cat != "(none)":
                data["category"] = cat

        if new_name != self._sel_name:
            if new_name in self.mgr.buffers:
                if not messagebox.askyesno("Overwrite?", f"'{new_name}' exists. Overwrite?",
                                           parent=self):
                    return
            self.mgr.rename(self._sel_name, new_name)
            self._sel_name = new_name

        self.mgr.add(new_name, data)
        self._refresh_all()
        self._select_item(new_name, tier)

    # ── Category management ────────────────────────────────────────────

    def _manage_categories(self, tier):
        dlg = tk.Toplevel(self)
        dlg.title(f"Categories – {TIER_LABELS[tier]}")
        dlg.geometry("320x350")
        dlg.configure(bg="#FAFAFA")
        dlg.grab_set()
        dlg.transient(self)

        tk.Label(dlg, text=f"Categories for {TIER_LABELS[tier]}",
                 font=("Segoe UI", 11, "bold"), bg="#FAFAFA").pack(padx=12, pady=(10, 6))

        list_frame = tk.Frame(dlg, bg="#FAFAFA")
        list_frame.pack(fill="both", expand=True, padx=12)

        cat_lb = tk.Listbox(list_frame, font=("Segoe UI", 10), bd=1,
                            highlightthickness=0, selectbackground="#90CAF9")
        cat_lb.pack(fill="both", expand=True)

        def refresh_cats():
            cat_lb.delete(0, "end")
            for c in self.mgr.categories.get(tier, []):
                cat_lb.insert("end", c)

        refresh_cats()

        btn_row = tk.Frame(dlg, bg="#FAFAFA")
        btn_row.pack(fill="x", padx=12, pady=8)

        def add_cat():
            from tkinter import simpledialog
            name = simpledialog.askstring("New Category", "Category name:", parent=dlg)
            if name and name.strip():
                self.mgr.add_category(tier, name.strip())
                refresh_cats()
                self._refresh_all()

        def rename_cat():
            sel = cat_lb.curselection()
            if not sel:
                return
            old = cat_lb.get(sel[0])
            from tkinter import simpledialog
            new = simpledialog.askstring("Rename Category", "New name:", parent=dlg,
                                         initialvalue=old)
            if new and new.strip() and new.strip() != old:
                self.mgr.rename_category(tier, old, new.strip())
                refresh_cats()
                self._refresh_all()

        def del_cat():
            sel = cat_lb.curselection()
            if not sel:
                return
            name = cat_lb.get(sel[0])
            if messagebox.askyesno("Delete?", f"Delete category '{name}'?\n"
                                   "Buffers will become uncategorized.", parent=dlg):
                self.mgr.remove_category(tier, name)
                refresh_cats()
                self._refresh_all()

        tk.Button(btn_row, text="+ Add", font=("Segoe UI", 9, "bold"),
                  bg="#2E7D32", fg="white", activebackground="#388E3C",
                  bd=0, padx=10, pady=2, cursor="hand2", command=add_cat).pack(side="left", padx=(0, 4))
        tk.Button(btn_row, text="Rename", font=("Segoe UI", 9),
                  bg="#1565C0", fg="white", activebackground="#1976D2",
                  bd=0, padx=10, pady=2, cursor="hand2", command=rename_cat).pack(side="left", padx=(0, 4))
        tk.Button(btn_row, text="Delete", font=("Segoe UI", 9),
                  bg="#C62828", fg="white", activebackground="#E53935",
                  bd=0, padx=10, pady=2, cursor="hand2", command=del_cat).pack(side="left")

    # ── Export ──────────────────────────────────────────────────────────

    def _open_export(self):
        if not HAS_PIL:
            messagebox.showerror("Error",
                "Pillow is required for image export.\n"
                "Install it with:  pip install Pillow", parent=self)
            return
        ExportDialog(self, self.mgr)

    # ── Volume calculator ──────────────────────────────────────────────

    def _open_calc(self, preselect=None):
        VolumeCalculatorDialog(self, self.mgr, preselect)


# ── Volume calculator dialog ───────────────────────────────────────────────


class VolumeCalculatorDialog(tk.Toplevel):
    def __init__(self, parent, mgr, preselect=None):
        super().__init__(parent)
        self.mgr = mgr
        self.title("Volume Calculator")
        self.geometry("560x540")
        self.minsize(480, 400)
        self.configure(bg="#FAFAFA")
        self.grab_set()
        self._build(preselect)

    def _build(self, preselect):
        hdr = tk.Frame(self, bg="#37474F", height=44)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Volume Calculator", font=("Segoe UI", 14, "bold"),
                 bg="#37474F", fg="white").pack(side="left", padx=14)

        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="Buffer:", font=("Segoe UI", 11)).grid(
            row=0, column=0, sticky="w")
        self.buf_var = tk.StringVar(value=preselect or "")
        ttk.Combobox(body, textvariable=self.buf_var, values=self.mgr.names("compound"),
                     width=28, state="readonly", font=("Segoe UI", 11)).grid(
            row=0, column=1, columnspan=2, sticky="ew", padx=(8, 0))

        ttk.Label(body, text="Target Volume:", font=("Segoe UI", 11)).grid(
            row=1, column=0, sticky="w", pady=(10, 0))
        self.vol_var = tk.StringVar()
        ttk.Entry(body, textvariable=self.vol_var, width=12,
                  font=("Segoe UI", 11)).grid(
            row=1, column=1, sticky="w", padx=(8, 0), pady=(10, 0))
        self.unit_var = tk.StringVar(value="mL")
        ttk.Combobox(body, textvariable=self.unit_var, values=VOL_UNITS, width=6,
                     state="readonly", font=("Segoe UI", 10)).grid(
            row=1, column=2, sticky="w", padx=(6, 0), pady=(10, 0))

        tk.Button(body, text="Calculate", font=("Segoe UI", 12, "bold"),
                  bg="#1565C0", fg="white", activebackground="#1976D2",
                  bd=0, padx=20, pady=6, cursor="hand2", command=self._calc
                  ).grid(row=2, column=0, columnspan=3, pady=14)

        body.columnconfigure(1, weight=1)

        ttk.Label(body, text="Recipe", font=("Segoe UI", 11, "bold")).grid(
            row=3, column=0, columnspan=3, sticky="w")
        self.tree = ttk.Treeview(body, columns=("c", "v", "u"), show="headings", height=6,
                                 style="Conc.Treeview")
        self.tree.heading("c", text="Component")
        self.tree.heading("v", text="Volume")
        self.tree.heading("u", text="Unit")
        self.tree.column("c", width=200)
        self.tree.column("v", width=100, anchor="e")
        self.tree.column("u", width=60)
        self.tree.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=(4, 8))
        self.tree.tag_configure("even", background="#F5F5F5")
        self.tree.tag_configure("odd", background="white")

        self.total_label = ttk.Label(body, text="", font=("Segoe UI", 11, "bold"))
        self.total_label.grid(row=5, column=0, columnspan=3, sticky="w")

        ttk.Label(body, text="Final Concentrations", font=("Segoe UI", 11, "bold")).grid(
            row=6, column=0, columnspan=3, sticky="w", pady=(10, 0))
        self.conc_tree = ttk.Treeview(body, columns=("i", "c", "u"), show="headings", height=5,
                                      style="Conc.Treeview")
        self.conc_tree.heading("i", text="Ingredient")
        self.conc_tree.heading("c", text="Concentration")
        self.conc_tree.heading("u", text="Unit")
        self.conc_tree.column("i", width=160)
        self.conc_tree.column("c", width=100, anchor="e")
        self.conc_tree.column("u", width=70)
        self.conc_tree.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=(4, 0))
        self.conc_tree.tag_configure("even", background="#F5F5F5")
        self.conc_tree.tag_configure("odd", background="white")

        body.rowconfigure(4, weight=1)
        body.rowconfigure(7, weight=1)

    def _calc(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for item in self.conc_tree.get_children():
            self.conc_tree.delete(item)
        self.total_label.config(text="")

        name = self.buf_var.get()
        if not name:
            messagebox.showerror("Error", "Select a buffer.", parent=self)
            return
        try:
            target = float(self.vol_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid volume.", parent=self)
            return
        unit = self.unit_var.get()

        vols = self.mgr.calc_volumes(name, target, unit)
        if not vols:
            return
        for i, v in enumerate(vols):
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert("", "end", values=(v["buffer"], fmt(v["volume"]), v["unit"]),
                             tags=(tag,))
        self.total_label.config(text=f"Total: {fmt(target)} {unit}")

        for i, comp in enumerate(self.mgr.final_conc(name)):
            tag = "even" if i % 2 == 0 else "odd"
            self.conc_tree.insert("", "end",
                                  values=(comp["name"], fmt(comp["concentration"]), comp["unit"]),
                                  tags=(tag,))


# ── Export dialog ──────────────────────────────────────────────────────────


class ExportDialog(tk.Toplevel):
    """Select buffers and export their recipes/concentrations as an image."""

    def __init__(self, parent, mgr):
        super().__init__(parent)
        self.mgr = mgr
        self.title("Export Buffers to Image")
        self.geometry("500x560")
        self.minsize(400, 420)
        self.configure(bg="#FAFAFA")
        self.grab_set()
        self.transient(parent)
        self._build()

    def _build(self):
        tk.Label(self, text="Select buffers to export",
                 font=("Segoe UI", 12, "bold"), bg="#FAFAFA").pack(padx=12, pady=(10, 4))

        # buffer list with checkboxes
        list_frame = tk.Frame(self, bg="#FAFAFA")
        list_frame.pack(fill="both", expand=True, padx=12)

        canvas = tk.Canvas(list_frame, bg="white", highlightthickness=1,
                           highlightbackground="#CCC")
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg="white")
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        self._check_vars = {}
        for tier in ("stock", "simple", "compound"):
            names = self.mgr.names(tier)
            if not names:
                continue
            tk.Label(inner, text=TIER_LABELS[tier], font=("Segoe UI", 9, "bold"),
                     bg="white", fg=TIER_COLORS[tier]["bg"]).pack(anchor="w", padx=8, pady=(6, 2))
            for name in names:
                var = tk.BooleanVar(value=False)
                self._check_vars[name] = var
                tk.Checkbutton(inner, text=name, variable=var, bg="white",
                               activebackground="white", font=("Segoe UI", 9),
                               anchor="w").pack(fill="x", padx=16)

        # select all / none
        sel_frame = tk.Frame(self, bg="#FAFAFA")
        sel_frame.pack(fill="x", padx=12, pady=(4, 0))
        tk.Button(sel_frame, text="Select All", font=("Segoe UI", 9),
                  bg="#E0E0E0", fg="#333", bd=0, padx=8, pady=2, cursor="hand2",
                  command=lambda: self._set_all(True)).pack(side="left", padx=(0, 4))
        tk.Button(sel_frame, text="Select None", font=("Segoe UI", 9),
                  bg="#E0E0E0", fg="#333", bd=0, padx=8, pady=2, cursor="hand2",
                  command=lambda: self._set_all(False)).pack(side="left")

        # options
        opt_frame = tk.LabelFrame(self, text="Include in export", font=("Segoe UI", 9, "bold"),
                                  bg="#FAFAFA", padx=8, pady=4)
        opt_frame.pack(fill="x", padx=12, pady=(8, 0))

        self._show_volumes = tk.BooleanVar(value=True)
        self._show_conc = tk.BooleanVar(value=True)
        tk.Checkbutton(opt_frame, text="Volumes / Recipe", variable=self._show_volumes,
                       bg="#FAFAFA", activebackground="#FAFAFA",
                       font=("Segoe UI", 9)).pack(side="left", padx=(0, 16))
        tk.Checkbutton(opt_frame, text="Final Concentrations", variable=self._show_conc,
                       bg="#FAFAFA", activebackground="#FAFAFA",
                       font=("Segoe UI", 9)).pack(side="left")

        # export button
        tk.Button(self, text="Export as Image", font=("Segoe UI", 11, "bold"),
                  bg="#1565C0", fg="white", activebackground="#1976D2",
                  bd=0, padx=20, pady=6, cursor="hand2",
                  command=self._export).pack(pady=10)

    def _set_all(self, val):
        for v in self._check_vars.values():
            v.set(val)

    def _export(self):
        selected = [n for n, v in self._check_vars.items() if v.get()]
        if not selected:
            messagebox.showinfo("Info", "Select at least one buffer.", parent=self)
            return
        if not self._show_volumes.get() and not self._show_conc.get():
            messagebox.showinfo("Info", "Enable at least one of Volumes or Concentrations.",
                                parent=self)
            return

        path = filedialog.asksaveasfilename(
            parent=self, title="Save Image",
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("TIFF Image", "*.tif *.tiff")],
        )
        if not path:
            return

        try:
            img = self._render(selected, self._show_volumes.get(), self._show_conc.get())
            img.save(path, dpi=(300, 300))
            messagebox.showinfo("Exported", f"Saved to:\n{path}", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Export failed:\n{e}", parent=self)

    # ── Rendering ─────────────────────────────────────────────────────

    @staticmethod
    def _load_fonts():
        try:
            return {
                "heading": ImageFont.truetype("segoeuib.ttf", 16),
                "body":    ImageFont.truetype("segoeui.ttf", 14),
                "small":   ImageFont.truetype("segoeui.ttf", 12),
            }
        except OSError:
            pass
        try:
            return {
                "heading": ImageFont.truetype("arialbd.ttf", 16),
                "body":    ImageFont.truetype("arial.ttf", 14),
                "small":   ImageFont.truetype("arial.ttf", 12),
            }
        except OSError:
            f = ImageFont.load_default()
            return {"heading": f, "body": f, "small": f}

    def _render(self, names, show_vol, show_conc):
        fonts = self._load_fonts()
        row_h = 22
        section_gap = 14
        pad = 20
        col_gap = 24  # gap between left and right columns
        hdr_color = "#37474F"
        hdr_fg = "#FFFFFF"
        even_bg = "#F5F5F5"
        odd_bg = "#FFFFFF"
        border = "#CCCCCC"

        # ── Build section data ──
        sections = []
        for name in names:
            buf = self.mgr.get(name)
            if not buf:
                continue
            tier = buf["type"]
            color = TIER_COLORS[tier]["bg"]
            sec = {"name": name, "tier": tier, "color": color, "tables": []}

            if tier == "compound":
                if show_vol:
                    rows = []
                    total_ul = to_ul(buf.get("total_volume", 0),
                                     buf.get("total_volume_unit", "µL"))
                    src_ul = 0
                    for src in buf.get("sources", []):
                        v, u = src["volume"], src["volume_unit"]
                        rows.append((src["buffer"], f"{fmt(v)} {u}"))
                        src_ul += to_ul(v, u)
                    water = total_ul - src_ul
                    if water > 0.01:
                        wv, wu = smart_vol(water, buf.get("total_volume_unit", "µL"))
                        rows.append(("H\u2082O", f"{fmt(wv)} {wu}"))
                    total_str = f"Total: {fmt(buf.get('total_volume', 0))} {buf.get('total_volume_unit', 'µL')}"
                    sec["tables"].append({
                        "label": "Recipe", "cols": ("Buffer", "Volume"),
                        "rows": rows, "footer": total_str,
                    })
                if show_conc:
                    rows = []
                    for comp in self.mgr.final_conc(name):
                        rows.append((comp["name"],
                                     f"{fmt(comp['concentration'])} {comp['unit']}"))
                    sec["tables"].append({
                        "label": "Final Concentrations",
                        "cols": ("Ingredient", "Concentration"),
                        "rows": rows,
                    })
            else:
                # stock / simple — components are always shown (they are the definition)
                rows = []
                for c in buf.get("components", []):
                    rows.append((c["name"], f"{fmt(c['concentration'])} {c['unit']}"))
                ph_str = f"pH {buf['pH']}" if buf.get("pH") else None
                sec["tables"].append({
                    "label": "Components", "cols": ("Ingredient", "Concentration"),
                    "rows": rows, "ph": ph_str,
                })

            if sec["tables"]:
                sections.append(sec)

        if not sections:
            img = Image.new("RGB", (400, 60), "white")
            ImageDraw.Draw(img).text((20, 20), "No buffer data to export.",
                                     fill="#666", font=fonts["small"])
            return img

        # ── Measure helpers ──
        tmp_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        cell_pad = 10   # padding inside each cell
        col_inner_gap = 20  # minimum gap between left-col text and right-col text

        def tw(text, font):
            bb = tmp_draw.textbbox((0, 0), text, font=font)
            return bb[2] - bb[0]

        def th(text, font):
            bb = tmp_draw.textbbox((0, 0), text, font=font)
            return bb[3] - bb[1]

        # Measure the tallest line to set row_h properly
        sample_h = th("ABCDghijklpqy0123", fonts["body"])
        row_h = sample_h + 10  # text height + vertical padding

        def table_col_widths(tbl):
            """Return (left_col_w, right_col_w) measured from actual text."""
            lw = tw(tbl["cols"][0], fonts["body"])
            rw = tw(tbl["cols"][1], fonts["body"])
            for label, val in tbl["rows"]:
                lw = max(lw, tw(label, fonts["body"]))
                rw = max(rw, tw(val, fonts["body"]))
            if tbl.get("footer"):
                lw = max(lw, tw(tbl["footer"], fonts["heading"]))
            return lw, rw

        def section_height(sec):
            h = 30  # title bar
            for tbl in sec["tables"]:
                if tbl.get("ph"):
                    h += row_h
                h += row_h + 6  # label
                h += row_h      # header
                h += row_h * len(tbl["rows"])
                if tbl.get("footer"):
                    h += row_h
                h += section_gap
            return h

        def section_width(sec):
            w = tw(sec["name"], fonts["heading"]) + tw(TIER_LABELS[sec["tier"]], fonts["small"]) + 50
            for tbl in sec["tables"]:
                lw, rw = table_col_widths(tbl)
                tw_total = lw + rw + 2 * cell_pad + col_inner_gap + 2 * cell_pad
                w = max(w, tw_total)
            return max(w, 300)

        # Pre-compute the value-column x offset per table (relative to section left)
        # so every table in every section uses a consistent split point
        global_left_w = 0
        for sec in sections:
            for tbl in sec["tables"]:
                lw, _ = table_col_widths(tbl)
                global_left_w = max(global_left_w, lw)
        val_x_offset = cell_pad + global_left_w + col_inner_gap

        # ── Two-column layout — pair sections ──
        pairs = []
        for i in range(0, len(sections), 2):
            left = sections[i]
            right = sections[i + 1] if i + 1 < len(sections) else None
            pairs.append((left, right))

        # Determine column width
        col_w = 300
        for sec in sections:
            col_w = max(col_w, section_width(sec))
        col_w = min(col_w, 520)
        # ensure col_w can fit the value column
        max_right_w = 0
        for sec in sections:
            for tbl in sec["tables"]:
                _, rw = table_col_widths(tbl)
                max_right_w = max(max_right_w, rw)
        min_needed = val_x_offset + max_right_w + 2 * cell_pad
        col_w = max(col_w, min_needed)

        img_w = 2 * col_w + col_gap + 2 * pad

        # Calculate total height
        total_h = pad
        for left, right in pairs:
            lh = section_height(left)
            rh = section_height(right) if right else 0
            total_h += max(lh, rh) + 10
        total_h += pad

        img = Image.new("RGB", (img_w, total_h), "white")
        draw = ImageDraw.Draw(img)

        # ── Draw helper ──
        def draw_section(sec, x_left, x_right, y_start):
            y = y_start
            # title bar
            draw.rectangle([x_left, y, x_right, y + 28], fill=sec["color"])
            draw.text((x_left + cell_pad, y + 5), sec["name"],
                      fill="white", font=fonts["heading"])
            tl = TIER_LABELS[sec["tier"]]
            tl_w = tw(tl, fonts["small"])
            draw.text((x_right - tl_w - cell_pad, y + 8), tl,
                      fill="#DDDDDD", font=fonts["small"])
            y += 30

            val_x = x_left + val_x_offset  # where the right column starts

            for tbl in sec["tables"]:
                if tbl.get("ph"):
                    draw.text((x_left + cell_pad, y + 3), tbl["ph"],
                              fill="#555", font=fonts["body"])
                    y += row_h

                draw.text((x_left + 4, y + 3), tbl["label"],
                          fill="#333", font=fonts["heading"])
                y += row_h + 6

                # header row
                draw.rectangle([x_left, y, x_right, y + row_h], fill=hdr_color)
                draw.text((x_left + cell_pad, y + 4), tbl["cols"][0],
                          fill=hdr_fg, font=fonts["body"])
                draw.text((val_x, y + 4), tbl["cols"][1],
                          fill=hdr_fg, font=fonts["body"])
                y += row_h

                for ri, (label, val) in enumerate(tbl["rows"]):
                    bg = even_bg if ri % 2 == 0 else odd_bg
                    draw.rectangle([x_left, y, x_right, y + row_h], fill=bg)
                    draw.line([x_left, y, x_right, y], fill=border)
                    draw.text((x_left + cell_pad, y + 4), label,
                              fill="#222", font=fonts["body"])
                    draw.text((val_x, y + 4), val,
                              fill="#222", font=fonts["body"])
                    y += row_h
                draw.line([x_left, y, x_right, y], fill=border)

                if tbl.get("footer"):
                    draw.text((x_left + cell_pad, y + 4), tbl["footer"],
                              fill="#1565C0", font=fonts["heading"])
                    y += row_h

                y += section_gap
            return y

        # ── Render pairs ──
        y = pad
        left_x0 = pad
        left_x1 = pad + col_w
        right_x0 = pad + col_w + col_gap
        right_x1 = right_x0 + col_w

        for left, right in pairs:
            y_left = draw_section(left, left_x0, left_x1, y)
            if right:
                y_right = draw_section(right, right_x0, right_x1, y)
                y = max(y_left, y_right) + 10
            else:
                y = y_left + 10

        # crop to actual content
        img = img.crop((0, 0, img_w, y + pad))
        return img


if __name__ == "__main__":
    app = App()
    app.mainloop()
