# MedGuard

**An Autonomous AI Agent for Pharmaceutical Supply Chain Integrity in Nigeria**

---

## The Problem I'm Trying to Solve

I'm a currently a pharmacist intern. I've worked in one of Nigeria's most prominent orthopedic hospitals for the past seven months.

Here's what I've seen: An orthopedic hospital running out of Tramadol, Cocodamol, and many other important medications. These aren't edge cases—they're the backbone medications for 80-90% of our patients. When we run out, I've had patients unfamiliar with the area ask us where else they can get their medications. Many of them end up at open markets, where the risk of counterfeit drugs is highest.

Nigeria has a pharmaceutical crisis at the intersection of three compounding failures:

**Fragmented supply chains.** There is no unified system tracking medications from importation through distribution to dispensing. Drugs move through the system invisibly, making it impossible to verify authenticity or trace problems to their source.

**Chronic shortages.** Hospitals routinely run out of essential medications. When a facility lacks stock, patients are directed to open markets—the primary entry point for counterfeit drugs.

**Counterfeit proliferation.** Substandard and falsified medications flood the market, particularly antimalarials and antibiotics. In a country battling malaria, subtherapeutic antimalarials don't just fail to cure—they drive resistance and cost lives.

The infrastructure itself makes detection nearly impossible. A batch of medication appearing simultaneously in Lagos and Kano should be an obvious counterfeit signal—Nigeria's road infrastructure cannot physically deliver goods between these locations in a single day. But without a unified tracking system, no one sees these impossible patterns.

---

## What MedGuard Does

MedGuard is an autonomous marathon AI agent that monitors pharmaceutical supply chains, detects anomalies signaling counterfeit risk, and intelligently coordinates medication transfers between facilities.

The system operates on a simple principle: **separate the data from the logic**. The agent works with whatever data it receives—it doesn't care about country boundaries. This makes the system configurable and scalable: start with Lagos, expand to Nigeria, eventually extend across Africa.

---

## How It Works

### The Data Layer

I had to learn discrete event simulation to model realistic pharmaceutical supply chain behavior. The foundation is a database tracking medications across the system—currently built with simulated data (30 medications, 70 brands of medications across 50 facilities) designed to reflect realistic Nigerian pharmaceutical patterns.

The data has three core components:

**Movements** track physical inventory changes: dispensing 30 units of paracetamol to a patient, transferring 30 units to another facility, receiving 10 units of insulin from a supplier, removing 10 vials of potassium chloride injection due to expiry. Every action that changes inventory state is recorded.

**Events** are signals that trigger movements: low stock alerts that prompt reordering, expiry warnings that require removal from shelves. Events are the system's way of knowing when to act.

**Anomalies** are patterns that suggest something is wrong—constraints violated, impossibilities detected, risks identified.

### Anomaly Detection

The agent continuously monitors for signals of counterfeit risk:

**Geographic impossibilities.** If Batch 1001 of a medication is delivered to Lagos and the same batch appears in Kano the next day, this is physically impossible given Nigerian infrastructure. The system flags this as a high counterfeit risk.

**Price anomalies.** Medications selling at suspiciously low prices indicate potential counterfeits. The agent can ingest pricing data across facilities and flag outliers.

**Unauthorized distribution.** Medications circulating through channels not connected to authorized importers or distributors can be identified and flagged.

**Rapid turnover.** A facility acting as a pass-through for illegitimate stock—medications moving through without being dispensed to real patients.

**Ghost stock.** Paper trail manipulation where stock exists on records but not physically, or vice versa.

**Impossible quantities.** Stock injected without proper transfer records—counterfeit added to inventory.

The agent doesn't just detect single anomalies—it **correlates them to form hypotheses**:

```
Single Anomaly       → Flag for review
Multiple Correlated  → Potential counterfeit incident
Pattern Across Sites → Supply chain compromise
```

### Intelligent Facility Transfer

When a facility runs low on medication, the agent orchestrates intelligent transfers:

**Basic scenario:** A pharmacist types "I need 30 units of paracetamol." The agent searches for viable facilities within a reasonable distance that have sufficient stock. "Viable" means facilities with high reliability scores (based on anomaly history) and appropriate proximity. The agent recommends options; once accepted, the transfer is coordinated.

**Waste minimization:** If the nearest facility only has 10 units, but those 10 units are expiring within 15 days, the agent reasons differently. Rather than rejecting the partial match, it creates a sub-request: take the 10 near-expiry units (preventing waste) and source the remaining 20 from another facility. The agent optimizes across multiple objectives simultaneously.

**Cold chain awareness:** When a user requests insulin, the agent recognizes this is a cold storage medication. It immediately narrows the search to facilities with cold storage capabilities and prioritizes proximity to minimize cold chain transport risk. The agent decomposes the task based on medication characteristics.

