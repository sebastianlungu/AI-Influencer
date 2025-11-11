#!/usr/bin/env python3
"""Generate large variety and scene banks with dedupe + reporting."""

from __future__ import annotations

import json
import math
import random
from collections import defaultdict, deque
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Sequence, Tuple

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_GLOBAL = BASE_DIR / "app" / "data" / "variety_bank.json"
LOCATIONS_DIR = BASE_DIR / "app" / "data" / "locations"

RNG = random.Random(20250215)

TARGET_PER_SLOT = 1000
TARGET_PER_LOCATION = 1000
BATCH_SIZE_SLOT = 220
BATCH_SIZE_SCENE = 240
MAX_EXPANSION_ROUNDS = 3  # beyond initial round
AGENTS = 5

SUPPRESSION_LIMITS = {
    "golden hour": 0,
    "hero pose": 0,
    "direct flash": 0,
    "studio white": 0,
    "soft focus": 0,
    "clean backdrop": 0,
    "perfect symmetry": 0,
    "hard shadow": 0,
    "flat lay": 0,
    "frozen still": 0,
}

suppressed_counts = {k: 0 for k in SUPPRESSION_LIMITS}
bigram_occurrences = {k: 0 for k in SUPPRESSION_LIMITS}

POLICY_TERMS = {"lingerie", "boudoir", "nudity", "fetish"}
policy_rejections: Dict[str, List[str]] = defaultdict(list)

batch_dedupe_log: Dict[str, List[int]] = defaultdict(list)
expansion_flags: Dict[str, int] = defaultdict(int)
suppressed_examples: Dict[str, List[str]] = defaultdict(list)
dedupe_examples: Dict[str, List[str]] = defaultdict(list)


def normalize(text: str) -> str:
    return " ".join(text.strip().split())


def within_length(text: str) -> bool:
    count = len(text.split())
    return 5 <= count <= 14


def enforce_bigrams(slot: str, text: str) -> bool:
    words = text.lower().split()
    seen = set()
    for i in range(len(words) - 1):
        bg = f"{words[i]} {words[i+1]}"
        if bg in SUPPRESSION_LIMITS:
            if bigram_occurrences[bg] >= SUPPRESSION_LIMITS[bg]:
                suppressed_counts[bg] += 1
                if len(suppressed_examples[bg]) < 3:
                    suppressed_examples[bg].append(text)
                return False
            seen.add(bg)
    for bg in seen:
        bigram_occurrences[bg] += 1
    return True


def enforce_policy(slot: str, text: str) -> bool:
    lower = text.lower()
    for term in POLICY_TERMS:
        if term in lower:
            if len(policy_rejections[slot]) < 5:
                policy_rejections[slot].append(text)
            return False
    return True


def determine_weight(text: str) -> float:
    lower = text.lower()
    rare_markers = {
        "holographic": 0.6,
        "volcanic": 0.7,
        "acid": 0.8,
        "monsoon": 0.85,
        "nocturne": 0.85,
        "typhoon": 0.8,
        "aurora": 0.7,
        "neon": 0.9,
        "carbon fiber": 0.85,
        "mirage": 0.75,
        "bio-lum": 0.65,
    }
    for marker, weight in rare_markers.items():
        if marker in lower:
            return weight
    return 1.0


def process_candidate(slot: str, text: str) -> str | None:
    cleaned = normalize(text)
    if not cleaned or not within_length(cleaned):
        return None
    if not enforce_bigrams(slot, cleaned):
        return None
    if not enforce_policy(slot, cleaned):
        return None
    return cleaned


def run_batches(
    slot: str,
    target: int,
    batch_size: int,
    generator: Callable[[random.Random, int], List[Tuple[str, float]]],
) -> List[Dict[str, float]]:
    items: List[Dict[str, float]] = []
    seen = set()
    total_rounds = 0
    while len(items) < target and total_rounds <= MAX_EXPANSION_ROUNDS:
        total_rounds += 1
        for agent in range(AGENTS):
            generated = generator(RNG, batch_size)
            dedup_removed = 0
            for text, weight in generated:
                processed = process_candidate(slot, text)
                if not processed:
                    continue
                key = processed.lower()
                if key in seen:
                    dedup_removed += 1
                    if len(dedupe_examples[slot]) < 5:
                        dedupe_examples[slot].append(processed)
                    continue
                items.append({"text": processed, "weight": weight})
                seen.add(key)
                if len(items) >= target:
                    break
            batch_label = f"round{total_rounds}_batch{agent+1}"
            batch_dedupe_log[f"{slot}:{batch_label}"].append(dedup_removed)
            if len(items) >= target:
                break
        if len(items) >= target:
            break
        if len(items) < 950 and total_rounds > MAX_EXPANSION_ROUNDS:
            raise RuntimeError(f"{slot} still short after {MAX_EXPANSION_ROUNDS} expansions")
    if len(items) < target:
        raise RuntimeError(f"{slot} shortfall: {len(items)}")
    expansion_flags[slot] = max(0, total_rounds - 1)
    return items[:target]


# Component pools per slot ----------------------------------------------------

TOP_COLORS = [
    "orchid gradient",
    "caramel smoked",
    "electric-blue piped",
    "midnight teal",
    "charcoal marl",
    "bone white",
    "onyx mesh",
    "sage mist",
    "molten copper",
    "polar silver",
    "graphite haze",
    "rosin green",
    "storm navy",
    "chalk blush",
    "plum eclipse",
    "amber rust",
    "pearl opal",
    "ice lavender",
    "dusky mauve",
    "obsidian glaze",
    "deep coral",
    "sandstone fade",
    "cool taupe",
    "cobalt frost",
    "saffron glow",
]

TOP_MATERIALS = [
    "sculpt-knit",
    "wet-look lycra",
    "ribbed modal",
    "aerated neoprene",
    "buttery jersey",
    "compression satin",
    "eco-suede",
    "micro waffle",
    "openwork mesh",
    "piqué shell",
    "thermal jersey",
    "cupro blend",
    "softshell weave",
    "herringbone knit",
    "matte scuba",
    "silken tricot",
    "double-face crepe",
    "tactile ponte",
    "textured jacquard",
    "lingerie mesh",
]

TOP_SILHOUETTES = [
    "longline sports bra",
    "wrap crop top",
    "zip-front bodysuit",
    "corset-hem tank",
    "crossover bralette",
    "asym cutout tee",
    "structured halter",
    "layered mockneck",
    "cap-sleeve crop",
    "minimal racer",
    "panelled leotard",
    "front-knot blouse",
    "spine-slit tunic",
    "double-strap cami",
    "pleated peplum",
    "balloon-sleeve crop",
    "vented polo",
    "shrug hybrid",
    "hooded crop",
    "bolero tee",
]

TOP_DETAILS = [
    "micro ruching",
    "laser-cut vents",
    "mesh insets",
    "bonded seams",
    "invisible zipper",
    "sheer laddering",
    "hook hardware",
    "embroidered piping",
    "thumb loops",
    "contrast binding",
    "pleat channels",
    "sculpted boning",
    "drawcord cinch",
    "angled placket",
    "rib collar",
    "lace-up spine",
]

