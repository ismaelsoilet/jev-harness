# 🧠 System 1.5 Architecture Trilogy

[ 🏠 Repositório](../../README.md) | [ 📚 Hub de Documentação](../README.md) | [ 🇬🇧 English Docs](../README.md) | [ 🇧🇷 Português](../README.pt-BR.md)

> **The conceptual north and implementation roadmap of `jev-harness` as the System 1.5 connective tissue for agentic software engineering.**

---

## 🧭 About the Trilogy

The documents in this directory define where `jev-harness` sits between **System 1** (TypeSafe Jev fast decision primitives) and **System 2** (expensive frontier reasoning models like GPT-6 Astra and Claude Fable 5.1).

Rather than an arbitrary set of scripts, `jev-harness` is engineered as the **macro-cognitive executive layer** described by Daniel Kahneman and formalized for agentic computing by Josh Rosen (September 2026):

```
┌────────────────────────────────────────────────────────┐
│               System 1: Fast Perception                │
│    (TypeSafe Jev System One, < 500µs local / 70ms API) │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│     System 1.5: Deterministic Connective Tissue        │
│                    (jev-harness)                       │
│  • Traceback slicing & secret redaction                │
│  • Deterministic short-circuits (pip/npm/cargo)        │
│  • Doom loop circuit breaker & effort leasing          │
│  • Calibration, entropy margins & quality veto         │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│             System 2: Slow Deliberation                │
│      (Frontier LLMs: GPT-6 Astra, Claude Fable 5.1)     │
└────────────────────────────────────────────────────────┘
```

---

## 📑 The Three Core Documents

| Document | Title | Purpose & Content |
| :--- | :--- | :--- |
| 🏛️ **[`SYSTEM_1_5_PLAN.md`](SYSTEM_1_5_PLAN.md)** | **Target Architecture & Verified Facts** | • Definition of System 1.5 (macro vs micro level) with primary sources.<br>• Verified facts from TypeSafe AI documentation and Josh Rosen articles.<br>• Ground truth audit: what `jev-harness` is today and what was verified on 2026-09-23.<br>• Identification of 1 production defect and 6 material gaps. |
| 🔭 **[`SYSTEM_1_5_OPPORTUNITIES.md`](SYSTEM_1_5_OPPORTUNITIES.md)** | **Ecosystem Landscape & 21 Opportunities** | • Comparative landscape with Foreman (552★), JevRouter (173★), Winnow (68★), and jev-guard (26★).<br>• The verdict on "Can we be System 1.5?": Yes, specifically for the code quality & test loop.<br>• Catalog of 21 prioritized opportunities across 4 tiers (Tier-0 Reliability, Tier-1 Calibration, Tier-2 Ergonomics, Tier-3 Moats). |
| 🛠️ **[`SYSTEM_1_5_IMPLEMENTATION.md`](SYSTEM_1_5_IMPLEMENTATION.md)** | **Implementation Plan & Horizons (H1–H3)** | • Phased implementation sequencing: Horizon 1 (Delivered in v0.2.0), Horizon 2 (Reliability & Trust), Horizon 3 (Enterprise & Multi-Worker).<br>• Precise acceptance criteria, required test contracts, and Definition of Done (DoD).<br>• *Note: This is an architectural engineering plan, not a release checklist.* |

---

## 🔍 Recommended Reading Order

1. **Start with [`SYSTEM_1_5_PLAN.md`](SYSTEM_1_5_PLAN.md)** to understand the theoretical foundation, cognitive model, and empirical facts.
2. **Read [`SYSTEM_1_5_OPPORTUNITIES.md`](SYSTEM_1_5_OPPORTUNITIES.md)** to see how `jev-harness` cooperates with other tools in the emerging System One ecosystem.
3. **Consult [`SYSTEM_1_5_IMPLEMENTATION.md`](SYSTEM_1_5_IMPLEMENTATION.md)** for detailed specifications, epic definitions, and acceptance criteria.
