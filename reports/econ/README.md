# Economy Reports Directory

**모든 경제 보고서는 여기에 저장됩니다.**

---

## 📁 Directory Structure

```
/Users/js/g9/reports/econ/
├── bulletins/              # Daily State Adjudication Bulletins
│   ├── BULLETIN_2025-12-30.md
│   └── BULLETIN_2025-12-31.md
├── asia/                   # Asia Reaction Layer (1-page addon)
│   ├── ASIA_2025-12-30.md
│   └── ASIA_2025-12-31.md
├── monthly/                # Monthly Macro Reports
│   └── MONTHLY_2025-12.md
└── archive/                # Old/Historical Reports
```

---

## 📊 Report Types

### 1. Daily Bulletin (`bulletins/`)
- **Source**: `regime_zero/engine/state_graph/bulletin_generator.py`
- **Frequency**: Daily
- **Content**: Market stress, state contradictions, resolution paths
- **Format**: Markdown (2 pages)

### 2. Asia Layer (`asia/`)
- **Source**: `asia_layer_integration.sh`
- **Frequency**: Daily (after US data)
- **Content**: KR/JP market reaction, X sentiment
- **Format**: Markdown (1 page addon)

### 3. Monthly Report (`monthly/`)
- **Source**: TBD
- **Frequency**: Monthly
- **Content**: Aggregated analysis, regime transitions
- **Format**: Markdown

---

## 🔄 VPS Mirror

```
/opt/g9/reports/econ/
├── bulletins/
├── asia/
├── monthly/
└── archive/
```

**Sync Command** (if needed):
```bash
rsync -avz root@141.164.35.214:/opt/g9/reports/econ/ /Users/js/g9/reports/econ/
```

---

## ✅ Path Guarantee

**이 경로는 절대 바뀌지 않습니다.**
- Local: `/Users/js/g9/reports/econ`
- VPS: `/opt/g9/reports/econ`

모든 스크립트는 이 경로로 고정되었습니다.

---

**Last Updated**: 2025-12-30