TOP_ACCENTS = [
    "orchid piping",
    "caramel binding",
    "electric-blue straps",
    "obsidian trims",
    "silver microbeads",
    "matte black elastics",
    "amber toggles",
    "opal taping",
    "plush edging",
    "carbon fiber snaps",
]


def generate_wardrobe_top(rng: random.Random, batch_size: int) -> List[Tuple[str, float]]:
    templates = [
        lambda c: f"{c['color']} {c['material']} {c['silhouette']} with {c['detail']}",
        lambda c: f"{c['material']} {c['silhouette']} trimmed in {c['accent']}",
        lambda c: f"structured {c['silhouette']} in {c['color']} {c['material']} featuring {c['detail']}",
        lambda c: f"{c['color']} {c['silhouette']} showing {c['detail']} and {c['accent']}",
    ]
    items = []
    attempts = 0
    while len(items) < batch_size and attempts < batch_size * 25:
        attempts += 1
        comps = {
            "color": rng.choice(TOP_COLORS),
            "material": rng.choice(TOP_MATERIALS),
            "silhouette": rng.choice(TOP_SILHOUETTES),
            "detail": rng.choice(TOP_DETAILS),
            "accent": rng.choice(TOP_ACCENTS),
        }
        text = rng.choice(templates)(comps)
        weight = determine_weight(text)
        items.append((text, weight))
    if len(items) < batch_size:
        raise RuntimeError("wardrobe_top generation underflow")
    return items


BOTTOM_COLORS = [
    "orchid smoke",
    "caramel stone",
    "electric-blue paneled",
    "graphite mist",
    "deep navy",
    "umber fade",
    "sand dune",
    "obsidian washed",
    "storm sage",
    "copper oxide",
    "ice pebble",
    "slate violet",
    "charcoal ink",
    "teal oxide",
    "amber clay",
    "pearl dusk",
    "burnt sienna",
    "ash rose",
    "noir marl",
    "pale oat",
]

BOTTOM_SILHOUETTES = [
    "high-rise leggings",
    "split-hem trousers",
    "pleated tennis skirt",
    "bike shorts",
    "wrap skort",
    "cargo joggers",
    "satin track pants",
    "sculpted flare pants",
    "paperbag shorts",
    "seamed midi skirt",
    "wrap palazzo pants",
    "pleated culottes",
    "technical capris",
    "belted mini skirt",
    "thermal tights",
    "draped sarong skirt",
    "panel joggers",
    "vented flare leggings",
    "kick-pleat skirt",
    "zip-off cargos",
]

BOTTOM_DETAILS = [
    "air vents",
    "zip cuffs",
    "ankle stirrups",
    "laser slashes",
    "panel mapping",
    "double waistband",
    "cargo loops",
    "pliable pleats",
    "micro piping",
    "contrast godets",
    "drawstring cinch",
    "bonded darts",
    "side snaps",
    "mesh calves",
    "wrap ties",
    "knife pleats",
]

BOTTOM_ACCENTS = [
    "orchid taping",
    "caramel piping",
    "electric-blue bar tacks",
    "mirrored snaps",
    "oxidized zip",
    "gunmetal rivets",
    "amber toggles",
    "matte belt",
    "contrast waistband",
]


def generate_wardrobe_bottom(rng: random.Random, batch_size: int) -> List[Tuple[str, float]]:
    templates = [
        lambda c: f"{c['color']} {c['silhouette']} with {c['detail']}",
        lambda c: f"{c['silhouette']} in {c['material']} featuring {c['accent']}",
        lambda c: f"{c['color']} {c['silhouette']} showing {c['detail']} and {c['accent']}",
    ]
    materials = [
        "compression jersey",
        "buttery scuba",
        "crisp twill",
        "matte satin",
        "lightweight ripstop",
        "fluid cupro",
        "softshell",
        "mesh overlay",
        "ribbed ponte",
        "double weave",
    ]
    items = []
    attempts = 0
    while len(items) < batch_size and attempts < batch_size * 25:
        attempts += 1
        comps = {
            "color": rng.choice(BOTTOM_COLORS),
            "silhouette": rng.choice(BOTTOM_SILHOUETTES),
            "detail": rng.choice(BOTTOM_DETAILS),
            "accent": rng.choice(BOTTOM_ACCENTS),
            "material": rng.choice(materials),
        }
        template = rng.choice(templates)
        text = template(comps)
        weight = determine_weight(text)
        items.append((text, weight))
    if len(items) < batch_size:
        raise RuntimeError("wardrobe_bottom generation underflow")
    return items


ACCESSORY_BASE = [
    "wrist wraps",
    "ankle weights",
    "visor",
    "headband",
    "fingerless gloves",
    "arm band",
    "belt bag",
    "anklet",
    "neck scarf",
    "hydration cuff",
    "ear cuff",
    "hair stick",
    "waist chain",
    "wrap belt",
    "thigh holster",
    "calf sleeve",
    "sports watch",
    "torque bracelet",
    "drop earrings",
    "shoulder guard",
    "lifting straps",
    "sleek backpack",
]

ACCESSORY_DETAILS = [
    "matte clasps",
    "lacquer edges",
    "woven cords",
    "gel padding",
    "carved links",
    "lattice engraving",
    "micro quilting",
    "contrast piping",
    "elastic lacing",
    "resin buckles",
    "split metalwork",
    "floating pearls",
    "utility loops",
    "braided leather",
    "carbon plate",
    "ridge emboss",
]

ACCESSORY_COLORS = [
    "orchid satin",
    "caramel suede",
    "electric-blue rubber",
    "graphite leather",
    "ivory acrylic",
    "obsidian resin",
    "gunmetal mesh",
    "smoky quartz",
    "opal lucite",
    "amber glass",
    "pearl enamel",
    "storm grey",
]


def generate_accessories(rng: random.Random, batch_size: int) -> List[Tuple[str, float]]:
    contexts = [
        "subtle sheen",
        "contrast stitch",
        "magnetic closure",
        "vented comfort",
        "sleek silhouette",
        "gel grip",
        "low-profile hardware",
        "braided tether",
        "arched lines",
        "shadow quilting",
    ]
    templates = [
        lambda c: f"{c['color']} {c['item']} with {c['detail']}",
        lambda c: f"{c['item']} featuring {c['color']} panels and {c['context']}",
        lambda c: f"{c['color']} {c['item']} showing {c['context']}",
    ]
    items = []
    attempts = 0
    while len(items) < batch_size and attempts < batch_size * 20:
        attempts += 1
        comps = {
            "color": rng.choice(ACCESSORY_COLORS),
            "item": rng.choice(ACCESSORY_BASE),
            "detail": rng.choice(ACCESSORY_DETAILS),
            "context": rng.choice(contexts),
        }
        text = rng.choice(templates)(comps)
        weight = determine_weight(text)
        items.append((text, weight))
    if len(items) < batch_size:
        raise RuntimeError("accessories generation underflow")
    return items


