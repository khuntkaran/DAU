# Rule table

Researched 2026-11-01. The MNRE and PIB sites could not be opened directly during research, so values come from search excerpts of those pages and from news reports.

Status meanings:

- `confirmed`: official source excerpt and independent reports agree.
- `verify`: reported by a source, not confirmed against a primary document. Check before the demo.
- `assumption`: our own default, not a scheme rule. Always labelled as an estimate in the UI.

| ID | Rule | Value | Source | Status |
|---|---|---|---|---|
| `CFA_SLAB_1` | CFA for the first 2 kW | ₹30,000 per kW | S1 | confirmed |
| `CFA_SLAB_2` | CFA for the third kW | ₹18,000 per kW | S1 | confirmed |
| `CFA_CAP` | No extra CFA above 3 kW | ₹78,000 maximum | S1 | confirmed |
| `CFA_BASIS` | 60% of benchmark to 2 kW, 40% for the next kW | Explains the slabs | S1, S2 | confirmed |
| `CFA_PRO_RATA` | Fractional kW earns the slab rate pro rata, so 2.5 kW gets ₹69,000 | Linear | None | assumption |
| `CFA_SPECIAL` | Special category states and UTs | ₹33,000 per kW, then ₹19,800 per kW, ₹85,800 maximum | S4, S5 | verify |
| `BENCHMARK_COST` | Benchmark cost | ₹50,000 per kW to 2 kW, ₹45,000 per kW after | S2 (draft) | verify |
| `SIZE_BANDS` | Suitable size by monthly use | 0-150 units: 1-2 kW; 150-300: 2-3 kW; above 300: 3 kW or more | S3 | confirmed |
| `GENERATION` | Monthly generation per kW | 120 kWh, about 4 kWh a day | S7 | assumption |
| `ROOF_AREA` | Shadow-free roof area per kW | 10 m² | S6 | verify |
| `TARIFF_DEFAULT` | Grid tariff when the household gives none | ₹6.50 per kWh | None | assumption |
| `DCR_MODULES` | Modules must meet the domestic content requirement | Quote must state DCR | None | verify |
| `VENDOR_REGISTERED` | Vendor must be registered on the national portal | Quote must state registration | None | verify |
| `MAINTENANCE_5Y` | Vendor provides five years of maintenance | Quote must state it | None | verify |

`GENERATION` follows the design document, which calls 120 an MNRE rule of thumb. Research found no MNRE benchmark for it, only vendor estimates of 110-130 kWh, so show it as an assumption, not a scheme rule. Keep it configurable. Official PIB material implies a lower figure, about 100 kWh from "3 kW gives about 300 units".

`DCR_MODULES`, `VENDOR_REGISTERED` and `MAINTENANCE_5Y` come from general knowledge of the scheme and were not found in this research. Confirm them in the guidelines, or treat them as advice to the household, not as scheme rules.

Stated out of scope for the demo: group housing and RWA rates (₹18,000 per kW, S4), state top-up subsidies, and loans.

## Formulas

```
subsidy(kw)   = min(kw, 2) × 30,000 + clamp(kw − 2, 0, 1) × 18,000
max size      = roof area × usable fraction / ROOF_AREA
system size   = monthly_units / GENERATION, rounded to the nearest 0.5 kW, then capped at max size
net cost      = max(price − subsidy, 0)
annual saving = min(annual generation, annual consumption) × tariff
payback years = net cost / annual saving, null when saving is 0
```

The usable fraction comes from the photo assessment. Before that finishes, or if AI fails, use 0.8 and label it an estimate.

## Golden example

Ahmedabad, 330 units a month, 40 m² roof, quote of ₹1,85,000, tariff ₹6.50.

```
raw size      = 330 / 120 = 2.75 → 3.0 kW     roof cap 40 × 0.8 / 10 = 3.2 kW, so no cap
subsidy       = ₹78,000
net cost      = ₹1,07,000
generation    = 3 × 120 × 12 = 4,320 kWh a year
consumption   = 330 × 12 = 3,960 kWh a year
annual saving = 3,960 × 6.50 = ₹25,740
payback       = 1,07,000 / 25,740 = 4.2 years
```

The design document shows ₹28,080 and 3.8 years here. That is an arithmetic error, because it uses generation instead of the smaller consumption figure.

## Sources

- S1: [PIB, Cabinet approves PM-Surya Ghar](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2010133&reg=48&lang=2)
- S2: [MNRE draft guidelines for PM-Surya Ghar](https://solarrooftop.pmsuryaghar.gov.in/notification/172_notification.pdf)
- S3: [PIB, PM Surya Ghar: India's Solar Revolution](https://www.pib.gov.in/PressReleaseIframePage.aspx?PRID=2111106&reg=48&lang=2)
- S4: [Mercom, Housing societies CFA](https://mercomindia.com/housing-societies-new-rooftop-solar-program)
- S5: [Quick Estimate, PM Surya Ghar FAQ](https://quickestimate.co/blog/pm-surya-ghar-faq)
- S6: [Secured Engineers, shadow-free area calculator](https://www.securedengineers.com/solar-shadow-free-area-calculator/)
- S7: Team design document, [SuryaSetu Architecture.html](../../../../SuryaSetu%20Architecture.html), not an official source
- Possible later update to check: [SolarQuarter, MNRE subsidy guidelines, September 2026](https://solarquarter.com/2026/09/01/pm-surya-ghar-scheme-mnre-details-rooftop-solar-subsidy-guidelines-for-residential-consumers/)
