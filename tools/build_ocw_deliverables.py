#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generează livrabile OCW din fișierul Eagle/Fusion `.brd`:
- Manufacturing/InkTime.bom (CSV, UTF-8)
- Manufacturing/InkTime.cpl (CSV tip JLC: Designator, Mid X, Mid Y, Layer, Rotation)
- Manufacturing/gerbers.zip — cupru, profil, găuri din XML; dacă există fișiere în
  Manufacturing/fusion_export/ (export CAM Fusion), sunt incluse cu prioritate (suprascriu numele identic).
- Hardware/InkTime_Schematic.pdf (din capturile PNG ale schemei)

Necesită: pip install gerbonara reportlab pillow
"""
from __future__ import annotations

import csv
import math
import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from gerbonara.apertures import CircleAperture, ExcellonTool
from gerbonara.excellon import ExcellonFile
from gerbonara.graphic_objects import Flash, Line, Region
from gerbonara.rs274x import GerberFile
from gerbonara.utils import MM, approximate_arc, sweep_angle

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
except ImportError as e:
    raise SystemExit("Instalează dependențele: pip install gerbonara reportlab pillow") from e


ROOT = Path(__file__).resolve().parents[1]
BRD_PATH = ROOT / "Hardware" / "InkTime v6_PCB_Partea2.brd"
IMG_SCH1 = ROOT / "Images" / "Schematic_part1.png"
IMG_SCH2 = ROOT / "Images" / "Schematic_part2.png"
OUT_BOM = ROOT / "Manufacturing" / "InkTime.bom"
OUT_CPL = ROOT / "Manufacturing" / "InkTime.cpl"
OUT_PDF = ROOT / "Hardware" / "InkTime_Schematic.pdf"
OUT_ZIP = ROOT / "Manufacturing" / "gerbers.zip"
FUSION_EXPORT_DIR = ROOT / "Manufacturing" / "fusion_export"
FUSION_SKIP_NAMES = frozenset({".gitkeep", "desktop.ini", "thumbs.db"})


def _eagle_arc_center(x1: float, y1: float, x2: float, y2: float, curve_deg: float) -> tuple[float, float] | None:
    dx = x2 - x1
    dy = y2 - y1
    chord = math.hypot(dx, dy)
    if chord < 1e-12:
        return None
    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2
    px = -dy / chord
    py = dx / chord
    theta = math.radians(abs(curve_deg))
    if theta < 1e-9:
        return None
    if abs(theta - math.pi) < 1e-6:
        return mx, my
    h = (chord / 2) / math.tan(theta / 2)
    s = 1.0 if curve_deg > 0 else -1.0
    return mx + s * h * px, my + s * h * py


def _wire_to_objects(elem: ET.Element) -> list:
    x1 = float(elem.get("x1", "0"))
    y1 = float(elem.get("y1", "0"))
    x2 = float(elem.get("x2", "0"))
    y2 = float(elem.get("y2", "0"))
    w = float(elem.get("width", "0.1524"))
    ap = CircleAperture(w, unit=MM)
    curve = elem.get("curve")
    if curve is None:
        return [Line(x1, y1, x2, y2, aperture=ap, unit=MM)]
    cdeg = float(curve)
    center = _eagle_arc_center(x1, y1, x2, y2, cdeg)
    if center is None:
        return [Line(x1, y1, x2, y2, aperture=ap, unit=MM)]
    cx, cy = center
    expected = math.radians(abs(cdeg))
    best_segs: list | None = None
    best_score = 1e9
    for clk in (True, False):
        pts = list(approximate_arc(cx, cy, x1, y1, x2, y2, clk, max_error=0.02))
        if len(pts) < 2:
            continue
        segs = [
            Line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], aperture=ap, unit=MM)
            for i in range(len(pts) - 1)
        ]
        ep_err = abs(pts[0][0] - x1) + abs(pts[0][1] - y1) + abs(pts[-1][0] - x2) + abs(pts[-1][1] - y2)
        sa = sweep_angle(cx, cy, x1, y1, x2, y2, clk)
        dsa = min(abs(sa - expected), abs(sa - (2 * math.pi - expected)))
        score = ep_err + dsa * 0.01
        if score < best_score:
            best_score = score
            best_segs = segs
    return best_segs if best_segs else [Line(x1, y1, x2, y2, aperture=ap, unit=MM)]


def _polygon_to_region(elem: ET.Element) -> Region | None:
    verts = elem.findall("vertex")
    if len(verts) < 3:
        return None
    outline: list[tuple[float, float]] = []
    for v in verts:
        outline.append((float(v.get("x", "0")), float(v.get("y", "0"))))
    return Region(outline=outline, unit=MM, polarity_dark=True)


def _collect_board_geometry(board: ET.Element) -> dict[int, list]:
    layers: dict[int, list] = {1: [], 2: [], 15: [], 16: [], 20: []}
    for sec in board:
        if sec.tag not in ("plain", "signals"):
            continue
        for el in sec.iter():
            if el.tag == "wire":
                ly = int(el.get("layer", "0"))
                if ly in layers:
                    layers[ly].extend(_wire_to_objects(el))
            elif el.tag == "polygon":
                ly = int(el.get("layer", "0"))
                if ly in layers:
                    r = _polygon_to_region(el)
                    if r is not None:
                        layers[ly].append(r)
    return layers


def _collect_vias(board: ET.Element) -> list[Flash]:
    flashes: list[Flash] = []
    by_drill: dict[float, ExcellonTool] = {}
    for via in board.iter("via"):
        d = float(via.get("drill", "0.35"))
        if d not in by_drill:
            by_drill[d] = ExcellonTool(diameter=d, plated=True, unit=MM)
        tool = by_drill[d]
        flashes.append(
            Flash(float(via.get("x", "0")), float(via.get("y", "0")), aperture=tool, unit=MM)
        )
    return flashes


def _write_gerber(path: Path, objects: list, comment: str) -> None:
    g = GerberFile(objects=list(objects), comments=[comment], import_settings=None)
    g.save(str(path), drop_comments=False)


def _copy_fusion_export_files(dest: Path) -> set[str]:
    """Copiază fișierele exportate manual din Fusion în `dest`. Returnează numele fișierelor."""
    names: set[str] = set()
    if not FUSION_EXPORT_DIR.is_dir():
        return names
    for src in sorted(FUSION_EXPORT_DIR.iterdir()):
        if not src.is_file():
            continue
        key = src.name.lower()
        if key in FUSION_SKIP_NAMES or src.name.startswith("."):
            continue
        shutil.copy2(src, dest / src.name)
        names.add(src.name)
    return names


def build_gerbers_zip() -> None:
    tree = ET.parse(BRD_PATH)
    root = tree.getroot()
    board = root.find(".//board")
    if board is None:
        raise SystemExit("Nu există nod <board> în fișierul .brd")
    layers = _collect_board_geometry(board)
    vias = _collect_vias(board)
    tmp = Path(tempfile.mkdtemp(prefix="inktime_gerber_"))
    try:
        fusion_names = _copy_fusion_export_files(tmp)

        auto_layers = [
            (
                "InkTime.GTL",
                layers[1],
                "Copper TOP (Eagle layer 1) — extras automat din XML .brd",
            ),
            ("InkTime.G1", layers[2], "Inner layer 1 / Route2 (Eagle layer 2)"),
            ("InkTime.G2", layers[15], "Inner layer 2 / Route15 (Eagle layer 15)"),
            (
                "InkTime.GBL",
                layers[16],
                "Copper BOTTOM (Eagle layer 16)",
            ),
            (
                "InkTime.GKO",
                layers[20],
                "Board outline / Dimension (Eagle layer 20)",
            ),
        ]
        for fname, objs, cmt in auto_layers:
            if fname not in fusion_names:
                _write_gerber(tmp / fname, objs, cmt)

        if "InkTime.drl" not in fusion_names and vias:
            ex = ExcellonFile(
                objects=vias, comments=["Plated through holes from via definitions"]
            )
            ex.save(str(tmp / "InkTime.drl"), drop_comments=False)

        if OUT_ZIP.exists():
            OUT_ZIP.unlink()
        archive_path = Path(
            shutil.make_archive(str(OUT_ZIP.with_suffix("")), "zip", root_dir=str(tmp))
        )
        if archive_path.resolve() != OUT_ZIP.resolve():
            shutil.move(str(archive_path), str(OUT_ZIP))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _rot_layer_deg(rot: str | None) -> tuple[str, float]:
    if not rot:
        return "Top", 0.0
    side = "Bottom" if rot.startswith("M") else "Top"
    body = rot[1:] if rot.startswith("M") else rot
    if body.startswith("R"):
        try:
            deg = float(body[1:])
        except ValueError:
            deg = 0.0
    else:
        deg = 0.0
    return side, deg


def build_bom_cpl() -> None:
    tree = ET.parse(BRD_PATH)
    board = tree.find(".//board")
    if board is None:
        raise SystemExit("Nu există nod <board>")
    elements = board.find("elements")
    if elements is None:
        raise SystemExit("Nu există <elements> în board")
    rows_bom = []
    rows_cpl = []
    for el in elements.findall("element"):
        name = el.get("name", "")
        val = (el.get("value") or "").replace("\n", " ").strip()
        pkg = el.get("package", "")
        lib = el.get("library", "")
        x = float(el.get("x", "0"))
        y = float(el.get("y", "0"))
        rot = el.get("rot")
        side, deg = _rot_layer_deg(rot)
        rows_bom.append(
            {
                "Designator": name,
                "Value": val,
                "Package": pkg,
                "Library": lib,
            }
        )
        rows_cpl.append(
            {
                "Designator": name,
                "Mid X mm": f"{x:.4f}",
                "Mid Y mm": f"{y:.4f}",
                "Layer": side,
                "Rotation": f"{deg:.0f}",
            }
        )
    OUT_BOM.parent.mkdir(parents=True, exist_ok=True)
    with OUT_BOM.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["Designator", "Value", "Package", "Library"],
            delimiter=",",
        )
        w.writeheader()
        w.writerows(rows_bom)
    with OUT_CPL.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["Designator", "Mid X mm", "Mid Y mm", "Layer", "Rotation"],
            delimiter=",",
        )
        w.writeheader()
        w.writerows(rows_cpl)


def build_schematic_pdf() -> None:
    if not IMG_SCH1.is_file() or not IMG_SCH2.is_file():
        raise SystemExit(f"Lipsesc {IMG_SCH1.name} sau {IMG_SCH2.name} în Images/")
    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT_PDF), pagesize=landscape(A4))
    w_page, h_page = landscape(A4)
    for img_path in (IMG_SCH1, IMG_SCH2):
        ir = ImageReader(str(img_path))
        iw, ih = ir.getSize()
        scale = min(w_page / iw, h_page / ih) * 0.95
        nw, nh = iw * scale, ih * scale
        x0 = (w_page - nw) / 2
        y0 = (h_page - nh) / 2
        c.drawImage(ir, x0, y0, width=nw, height=nh)
        c.showPage()
    c.save()


def main() -> None:
    if not BRD_PATH.is_file():
        raise SystemExit(f"Lipsește fișierul board: {BRD_PATH}")
    build_bom_cpl()
    build_schematic_pdf()
    build_gerbers_zip()
    print("OK:", OUT_BOM, OUT_CPL, OUT_PDF, OUT_ZIP, sep="\n")


if __name__ == "__main__":
    main()
