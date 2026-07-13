"""
Utility module containing mapping dictionaries for habitat attributes.
These mappings define the transformation rules for various habitat attributes
when synchronizing between QGIS and BNG API.
"""

# AiDash Code to Habitat Name mapping (for display in attributes)
AIDASH_CODE_TO_NAME = {
    # Arable and horticulture (a)
    "a1": "Arable field margins cultivated annually",
    "a2": "Arable field margins game bird mix",
    "a3": "Arable field margins pollen and nectar",
    "a4": "Arable field margins tussocky",
    "a5": "Cereal crops",
    "a6": "Winter stubble",
    "a7": "Horticulture",
    "a8": "Intensive orchards",
    "a9": "Non-cereal crops",
    "a10": "Temporary grass and clover leys",
    
    # Grassland (b)
    "b1": "Traditional orchards",
    "b2": "Bracken",
    "b3": "Floodplain Wetland mosaic and CFGM",
    "b4": "Lowland calcareous grassland",
    "b5": "Lowland dry acid grassland",
    "b6": "Lowland meadows",
    "b7": "Modified grassland",
    "b8": "Other lowland acid grassland",
    "b9": "Other neutral grassland",
    "b10": "Tall herb communities (H6430)",
    "b11": "Upland acid grassland",
    "b12": "Upland calcareous grassland",
    "b13": "Upland hay meadows",
    
    # Heathland and scrub (c)
    "c1": "Blackthorn scrub",
    "c2": "Bramble scrub",
    "c3": "Gorse scrub",
    "c4": "Hawthorn scrub",
    "c5": "Hazel scrub",
    "c6": "Lowland Heathland",
    "c7": "Mixed scrub",
    "c8": "Mountain heaths and willow scrub",
    "c9": "Rhododendron scrub",
    "c10": "Dunes with sea buckthorn (H2160)",
    "c11": "Other Sea buckthorn scrub",
    "c12": "Upland Heathland",
    "c31": "Willow Scrub",
    "c32": "Mountain heaths",
    "c33": "Willow scrub",
    
    # Lakes and standing open water (d)
    "d1": "Aquifer fed naturally fluctuating water bodies",
    "d2": "Ornamental lake or pond",
    "d3": "High alkalinity lakes",
    "d4": "Low alkalinity lakes",
    "d5": "Marl Lakes",
    "d6": "Moderate alkalinity lakes",
    "d7": "Peat Lakes",
    "d8": "Ponds (Priority Habitat)",
    "d9": "Ponds (non-priority habitat)",
    "d10": "Reservoirs",
    "d11": "Temporary lakes, ponds and pools (H3170)",
    "d12": "Ornamental lakes",
    "d13": "Ornamental woodland pond",
    "d14": "Ornamental non-woodland pond",
    "d15": "Temporary lakes (H3170)",
    "d16": "Temporary woodland pools and ponds (H3170)",
    "d17": "Temporary non-woodland pools and ponds (H3170)",
    "d18": "Woodland Ponds (Priority Habitat)",
    "d19": "Non-Woodland Ponds (Priority Habitat)",
    "d20": "Woodland Ponds (non-priority habitat)",
    "d21": "Non-Woodland Ponds (non-priority habitat)",
    
    # Sparsely vegetated land (e)
    "e1": "Calaminarian grasslands",
    "e2": "Coastal sand dunes",
    "e3": "Coastal vegetated shingle",
    "e4": "Ruderal/Ephemeral",
    "e5": "Inland rock outcrop and scree habitats",
    "e6": "Limestone pavement",
    "e7": "Maritime cliff and slopes",
    "e8": "Other inland rock and scree",
    "e29": "Tall forbs",
    
    # Urban (f)
    "f1": "Allotments",
    "f2": "Artificial unvegetated, unsealed surface",
    "f3": "Bioswale",
    "f4": "Intensive green roof",
    "f5": "Built linear features",
    "f6": "Cemeteries and churchyards",
    "f7": "Developed land; sealed surface",
    "f8": "Other green roof",
    "f11": "Ground level planters",
    "f12": "Biodiverse green roof",
    "f13": "Introduced shrub",
    "f14": "Open Mosaic Habitats on Previously Developed Land",
    "f15": "Rain garden",
    "f16": "Actively worked sand pit quarry or open cast mine",
    "f18": "Sustainable drainage system",
    "f19": "Unvegetated garden",
    "f20": "Vacant or derelict land",
    "f21": "Vegetated garden",
    "f25": "Bare ground",
    
    # Wetland (g)
    "g1": "Blanket bog",
    "g2": "Depressions on Peat substrates (H7150)",
    "g3": "Fens (upland and lowland)",
    "g3i": "Fens:Lowland Fens",
    "g4": "Lowland raised bog",
    "g5": "Oceanic Valley Mire[1] (D2.1)",
    "g6": "Purple moor grass and rush pastures",
    "g7": "Reedbeds",
    "g8": "Transition mires and quaking bogs (H7140)",
    
    # Woodland and forest (h)
    "h1": "Felled",
    "h1i": "Felled: Ancient Woodland",
    "h2": "Lowland beech and yew woodland",
    "h2i": "Lowland beech and yew woodland: Ancient Woodland",
    "h3": "Lowland mixed deciduous woodland",
    "h3i": "Lowland mixed deciduous woodland: Ancient Woodland",
    "h4": "Native pine woodlands",
    "h4i": "Native pine woodlands: Ancient Woodland",
    "h5": "Other coniferous woodland",
    "h5i": "Other coniferous woodland: Ancient Woodland",
    "h6": "Other Scot's Pine woodland",
    "h6i": "Other Scot's Pine woodland: Ancient Woodland",
    "h7": "Other woodland; broadleaved",
    "h7i": "Other woodland; broadleaved: Ancient Woodland",
    "h8": "Other woodland; mixed",
    "h8i": "Other woodland; mixed: Ancient Woodland",
    "h9": "Upland birchwoods",
    "h9i": "Upland birchwoods: Ancient Woodland",
    "h10": "Upland mixed ashwoods",
    "h10i": "Upland mixed ashwoods: Ancient Woodland",
    "h11": "Upland oakwood",
    "h11i": "Upland oakwood: Ancient Woodland",
    "h12": "Wet woodland",
    "h12i": "Wet woodland: Ancient Woodland",
    "h13": "Wood-pasture and parkland",
    "h13i": "Wood-pasture and parkland: Ancient Woodland",
    
    # Coastal lagoons (i)
    "i1": "Coastal lagoons",
    
    # Rocky shore (j)
    "j1": "High energy littoral rock",
    "j2": "High energy littoral rock - on peat, clay or chalk",
    "j3": "Moderate energy littoral rock",
    "j4": "Moderate energy littoral rock - on peat, clay or chalk",
    "j5": "Low energy littoral rock",
    "j6": "Low energy littoral rock - on peat, clay or chalk",
    "j7": "Features of littoral rock",
    "j8": "Features of littoral rock - on peat, clay or chalk",
    
    # Saltmarsh (k)
    "k1": "Saltmarshes and saline reedbeds",
    "k2": "Artificial saltmarshes and saline reedbeds",
    "k3": "Saltmarshes and saline reedbeds: Spartina Saltmarsh Swards",
    "k4": "Saltmarshes and saline reedbeds: Mediterranean Saltmarsh Swards",
    
    # Intertidal sediment (l)
    "l1": "Littoral coarse sediment",
    "l2": "Littoral mud",
    "l3": "Littoral mixed sediments",
    "l4": "Littoral seagrass",
    "l5": "Littoral seagrass on peat, clay or chalk",
    "l6": "Littoral biogenic reefs - Mussels",
    "l7": "Littoral biogenic reefs - Sabellaria",
    "l8": "Features of littoral sediment",
    "l9": "Artificial littoral coarse sediment",
    "l10": "Artificial littoral mud",
    "l11": "Artificial littoral sand",
    "l12": "Artificial littoral muddy sand",
    "l13": "Artificial littoral mixed sediments",
    "l14": "Artificial littoral seagrass",
    "l15": "Artificial littoral biogenic reefs",
    "l16": "Littoral sand",
    "l17": "Littoral muddy sand",
    
    # Artificial hard structures (m)
    "m1": "Artificial hard structures",
    "m2": "Artificial features of hard structures",
    "m3": "Artificial hard structures with Integrated Greening of Grey Infrastructure (IGGI)",
    
    # Hedgerows and lines of trees (n)
    "n1": "Species-rich native hedgerow with trees - associated with bank or ditch",
    "n2": "Species-rich native hedgerow with trees",
    "n3": "Species-rich native hedgerow - associated with bank or ditch",
    "n4": "Native hedgerow with trees - associated with bank or ditch",
    "n5": "Species-rich native hedgerow",
    "n6": "Native hedgerow - associated with bank or ditch",
    "n7": "Native hedgerow with trees",
    "n8": "Ecologically valuable line of trees",
    "n9": "Ecologically valuable Line of trees - associated with bank or ditch",
    "n10": "Native hedgerow",
    "n11": "Line of trees",
    "n12": "Line of trees - associated with bank or ditch",
    "n13": "Non-native and ornamental hedgerow",
    
    # Rivers and streams (o)
    "o1": "Priority Habitat",
    "o2": "Other Rivers and Streams",
    "o3": "Ditches",
    "o4": "Canals",
    "o5": "Culvert",
    
    # Watercourse footprint (q)
    "q1": "Watercourse footprint",
    
    # Individual trees (r)
    "r1": "Urban Tree",
    "r1i": "Urban Tree: Ancient and Veteran Trees",
    "r2": "Rural Tree",
    "r2i": "Rural Tree: Ancient and Veteran Trees",
    
    # Sub-tidal (s)
    "s1": "Sub-tidal footprint",
}