LIGHTING_KEYS = [
    "orchid gelled rim",
    "caramel bounce",
    "electric-blue kicker",
    "amber spot",
    "moonlit fill",
    "chromed edge",
    "violet strip",
    "sodium vapor wash",
    "polar moonbeam",
    "neon spill",
    "storm lantern glow",
    "mist-diffused key",
    "soft cobalt wrap",
    "copper dome glow",
    "teal haze wash",
    "magenta bloom",
    "direct flash",
]

LIGHTING_ACTIONS = [
    "cutting through rain",
    "skimming muscular contours",
    "ricocheting off wet stone",
    "grazing steel railings",
    "pooling underfoot vapor",
    "glazing cheekbone sheen",
    "feathering across shoulders",
    "backlighting stray strands",
    "layering over temple mist",
    "splitting shadow bands",
    "pinging off mirror tiles",
    "haloing against lacquer panels",
    "glowing through mesh fabric",
    "warming caramel undertones",
    "cooling specular highlights",
    "sequencing with LED rhythm",
    "painting golden hour gradients",
    "etching hard shadow bands",
]

LIGHTING_SUPPORT = [
    "negative fill from matte flags",
    "soft poly bounce",
    "sodium spill controlled by barn doors",
    "feathered scrim diffusion",
    "circular polarizer on key",
    "double diffusion sock",
    "rain haze adding volumetric depth",
    "mirror board accent",
    "silk butterfly overhead",
    "wet pavement reflection",
    "glass block scatter",
    "mist fan drift",
    "lantern practicals behind frame",
    "LED tunnel pulses",
    "laser speckle toned down",
    "candle clusters forward",
    "studio white cyc wash",
]


def generate_lighting(rng: random.Random, batch_size: int) -> List[Tuple[str, float]]:
    templates = [
        lambda c: f"{c['key']} {c['action']} with {c['support']}",
        lambda c: f"{c['key']} shaping profile while {c['support']}",
        lambda c: f"{c['key']} {c['action']} against {c['support']}",
    ]
    items = []
    attempts = 0
    while len(items) < batch_size and attempts < batch_size * 30:
        attempts += 1
        comps = {
            "key": rng.choice(LIGHTING_KEYS),
            "action": rng.choice(LIGHTING_ACTIONS),
            "support": rng.choice(LIGHTING_SUPPORT),
        }
        text = rng.choice(templates)(comps)
        weight = determine_weight(text)
        items.append((text, weight))
    if len(items) < batch_size:
        raise RuntimeError("lighting generation underflow")
    return items


CAMERA_FOCAL = ["24mm", "28mm", "35mm", "40mm", "50mm", "55mm", "65mm", "75mm", "85mm", "105mm"]
CAMERA_APERTURES = ["f/1.4", "f/1.6", "f/1.8", "f/2.0", "f/2.2", "f/2.5", "f/2.8", "f/3.2"]
CAMERA_MOVES = [
    "steadicam drift",
    "shoulder rig sway",
    "slider creep",
    "gimbal float",
    "handheld lockoff",
    "jib rise",
    "dolly push",
    "crane drop",
    "cable cam sweep",
    "monopod lean",
]
CAMERA_MODS = [
    "soft ND stack",
    "polarizer pop",
    "diffusion sock",
    "mist filter",
    "split diopter",
    "matte box flags",
    "anamorphic squeeze",
    "macro tube",
    "tilt-shift plate",
    "stabilized carriage",
    "swing tilt",
    "low-con filter",
]
CAMERA_FOCUS = [
    "buttery falloff on iris",
    "tight face lock",
    "hourglass emphasis",
    "bokeh-laced skyline",
    "satin torso glow",
    "glitter rain streaks",
    "electric signage blur",
    "orchid accessory pop",
    "caramel undertone fidelity",
    "specular shoulder roll",
    "forearm tension detail",
    "curated highlight bloom",
    "soft focus drift",
]


def generate_camera(rng: random.Random, batch_size: int) -> List[Tuple[str, float]]:
    templates = [
        lambda c: f"{c['focal']} prime at {c['aperture']} on {c['move']} with {c['mod']} for {c['focus']}",
        lambda c: f"{c['focal']} lens {c['move']} using {c['mod']} chasing {c['focus']}",
    ]
    items = []
    attempts = 0
    while len(items) < batch_size and attempts < batch_size * 20:
        attempts += 1
        comps = {
            "focal": rng.choice(CAMERA_FOCAL),
            "aperture": rng.choice(CAMERA_APERTURES),
            "move": rng.choice(CAMERA_MOVES),
            "mod": rng.choice(CAMERA_MODS),
            "focus": rng.choice(CAMERA_FOCUS),
        }
        text = rng.choice(templates)(comps)
        weight = determine_weight(text)
        items.append((text, weight))
    if len(items) < batch_size:
        raise RuntimeError("camera generation underflow")
    return items


ANGLE_ALTITUDES = [
    "low",
    "grounded",
    "waist-high",
    "eye-level",
    "elevated",
    "overhead",
    "towering",
    "drone",
    "floating",
    "shoulder-height",
    "flat lay",
]
ANGLE_MOTIONS = [
    "parallax sweep",
    "arc slide",
    "dolly drift",
    "gimbal hover",
    "lockoff",
    "whip-pan settle",
    "crane drop",
    "cable glide",
    "push-in",
    "reverse pull",
    "perfect symmetry hold",
]
ANGLE_REFERENCES = [
    "above obsidian pier tiles",
    "skimming canal rails",
    "through cedar lattice",
    "over chalk cliffs",
    "past neon kanji",
    "across terracotta rooflines",
    "over misted rice paddies",
    "from marble colonnade",
    "over basalt ridge",
    "through palm canopy",
    "over dune crest",
    "through bamboo torii",
    "over copper rooftop",
    "near glass balustrade",
    "through rain-streaked window",
    "clean backdrop sweep",
]


def generate_angle(rng: random.Random, batch_size: int) -> List[Tuple[str, float]]:
    templates = [
        lambda c: f"{c['altitude']} {c['motion']} {c['reference']}",
        lambda c: f"{c['motion']} from {c['reference']} at {c['altitude']} height",
    ]
    items = []
    attempts = 0
    while len(items) < batch_size and attempts < batch_size * 20:
        attempts += 1
        comps = {
            "altitude": rng.choice(ANGLE_ALTITUDES),
            "motion": rng.choice(ANGLE_MOTIONS),
            "reference": rng.choice(ANGLE_REFERENCES),
        }
        text = rng.choice(templates)(comps)
        weight = determine_weight(text)
        items.append((text, weight))
    if len(items) < batch_size:
        raise RuntimeError("angle generation underflow")
    return items


POSE_ACTIONS = [
    "resetting ponytail",
    "tying wrap belt",
    "adjusting glove",
    "rolling shoulder",
    "lifting chin",
    "checking wrist wrap",
    "pinning hood",
    "stretching quad",
    "engaging core twist",
    "floating heel raise",
    "balancing on toe point",
    "smoothing ribbed hem",
    "fingertip grazing jawline",
    "palming thigh seam",
    "hooking thumb into pocket",
    "fastening harness clip",
    "zipping bodysuit",
    "tucking stray wave",
    "pressing palm to sternum",
    "sweeping braid over shoulder",
]

