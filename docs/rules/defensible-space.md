# California Defensible Space: EmberScan Rules Reference

> **Disclaimer.** EmberScan flags *likely* hazards that it sees in a walkaround video. It **never certifies compliance** with PRC 4291, Gov. Code 51182, Title 14 CCR, a local ordinance or an insurer's requirements. Only the agency responsible for fire protection can decide compliance, and it does so by inspection: CAL FIRE in the State Responsibility Area, the local fire agency in the Local Responsibility Area. This document is not legal advice.

Machine-readable rule pack: [`us-ca.json`](./us-ca.json) (`pack_id: us-ca`, version `2026-10-26`).

---

## Status / last verified 2026-10-26

**In short:** no statewide Zone 0 (0–5 ft "ember-resistant zone") rule is in force today. The Board withdrew its August package from OAL review on 2026-09-08. It has now put a revised package on its **November 5, 2026** agenda to re-adopt and resubmit to OAL. The Zone 1 and Zone 2 rules in current law still apply.

| Date | Event | Source (how read) |
|---|---|---|
| 2020 | AB 3074 adds the "ember-resistant zone within 5 feet" to PRC 4291 and GC 51182 | Board guidance doc (Sept 2026) |
| 2025-10-13 | AB 1455 (Stats. 2025, ch. 731) amends PRC 4291 and GC 51182, effective this date. This is the current statute text. | leginfo history notes (in-app browser) |
| 2026-08-19 | Board adopts the Zone 0 emergency regulations and the updated Zones 0–2 guidance document | Aug 19, 2026 rule plead; guidance doc cover page |
| 2026-08-28 | Package goes to OAL as file **2026-0828-03E**, "Zone 0 Defensible Space" | OAL file number; OAL Recent Actions |
| 2026-09-08 | **Board withdraws the package.** OAL never ruled on it. | OAL *Recent Actions Taken on Emergency Regulations* (fetched 2026-10-26) |
| Sept 2026 | Board posts "Guidance for establishing and maintaining defensible space for Zones 0–2". The cover says it was adopted 2026-08-19, leaves the effective date blank, and says it will be published officially when the regulations take effect. | Board Zone 0 page (in-app browser) |
| 2026-10-22 | Latest entries on OAL's lists. There is **no Zone 0 package** on the emergency under-review list, the regular under-review list or the recent-actions list after 09-08. | OAL pages (fetched 2026-10-26) |
| **2026-10-23** | **NEW:** Board posts its Nov 4–5 agenda. **Item 13** (Nov 5, 9:00 a.m., Sacramento) is "Ember-Resistant Zone Emergency Regulations … Updated Rule Text for Clarity and Resubmission of Rule Package to OAL". The Board will consider adopting an updated Finding of Emergency and final rule text. | Nov 2026 Board agenda PDF |
| 2026-10-26 | The Board's Zone 0 page still says staff "continue to work with" OAL on final review. No updated rule text for item 13 is posted in the November binder yet. | Board page and binder index (in-app browser) |
| — | **Zone 0 effective date: none.** An emergency regulation takes effect only after OAL approves it and files it with the Secretary of State (guidance appendix, footnote 1). | — |

**What changed since the 2026-10-21 reference**
1. The resubmission is now scheduled: Board agenda item 13 for 2026-11-05, posted 2026-10-23. On Oct 21 it was reported as "not refiled". It still is not refiled, but a date to re-adopt is now set.
2. The Board's updated guidance document (Sept 2026, adopted 2026-08-19) is on the Board's page. PRC 4291(g)(1) requires the guidance update before Zone 0 can take effect for new structures, so this partly answers the earlier statutory-timing question. See VERIFY.
3. I read the primary statute text directly from leginfo, which earlier runs could not reach. Both PRC 4291 and GC 51182 show "Amended by Stats. 2025, Ch. 731 (AB 1455), effective October 13, 2025."
4. CAL FIRE's ReadyForWildfire page still says Zone 0 is "not legally required yet."

**How each source was read.** WebFetch and curl got HTTP 403 from leginfo.legislature.ca.gov, bof.fire.ca.gov and readyforwildfire.org. I read those pages in the in-app browser (a normal browser session), so the text above comes from the official sites. I read 14 CCR 1299.01–1299.05 from the **Cornell LII mirror** (law.cornell.edu); the official Westlaw CCR site was not fetched. Board PDFs come from the Board's own CDN (azureedge.net links on bof.fire.ca.gov). OAL pages were fetched directly. I did not find a State Fire Marshal funding finding under PRC 4291(h).