# Reverse mapping: Name to Code (for lookups from UI)
AIDASH_NAME_TO_CODE = {v: k for k, v in AIDASH_CODE_TO_NAME.items()}

# Mapping for habitat condition values - format: "DisplayName (code)": "code"
CONDITION_MAP = {
    "Good (good)": "good",
    "Fairly Good (fairly good)": "fairly good",
    "Moderate (moderate)": "moderate",
    "Fairly Poor (fairly poor)": "fairly poor",
    "Poor (poor)": "poor",
    "N/A - Other (NA - other)": "NA - other",
    "Condition Assessment N/A (condition assessment NA)": "condition assessment NA"
}

# Mapping for strategic significance values - format: "DisplayName (code)": "code"
STRATEGIC_SIGNIFICANCE_MAP = {
    "Low (low)": "low",
    "Medium (medium)": "medium",
    "High (high)": "high"
}

# Mapping for distinctiveness values - format: "DisplayName (code)": "code"
DISTINCTIVENESS_MAP = {
    "Very Low (very low)": "very low",
    "Low (low)": "low",
    "Medium (medium)": "medium",
    "High (high)": "high",
    "Very High (very_high)": "very_high"
}

# Mapping for watercourse encroachment values - format: "DisplayName (code)": "code"
WATERCOURSE_ENCROACHMENT_MAP = {
    "Major (major)": "major",
    "Minor (minor)": "minor",
    "No Encroachment (no_encroachment)": "no_encroachment"
}