POSE_CONTEXT = [
    "mid-stride",
    "between breaths",
    "above rooftop puddle",
    "beside training rail",
    "under lantern glow",
    "against basalt wall",
    "framed by glass fins",
    "beneath palm shadows",
    "at shoreline spray",
    "within market bustle",
    "on terracotta steps",
    "inside railcar doorway",
    "under vaulted arcade",
    "at helipad edge",
    "within mangrove mist",
    "frozen still moment",
]

POSE_DETAILS = [
    "eyes locked forward",
    "chin dipped slightly",
    "glance over shoulder",
    "soft smile hint",
    "focused brow",
    "steady inhale",
    "cheek catching sparkle",
    "muscles flexed",
    "weight on lead leg",
    "hips angled open",
    "fingers splayed",
    "nails brushing collar",
    "gold cuff catching light",
    "orchid ribbon trailing",
    "electric-blue manicure glinting",
    "hero pose intensity",
]


def generate_pose(rng: random.Random, batch_size: int) -> List[Tuple[str, float]]:
    templates = [
        lambda c: f"{c['action']} {c['context']} with {c['detail']}",
        lambda c: f"{c['action']} while {c['detail']} {c['context']}",
    ]
    items = []
    attempts = 0
    while len(items) < batch_size and attempts < batch_size * 25:
        attempts += 1
        comps = {
            "action": rng.choice(POSE_ACTIONS),
            "context": rng.choice(POSE_CONTEXT),
            "detail": rng.choice(POSE_DETAILS),
        }
        text = rng.choice(templates)(comps)
        weight = determine_weight(text)
        items.append((text, weight))
    if len(items) < batch_size:
        raise RuntimeError("pose generation underflow")
    return items


TWIST_ELEMENTS = [
    "breeze lifting orchid ribbon",
    "rain droplets tracing shoulders",
    "shadow bands from latticework",
    "specular puddles reflecting neon",
    "steam curl from street grate",
    "salt spray misting ankles",
    "lantern ash drifting by",
    "dappled palm light fluttering",
    "passing tram flare",
    "pigeon wing blur",
    "train spark halo",
    "mist fan drift",
    "glitter dust motes",
    "silk scarf caught midair",
    "city screen reflections",
    "candle smoke ribbon",
    "bamboo leaf flickers",
    "snow flurry shimmer",
    "desert heat shimmer",
    "aurora glow echo",
    "fountain spray arcs",
    "hologram reflections pulsing",
    "volcanic plume wisps",
    "lagoon light caustics",
    "orchid confetti swirl",
    "metro wind gust",
    "paper program flutter",
    "laser haze pass",
    "storm cloud shadow",
    "harbor mist ribbon",
    "silica dust glitter",
    "sand drift ribbons",
    "petal storm burst",
    "fjord spray fan",
    "ember sparks rising",
    "mirror shard flare",
    "LED ticker glow",
    "aurora curtain sweep",
    "typhoon mist breath",
    "desert mirage shimmer",
    "stadium light sweep",
    "river droplet halo",
    "market incense plume",
    "tea steam curl",
    "paper fan flutter",
    "metro door gust",
    "snowmelt drip spray",
    "glow plankton sparkle",
    "kite tail streak",
    "saffron powder cloud",
    "subway brake spark",
    "gelled strobe flicker",
    "sun prism flare",
    "canopy shadow ripple",
    "bubble machine drift",
]

TWIST_CONTEXT = [
    "across collarbones",
    "around waistline",
    "behind silhouette",
    "through foreground",
    "hugging calf line",
    "over shoulder",
    "through mirrored wall",
    "around terrace rail",
    "between subject and camera",
    "clinging to hair",
    "rippling over fabric",
    "skimming fingertips",
    "wrapping ankle weights",
    "washing across core",
    "framing gaze",
    "spiraling around thighs",
    "threading past cheekbone",
    "chasing along jawline",
    "skirting heeled foot",
    "looping around wrists",
    "hovering over shoulders",
    "crossing midsection",
    "hugging outer quad",
    "cutting through negative space",
    "braiding through hair",
    "scattering over trapezius",
    "curling near temple",
    "slinking beneath chin",
    "glancing across obliques",
    "falling across scapula",
    "floating near waist cinch",
    "spiraling around hipbone",
    "washing over delts",
    "racing along shin",
    "hugging shoe heel",
    "chasing along spine",
    "wrapping around torso",
    "hovering beside jaw",
    "skipping across cuffs",
    "threading through elbow bend",
    "tracing quadricep line",
    "orbiting glutes",
    "swinging above eyebrow",
    "skimming clavicle",
    "drifting over knee line",
    "crossing chest plane",
    "flickering near ankle strap",
    "slicing across silhouette edge",
    "curving around lat line",
    "hugging calf compression",
    "climbing past shoulder seam",
    "painting across lower back",
    "folding over ribcage",
    "floating near neckline",
]


def generate_twist(rng: random.Random, batch_size: int) -> List[Tuple[str, float]]:
    templates = [
        lambda c: f"{c['element']} {c['context']}",
        lambda c: f"{c['element']} weaving {c['context']}",
    ]
    items = []
    attempts = 0
    while len(items) < batch_size and attempts < batch_size * 20:
        attempts += 1
        comps = {
            "element": rng.choice(TWIST_ELEMENTS),
            "context": rng.choice(TWIST_CONTEXT),
        }
        text = rng.choice(templates)(comps)
        weight = determine_weight(text)
        items.append((text, weight))
    if len(items) < batch_size:
        raise RuntimeError("twist generation underflow")
    return items


NEGATIVE_LIST = ["doll-like", "uncanny face", "plastic skin", "text", "logos", "extra digits"]


# Location components ---------------------------------------------------------

