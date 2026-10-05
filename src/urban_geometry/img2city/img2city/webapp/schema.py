"""img2city/webapp/schema.py -- typed edit-form schema for the per-building spec.json.

Derived from the spec vocabulary the agents write against
(generate.py SPEC_LINES / components._build_building / city_generate.poly_params
/ parts_learned.py signatures).  The frontend renders the edit panel from this;
labels are bilingual (label / label_en) and the UI picks by language.
`path` is a dot path into spec.json.
"""

WALLS = ["brick", "stone", "stucco", "white", "slab"]
MATS = ["iron", "stone", "white", "stucco", "slate", "slate_dark", "copper",
        "brick", "mullion", "sign", "roof"]

SCHEMA = {
    "groups": [
        {
            "title": "Massing",
            "fields": [
                {"path": "floors", "label": "Storeys",
                 "type": "int", "min": 1, "max": 100, "masses_override": True, "live": True},
                {"path": "floor_h", "label": "Floor height (m)",
                 "type": "float", "min": 2.4, "max": 5.0, "step": 0.1, "live": True},
                {"path": "facade", "label": "Facade system",
                 "type": "enum", "choices": ["masonry", "glass"],
                 "masses_override": True},
                {"path": "typology", "label": "Typology",
                 "type": "enum", "choices": ["terrace", "institutional"]},
                {"path": "plinth", "label": "Plinth", "type": "bool"},
            ],
        },
        {
            "title": "Walls & palette",
            "fields": [
                {"path": "wall", "label": "Wall material",
                 "type": "enum", "choices": WALLS},
                {"path": "colors.wall", "label": "Wall colour", "type": "color"},
                {"path": "colors.stucco", "label": "Stucco colour", "type": "color"},
                {"path": "colors.frame", "label": "Frame colour", "type": "color"},
                {"path": "colors.roof", "label": "Roof colour", "type": "color"},
                {"path": "colors.glass_look", "label": "Curtain-wall look",
                 "type": "enum", "choices": ["mirror", "glossy", "satin", "matte"]},
            ],
        },
        {
            "title": "Roof",
            "fields": [
                {"path": "terrace.roof_form", "label": "Roof form",
                 "type": "enum", "choices": ["valley", "gable", "flat", "mansard"],
                 "poly": "roof_form"},
                {"path": "terrace.roof_tone", "label": "Roof tone",
                 "type": "enum", "choices": ["dark", "mid", "light"], "poly": "roof_tone"},
                {"path": "terrace.dormers", "label": "Dormers",
                 "type": "bool", "poly": "dormers"},
            ],
        },
        {
            "title": "Terrace facade",
            "fields": [
                {"path": "terrace.bay_m", "poly_drop": True, "label": "Bay width (m)",
                 "type": "float", "min": 3.0, "max": 9.0, "step": 0.1},
                {"path": "terrace.stucco_floors", "poly_drop": True, "label": "Stucco storeys",
                 "type": "int", "min": 0, "max": 2},
                {"path": "terrace.balcony", "poly_drop": True, "label": "Balcony", "type": "bool"},
                {"path": "terrace.railings", "poly_drop": True, "label": "Railings", "type": "bool"},
                {"path": "terrace.pediment", "poly_drop": True, "label": "Pediment", "type": "bool"},
                {"path": "terrace.bay_windows", "poly_drop": True, "label": "Bay windows", "type": "bool"},
                {"path": "terrace.shopfront", "label": "Shopfront", "type": "bool"},
            ],
        },
        {
            "title": "Facade grammar",
            "fields": [
                {"path": "ribbon.glaze_frac", "label": "Ribbon glazing fraction",
                 "type": "float", "min": 0.3, "max": 0.8, "step": 0.02},
                {"path": "ribbon.mullion_m", "label": "Mullion spacing (m)",
                 "type": "float", "min": 0.8, "max": 2.5, "step": 0.1},
                {"path": "ribbon.spandrel", "label": "Spandrel material",
                 "type": "enum", "choices": ["white", "sign", "stone"]},
                {"path": "arch_windows", "label": "Arched windows", "type": "bool"},
                {"path": "arch_row", "label": "Arch storey",
                 "type": "int", "min": 0, "max": 10},
                {"path": "balustrade", "label": "Balustrade", "type": "bool"},
                {"path": "podium.floors", "label": "Glass podium storeys",
                 "type": "int", "min": 1, "max": 2},
            ],
        },
    ],
    # per-item editors for list sections; value types resolved from the data
    "lists": {
        "masses": {"title": "Masses", "fields": [
            {"key": "floors", "label": "Storeys",
             "type": "int", "min": 1, "max": 100},
            {"key": "facade", "label": "Facade",
             "type": "enum", "choices": ["masonry", "glass"]},
            {"key": "wall", "label": "Wall",
             "type": "enum", "choices": WALLS},
        ]},
        "roof": {"title": "Roof elements", "generic": True},
        "extra_parts": {"title": "Dialect parts",
                        "generic": True},
        "volumes": {"title": "Attached volumes",
                    "generic": True},
    },
    "materials": MATS,
}


def get_schema():
    return SCHEMA
