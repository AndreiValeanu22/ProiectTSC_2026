# InkTime – Proiect TSC 2026

## Rezumat

Acest depozit conține schematica nativă, placa de circuit imprimat, livrabilele de manufacturare, materialele mecanice parțiale și documentația vizuală pentru dispozitivul **InkTime**, aliniate structurii cerute în ghidul de proiect de pe [OCW – Proiect 2026](https://ocw.cs.pub.ro/courses/tsc/proiect2026).

## Conformitate cu structura de încărcare (OCW)

| Cerință OCW | Conținut în acest depozit |
|-------------|---------------------------|
| `Hardware/` – schematic `.sch` | `ProjectTSCEtapa1.sch` |
| `Hardware/` – placă `.brd` | `InkTime v6_PCB_Partea2.brd` |
| `Hardware/` – print schematic `.pdf` | `InkTime_Schematic.pdf` (compus din capturile din `Images/`) |
| `Manufacturing/` – `gerbers.zip` | `gerbers.zip` (straturi de cupru 1, 2, 15, 16; profil; fișier de găuri; vezi nota de mai jos) |
| `Manufacturing/` – BOM `.bom` | `InkTime.bom` |
| `Manufacturing/` – Pick&Place `.cpl` | `InkTime.cpl` |
| `Mechanical/` – ansamblu 3D | `ProjectTSCEtapa1.f3z`, `InkTime_Case.f3z`, modele `.STEP` pentru componente, `InkTime v6_PCB_Partea2.3mf` (vezi secțiunea *Modelare 3D*) |
| `Images/` | Randări și capturi (PCB, schematic, previzualizări 3D) |
| `LICENSE`, `README.md` | Prezente |

### Fișierul `InkTime.fbrd` din `Hardware/`

`InkTime.fbrd` este **fișierul de referință** furnizat prin arhiva OCW pentru recomandări de amplasament mecanic; **nu** înlocuiește proiectul de placă editabil. Proiectul de placă livrat pentru evaluare este `InkTime v6_PCB_Partea2.brd`. Fișierul `InkTime.fbrd.brd`, care genera confuzie în review (nu corespundea unui flux clar schematic → placă), a fost **eliminat** din depozit.

## Structura directoarelor

- `Hardware/` – schematic, placă, PDF-ul schemei.
- `Manufacturing/` – `gerbers.zip`, `InkTime.bom`, `InkTime.cpl` (generate și re-generabile cu `tools/build_ocw_deliverables.py` din placa curentă).
- `Mechanical/` – proiecte Fusion (`.f3z`), model 3MF al PCB-ului, modele STEP pentru componente (ex.: conector USB-C, celulă baterie).
- `Images/` – capturi pentru documentație și pentru compunerea PDF-ului schemei.
- `tools/` – scriptul de generare a livrabilelor de manufacturare și a PDF-ului schemei.

## Notă privind `gerbers.zip`

Arhiva a fost produsă **automat din fișierul `.brd`** (straturi de cupru, poligoane de plan de masă incluse în XML, profil, găuri din definițiile de via). Este potrivită pentru verificare structurală și pentru fluxuri de tip preview. Pentru comandă de serie la fabrică, se recomandă **validarea și, dacă este necesar, re-exportul** din Fusion Electronics cu setările CAM și regulile DRC oficiale ale cursului, astfel încât să fie incluse explicit și straturile auxiliare (mască de lipire, pastă, serigrafie), conform [tutorialului OCW pentru Gerber](https://ocw.cs.pub.ro/courses/tsc/proiect2026).

## Modelare 3D (ansamblu complet)

Ansamblul explodat complet (PCB + baterie + display + carcasă), în format **STEP** unificat, **nu este inclus**, deoarece modelarea integrală a ansamblului final nu a putut fi finalizată în timpul disponibil. În schimb, depozitul conține:

- proiecte Fusion (`ProjectTSCEtapa1.f3z`, `InkTime_Case.f3z`);
- export 3MF al PCB-ului cu componente (`InkTime v6_PCB_Partea2.3mf`);
- modele **STEP** pentru subansamble și componente (denumiri derivate din catalog; consultați tabelul de mai jos).

| Fișier | Rol presupus în proiect |
|--------|-------------------------|
| `KH-TYPE-C-16P--3DModel-STEP-269445.STEP` | Model 3D conector USB-C |
| `EVP-AKE31A--3DModel-STEP-56544.STEP` | Model 3D baterie / celulă (EVP-AKE31A) |
| `5034802400--3DModel-STEP-56544.STEP` | Model 3D componentă suplimentară (cod producător) |
| `InkTime v6_PCB_Partea2.3mf` | PCB cu componente (3MF) |
| `ProjectTSCEtapa1.f3z`, `InkTime_Case.f3z` | Proiecte Fusion (ansamblu parțial / carcasă) |

## Note de proiectare și decizii documentate

### Ajustări la nivelul butoanelor

Amplasamentul și geometria **butoanelor** au fost **revizuite incremental** pe stratul de placă, în corelație cu recomandările mecanice din materialele OCW, cu scopul de a **atenua conflictele dimensionale** și de a **reduce severitatea unor erori raportate de DRC** (ex.: depășiri de contur sau interferențe cu zonele de toleranță ale mufei USB-C). Modificările au fost limitate la domeniul necesar menținerii alinierii funcționale cu carcasa, fără a altera schema logică a sistemului.

### Rutare incompletă (airwires)

Procesul de rutare este **în desfășurare**: în stadiul curent al plăcii există **douăzeci și șase de conexiuni nerealizate complet** (afișate de editor ca *airwires*). Cauza principală este **densitatea foarte ridicată** a interconexiunilor în proximitatea circuitelor integrate în capsulă fină (inclusiv sub zona BGA), coroborată cu **restricții severe de spațiu** pe straturile exterioare și cu necesitatea respectării lățimilor minime pentru alimentare și a keepout-ului antenei. În aceste condiții, finalizarea tuturor traseelor ar fi impus fie relaxarea unor constrângeri de proiect (nepermisă de cerințele cursului), fie o re-arhitectură suplimentară a stratului de rutare; varianta adoptată păstrează integritatea regulilor critice și acceptă explicit restul conexiunilor ca **datorie tehnică** pentru o iterație ulterioară.

## Note de proiect (PCB)

- Patru straturi: Top și Bottom pentru semnale, **Route2** ca plan de masă, **Route15** ca plan de alimentare (conform denumirilor din fișierul `.brd`).
- Trasee de putere: **0,3 mm**; semnale: **minimum 0,15 mm**.
- Antenă la marginea plăcii, cu **keepout** (fără cupru) pe straturile relevante.
- Condensatoare de decuplare cât mai aproape de pini de alimentare.
- Componente plasate exclusiv pe **TOP**.

## ERC / DRC (stadiu curent)

- ERC: **0 erori** / **44 avertismente**.
- DRC (ultima rulare documentată): *Overlap* – 65; *Drill Clearance* – 3; *Copper Clearance* – 10; *Copper – Restrict Clearance* – 4; *Board Outline Clearance* – 2; *Air Wire* – 26. Rezultatele trebuie re-verificate după fiecare modificare a plăcii sau după re-exportul CAM.

## Plan de verificare

- DRC cu fișierul de reguli OCW.
- Verificare keepout în zona antenei.
- Verificare rutare de putere și clearance.
- Regenerare livrabile: `python tools/build_ocw_deliverables.py`.

## Regenerarea livrabilelor

Din rădăcina depozitului, cu Python 3 și pachetele `gerbonara`, `reportlab`, `pillow` instalate:

```bash
python tools/build_ocw_deliverables.py
```

## Licență

Vezi `LICENSE` (MIT).
