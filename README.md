# ⚡ Multi-Zone Redispatch 2.0 & Dynamic Line Rating (DLR) Congestion Engine

> **Physics-based AC power flow simulation and economic optimization framework to quantify grid congestion relief, curtailment mitigation, and redispatch savings across German transmission corridors.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Pandapower](https://img.shields.io/badge/Grid%20Engine-Pandapower-orange.svg)](https://www.pandapower.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://redispatch-dlr-congestion-engine-9kenvhm2nbhzprg9mprj7i.streamlit.app/)

---

## 📌 Executive Summary

Under Germany's **Redispatch 2.0** regulatory mechanism, heavy wind feed-in from northern coastal hubs regularly overloads static seasonal transmission limits ($I_{\text{max}}$). This forces transmission system operators (TSOs) to mandate expensive **downward renewable curtailment** in the north and compensatory **upward conventional ramping** in the south.

This engine demonstrates how **Dynamic Line Rating (DLR)** unlocks latent transmission capacity during high wind conditions—reducing congestion costs and avoiding green power curtailment.

---

## 🔬 Technical Methodology

### 1. IEEE 738 Dynamic Thermal Line Rating Formulation
Static line ratings assume worst-case environmental conditions (e.g., $T_{\text{amb}} = 40^\circ\text{C}$, low wind speed). The DLR engine dynamically computes convective and radiative cooling:

$$I_{\text{DLR}} = I_{\text{base}} \cdot \sqrt{\frac{T_{\text{conductor,max}} - T_{\text{ambient}}}{T_{\text{conductor,max}} - T_{\text{reference}}}} \cdot \left(1.0 + 0.18 \cdot v_{\text{wind}}^{0.55}\right)$$

### 2. AC Power Flow Modeling (Pandapower)
A synthetic 4-bus 110 kV transmission corridor models the German north-to-south power flow:
* **Bus 1 (North Offshore Hub):** Slack node providing voltage reference.
* **Bus 2 (North Onshore Node):** High-penetration renewable wind cluster injection.
* **Bus 3 (Central Corridor):** Bottleneck transmission interface (Line 2–3).
* **Bus 4 (South Industrial Load):** Heavy demand center with flexible balancing units.

### 3. Redispatch 2.0 Economic Optimization
Congestion overloads on the corridor trigger cost evaluations:

$$\text{Redispatch Cost } (€) = \sum_{t=1}^{T} \Delta P_{\text{overload}}(t) \times \left(C_{\text{downward}} + C_{\text{upward}}\right)$$

Where $C_{\text{downward}} = 45\text{ €/MWh}$ (curtailment compensation) and $C_{\text{upward}} = 115\text{ €/MWh}$ (conventional unit activation).

---

## 📂 Repository Architecture

```text
redispatch-dlr-congestion-engine/
│
├── .github/
│   └── workflows/
│       └── ci.yml               # Automated PyTest CI/CD pipeline
├── src/
│   ├── __init__.py
│   ├── dlr_model.py             # IEEE 738 thermal line rating engine
│   ├── network_builder.py       # Pandapower 4-bus network topology
│   └── redispatch_optimizer.py  # Time-series AC power flow & cost solver
├── tests/
│   ├── __init__.py
│   └── test_redispatch.py       # Unit & integration test suites
├── app.py                       # Interactive Streamlit dashboard
├── redispatch_dlr_simulation.py # Standalone physics simulation script
├── requirements.txt
├── README.md
└── .gitignore
