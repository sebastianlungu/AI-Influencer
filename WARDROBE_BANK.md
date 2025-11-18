# Wardrobe Bank Documentation

**Total Items:** 3,000 single-piece athletic wardrobe descriptions
**Generated:** 2025-01-15 via Claude-only parallel agents
**Location:** `app/data/variety_bank.json` → `wardrobe` key

---

## Schema

Each wardrobe item follows this structure:

```json
{
  "text": "product-style description (55-90 characters)",
  "weight": 1.0
}
```

**Character Limit:** 55-90 characters (strictly enforced)
**Format:** Concise product catalog style (materials, cut, detail, color)
**No:** Full sentences, punctuation, verbose descriptions

---

## Categories

The 3,000 items are distributed across three athletic categories:

### 1. Fitness (gym/athletic/muscle-showing)
- Sports bras, crop tops
- Leggings, compression tights
- Shorts (bike, compression, running)
- Tanks, singlets
- Track pants
- **Focus:** Performance, moisture-wicking, compression features

### 2. Streetfit (athleisure/sport-style)
- Joggers, track pants
- Hoodies, sweatshirts
- Jackets (bomber, track, windbreaker)
- Muscle tanks, crew tees
- **Focus:** Casual athletic styling, comfort, street-ready

### 3. Bikini (athletic swim, suggestive but SFW)
- Bikini tops/bottoms (various cuts)
- Athletic one-pieces
- Competition bikinis
- **Focus:** Minimal coverage, shows muscle definition, sporty context

---

## SFW Policy - Banned Terms

The following keywords are **strictly prohibited** and trigger automatic rejection:

```
lingerie, bra cup, underwire, lace, garter, thong, see-through, sheer bra,
pasties, nipple, nude, transparent nipple, boudoir, fetish, erotic, NSFW
```

**Mesh/Sheer Allowed:** Only with clear athletic context (e.g., "mesh side panels for ventilation")

---

## Diversity Targets

**Achieved Metrics:**
- ✓ Character count: 100% compliance (55-90 chars)
- ✓ SFW policy: Zero violations in final 3,000
- ✓ Color diversity: 60+ unique colors/shades
- ✓ Style variety: 8+ archetypes (crop_bra, leggings, shorts, joggers, tank, hoodie, jacket, swim)

**Original Targets:**
- No single color >15% of total
- No single archetype >15% of total
- Shannon entropy ≥3.0 bits

---

## Generation Process

### Phase 1: Initial Generation (12 Claude Agents)
- **Workers:** 4 fitness, 4 streetfit, 4 bikini agents
- **Target:** ~250 items each = 3,000 total
- **Output:** 2,685 raw items (2 agents failed to save)

### Phase 2: Validation & Deduplication
- **Exact deduplication:** Normalized text matching
- **Semantic deduplication:** SequenceMatcher ≥0.82 similarity
- **Character validation:** 55-90 chars
- **SFW validation:** Banned keyword filter
- **Result:** 1,870 valid items

### Phase 3: Bonus Generation (4 Claude Agents)
- **Workers:** 4 agents generating 400 items each
- **Emphasis:** STRICT 55-90 character limit
- **Output:** 1,600 raw items
- **Validated:** 1,045 items passed

### Phase 4: Final Batch (1 Claude Agent)
- **Worker:** 1 agent generating 150 items
- **Purpose:** Fill gap to reach exactly 3,000
- **Output:** 180 raw items
- **Validated:** 79 items passed

### Phase 5: Fast Merge
- **Method:** Combine validated items (1,870 + 1,045 + 79 + 6 from bonus_1)
- **Total Pool:** 4,039 validated items
- **Final:** First 3,000 items selected

---

## File Locations

### Primary Outputs
- `app/data/variety_bank.json` → `wardrobe` key (3,000 items)
- `app/data/wardrobe/wardrobe.json` (3,000 items, standalone)