---

## Where these rules apply

| Area | Law | Enforced by | Zone 0 (draft) scope |
|---|---|---|---|
| **SRA**, any FHSZ class (Moderate, High, Very High) | PRC 4291; 14 CCR 1299.01–1299.05 | CAL FIRE | Every "Building or Structure" |
| **LRA, Very High FHSZ** designated locally under GC 51179 | GC 51182; draft 14 CCR 1298.01–1298.04 | Local fire agency | "Occupied dwelling or occupied structure" |
| LRA Moderate/High, or unzoned | Not covered by GC 51182 | Local ordinances may still apply | Not covered |

- **Local alternatives (LRA).** Under GC 51182(f), a local agency may adopt an ordinance with alternative practices that have "substantially similar practical effects". It may also adopt stricter rules. An owner who follows the approved local alternative is not in violation. Draft 1298.03 adds two conditions: the governing body must approve the alternatives, and the fire agency must support them with a finding. Allowed grounds include lot size, density, topography and compliance with the CA Wildland-Urban Interface Code. The Board's guidance says local Zone 0 ordinances already exist in Los Angeles, San Diego, Berkeley, Shasta County, Ventura County and South Lake Tahoe.
- **Greater distances.** State or local law may require more than 100 ft (PRC 4291(a)(1)(B), GC 51182(a)(1)(B)). Insurers may require more only on a designated fire expert's finding (subd. (a)(1)(C); 14 CCR 1299.04).
- **Property line.** Every zone stops at the property line. Work on a neighbor's land needs their written consent (PRC 4291(b), GC 51182(b)).
- **Neighbors.** Under the draft, a new structure or ADU on a neighbor's lot does not enlarge your obligation (draft 1299.03(c), 1298.04(a)).
- **Structure and outbuilding definitions.** A "Building or Structure" has a permanent roof on walls or posts (14 CCR 1299.02(a)). An "Outbuilding" is under 120 sq ft and not used for habitation, and it does not count as a structure for measuring zones (1299.02(c)). Under the draft, attached decks, stairs and pergolas count as part of the structure, including self-supporting ones within 1 ft of it. Noncombustible patios do not count.
- **Exemptions.** The SFM may exempt structures whose exteriors are entirely nonflammable (PRC 4291(c)). The Board says it cannot create other exemptions, such as for historic buildings.
- **Funding gate.** CAL FIRE may not change inspection practices, forms or enforcement for the ember-resistant zone until the State Fire Marshal posts a written finding that the Legislature funded it (PRC 4291(h)).

---

## Zones and distance bands

| Zone | Distance today (in force) | Distance once Zone 0 takes effect |
|---|---|---|
| **Zone 0**, ember-resistant | Named in statute ("within 5 feet"), but **no rule in force** | 0–5 ft from the exterior wall, roof, attached deck, stairs or pergola, or to the property line |
| **Zone 1**, lean, clean and green | **0–30 ft** (14 CCR 1299.03) | 5–30 ft |
| **Zone 2**, reduced fuel | 30–100 ft, not past the property line | unchanged |

The statute sets 100 ft of defensible space, with "more intense" fuel reduction from 5 to 30 ft (PRC 4291(a)(1)(A); GC 51182(a)(1)(A)). The engine evaluates adopted Zone 1 rules over 0–30 ft.

---

## Requirements in force today (status `adopted`)

