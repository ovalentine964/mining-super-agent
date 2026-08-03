"""
Mineral dataset constants — 20 mineral classes with look-alike pairs.
"""

MINERAL_CLASSES = [
    "gold", "copper", "pyrite", "chalcopyrite", "quartz",
    "feldspar", "mica", "calcite", "dolomite", "gypsum",
    "magnetite", "hematite", "limonite", "galena", "sphalerite",
    "fluorite", "tourmaline", "garnet", "olivine", "biotite",
]

CLASS_TO_IDX = {name: idx for idx, name in enumerate(MINERAL_CLASSES)}
IDX_TO_CLASS = {idx: name for name, idx in CLASS_TO_IDX.items()}

# Minerals commonly confused with each other
LOOK_ALIKE_PAIRS = [
    ("gold", "pyrite"),
    ("gold", "chalcopyrite"),
    ("gold", "copper"),
    ("pyrite", "chalcopyrite"),
    ("calcite", "dolomite"),
    ("magnetite", "hematite"),
    ("muscovite", "biotite"),
    ("gypsum", "calcite"),
]

# Economic minerals that require expert review
ECONOMIC_MINERALS = {"gold", "copper", "galena", "sphalerite"}