def build_location_components() -> Dict[str, Dict[str, List[str]]]:
    return {
        "japan": {
            "descriptors": [
                "neon-soaked",
                "misty",
                "cedar-lined",
                "rain-glossed",
                "paper-lantern",
                "shoji-framed",
                "bamboo-shadowed",
                "moonlit",
                "dusk-toned",
                "stormlit",
                "powder-snow",
                "summer-heat",
                "coastal-breeze",
                "glowing-amber",
                "orchid-accented",
                "charcoal-stone",
                "copper-roofed",
                "sakura-drifted",
                "ink-brushed",
                "plaza-lit",
            ],
            "settings": [
                "shoji alley",
                "bamboo skywalk",
                "onsen deck",
                "metro platform",
                "tea house courtyard",
                "coastal torii causeway",
                "lantern market lane",
                "glass monorail bridge",
                "riverwalk tatami landing",
                "rooftop zen garden",
                "underground arcade",
                "rain tunnel crossing",
                "elevated expressway shoulder",
                "stone stair switchback",
                "shinkansen concourse",
                "harbor boardwalk",
                "kumiko lobby",
                "volcanic sand path",
                "neon rooftop dojo",
                "plum orchard row",
            ],
            "foregrounds": [
                "orchid noren sway",
                "glowing vending glass",
                "paper umbrella stacks",
                "condensation rising",
                "polished stone lanterns",
                "mirror puddles",
                "bamboo shadows",
                "fiber optic railings",
                "luminous kanji signage",
                "amber taiko drums",
                "steam wisps",
                "holographic ads",
                "floating petals",
                "woven basket stalls",
                "ferried light trails",
                "charcoal gravel sprays",
                "bike streaks",
                "silk banners",
                "ceramic wind chimes",
                "koi pond sparkle",
            ],
            "ambience": [
                "blue-hour glow",
                "pre-dawn hush",
                "typhoon break calm",
                "winter noon clarity",
                "humid midnight pulse",
                "lantern-lit dusk",
                "sodium vapor hum",
                "fog-softened sunrise",
                "storm-cleared sky",
                "festival neon rhythm",
                "monorail shadow bands",
                "cicada-laced afternoon",
                "rain chorus echo",
                "moonbow shimmer",
                "amber heater warmth",
            ],
            "accessories": [
                "lacquered kanzashi hairpin with orchid tips",
                "charcoal sensu fan tucked into belt",
                "caramel obi sash repurposed as wrist wrap",
                "braided omamori charm clipped to bag",
                "rice paper visor with electric-blue trim",
                "bamboo bottle slung across shoulder",
            ],
            "twists": [
                "paper lantern embers drifting across frame",
                "bullet train wind ripping through hair",
                "onsen steam veiling lower frame",
                "koi splash refracting electric-blue highlights",
                "plum blossom flurry crossing lens",
            ],
        },
        "greece": {
            "descriptors": [
                "sun-bleached",
                "wind-etched",
                "cobalt-trimmed",
                "whitewashed",
                "marble-lined",
                "bougainvillea-draped",
                "shadow-cooled",
                "salt-kissed",
                "terrace-perched",
                "dusk-lavender",
                "gold-leafed",
                "sage-scented",
                "volcanic",
                "cliff-hugging",
                "market-bright",
                "lantern-ready",
                "cycladic",
                "olive-grove",
                "aegean-breeze",
                "cerulean-skied",
            ],
            "settings": [
                "caldera overlook",
                "labyrinth alley",
                "clifftop amphitheater",
                "pebble harbor",
                "windmill deck",
                "terracotta stair",
                "monastery courtyard",
                "olive press patio",
                "ferry gangway",
                "moonlit colonnade",
                "stone agora",
                "cafe arcade",
                "limestone breakwater",
                "fishing quay",
                "market promenade",
                "sunken plaza",
                "vineyard terrace",
                "glass-bottom pier",
                "navy rooftop",
                "laneway overlook",
            ],
            "foregrounds": [
                "bougainvillea ribbons",
                "salt spray sparkle",
                "rope rail shadows",
                "cobalt door frames",
                "terracotta urn stacks",
                "linen awnings",
                "olive crates",
                "marble mosaic tiles",
                "harbor lanterns",
                "sailcloth folds",
                "copper bells",
                "netted floats",
                "dune grass tufts",
                "painted pottery",
                "candled niches",
                "chalky stucco texture",
                "stone bench carve",
                "whitecap reflections",
                "rope-lashed posts",
                "sun dial shadows",
            ],
            "ambience": [
                "mosaic-reflected sunrise",
                "cerulean midday blaze",
                "lavender nautical dusk",
                "moonlit breeze",
                "pre-storm teal haze",
                "cicada noon hum",
                "lantern-flecked midnight",
                "shadow-banded afternoon",
                "gold retreated twilight",
                "harbor light bloom",
                "beacon sweep glow",
                "distant lightning flicker",
                "olive smoke drift",
                "mirage heat shimmer",
                "chalk dust sparkle",
            ],
            "accessories": [
                "woven leather gladiator cuffs with orchid laces",
                "caramel amphora pendant on satin cord",
                "electric-blue enamel worry beads on wrist",
                "marble cabochon arm cuff",
                "linen headwrap pinned with bronze disc",
            ],
            "twists": [
                "meltemi gust carving through draped fabric",
                "salt spray halo scattering highlights",
                "sun flare refracting from cobalt dome",
                "goat bell jingle caught in background blur",
                "sand eddies tracing ankles",
            ],
        },
        "italy": {
            "descriptors": [
                "cobblestone",
                "terracotta-toned",
                "marble-veined",
                "shadowy arcade",
                "dawn-rosy",
                "espresso-dark",
                "canal-side",
                "olive-grove",
                "sunken courtyard",
                "palazzo-lit",
                "hazy vineyard",
                "tram-lit",
                "buttery-stucco",
                "sepia-drenched",
                "neon-metro",
                "lakeside",
                "limestone",
                "gilded",
                "volcanic ash",
                "alpine breeze",
            ],
            "settings": [
                "palazzo loggia",
                "midnight piazza",
                "tram stop platform",
                "spiral stair landing",
                "bridge balustrade",
                "canal dock",
                "rooftop terrazza",
                "fashion house portico",
                "vintage funicular",
                "olive mill patio",
                "wine cave mouth",
                "vespa lane",
                "marina quay",
                "colonnade shadow path",
                "citrus grove aisle",
                "marble quarry ledge",
                "rail station hall",
                "cobble courtyard",
                "volcanic beachwalk",
                "glasshouse atrium",
            ],
            "foregrounds": [
                "caramel travertine tiles",
                "string lights",
                "linen cafe chairs",
                "vespa silhouettes",
                "planter boxes",
                "fountain mist",
                "copper lanterns",
                "cured leather awnings",
                "wine crate stacks",
                "shadow-striped arches",
                "marble busts",
                "potted olive trees",
                "amber glass sconces",
                "polished gondola rails",
                "woven reed mats",
                "patterned marble inlay",
                "candle clusters",
                "mirrored boutique windows",
                "floral market wraps",
                "iron gate lattice",
            ],
            "ambience": [
                "warm espresso dawn",
                "storm-soft noon",
                "copper dusk glow",
                "string-light midnight",
                "fog-laced sunrise",
                "metro neon pulse",
                "heritage lamp wash",
                "canal mist wave",
                "truffle-scented breeze",
                "alpine light spill",
                "volcanic heat shimmer",
                "moonlit marble gleam",
                "late-night fashion week hum",
                "vineyard golden haze",
                "market chatter echo",
            ],
            "accessories": [
                "caramel leather micro-satchel with orchid stitching",
                "gold filigree choker anchoring electric-blue bead",
                "silk foulard threaded through braid",
                "architectural cuff shaped like Duomo ribs",
            ],
            "twists": [
                "espresso steam drifting near face",
                "vespa headlight flare kissing lens",
                "canal ripple bouncing electric shimmer",
                "confetti from festa swirling midair",
            ],
        },
        "france": {
            "descriptors": [
                "haussmannian",
                "atelier-lit",
                "cobble-wet",
                "gilded",
                "riverbank",
                "arcaded",
                "midnight-indigo",
                "fog-framed",
                "buttery-stone",
                "graphite-sky",
                "garden-laced",
                "metro-entrance",
                "balcony-lined",
                "chalky limestone",
                "lantern-brushed",
                "winter market",
                "rooftop zinc",
                "seine-mist",
                "velvet-night",
                "couture-lab",
            ],
            "settings": [
                "pont landing",
                "atelier bay window",
                "passage couvert",
                "marche canopy",
                "gilded stair",
                "opera colonnade",
                "canal lock",
                "butte rooftop",
                "glass canopy arcade",
                "art deco metro stop",
                "botanical orangerie",
                "cobble musee court",
                "quai bookstall",
                "loft freight elevator",
                "midnight carousel",
                "train hall skylight",
                "cafe terrace",
                "fashion week tent",
                "winter garden",
                "sunken plaza mirror",
            ],
            "foregrounds": [
                "folding bistro chairs",
                "chalkboard menus",
                "tricolor ribbons",
                "cast-iron lampposts",
                "gilded railings",
                "lacquered doors",
                "metro tiles",
                "steam vent glow",
                "umbrella canopy",
                "mirror puddles",
                "electric-blue accent light",
                "couture racks",
                "lace curtains",
                "gallery plinths",
                "ivory pebbles",
                "sculpted hedges",
                "patisserie boxes",
                "balcony planters",
                "chalk dust haze",
                "carousel bulbs",
            ],
            "ambience": [
                "soft overcast morning",
                "coppery sunset drizzle",
                "sparkling midnight rain",
                "pre-dawn metro glow",
                "winter mist veil",
                "bastille fireworks haze",
                "limelight spill",
                "sodium rim reflection",
                "fog-laced spotlight",
                "crisp blue noon",
                "magenta show wash",
                "streetlamp halo",
                "arcade shadow rhythm",
                "gallery hush",
                "balcony breeze",
            ],
            "accessories": [
                "mini beret hairpin with orchid thread",
                "caramel leather wristlet with metallic tassel",
                "electric-blue silk neckerchief",
                "lace opera gloves with rubberized grip",
            ],
            "twists": [
                "metro breeze lifting coat hem",
                "champagne bubble spray softening highlights",
                "Seine mist hugging calves",
                "carousel sparkles streaking bokeh",
            ],
        },
        "spain": {
            "descriptors": [
                "tile-lined",
                "albero-dusted",
                "citrus-scented",
                "olive-shadowed",
                "coastal haze",
                "graffiti-splashed",
                "gothic arch",
                "gaudi-esque",
                "deserted plaza",
                "sirena-lit",
                "sun-bleached",
                "vine-strung",
                "market-noisy",
                "tram-crossed",
                "breeze-block",
                "chalk cliff",
                "terracotta ridge",
                "steel-port",
                "vineyard lane",
                "storm cooled",
            ],
            "settings": [
                "azulejo courtyard",
                "tram viaduct",
                "palm promenade",
                "seaside amphitheater",
                "olive mill lane",
                "gothic cloister",
                "rooftop mirador",
                "harbor ramp",
                "plaza fountain lip",
                "market arcade",
                "desert wind farm",
                "cathedral step",
                "sunken patio",
                "orange grove path",
                "industrial loft",
                "metro mezzanine",
                "bullring tunnel",
                "chalk canyon road",
                "glass canopy station",
                "vineyard crush pad",
            ],
            "foregrounds": [
                "flamenco fan stack",
                "painted tiles",
                "wrought iron gates",
                "hanging lanterns",
                "palm shadows",
                "misting fountains",
                "cable shadows",
                "scooter blur",
                "cork basket towers",
                "wicker lights",
                "porcelain jars",
                "ripe citrus piles",
                "salt pans",
                "wind turbine silhouettes",
                "gaudi mosaics",
                "chalk dust clouds",
                "saffron banners",
                "sunshade stripes",
                "arched brickwork",
                "rope lighting",
            ],
            "ambience": [
                "saffron sunset glow",
                "blue-hour tram sparks",
                "dawn fog rolling in",
                "noon heat shimmer",
                "rain-cooled midnight",
                "feria lantern blaze",
                "olive-smoke dusk",
                "sea breeze glitter",
                "storm-washed morning",
                "harbor sodium wash",
                "desert gust swirl",
                "porcelain moonlight",
                "vineyard golden haze",
                "metro fluorescence pulse",
                "roofline lightning arc",
            ],
            "accessories": [
                "embroidered mantilla clip securing waves",
                "caramel leather fan holster",
                "electric-blue cord bracelet with ceramic charm",
                "filigree peineta comb with orchid enamel",
            ],
            "twists": [
                "flamenco fringe snapping midair",
                "cava mist condensing on frame edge",
                "metro sparks tracing bokeh",
                "orange blossom gust drifting through light",
            ],
        },
        "iceland": {
            "descriptors": [
                "basalt",
                "glacier-lit",
                "aurora-tinted",
                "steam-veiled",
                "storm-blown",
                "blue-lagoon",
                "geothermal",
                "volcanic plain",
                "black-sand",
                "tundra moss",
                "arctic coastal",
                "fjordside",
                "ice cave",
                "low-sun",
                "mist-slung",
                "wind-carved",
                "sleet-bright",
                "moonstone",
                "steel-sky",
                "lupine-field",
            ],
            "settings": [
                "harbor pier",
                "lava ridge",
                "glacier overlook",
                "geothermal boardwalk",
                "saga church step",
                "reclaimed factory loft",
                "fjord ferry dock",
                "skyr warehouse",
                "black sand dune",
                "ice cave entry",
                "aurora observatory",
                "moss meadow",
                "wind farm platform",
                "volcanic crater rim",
                "coastal pool deck",
                "waterfall mist shelf",
                "arctic greenhouse",
                "urban mural lane",
                "snowfield runway",
                "sleeted streetcar bay",
            ],
            "foregrounds": [
                "geo steam jets",
                "glacial pools",
                "mossy stones",
                "icicle strings",
                "drift ice chunks",
                "ember warning lights",
                "basalt columns",
                "charcoal windbreaks",
                "solar-powered lanterns",
                "sleet streaks",
                "reflective puddles",
                "rope barriers",
                "black sand spray",
                "aurora rods",
                "harbor chainlines",
                "snow tractors",
                "recycled glass walls",
                "shipping pallets",
                "drone beacons",
                "wind-blown flags",
            ],
            "ambience": [
                "aurora sweep midnight",
                "polar blue dawn",
                "copper low sun",
                "storm break shimmer",
                "freezing rain sparkle",
                "geothermal fog glow",
                "wind-lashed noon",
                "ice crystal haze",
                "nightless sky wash",
                "harbor sodium hush",
                "moonbow glint",
                "snowglobe swirl",
                "volcanic ember haze",
                "arctic twilight",
                "fjord mist hush",
            ],
            "accessories": [
                "thermal ear wrap with orchid piping",
                "caramel shearling mitt clips",
                "electric-blue crampon straps",
                "ice spike anklets",
            ],
            "twists": [
                "aurora reflection rippling across cheeks",
                "volcanic spark ember drifting by",
                "steam bursts outlining silhouette",
                "snow microflakes glittering at lens",
            ],
        },
        "switzerland": {
            "descriptors": [
                "alpine",
                "glacial",
                "cable-car",
                "lakefront",
                "watchmaking",
                "tram-lined",
                "forest-edge",
                "valley mist",
                "stone chalet",
                "mid-century modern",
                "bank district",
                "pre-dawn frost",
                "sunlit pasture",
                "glass canopy",
                "granite tunnel",
                "meadow bloom",
                "snowfield",
                "clocktower",
                "river bend",
                "steel viaduct",
            ],
            "settings": [
                "lake promenade",
                "funicular platform",
                "train hall",
                "rooftop greenhouse",
                "clock tower terrace",
                "watch factory floor",
                "mountain lookout",
                "meadow boardwalk",
                "glacial canyon",
                "urban plaza",
                "cobble bridge",
                "tram bend",
                "granite stair",
                "ski lodge deck",
                "art museum court",
                "forested switchback",
                "river lock",
                "chalet balcony",
                "hydroelectric spillway",
                "airport skylink",
            ],
            "foregrounds": [
                "precision railings",
                "planed timber posts",
                "mirror lake reflections",
                "cable shadows",
                "clock gears",
                "steel trusses",
                "flower boxes",
                "copper gutters",
                "frosted glass walls",
                "stone inlays",
                "ski racks",
                "avalanche fencing",
                "watch faces",
                "granite benches",
                "alpine wildflowers",
                "tram cables",
                "glacial runoff",
                "bike lanes",
                "snowmelt puddles",
                "architectural louvers",
            ],
            "ambience": [
                "golden alpine dawn",
                "silver blue noon",
                "glacier moon glow",
                "storm-cleared afternoon",
                "misty meadow sunrise",
                "tram spark twilight",
                "lake mist hush",
                "aurora surprise",
                "winter market glow",
                "factory warm spill",
                "pre-storm graphite sky",
                "nocturne sodium rim",
                "clear midnight frost",
                "cafe lamp wash",
                "summit star field",
            ],
            "accessories": [
                "precision chain belt with enamel edelweiss",
                "caramel leather ski pass holster",
                "electric-blue rope leash wrist wrap",
                "felt alpine hat pin with orchid crystal",
            ],
            "twists": [
                "snow dust devils spiraling at boots",
                "lake spray misting calves",
                "cable car shadow sweeping torso",
                "clock tower chime vibration blurring lights",
            ],
        },
        "maldives": {
            "descriptors": [
                "lagoon-set",
                "sun-bleached",
                "reefside",
                "overwater",
                "sandbar",
                "jetty-lined",
                "mangrove",
                "coral-toned",
                "storm-cleared",
                "dawn-lit",
                "moon-washed",
                "orchid-canopied",
                "aqua-latticed",
                "glass-deck",
                "spa-quiet",
                "yacht-anchored",
                "palapa",
                "hammock-bay",
                "driftwood",
                "luminescent",
            ],
            "settings": [
                "overwater villa walk",
                "infinity pool lip",
                "reef dock",
                "lagoon swing",
                "sandbar runway",
                "tidepool patio",
                "catamaran net",
                "jetty pavilion",
                "jungle boardwalk",
                "manta point platform",
                "spa courtyard",
                "outdoor cinema",
                "sunset deck",
                "hammock lounge",
                "coral nursery raft",
                "glow plankton bay",
                "yacht stern",
                "palm tunnel",
                "sky bar bridge",
                "rain pavilion",
            ],
            "foregrounds": [
                "glass floor panels",
                "orchid garlands",
                "palm shadows",
                "rope hammocks",
                "wave spray",
                "glistening shells",
                "driftwood stacks",
                "tiki lanterns",
                "rattan lantern cords",
                "floating breakfast trays",
                "coral tiles",
                "teal surfboards",
                "mist fans",
                "woven parasols",
                "bioluminescent trails",
                "fiber optic railings",
                "silk cabana drapes",
                "persimmon cushions",
                "bubble curtain",
                "kelp ropes",
            ],
            "ambience": [
                "sunrise pastel wash",
                "tropic noon glare",
                "copper sunset melt",
                "monsoon break calm",
                "starlit midnight lagoon",
                "bio-lum glow",
                "rain cooled dusk",
                "turquoise noon shimmer",
                "storm lantern glow",
                "pale moon tide",
                "mangrove mist morning",
                "UV neon party",
                "drizzle cooled afternoon",
                "paddle splash sparkle",
                "trade wind gust",
            ],
            "accessories": [
                "shell-inlaid anklet with electric-blue bead",
                "caramel raffia visor edged in orchid cord",
                "reef-safe bangles stacked with glassy sheen",
                "waterproof waist pack with copper zipper",
            ],
            "twists": [
                "bioluminescent wake streaking past calves",
                "salt mist halo coating arms",
                "palm shadow lattice drifting over torso",
                "flying fish arc blurring background",
            ],
        },
        "uae_dubai": {
            "descriptors": [
                "desert-luxe",
                "skydeck",
                "glass-canopy",
                "marina-lit",
                "souk-lined",
                "industrial port",
                "neon-skyline",
                "gold-foiled",
                "sandstorm",
                "oasis",
                "palm-garden",
                "helipad",
                "midnight mall",
                "art-district",
                "futurist",
                "opulent atrium",
                "dune-fringe",
                "metro-skybridge",
                "pierside",
                "carbon fiber",
            ],
            "settings": [
                "skybridge walkway",
                "helipad rim",
                "dune edge deck",
                "marina promenade",
                "souk courtyard",
                "desert camp platform",
                "palm frond pier",
                "museum atrium",
                "metro mezzanine",
                "solar farm lane",
                "fountain plaza",
                "luxury tram stop",
                "yacht slip",
                "roof pool causeway",
                "glass elevator lobby",
                "future park canopy",
                "mirage garden",
                "industrial crane bay",
                "steel skywalk",
                "crypto gallery",
            ],
            "foregrounds": [
                "laser beam fog",
                "gold mashrabiya shadows",
                "LED fountain arcs",
                "carbon-fiber benches",
                "mirror cladding",
                "palm sculptures",
                "desert rose planters",
                "laminated dunes",
                "hover drone lights",
                "smart kiosks",
                "saffron carpets",
                "prayer lantern stacks",
                "fiber optic palms",
                "chrome bollards",
                "aqua taxis",
                "scent misters",
                "marina ropes",
                "jet stream plumes",
                "glass fins",
                "architectural screens",
            ],
            "ambience": [
                "desert dawn blush",
                "midnight neon pulse",
                "sandstorm amber haze",
                "skyline laser wash",
                "moonlit marina breeze",
                "atrium diffused noon",
                "mirage noon glare",
                "oasis twilight cool",
                "storm build teal",
                "carbon fiber sheen night",
                "LED synchronized glow",
                "fountain mist sparkle",
                "helipad sodium rim",
                "metro cyan wash",
                "palm shadow rhythm",
            ],
            "accessories": [
                "gold filigree waist chain with orchid crystal",
                "caramel leather falconry glove-inspired cuff",
                "electric-blue visor with mirrored shield",
                "souk bead anklet with carbon charm",
            ],
            "twists": [
                "dune breeze lofting silk panels",
                "fountain jets refracting across lens",
                "thermal updraft nudging hair",
                "skyline holo ads pulsing reflections",
            ],
        },
        "thailand": {
            "descriptors": [
                "canal-side",
                "temple-courtyard",
                "market-lit",
                "monsoon-cooled",
                "mango-grove",
                "lantern-strung",
                "jungle-border",
                "limestone-cliff",
                "island-pier",
                "old-town",
                "skytrain",
                "street-food",
                "sunrise-orange",
                "rain-washed",
                "nocturne-neon",
                "floating-market",
                "saffron-robed",
                "teakhouse",
                "cloud-forest",
                "lagoon-misted",
            ],
            "settings": [
                "wat staircase",
                "canal footbridge",
                "floating market dock",
                "skytrain platform",
                "soi mural lane",
                "spa pavilion",
                "jungle boardwalk",
                "teak mansion veranda",
                "island karst cave",
                "rooftop infinity ledge",
                "bazaar arcade",
                "night market aisle",
                "lotus pond deck",
                "mango orchard row",
                "monsoon rooftop",
                "heritage tram stop",
                "harbor ferry gate",
                "limestone beach arch",
                "rice terrace ridge",
                "tech park skywalk",
            ],
            "foregrounds": [
                "saffron monk umbrellas",
                "lotus lanterns",
                "wet cobbles",
                "banana leaves",
                "neon tuk-tuk trails",
                "hanging flower garlands",
                "spice baskets",
                "mist fans",
                "candle clusters",
                "rattan screens",
                "color flag strings",
                "floating blooms",
                "teak balustrades",
                "woven mats",
                "market chalkboards",
                "pho leaves",
                "dragonfruit crates",
                "palm halos",
                "dripping eaves",
                "canal reflections",
            ],
            "ambience": [
                "sunrise saffron wash",
                "monsoon drizzle sparkle",
                "humid midnight neon",
                "blue-hour incense haze",
                "candlelit dusk",
                "lotus mist morning",
                "thunder build glow",
                "river breeze shimmer",
                "lantern festival blaze",
                "electric market hum",
                "storm-cleared moon",
                "cicada twilight",
                "jungle chorus dawn",
                "skytrain shimmer night",
                "canal mirror noon",
            ],
            "accessories": [
                "silk pha khao ma belt with orchid line",
                "caramel teak bead bracelet",
                "electric-blue lacquered hair stick",
                "lotus charm anklet with bells",
            ],
            "twists": [
                "incense smoke ribbons weaving around arms",
                "longtail boat spray crossing background",
                "monsoon fan gust rippling outfit",
                "firefly arcs peppering bokeh",
            ],
        },
    }


