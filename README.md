# InkTime – Proiect TSC 2026

## Summary
Acest proiect conține schematicul, PCB-ul, fișierele de manufacturare și modelul 3D
pentru dispozitivul InkTime, realizate conform cerințelor din OCW.

## Structure
- `Hardware/` – fișierele de schematic și PCB
- `Manufacturing/` – Gerber, BOM, Pick&Place
- `Mechanical/` – ansamblu 3D (PCB + componente + carcasă)
- `Images/` – randări și capturi
- `README.md`, `LICENSE`

## Design Notes
- PCB cu **4 straturi**: Top/Bottom pentru semnale, Route2 = GND plane, Route63 = Power plane.
- **Trasee power**: 0.3 mm; **semnale**: min 0.15 mm.
- **Antena** amplasată la margine, cu keepout (fără cupru) pe toate layerele.
- Condensatoarele de decuplare sunt plasate cât mai aproape de pinii de alimentare.
- Toate componentele sunt pe **TOP**.

## DRC / ERC
- ERC: [0 erori / 44 warnings]
- DRC: [Overlap - 65, Drill Clearance - 3, Cooper Clearance - 10, Cooper - Restrict Clearance - 4, Board Outline Clearance - 2, Air Wire - 26]

## Known Issues / Deviations
- [„Au rămas 26 airwires”]

## Test Plan
- DRC cu fișierul OCW
- Verificare keepout antenă
- Verificare rutare power și clearance

## Files
- Schematic: `Hardware/[nume].fsch`
- PCB: `Hardware/[nume].fbrd`
- Gerber: `Manufacturing/gerbers.zip`
- BOM: `Manufacturing/[nume].bom`
- CPL: `Manufacturing/[nume].cpl`
- 3D Assembly: `Mechanical/[nume].step` / `Mechanical/[nume].f3z`