# Mapping for watercourse and riparian encroachment values - format: "DisplayName (code)": "code"
WATERCOURSE_AND_RIPARIAN_ENCROACHMENT_MAP = {
    "Major/Major (major-major)": "major-major",
    "Major/Moderate (major-moderate)": "major-moderate",
    "Major/Minor (major-minor)": "major-minor",
    "Major/No Encroachment (major-no_encroachment)": "major-no_encroachment",
    "Moderate/Moderate (moderate-moderate)": "moderate-moderate",
}

# Mapping for riparian encroachment values - format: "DisplayName (code)": "code"
RIPARIAN_ENCROACHMENT_MAP = {
    "Major/Major (major-major)": "major-major",
    "Major/Moderate (major-moderate)": "major-moderate",
    "Major/Minor (major-minor)": "major-minor",
    "Major/No Encroachment (major-no_encroachment)": "major-no_encroachment",
    "Moderate/Moderate (moderate-moderate)": "moderate-moderate",
    "Moderate/Minor (moderate-minor)": "moderate-minor",
    "Moderate/No Encroachment (moderate-no_encroachment)": "moderate-no_encroachment",
    "Minor/Minor (minor-minor)": "minor-minor",
    "Minor/No Encroachment (minor-no_encroachment)": "minor-no_encroachment",
    "No Encroachment/No Encroachment (no_encroachment-no_encroachment)": "no_encroachment-no_encroachment"
}

# Mapping for tree size values - format: "DisplayName (code)": "code"
TREE_SIZE_MAP = {
    "Small (small)": "small",
    "Medium (medium)": "medium",
    "Large (large)": "large",
    "Very Large (very_large)": "very_large"
}

# Mapping for Tree AiDash codes (trees only) - format: "CodeName (code)": "code"
TREE_AIDASHCODE_MAP = {
    "R1 - Urban Tree (r1)": "r1",
    "R1i - Urban Tree Irreplaceable (r1i)": "r1i",
    "R2 - Rural Tree (r2)": "r2",
    "R2i - Rural Tree Irreplaceable (r2i)": "r2i",
    "R3 - Woodland Tree (r3)": "r3",
    "R4 - Traditional Orchard Tree (r4)": "r4"
}