LOCATION_COMPONENTS = build_location_components()


def generate_scene_for(location: str) -> Callable[[random.Random, int], List[Tuple[str, float]]]:
    comps = LOCATION_COMPONENTS[location]

    def generator(rng: random.Random, batch_size: int) -> List[Tuple[str, float]]:
        templates = [
            lambda c: f"{c['descriptor']} {c['setting']} with {c['foreground']} under {c['ambience']}",
            lambda c: f"{c['descriptor']} {c['setting']} framed by {c['foreground']} during {c['ambience']}",
            lambda c: f"{c['descriptor']} {c['setting']} featuring {c['foreground']} amidst {c['ambience']}",
        ]
        items: List[Tuple[str, float]] = []
        attempts = 0
        while len(items) < batch_size and attempts < batch_size * 35:
            attempts += 1
            parts = {
                "descriptor": rng.choice(comps["descriptors"]),
                "setting": rng.choice(comps["settings"]),
                "foreground": rng.choice(comps["foregrounds"]),
                "ambience": rng.choice(comps["ambience"]),
            }
            text = rng.choice(templates)(parts)
            weight = determine_weight(text)
            items.append((text, weight))
        if len(items) < batch_size:
            raise RuntimeError(f"{location} scene generation underflow")
        return items

    return generator