```

### Why This Architecture?

**Centralized agent, distributed data collection.** One intelligent agent monitors all facilities from a central location. This lets the system see patterns across facilities—like that "Lagos to Kano in 2 hours" impossible movement—that distributed agents would miss.

**Built for Nigerian infrastructure.** The system assumes unreliable power, poor internet, cost-conscious facilities. One smart agent watching over hundreds of simple data collectors makes more sense than deploying full AI agents at every location.

---

## Technical Implementation

### Discrete Event Simulation

The simulation engine models realistic pharmaceutical supply chain dynamics using discrete event simulation (DES). Events sit in a priority queue ordered by time, the clock jumps to each event, state changes occur, and the cycle repeats.

Event types include:
- `HOURLY_TICK`: Dispense medications, check expiry
- `AGENT_CYCLE`: Run detection and reasoning (every 4 hours)
- `INJECT_*`: Test anomalies for validation

### Agent Reasoning

The agent combines several AI reasoning approaches:

**Planning:** Task decomposition, chain-of-thought reasoning, tree-of-thought exploration, reflection loops, and ReAct-style reasoning to handle complex scenarios.

**Memory:** Short-term memory for active conversations and transfers; long-term memory (ChromaDB) for facility reliability scores, historical patterns, and learned anomalies.

**Tool integration:** The agent has access to tools for querying inventory, logging hypotheses, initiating transfers, and potentially integrating with the NAFDAC Green API for verification.

### Database Schema

```sql
-- Core reference data
medications, companies, facilities, brands, batches, inventory

-- Operational data (generated by simulation)
movements, events, anomalies

-- Indexes for common queries
idx_movements_batch, idx_movements_facility, idx_movements_timestamp
idx_anomalies_type, idx_events_type
```

The schema separates static reference data (seeded) from operational data (generated through simulation). You don't seed movements, events, or anomalies because they are results of system behavior, not initial state—seeding them would break causality.

---

## Project Structure

```
medguard/
├── src/
│   └── medguard/
│       ├── __init__.py
│       ├── data/
│       │   ├── seed/           # Static reference data
│       │   └── generators/     # Data generation logic
│       ├── db/
│       │   ├── schema.sql
│       │   └── database.py
│       ├── detection/
│       │   ├── events.py
│       │   └── anomalies.py
│       ├── simulation/
│       │   └── engine.py
│       └── agent/              # Coming soon
│           └── reasoning.py
├── pyproject.toml
└── README.md
```

---

## Current Status

| Component | Status |
|-----------|--------|
| Data Generators | ✅ Complete |
| Database Schema | ✅ Complete |
| Simulation Engine | ✅ Complete |
| Event Detection | ✅ Complete |
| Anomaly Detection | ✅ Complete |
| Agent Reasoning | 🔄 In Progress |
| Dashboard | 📋 Planned |
| API Layer | 📋 Planned |

---

## Why Simulated Data?

This system uses realistic synthetic data modeling Nigeria's pharmaceutical supply chain—50 facilities across 6 cities, 50+ medications across therapeutic classes, and simulated batch movements. The data generator intentionally injects anomalies (impossible transfer speeds, unauthorized distribution channels) to demonstrate detection capabilities.

This approach allows reproducible demonstration without requiring access to proprietary pharmacy data. The detection algorithms are data-source agnostic—in production, MedGuard would connect to real pharmacy systems, logistics tracking, and regulatory databases.

---

## The Bigger Picture

MedGuard doesn't claim to solve the pharmaceutical supply chain crisis. It asks a more modest question: **given that we can't immediately fix fragmented infrastructure, what intelligent interventions can reduce harm right now?**

By monitoring for counterfeit signals, coordinating transfers to prevent stockouts, and minimizing waste from expiring medications, an autonomous agent can act as a safeguard layer—making the system more resilient without requiring the system itself to change.

The agent is only as intelligent as the data it receives. But with the right data infrastructure, this approach could meaningfully reduce the prevalence of counterfeit medications in Nigeria and, eventually, across Africa.

---

## Future Vision

**Consumer verification.** Patients could point their smartphone at a medication and trace its journey through the supply chain. The agent would verify registration, check for anomalies, and report confidence levels.

**Regulatory integration.** A unified database would benefit regulators, supply chain managers, and patients alike. Like how MTN knows every active number on its network, the pharmaceutical system could track every medication batch from importation to patient.

**Cross-industry extension.** The same logic—separating data from intelligence, monitoring for anomalies, coordinating transfers—could apply to agricultural supply chains or other domains where authenticity and availability matter.

**Continental scale.** Because the agent works on data rather than country-specific logic, the system can expand across Africa as data sources become available.

---

## About

Built by a Nigerian pharmacist who got tired of watching patients walk out of hospitals empty-handed, heading toward open markets where counterfeit drugs thrive.

The question that drives this project: **How can I help, using what I know and what I can build?**

---
---

## Acknowledgments

This project is being developed for the Gemini 3 Developer Competition. It uses Google's Gemini API for agent reasoning.

## Resources
- https://stackoverflow.com/questions/18387209/sqlite-syntax-for-creating-table-with-foreign-key
- https://www.sqlite.org/foreignkeys.html#fk_basics
- https://stackoverflow.com/questions/65388213/why-is-pathlib-path-file-parent-parent-sensitive-to-my-working-directory
- https://stackoverflow.com/questions/35717263/how-threadsafe-is-sqlite3
- https://www.sqlite.org/threadsafe.html
- https://en.wikipedia.org/wiki/ACID
- https://en.wikipedia.org/wiki/Thread_safety
- https://lilianweng.github.io/posts/2023-03-15-prompt-engineering/
- https://ai.google.dev/gemini-api/docs
- https://www.youtube.com/watch?v=2K1VsnGlCoI&t=454s
- https://www.reddit.com/r/learnpython/comments/1j4ia9n/when_should_i_use_a_list_dictionary_tuple_or_set/
- 