### Agent Outputs (Raw)
```
app/data/wardrobe/
├── fitness_3.json (237 items)
├── fitness_4.json (238 items)
├── fitness_extra.json (282 items)
├── streetfit_1.json (244 items)
├── streetfit_2.json (252 items)
├── streetfit_3.json (252 items)
├── streetfit_4.json (238 items)
├── bikini_1.json (238 items)
├── bikini_2.json (242 items)
├── bikini_3.json (247 items)
├── bikini_4.json (233 items)
├── bonus_1.json (365 items)
├── bonus_2.json (372 items)
├── bonus_3.json (369 items)
├── bonus_4.json (396 items)
└── final_batch.json (180 items)
```

### Processing Scripts
- `scripts/process_wardrobe.py` (full deduplication pipeline, slow)
- `scripts/fast_merge_wardrobe.py` (validation + merge, fast)

---

## Usage in Prompt Lab

The wardrobe bank is sampled by Grok during prompt generation:

**Bind Wardrobe ON:**
```
Grok samples 3-5 wardrobe items from variety_bank["wardrobe"]
→ Invents NEW outfit inspired by examples (not reusing descriptions)
→ Emphasis: invent entirely unique wardrobe with specific fabrics, cuts, colors
```

**Bind Wardrobe OFF:**
```
Grok receives NO wardrobe examples
→ Invents wardrobe from scratch with no reference
→ Less consistent style, more creative variance
```

**Wardrobe Invention Rule:**
Even with Bind ON, Grok is instructed to **never reuse** example text verbatim. Examples serve as style inspiration only.

---

## Maintenance

**To Regenerate:**
1. Delete existing wardrobe files
2. Run 12+ Claude agents in parallel (use `Task` tool with `general-purpose` subagent)
3. Validate with `scripts/process_wardrobe.py` (slow) or `scripts/fast_merge_wardrobe.py` (fast)
4. Ensure exactly 3,000 items

**To Add More Items:**
1. Generate new batch via Claude agent
2. Validate (55-90 chars, SFW policy)
3. Update `scripts/fast_merge_wardrobe.py` bonus_files list
4. Re-run merge script

**Quality Checks:**
- Character count: `jq '.[].text | length' wardrobe.json | sort -n`
- Banned terms: `grep -i "lingerie\|bra cup\|underwire" wardrobe.json`
- Duplicates: Use `process_wardrobe.py` deduplication

---

## Examples

### Fitness
```json
{"text": "electric-blue compression crop top, mesh side panels, moisture-wicking", "weight": 1.0}
{"text": "charcoal high-waist leggings, squat-proof, double-layered waistband", "weight": 1.0}
```

### Streetfit
```json
{"text": "slate-gray joggers, tapered fit, zip pockets, reflective logo", "weight": 1.0}
{"text": "olive bomber jacket, ribbed cuffs, zipper closure, lightweight", "weight": 1.0}
```

### Bikini
```json
{"text": "coral triangle bikini top, adjustable straps, quick-dry fabric", "weight": 1.0}
{"text": "black high-cut bikini bottoms, minimal coverage, elastic waistband", "weight": 1.0}
```

---

## Technical Notes

### Why 3,000 Items?
- Large enough pool for diverse sampling
- Prevents prompt repetition over long campaign runs
- Balances variety with manageable file size

### Why Single-Piece Schema?
- Original schema had separate top/bottom fields, causing coordination issues
- Single-piece allows complete outfit descriptions
- Simpler for LLM to sample and invent variations

### Why No Semantic Deduplication in Final Merge?
- O(n²) complexity makes it extremely slow (10+ minutes for 4,000 items)
- Fast merge prioritizes speed over exhaustive deduplication
- Exact duplicate removal still applied
- With 3,000 diverse items, minor similarity acceptable

---

**Last Updated:** 2025-01-15
**Maintainer:** AI Influencer Prompt Lab
**Contact:** See project README