def build_overrides(location: str) -> Dict[str, List[Dict[str, float]]]:
    data = LOCATION_COMPONENTS[location]
    overrides: Dict[str, List[Dict[str, float]]] = {}
    if "accessories" in data:
        overrides["accessories"] = [{"text": normalize(t), "weight": 0.6} for t in data["accessories"]]
    if "twists" in data:
        overrides["twist"] = [{"text": normalize(t), "weight": 0.6} for t in data["twists"]]
    return overrides


SLOT_GENERATORS = {
    "wardrobe_top": lambda rng, n: generate_wardrobe_top(rng, n),
    "wardrobe_bottom": lambda rng, n: generate_wardrobe_bottom(rng, n),
    "accessories": lambda rng, n: generate_accessories(rng, n),
    "lighting": lambda rng, n: generate_lighting(rng, n),
    "camera": lambda rng, n: generate_camera(rng, n),
    "angle": lambda rng, n: generate_angle(rng, n),
    "pose_microaction": lambda rng, n: generate_pose(rng, n),
    "twist": lambda rng, n: generate_twist(rng, n),
}


def main() -> None:
    LOCATIONS_DIR.mkdir(parents=True, exist_ok=True)

    global_bank = {}
    for slot, generator in SLOT_GENERATORS.items():
        items = run_batches(slot, TARGET_PER_SLOT, BATCH_SIZE_SLOT, generator)
        global_bank[slot] = items
    global_bank["negative"] = NEGATIVE_LIST

    with OUTPUT_GLOBAL.open("w", encoding="utf-8") as fh:
        json.dump(global_bank, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    for location in LOCATION_COMPONENTS:
        generator = generate_scene_for(location)
        key = f"location_{location}"
        scenes = run_batches(key, TARGET_PER_LOCATION, BATCH_SIZE_SCENE, generator)
        overrides = build_overrides(location)
        payload = {"scenes": scenes}
        if overrides:
            payload["overrides"] = overrides
        out_path = LOCATIONS_DIR / f"{location}.json"
        with out_path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

    report = {
        "final_counts": {slot: len(data) for slot, data in global_bank.items() if slot != "negative"},
        "location_counts": {
            loc: len(json.loads((LOCATIONS_DIR / f"{loc}.json").read_text(encoding='utf-8'))["scenes"])
            for loc in LOCATION_COMPONENTS
        },
        "dedupe_log": batch_dedupe_log,
        "dedupe_examples": dedupe_examples,
        "expansions": expansion_flags,
        "suppressed_counts": suppressed_counts,
        "policy_rejections": policy_rejections,
    }
    report_path = BASE_DIR / "app" / "data" / "logs.txt"
    with report_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(report, indent=2))
        fh.write("\n")


if __name__ == "__main__":
    main()