# Mapping for planar AiDash codes (self-mapped)
PLANAR_AIDASHCODE_MAP = {
    "a1": "a1", "a10": "a10", "a11": "a11", "a12": "a12", "a13": "a13", "a14": "a14",
    "a15": "a15", "a16": "a16", "a17": "a17", "a18": "a18", "a19": "a19", "a2": "a2",
    "a20": "a20", "a21": "a21", "a22": "a22", "a23": "a23", "a24": "a24", "a3": "a3",
    "a4": "a4", "a5": "a5", "a6": "a6", "a7": "a7", "a8": "a8", "a9": "a9",
    "b1": "b1", "b10": "b10", "b11": "b11", "b12": "b12", "b13": "b13", "b14": "b14",
    "b15": "b15", "b16": "b16", "b17": "b17", "b18": "b18", "b19": "b19", "b2": "b2",
    "b20": "b20", "b21": "b21", "b22": "b22", "b23": "b23", "b24": "b24", "b25": "b25",
    "b26": "b26", "b27": "b27", "b28": "b28", "b29": "b29", "b3": "b3", "b30": "b30",
    "b31": "b31", "b4": "b4", "b5": "b5", "b6": "b6", "b7": "b7", "b8": "b8", "b9": "b9",
    "c1": "c1", "c10": "c10", "c11": "c11", "c12": "c12", "c13": "c13", "c14": "c14",
    "c15": "c15", "c16": "c16", "c17": "c17", "c18": "c18", "c19": "c19", "c2": "c2",
    "c20": "c20", "c21": "c21", "c25": "c25", "c26": "c26", "c27": "c27", "c28": "c28",
    "c29": "c29", "c3": "c3", "c30": "c30", "c31": "c31", "c32": "c32", "c33": "c33",
    "c4": "c4", "c5": "c5", "c6": "c6", "c7": "c7", "c8": "c8", "c9": "c9",
    "d1": "d1", "d10": "d10", "d11": "d11", "d12": "d12", "d13": "d13", "d14": "d14",
    "d15": "d15", "d16": "d16", "d17": "d17", "d18": "d18", "d19": "d19", "d2": "d2",
    "d20": "d20", "d21": "d21", "d3": "d3", "d4": "d4", "d5": "d5", "d6": "d6",
    "d7": "d7", "d8": "d8", "d9": "d9",
    "e1": "e1", "e10": "e10", "e11": "e11", "e12": "e12", "e13": "e13", "e14": "e14",
    "e15": "e15", "e16": "e16", "e17": "e17", "e18": "e18", "e19": "e19", "e2": "e2",
    "e20": "e20", "e21": "e21", "e22": "e22", "e23": "e23", "e24": "e24", "e25": "e25",
    "e26": "e26", "e27": "e27", "e28": "e28", "e29": "e29", "e3": "e3", "e4": "e4",
    "e5": "e5", "e6": "e6", "e7": "e7", "e8": "e8", "e9": "e9",
    "f1": "f1", "f11": "f11", "f12": "f12", "f13": "f13", "f14": "f14",
    "f15": "f15", "f16": "f16", "f18": "f18", "f19": "f19", "f2": "f2", "f20": "f20",
    "f21": "f21", "f24": "f24", "f25": "f25", "f3": "f3", "f4": "f4", "f5": "f5",
    "f6": "f6", "f7": "f7", "f8": "f8",
    "g1": "g1", "g10": "g10", "g11": "g11", "g12": "g12", "g13": "g13", "g14": "g14",
    "g16": "g16", "g17": "g17", "g18": "g18", "g19": "g19", "g2": "g2", "g20": "g20",
    "g21": "g21", "g22": "g22", "g23": "g23", "g24": "g24", "g25": "g25", "g26": "g26",
    "g3": "g3", "g3i": "g3i", "g4": "g4", "g5": "g5", "g6": "g6", "g7": "g7", "g8": "g8",
    "h1": "h1", "h10": "h10", "h10i": "h10i", "h11": "h11", "h11i": "h11i", "h12": "h12",
    "h12i": "h12i", "h13": "h13", "h13i": "h13i", "h15": "h15", "h15i": "h15i", "h16": "h16",
    "h16i": "h16i", "h17": "h17", "h17i": "h17i", "h18": "h18", "h18i": "h18i", "h19": "h19",
    "h19i": "h19i", "h1i": "h1i", "h2": "h2", "h20": "h20", "h20i": "h20i", "h21": "h21",
    "h21i": "h21i", "h22": "h22", "h22i": "h22i", "h23": "h23", "h23i": "h23i", "h24": "h24",
    "h24i": "h24i", "h25": "h25", "h25i": "h25i", "h26": "h26", "h26i": "h26i", "h28": "h28",
    "h28i": "h28i", "h29": "h29", "h29i": "h29i", "h2i": "h2i", "h3": "h3", "h30": "h30",
    "h30i": "h30i", "h31": "h31", "h31i": "h31i", "h32": "h32", "h32i": "h32i", "h3i": "h3i",
    "h4": "h4", "h4i": "h4i", "h5": "h5", "h5i": "h5i", "h6": "h6", "h6i": "h6i", "h7": "h7",
    "h7i": "h7i", "h8": "h8", "h8i": "h8i", "h9": "h9", "h9i": "h9i",
    "i1": "i1",
    "j1": "j1", "j2": "j2", "j3": "j3", "j4": "j4", "j5": "j5", "j6": "j6", "j7": "j7", "j8": "j8",
    "k1": "k1", "k2": "k2", "k3": "k3", "k4": "k4",
    "l1": "l1", "l10": "l10", "l11": "l11", "l12": "l12", "l13": "l13", "l14": "l14", "l15": "l15",
    "l16": "l16", "l17": "l17", "l2": "l2", "l3": "l3", "l4": "l4", "l5": "l5", "l6": "l6",
    "l7": "l7", "l8": "l8", "l9": "l9",
    "m1": "m1", "m2": "m2", "m3": "m3",
    "n15": "n15",
    "o10": "o10", "o11": "o11", "o12": "o12", "o13": "o13", "o14": "o14", "o15": "o15",
    "o17": "o17", "o18": "o18", "o7": "o7", "o8": "o8",
    "p1": "p1", "p10": "p10", "p11": "p11", "p12": "p12", "p13": "p13", "p14": "p14",
    "p15": "p15", "p16": "p16", "p17": "p17", "p18": "p18", "p19": "p19", "p2": "p2",
    "p21": "p21", "p22": "p22", "p3": "p3", "p4": "p4", "p5": "p5", "p6": "p6", "p7": "p7",
    "p8": "p8",
    "q1": "q1",
    "s1": "s1"
}