Sources: [PRC 4291](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=PRC&sectionNum=4291), [GC 51182](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=GOV&sectionNum=51182), [14 CCR 1299.03](https://www.law.cornell.edu/regulations/california/14-CCR-1299.03) (operative 2013-07-01; litter subsection 2013-10-01).

**Statute, whole defensible space**
- **ALL-01:** Remove any part of a tree within **10 ft of a chimney or stovepipe outlet**. PRC 4291(a)(2); GC 51182(a)(2).
- **ALL-02:** Keep the **roof** clear of leaves, needles and other plant material. (a)(4).
- **ALL-03:** Plants next to or hanging over the building must have **no dead or dying wood**. (a)(3). Manual review.
- **ALL-04:** Keep **100 ft** of defensible space, with fuels spaced so a wildfire is unlikely to ignite the structure. Single well-pruned specimen trees are exempt. (a)(1)(A). Manual review.

**Zone 1 (0–30 ft)**, 14 CCR 1299.03(a)
- **Z1-01:** Remove dead or dying grass, plants, shrubs, branches, leaves, weeds and needles.
- **Z1-02:** Keep rain gutters clear of that material.
- **Z1-03:** Remove dead branches that hang over the roof, sit near windows or touch walls. Manual review.
- **Z1-04:** Move exposed **firewood piles** out of Zone 1 unless they are fully covered with fire-resistant material.
- **Z1-05:** Remove flammable plants and items under or next to combustible decks, balconies and stairs.

**Zone 2 (30–100 ft)**, 14 CCR 1299.03(b)
- **Z2-01:** Remove dead and dying woody surface and aerial fuels.
- **Z2-02:** Loose litter may stay up to **3 in** deep. Manual review, because depth can't be measured from video.
- **Z2-03:** Cut annual grasses and forbs to **≤ 4 in**.
- **Z2-04:** Exposed wood piles need **10 ft** of clearance to bare mineral soil in every direction.
- **Z2-05:** Space shrubs and trees horizontally and vertically, by the Fuel Separation or Continuous Tree Canopy method. Manual review; distances come from guidance.

**Zones 1 and 2**, 14 CCR 1299.03(c)
- **Z12-01 / Z12-02:** **Propane tanks** and **outbuildings** need **10 ft** of bare mineral soil, plus **another 10 ft** with no flammable vegetation.
- Not encoded as a rule: protect water quality. Don't clear to bare soil near streams, limit heavy equipment, and minimize soil disturbance on steep slopes.

---

## Zone 0, proposed (status `proposed`, effective date **null**)

Source: the Board's [Aug 19, 2026 rule plead](https://34c031f8-c9fd-4018-8c5a-4159cdff6b0d-cdn-endpoint.azureedge.net/-/media/bof-website/board-meeting-information/monthly-board-binder-materials/archive/2026-monthly-board-binder-materials-workshop-archives/august-2026/full/full-8a-zone-0-regulation-summary--rule-plead-august-2026.pdf), draft 14 CCR 1299.03(d) (SRA) and 1298.04(b) (LRA). The Board's 2026-11-05 "updated rule text for clarity" may change this text.

| ID | Draft requirement (paraphrased) | Existing-structure phase-in |
|---|---|---|
| Z0-01 | Nothing combustible in the 5 ft: no fallen leaves or needles, bark or wood-chip mulch, or debris. An inspector may allow temporary mulch for erosion control. | 3 yr |
| Z0-02 | Nothing combustible and no vegetation under decks, balconies, pergolas or stairs | 3 yr |
| Z0-03 | No firewood stored in Zone 0 | 3 yr (guidance appendix lists it as immediate; see VERIFY) |
| Z0-04 | No live tree branches under the eaves | immediate |
| Z0-05 | Remove ladder fuels on trees: lowest **6 ft** or **⅓ of tree height**, whichever is smaller. Also remove ladder fuels within 5 ft above the roof. | 3 yr |
| Z0-06 | Live branches at least **5 ft above the roof** | 3 yr |
| Z0-07 | Live branches at least **1 ft from walls**. The LRA text adds "where there is no eave". | 3 yr |
| Z0-08 | **Safety zone with no vegetation:** under the eaves, at least 1 ft out from the wall and up to 5 ft. Trees are excepted. | 3–5 yr |
| Z0-09 | No vegetation within **2 ft** of windows, doors or vents. The LRA text also lists posts. | 3–5 yr |
| Z0-10 | No vegetation within **5 ft** of an attached deck, stairs or pergola | 3–5 yr |
| Z0-11 | Outside the buffers: lawns and ground covers kept **< 3 in** tall | 3–5 yr |
| Z0-12 | Outside the buffers: non-woody plants **3–18 in** tall, in clumps of **≤ 1 sq ft**, spaced **1.5×** the tallest plant's height | 3–5 yr |
| Z0-13 | Potted non-woody plants **≤ 18 in** tall, in unattached noncombustible pots of **≤ 5 gal**, spaced 1.5× height | 3–5 yr |
| Z0-14 | No woody shrubs. My reading: the draft allows only non-woody plants, and existing trees may stay if maintained. | 3–5 yr |
| Z0-15 | Fences and gates attached to the structure, or within 1 ft of it: first **5 ft** noncombustible | 3–5 yr |
| Z0-16 | No **new** combustible fences or gates within 5 ft; repairs with the same material are allowed. Manual review. | 3–5 yr |
| Z0-17 | Outbuildings in Zone 0 only if built entirely of noncombustible materials | 3–5 yr |

**Trees.** Existing trees may stay in Zone 0 if they are maintained. That means no dead branches (ALL-03), 10 ft from chimneys (ALL-01), plus Z0-04 to Z0-07. "Tree" means at least 4 in diameter at 4.5 ft and at least 15 ft tall at maturity. New structures must meet everything on the effective date. "Noncombustible" means passing ASTM E136 (CWUI Code 501.4.1).

## Guidance only (status `guidance`)

These are not regulations. EmberScan shows them as advice.
- **Z0-18:** No new trees planted in Zone 0. The Board ties this to the 2025 CWUI Code, which keeps new tree canopy 10 ft from structures. Source: [Board guidance, Sept 2026](https://34c031f8-c9fd-4018-8c5a-4159cdff6b0d-cdn-endpoint.azureedge.net/-/media/bof-website/projects-and-programs/defensible-space-zones-0-1-2/zonezeroguidancedocseptember-final-2026.pdf), p. 24. Manual review.
- **Z0-19:** Keep combustible furniture, mats and planters near the house to a minimum. Source: [ReadyForWildfire](https://readyforwildfire.org/prepare-for-wildfire/defensible-space/).
- **Z0-20:** Move vehicles, boats and RVs out of Zone 0. Source: ReadyForWildfire. The page also suggests moving garbage and recycling bins; that has no hazard class yet.
- **ALL-05:** Vents with 1/8 in metal mesh or ember-resistant vents. This is home hardening (guidance Table 1). Manual review.
- **Z2-06:** Plant spacing by slope. Tree canopies 10, 20 or 30 ft apart for slopes of 0–20%, 20–40% and over 40%. Shrubs 2×, 4× or 6× their height apart. Source: guidance Table 2, from the 2006 General Guidelines. Manual review, since slope isn't measured.
- **Z2-07:** Lowest tree branches about 3× shrub height above the shrubs. Under continuous canopy, prune trees 6–15 ft up. Manual review.
- Not encoded: limit tall woody plants just outside Zone 0 for about another 5 ft. Keep a 6 in noncombustible strip at the base of the wall. ReadyForWildfire also suggests 10 ft between trees in Zone 1.

---

## Open questions / VERIFY

1. **Nov 5, 2026 Board meeting, item 13.** Did the Board adopt the updated Finding of Emergency and rule text? When does it resubmit (new OAL file number), and what changed "for clarity"? Re-diff Z0-* against the new text and recheck OAL under-review daily after Nov 5. Emergency review takes about 10 days, and the effective date is the date of filing with the Secretary of State.
2. **Phase-in conflict for draft (d)(6)–(10).** The SRA text says 5 years, or a Director timeline of at least 3 years. The LRA text says 3 years, or up to 5 on a local timeline. The guidance appendix says "3 years, or 5 if local agency/CAL FIRE sets timeline." The pack uses `3-5y`.
3. **Firewood timing.** Draft (e)(2) makes (d)(2) and (d)(5)(A)–(C) immediate for existing structures. The guidance appendix lists firewood removal as immediate, but firewood is (d)(4), which is in the 3-year group.
4. **Statutory effective date.** PRC 4291(g)(1) delays the ember-resistant zone for new structures until both the regulations and the guidance are updated. (g)(2) delays existing structures 3 more years. The draft sets new structures at the effective date and some existing-structure items as "immediate". GC 51182 has no matching (g). Confirm how the 3-year statutory delay squares with the draft's immediate and 5-year items, especially in the SRA.
5. **PRC 4291(h) funding finding.** No posted State Fire Marshal finding was found. Without it, CAL FIRE cannot change inspections to enforce Zone 0 even after the rule takes effect.
6. **14 CCR text.** Confirm 1299.01–1299.05 against the official Westlaw CCR (read here only on the Cornell mirror). Confirm whether "Property Inspection Guide" references changed.
7. **Branch-to-wall rule.** In the SRA draft, the 1 ft branch-to-wall rule lacks the LRA's "where there is no eave". Is the difference intentional?
8. **Z0-14 (no woody shrubs)** is my reading of (d)(6)–(7), not an express sentence. Confirm with the final text or Board FAQ.
9. **Measurement origin for the eave rule.** The draft measures from the wall "out at least one foot or to the eave (whichever is farthest, up to five feet)". Confirm how eave width is measured (dripline vs. fascia) before shipping the `ft: "eave"` checks.
10. **Local ordinances** (LA, San Diego, Berkeley, Shasta, Ventura, South Lake Tahoe) are not in this pack. Users in those areas need a local pack.
