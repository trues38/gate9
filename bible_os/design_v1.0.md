# Bible Meaning OS v1.0 - Architecture Design Document

## 1. Meaning Regimes (30 Core Patterns)
The core of the Meaning Engine is the classification of biblical text into 30 archetypal "Regimes". These are not just topics, but "movement patterns" of the soul and history.

| ID | Regime Name | Concept/Vibe | Representative Archetype |
|----|-------------|--------------|--------------------------|
| R01 | **The Wilderness (Middbar)** | Isolation, preparation, scarcity, silence | Moses, John the Baptist |
| R02 | **The Pit (Sheol)** | Despair, trapping, deep depression, death | Joseph, Jeremiah |
| R03 | **The Betrayal (Galan)** | Broken trust, conspiracy, loneliness | David (Absalom), Jesus (Judas) |
| R04 | **The Restoration (Shuv)** | Returning, rebuilding, healing after break | Nehemiah, Peter |
| R05 | **The Calling (Qara)** | Burden, assignment, hesitation, mission | Gideon, Jonah, Paul |
| R06 | **The Sacrifice (Olah)** | Costly giving, letting go, pain for purpose | Abraham (Isaac), Widow's Mite |
| R07 | **The Chaos (Tohu wa-bohu)** | Confusion, disorder, overwhelming complexity | Flood, Babel |
| R08 | **The Order (Seder)** | Structure, law, boundaries, clarity | Leviticus, Wisdom Lit |
| R09 | **The Exile (Galut)** | Displacement, foreignness, longing for home | Daniel, Ezekiel |
| R10 | **The Exodus (Yatsa)** | Escape, liberation, breaking chains, transition | Israel out of Egypt |
| R11 | **The Waiting (Qavah)** | Patience, delay, hiddenness, endurance | Simeon/Anna, David in caves |
| R12 | **The Battle (Milchamah)** | Conflict, spiritual warfare, enemies, courage | Joshua, David vs Goliath |
| R13 | **The Feast (Mishteh)** | Celebration, abundance, joy, consummation | Wedding at Cana, Last Supper |
| R14 | **The Famine (Ra'ab)** | Spiritual dryness, economic lack, hunger | Elijah/Widow, Prodigal Son |
| R15 | **The Covenant (Berit)** | Promise, binding relationship, loyalty | Abrahamic/Davidic Covenant |
| R16 | **The Judgment (Mishpat)** | Consequences, exposure, reckoning, justice | Prophets, Revelation |
| R17 | **The Grace (Chen)** | Unmerited favor, surprise rescue, reversal | Mephibosheth, Zacchaeus |
| R18 | **The Wisdom (Chokmah)** | Insight, pattern recognition, practical skill | Solomon, Proverbs |
| R19 | **The Folly (Kesil)** | Blindness, mistake, stubborness, ruin | Rehoboam, Saul |
| R20 | **The Identity (Shem)** | Naming, who am I, belovedness, sonship | Jacob->Israel, Baptism |
| R21 | **The Family (Mishpachah)** | Bloodline, inheritance, dysfunction, brotherhood | Cain/Abel, Mary/Martha |
| R22 | **The Kingship (Malchut)** | Authority, leadership, responsibility, power | David, Jesus |
| R23 | **The Servanthood (Ebed)** | Humility, washing feet, hidden work | Suffering Servant, Deacons |
| R24 | **The Resurrection (Tekiyah)** | New life from death, impossibility made real | Lazarus, Easter |
| R25 | **The Lament (Qinah)** | Grief, pouring out complaint, tears | Psalms, Lamentations |
| R26 | **The Praise (Tehillah)** | Awe, wonder, gratitude, shift of focus | Miriam’s Song, Magnificat |
| R27 | **The Temptation (Nasah)** | Testing, crossroads, desire vs duty | Eden, Wilderness Temptation |
| R28 | **The Vision (Chazon)** | Future sight, revelation, dream, apocalypse | Daniel, John (Rev) |
| R29 | **The Silence (Hesh)** | God's apparent absence, mystery | Job, 400 years intertestamental |
| R30 | **The Incarnation (Tabernacle)** | Presence, God with us, tangible reality | Tabernacle, Jesus Flesh |

---

## 2. Clustering Rules & Classification Logic
How verses are assigned to Regimes.

### A. Dimensional Scoring
Each verse/chapter is scored on 3 axes:
1.  **Emotion Vector** (e.g., Fear, Joy, Anger, Sorrow, Hope)
2.  **Situation Vector** (e.g., Conflict, Poverty, Illness, Leadership, Family)
3.  **Action Mode** (e.g., Passive/Enduring, Active/Fighting, Reflective/Praying)

### B. Archetype Matching
- **Joseph Type**: Victim -> Ruler (suffering w/ purpose) -> matches R02, R22
- **David Type**: Warrior/Worshipper (oscillation) -> matches R12, R26, R03
- **Peter Type**: Impulsive -> Humble (failure & restoration) -> matches R04, R20

### C. Keyword & Semantic Expansion
- "Darkness, pit, mire, silence" -> **R02 (The Pit)**
- "Build, wall, gate, measure" -> **R04 (Restoration) / R08 (Order)**
- "Wait, watch, how long" -> **R11 (The Waiting)**

---

## 3. Embedding Strategy & Data Architecture

### Database: DuckDB (Local High Performance)
**Table: `bible_verse_vectors`**
- `id`: Unique Verse ID (GEN-001-001)
- `text_raw`: Original Text
- `text_modern`: Modern Translation (NIV/ESV equiv)
- `embedding`: 1536d vector (OpenAI/Deepseek)
- `regime_tags`: JSON Array of top 3 Regimes [R01, R11]
- `emotion_profile`: {sorrow: 0.8, hope: 0.2}
- `context_summary`: One sentence context of the chapter.

### Embedding Levels
1.  **Verse Level**: Dense retrieval for specific phrases.
2.  **Chapter Context Level**: To catch the "vibe" that doesn't exist in a single verse.
3.  **Regime Centroids**: 30 pre-calculated vectors representing the "ideal meaning" of each Regime.

---

## 4. Input Analysis Layer (The Question Parser)

When user inputs: *"I feel like a failure business-wise and my partner doesn't understand."*

**Analysis Output:**
1.  **Primary Emotion**: Shame / Isolation (Failure)
2.  **Situation**: Economic (Business) + Relational (Partner)
3.  **Underlying Need (Why)**: Validation, Hope, Direction
4.  **Temporal State**: "After the crash" (Past-focused) or "In the hole" (Present-focused)

---

## 5. Question -> Regime Mapping Algorithm

Algorithm `RegimeSelector(InputAnalysis)`:
1.  **Direct Semantic Search**: Query vector vs Regime Centroids.
2.  **Component Mixing**:
    - *Economic Failure* -> Maps to **R14 (Famine)** or **R19 (Folly)** or **R02 (Pit)**
    - *Relational Misunderstanding* -> Maps to **R03 (Betrayal)** or **R01 (Wilderness)**
3.  **Narrative Arc Matching**: Is this a "Job" moment (innocent suffering) or a "Prodigal" moment (consequence of action)?
    - IF `Self-Blame` is High -> Check **R04 (Restoration)** or **R17 (Grace)**.
    - IF `External-Blame` is High -> Check **R12 (Battle)** or **R25 (Lament)**.

**Result**: Select Top 2 Regimes. (e.g., **R14 (Famine)** + **R01 (Wilderness)**)

---

## 6. Regime -> Verse Cluster Matching

Once Regime is selected (e.g., **R14 Famine**), we don't just dump verses. We filter by **Vibe**.

*Context*: User is sad/hopeless.
*Goal*: Empathy -> Hope.

1.  **Fetch Candidates** from `bible_verse_vectors` where `regime` IN (R14, R01).
2.  **Filter by Emotion**: exclude "Judgment" verses; prioritize "Lament" or "Sustenance" verses.
3.  **Key Passage Selection**:
    -   *Elijah fed by ravens (1 Kings 17)* -> Divine provision in scarcity.
    -   *Isaac sowing in famine (Gen 26)* -> Action amidst lack.

---

## 7. Meaning Transformation Layer (The "Bridge")

This is the "Meaning Engine" core. It translates symbols.

| Biblical Symbol | Business/Modern Reality |
|-----------------|-------------------------|
| "Famine" | Market Downturn / Cashflow Crunch |
| "Enemy/Philistine" | Competitor / Internal Doubts / Debt |
| "Sword" | Skill / Strategy / Tech Stack |
| "Wilderness" | Career Gap / Pivot Phase / Startup Valley of Death |
| "Idol" | Money / Status / Addiction |
| "Temple" | Inner Self / Community / Core Values |

**Transformation Logic**:
*"Do not go down to Egypt" (Gen 26)*
-> *Transformation*: "Do not return to old easy habits or quick debt solutions just because things are tight."

---

## 8. Final Response Generation Logic (Template)

**Constraint**: NEVER sound like a chatbot. Sound like a wise sage/mentor.

**Structure (5 steps)**:
1.  **The Mirror (Empathy)**: "It sounds like you are walking through a valley of dry bones, where your effort yields no profit and you feel unheard."
2.  **The Regime (Diagnosis)**: "You are currently in the **Wilderness Regime (R01)**. This is not a punishment, but a place of stripping and preparation. It is where manna is found."
3.  **The Ancient Text (Anchor)**: "Consider Isaac. There was a famine in the land... but he sowed in that land and reaped a hundredfold (Gen 26). Or Elijah, who sat by the Brook Cherith."
4.  **The Bridge (Application)**: "In your business, this means 'staying in the land'—don't panic-pivot. The silence of your partner is the silence of the desert—it invites you to find your own voice first."
5.  **The Direction (One Liner)**: "Today, do not look for the feast; look for the raven that brings just enough for today."

---

## 9. Architecture (Single Tenant / Configurable)

- **Config Path**: `/g9/bible_os/config/user_profile.json`
- **Data Path**: `/g9/bible_os/data/db/bible.duckdb`
- **Modules**:
    - `ingestOR.py` (Parses TXT -> Chunks)
    - `regime_clf.py` (Classifies Chunks -> Regimes)
    - `query_engine.py` (The RAG + Logic Pipeline)