# Mapping for Watercourse/Hedgerow AiDash codes (self-mapped)
WATERCOURSE_HEDGEROW_AIDASHCODE_MAP = {
    "n1": "n1", "n10": "n10", "n11": "n11", "n12": "n12", "n13": "n13", "n14": "n14",
    "n2": "n2", "n3": "n3", "n4": "n4", "n5": "n5", "n6": "n6", "n7": "n7",
    "n8": "n8", "n9": "n9",
    "o1": "o1", "o16": "o16", "o2": "o2", "o3": "o3", "o4": "o4", "o5": "o5"
}



def map_value(value, mapping_dict, default=None):
    """
    Maps a value using the provided mapping dictionary.
    
    Args:
        value: The value to map
        mapping_dict: Dictionary containing the mapping rules
        default: Default value to return if no mapping is found
        
    Returns:
        Mapped value if found, default value otherwise
    """
    if value is None:
        return default
    
    value_str = str(value).strip()
        
    # Try exact match first (case-sensitive)
    mapped_value = mapping_dict.get(value_str, None)
    if mapped_value:
        return mapped_value
    
    # If the supplied value already matches one of the mapping values (code form), accept it.
    lower_value = value_str.lower()
    for mapped in mapping_dict.values():
        if isinstance(mapped, str) and mapped.lower() == lower_value:
            return mapped
        
    # Try case-insensitive key match
    for k, v in mapping_dict.items():
        if isinstance(k, str) and k.lower() == lower_value:
            return v
            
    # Log if no match found
    from qgis.core import QgsMessageLog
    QgsMessageLog.logMessage(f"No mapping found for value: {value_str}", "BNGAI Plugin", level=2)
    return default if default is not None else value_str


def get_habitat_name(code, default=None):
    """
    Get the habitat name for an AiDash code.
    
    Args:
        code: The AiDash code (e.g., 'a1', 'b7')
        default: Default value if code not found
        
    Returns:
        Habitat name string or default
    """
    if code is None:
        return default
    return AIDASH_CODE_TO_NAME.get(str(code).strip().lower(), default or code)


def get_habitat_code(name, default=None):
    """
    Get the AiDash code for a habitat name.
    
    Args:
        name: The habitat name (e.g., 'Modified grassland')
        default: Default value if name not found
        
    Returns:
        AiDash code string or default
    """
    if name is None:
        return default
    return AIDASH_NAME_TO_CODE.get(str(name).strip(), default or name)


def format_habitat_display(code):
    """
    Format a habitat code for display as 'code - name'.
    
    Args:
        code: The AiDash code
        
    Returns:
        Formatted string like 'a1 - Arable field margins cultivated annually'
    """
    if code is None:
        return ""
    code_str = str(code).strip().lower()
    name = AIDASH_CODE_TO_NAME.get(code_str)
    if name:
        return f"{code_str} - {name}"
    return code_str