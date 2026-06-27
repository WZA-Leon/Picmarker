import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk
import os
import exifread
import threading
from pathlib import Path
import platform
import json
import piexif
import shutil

# ==================== 全局配置加载 ====================
SETTINGS_PATH = Path(__file__).parent / "settings.json"
DEFAULT_SETTINGS = {
    "gui": {
        "font_family": "Microsoft YaHei",
        "font_size": 10,
        "title_font_size": 11,
        "window_size": "1200x900",
        "preview_auto_refresh": True,
    },
    "watermark": {
        "bar_height": 280,
        "background_color": [255, 255, 255],
        "icon_max_height": 140,
        "icon_margin_left": 40,
        "icon_margin_right": 40,
        "vertical_center_offset": 30,
        "left_text": {
            "camera": {"x_offset": 0, "y": -40},
            "lens": {"x_offset": 0, "y": 10},
            "name": {"x_offset": 0, "y": 60}
        },
        "right_text": {
            "params": {"x_offset": -40, "y": -40},
            "time": {"x_offset": -40, "y": 10}
        },
        "fonts": {
            "camera": 56,
            "lens": 44,
            "name": 48,
            "params": 56,
            "time": 44
        },
        "colors": {
            "camera": [0, 0, 0],
            "lens": [80, 80, 80],
            "name": [30, 30, 30],
            "params": [0, 0, 0],
            "time": [80, 80, 80]
        },
        "stroke": {
            "enabled": True,
            "width": 3,
            "fill": [255, 255, 255]
        }
    },
    "brand_icons": {
        "FUJIFILM": "fujifilm.png",
        "Canon": "canon.png",
        "NIKON": "nikon.png",
        "SONY": "sony.png",
        "Panasonic": "panasonic.png",
        "Olympus": "olympus.png",
        "Leica": "leica.png",
        "Hasselblad": "hasselblad.png",
        "DJI": "dji.png",
        "GoPro": "gopro.png"
    },
    "model_short_names": {
        "NIKON Z30": "Z30",
        "NIKON Z50": "Z50",
        "NIKON Z6": "Z6",
        "NIKON Z7": "Z7",
        "CANON EOS R5": "EOS R5",
        "SONY ILCE-7M3": "A7 III"
    },
    "brand_fix_map": {
        "NIKON CORPORATION": "NIKON",
        "NIKON CORP": "NIKON",
        "FUJIFILM": "FUJIFILM",
        "CANON": "Canon",
        "SONY": "SONY"
    },
"camera_database": {
    "NIKON": {
        "cameras": [
            "D1",
            "D1H",
            "D1X",
            "D2H",
            "D2Hs",
            "D2X",
            "D2Xs",
            "D3",
            "D3s",
            "D3X",
            "D4",
            "D4s",
            "D5",
            "D6",
            "D40",
            "D40x",
            "D50",
            "D60",
            "D70",
            "D70s",
            "D80",
            "D90",
            "D100",
            "D200",
            "D300",
            "D300s",
            "D500",
            "D600",
            "D610",
            "D700",
            "D750",
            "D780",
            "D800",
            "D800E",
            "D810",
            "D850",
            "D3000",
            "D3100",
            "D3200",
            "D3300",
            "D3400",
            "D3500",
            "D5000",
            "D5100",
            "D5200",
            "D5300",
            "D5500",
            "D5600",
            "D7000",
            "D7100",
            "D7200",
            "D7500",
            "D8000",
            "D8700",
            "Z5",
            "Z5 II",
            "Z6",
            "Z6 II",
            "Z6 III",
            "Z7",
            "Z7 II",
            "Z8",
            "Z9",
            "Z30",
            "Z50",
            "Z50 II",
            "Zfc",
            "Zf",
            "P1",
            "P2",
            "P3",
            "P4",
            "P50",
            "P60",
            "P80",
            "P90",
            "P100",
            "P300",
            "P310",
            "P330",
            "P340",
            "P500",
            "P510",
            "P520",
            "P530",
            "P600",
            "P610",
            "P7000",
            "P7100",
            "P7700",
            "P7800",
            "P900",
            "P950",
            "P1000",
            "P1100",
            "P5000",
            "P5100"
        ],
        "lenses": [
            "NIKKOR Z 14-24mm f/2.8 S",
            "NIKKOR Z 24-70mm f/4 S",
            "NIKKOR Z 24-70mm f/2.8 S",
            "NIKKOR Z 24-120mm f/4 S",
            "NIKKOR Z 70-200mm f/2.8 VR S",
            "NIKKOR Z 100-400mm f/4.5-5.6 VR S",
            "NIKKOR Z 180-600mm f/5.6-6.3 VR",
            "NIKKOR Z 400mm f/4.5 VR S",
            "NIKKOR Z 600mm f/6.3 VR S",
            "NIKKOR Z 800mm f/6.3 VR S",
            "NIKKOR Z 50mm f/1.8 S",
            "NIKKOR Z 50mm f/1.2 S",
            "NIKKOR Z 85mm f/1.8 S",
            "NIKKOR Z 85mm f/1.2 S",
            "NIKKOR Z 35mm f/1.8 S",
            "NIKKOR Z 20mm f/1.8 S",
            "NIKKOR Z 24mm f/1.8 S",
            "NIKKOR Z 105mm f/2.8 VR S",
            "NIKKOR Z 28-75mm f/2.8",
            "NIKKOR Z 40mm f/2",
            "NIKKOR Z 28mm f/2.8",
            "NIKKOR Z 26mm f/2.8",
            "NIKKOR Z 70-180mm f/2.8",
            "NIKKOR Z 24-200mm f/4-6.3 VR",
            "NIKKOR Z 135mm f/1.8 S Plena",
            "NIKKOR Z DX 16-50mm f/3.5-6.3 VR",
            "NIKKOR Z DX 18-140mm f/3.5-6.3 VR",
            "NIKKOR Z DX 50-250mm f/4.5-6.3 VR",
            "NIKKOR Z DX 24mm f/1.7",
            "AF-S NIKKOR 14-24mm f/2.8G ED",
            "AF-S NIKKOR 16-35mm f/4G ED VR",
            "AF-S NIKKOR 24-70mm f/2.8G ED",
            "AF-S NIKKOR 24-70mm f/2.8E ED VR",
            "AF-S NIKKOR 24-120mm f/4G ED VR",
            "AF-S NIKKOR 70-200mm f/2.8G ED VR II",
            "AF-S NIKKOR 70-200mm f/2.8E FL ED VR",
            "AF-S NIKKOR 80-400mm f/4.5-5.6G ED VR",
            "AF-S NIKKOR 200-500mm f/5.6E ED VR",
            "AF-S NIKKOR 200-400mm f/4G ED VR II",
            "AF-S NIKKOR 500mm f/4E FL ED VR",
            "AF-S NIKKOR 600mm f/4E FL ED VR",
            "AF-S NIKKOR 400mm f/2.8E FL ED VR",
            "AF-S NIKKOR 300mm f/4E PF ED VR",
            "AF-S NIKKOR 300mm f/2.8G ED VR II",
            "AF-S NIKKOR 20mm f/1.8G ED",
            "AF-S NIKKOR 24mm f/1.4G ED",
            "AF-S NIKKOR 28mm f/1.4E ED",
            "AF-S NIKKOR 35mm f/1.4G",
            "AF-S NIKKOR 50mm f/1.4G",
            "AF-S NIKKOR 50mm f/1.8G",
            "AF-S NIKKOR 58mm f/1.4G",
            "AF-S NIKKOR 85mm f/1.4G",
            "AF-S NIKKOR 85mm f/1.8G",
            "AF-S NIKKOR 105mm f/1.4E ED",
            "AF-S NIKKOR 60mm f/2.8G ED",
            "AF-S NIKKOR 105mm f/2.8G IF-ED VR",
            "AF-S DX NIKKOR 18-55mm f/3.5-5.6G VR",
            "AF-S DX NIKKOR 18-140mm f/3.5-5.6G ED VR",
            "AF-S DX NIKKOR 16-80mm f/2.8-4E ED VR",
            "AF-S DX NIKKOR 35mm f/1.8G",
            "AF-S DX NIKKOR 17-55mm f/2.8G IF-ED",
            "AF-P DX NIKKOR 70-300mm f/4.5-6.3G ED VR",
            "AF-P FX NIKKOR 70-300mm f/4.5-5.6E ED VR",
            "AF-S NIKKOR 500mm f/5.6E PF ED VR"
        ]
    },
    "Canon": {
        "cameras": [
            "EOS-1D",
            "EOS-1D Mark II",
            "EOS-1D Mark II N",
            "EOS-1D Mark III",
            "EOS-1D Mark IV",
            "EOS-1D C",
            "EOS-1D X",
            "EOS-1D X Mark II",
            "EOS-1D X Mark III",
            "EOS-1Ds",
            "EOS-1Ds Mark II",
            "EOS-1Ds Mark III",
            "EOS 5D",
            "EOS 5D Mark II",
            "EOS 5D Mark III",
            "EOS 5D Mark IV",
            "EOS 5DS",
            "EOS 5DS R",
            "EOS 6D",
            "EOS 6D Mark II",
            "EOS 7D",
            "EOS 7D Mark II",
            "EOS 10D",
            "EOS 20D",
            "EOS 20Da",
            "EOS 30D",
            "EOS 40D",
            "EOS 50D",
            "EOS 60D",
            "EOS 60Da",
            "EOS 70D",
            "EOS 80D",
            "EOS 90D",
            "EOS 77D",
            "EOS 100D",
            "EOS 200D",
            "EOS 200D II",
            "EOS 250D",
            "EOS 300D",
            "EOS 350D",
            "EOS 400D",
            "EOS 450D",
            "EOS 500D",
            "EOS 550D",
            "EOS 600D",
            "EOS 650D",
            "EOS 700D",
            "EOS 750D",
            "EOS 760D",
            "EOS 800D",
            "EOS 850D",
            "EOS 1000D",
            "EOS 1100D",
            "EOS 1200D",
            "EOS 1300D",
            "EOS 1500D",
            "EOS 3000D",
            "EOS 4000D",
            "D30",
            "D60",
            "EOS R",
            "EOS Ra",
            "EOS RP",
            "EOS R3",
            "EOS R5",
            "EOS R5 C",
            "EOS R6",
            "EOS R6 Mark II",
            "EOS R6 Mark III",
            "EOS R8",
            "EOS R1",
            "EOS R7",
            "EOS R10",
            "EOS R50",
            "EOS R50 V",
            "EOS R100",
            "EOS M",
            "EOS M2",
            "EOS M3",
            "EOS M5",
            "EOS M6",
            "EOS M6 Mark II",
            "EOS M10",
            "EOS M50",
            "EOS M50 Mark II",
            "EOS M100",
            "EOS M200"
        ],
        "lenses": [
            "RF 14-35mm f/4L IS USM",
            "RF 15-35mm f/2.8L IS USM",
            "RF 24-50mm f/4.5-6.3 IS STM",
            "RF 24-70mm f/2.8L IS USM",
            "RF 24-105mm f/4L IS USM",
            "RF 24-105mm f/4-7.1 IS STM",
            "RF 70-200mm f/2.8L IS USM",
            "RF 70-200mm f/4L IS USM",
            "RF 100-400mm f/5.6-8 IS USM",
            "RF 100-500mm f/4.5-7.1L IS USM",
            "RF 600mm f/11 IS STM",
            "RF 800mm f/11 IS STM",
            "RF 16mm f/2.8 STM",
            "RF 24mm f/1.8 Macro IS STM",
            "RF 28mm f/2.8 STM",
            "RF 35mm f/1.8 Macro IS STM",
            "RF 50mm f/1.8 STM",
            "RF 50mm f/1.2L USM",
            "RF 85mm f/2 Macro IS STM",
            "RF 85mm f/1.2L USM",
            "RF 135mm f/1.8L IS USM",
            "RF-S 18-45mm f/4.5-6.3 IS STM",
            "RF-S 18-150mm f/3.5-6.3 IS STM",
            "RF-S 55-210mm f/5-7.1 IS STM",
            "EF 16-35mm f/2.8L III USM",
            "EF 24-70mm f/2.8L II USM",
            "EF 70-200mm f/2.8L IS III USM",
            "EF 70-200mm f/4L IS II USM",
            "EF 24-105mm f/4L IS II USM",
            "EF 100-400mm f/4.5-5.6L IS II USM",
            "EF 70-300mm f/4-5.6L IS USM",
            "EF 100mm f/2.8L Macro IS USM",
            "EF 50mm f/1.8 STM",
            "EF 50mm f/1.4 USM",
            "EF 85mm f/1.4L IS USM",
            "EF 85mm f/1.8 USM",
            "EF 135mm f/2L USM",
            "EF 40mm f/2.8 STM",
            "EF-S 10-18mm f/4.5-5.6 IS STM",
            "EF-S 17-55mm f/2.8 IS USM",
            "EF-S 18-135mm f/3.5-5.6 IS USM",
            "EF-S 24mm f/2.8 STM"
        ]
    },
    "SONY": {
        "cameras": [
            "A100",
            "A200",
            "A230",
            "A290",
            "A300",
            "A330",
            "A350",
            "A380",
            "A390",
            "A450",
            "A500",
            "A550",
            "A560",
            "A580",
            "A700",
            "A850",
            "A900",
            "SLT-A33",
            "SLT-A35",
            "SLT-A37",
            "SLT-A55",
            "SLT-A57",
            "SLT-A58",
            "SLT-A65",
            "SLT-A77",
            "SLT-A77 II",
            "SLT-A99",
            "SLT-A99 II",
            "NEX-3",
            "NEX-5",
            "NEX-5C",
            "NEX-5N",
            "NEX-5R",
            "NEX-5T",
            "NEX-6",
            "NEX-7",
            "NEX-C3",
            "NEX-F3",
            "NEX-3N",
            "A1",
            "A1 II",
            "A5",
            "A7",
            "A7 II",
            "A7 III",
            "A7 IV",
            "A7 V",
            "A7C",
            "A7C II",
            "A7R",
            "A7R II",
            "A7R III",
            "A7R IIIA",
            "A7R IV",
            "A7R IVA",
            "A7R V",
            "A7S",
            "A7S II",
            "A7S III",
            "A9",
            "A9 II",
            "A9 III",
            "A5000",
            "A5100",
            "A6000",
            "A6100",
            "A6300",
            "A6400",
            "A6500",
            "A6600",
            "A6700",
            "ZV-1",
            "ZV-1 II",
            "ZV-1F",
            "ZV-E1",
            "ZV-E10",
            "ZV-E10 II",
            "RX1",
            "RX1R",
            "RX1R II",
            "RX1R III",
            "RX10",
            "RX10 II",
            "RX10 III",
            "RX10 IV",
            "RX100",
            "RX100 II",
            "RX100 III",
            "RX100 IV",
            "RX100 V",
            "RX100 VI",
            "RX100 VII",
            "RX0",
            "RX0 II"
        ],
        "lenses": [
            "FE 14mm f/1.8 GM",
            "FE 20mm f/1.8 G",
            "FE 24mm f/1.4 GM",
            "FE 24mm f/2.8 G",
            "FE 28mm f/2",
            "FE 35mm f/1.4 GM",
            "FE 35mm f/1.8",
            "FE 35mm f/2.8 ZA",
            "FE 40mm f/2.5 G",
            "FE 50mm f/1.2 GM",
            "FE 50mm f/1.4 ZA",
            "FE 50mm f/1.8",
            "FE 55mm f/1.8 ZA",
            "FE 85mm f/1.4 GM",
            "FE 85mm f/1.8",
            "FE 90mm f/2.8 Macro G OSS",
            "FE 100mm f/2.8 STF GM OSS",
            "FE 135mm f/1.8 GM",
            "FE 12-24mm f/2.8 GM",
            "FE 12-24mm f/4 G",
            "FE 16-35mm f/2.8 GM",
            "FE 16-35mm f/2.8 GM II",
            "FE 16-35mm f/4 ZA OSS",
            "FE 20-70mm f/4 G",
            "FE 24-50mm f/2.8 G",
            "FE 24-70mm f/2.8 GM",
            "FE 24-70mm f/2.8 GM II",
            "FE 24-70mm f/4 ZA OSS",
            "FE 24-105mm f/4 G OSS",
            "FE 24-240mm f/3.5-6.3 OSS",
            "FE 28-60mm f/4-5.6",
            "FE 28-70mm f/3.5-5.6 OSS",
            "FE 70-200mm f/2.8 GM OSS",
            "FE 70-200mm f/2.8 GM OSS II",
            "FE 70-200mm f/4 G OSS",
            "FE 70-300mm f/4.5-5.6 G OSS",
            "FE 100-400mm f/4.5-5.6 GM OSS",
            "FE 200-600mm f/5.6-6.3 G OSS",
            "FE 400mm f/2.8 GM OSS",
            "FE 600mm f/4 GM OSS",
            "E 10-18mm f/4 OSS",
            "E 16-50mm f/3.5-5.6 OSS",
            "E 18-105mm f/4 G OSS",
            "E 18-135mm f/3.5-5.6 OSS",
            "E 18-200mm f/3.5-6.3 OSS",
            "E 55-210mm f/4.5-6.3 OSS",
            "E 70-350mm f/4.5-6.3 G OSS",
            "E 16-55mm f/2.8 G",
            "E 20mm f/2.8",
            "E 24mm f/1.8 ZA",
            "E 30mm f/3.5 Macro",
            "E 35mm f/1.8 OSS",
            "E 50mm f/1.8 OSS",
            "E 16mm f/2.8"
        ]
    },
    "FUJIFILM": {
        "cameras": [
            "GFX100 II",
            "GFX100S II",
            "GFX100S",
            "GFX100",
            "GFX 50S II",
            "GFX 50S",
            "GFX 50R",
            "GFX100RF",
            "X-H2S",
            "X-H2",
            "X-H1",
            "X-Pro3",
            "X-Pro2",
            "X-T5",
            "X-T4",
            "X-T3",
            "X-T2",
            "X-T1",
            "X-S20",
            "X-S10",
            "X-T50",
            "X-T30 III",
            "X-T30 II",
            "X-T30",
            "X-T20",
            "X-T10",
            "X-T200",
            "X-T100",
            "X-E5",
            "X-E4",
            "X-E3",
            "X-E2S",
            "X-M5",
            "X-A7",
            "X-A5",
            "X-A3",
            "X-A20",
            "X-A10",
            "X100VI",
            "X100V",
            "X100F",
            "X100T",
            "XF10",
            "X70",
            "X30"
        ],
        "lenses": [
            "XF 8-16mm f/2.8 R LM WR",
            "XF 10-24mm f/4 R OIS WR",
            "XF 14mm f/2.8 R",
            "XF 16mm f/1.4 R WR",
            "XF 16mm f/2.8 R WR",
            "XF 18mm f/1.4 R LM WR",
            "XF 18mm f/2 R",
            "XF 23mm f/1.4 R LM WR",
            "XF 23mm f/2 R WR",
            "XF 27mm f/2.8 R WR",
            "XF 33mm f/1.4 R LM WR",
            "XF 35mm f/1.4 R",
            "XF 35mm f/2 R WR",
            "XF 50mm f/1.0 R WR",
            "XF 50mm f/2 R WR",
            "XF 56mm f/1.2 R",
            "XF 56mm f/1.2 R WR",
            "XF 60mm f/2.4 R Macro",
            "XF 80mm f/2.8 R LM OIS WR Macro",
            "XF 90mm f/2 R LM WR",
            "XF 200mm f/2 R LM OIS WR",
            "XF 16-50mm f/2.8-4.8 R LM WR",
            "XF 16-55mm f/2.8 R LM WR",
            "XF 16-80mm f/4 R OIS WR",
            "XF 18-55mm f/2.8-4 R LM OIS",
            "XF 18-120mm f/4 LM PZ WR",
            "XF 50-140mm f/2.8 R LM OIS WR",
            "XF 55-200mm f/3.5-4.8 R LM OIS",
            "XF 70-300mm f/4-5.6 R LM OIS WR",
            "XF 100-400mm f/4.5-5.6 R LM OIS WR",
            "XF 150-600mm f/5.6-8 R LM OIS WR",
            "XF 16-50mm f/3.5-5.6 OIS (kit)",
            "XF 15-45mm f/3.5-5.6 OIS PZ",
            "GF 23mm f/4 R LM WR",
            "GF 30mm f/3.5 R WR",
            "GF 35-70mm f/4.5-5.6 WR",
            "GF 45mm f/2.8 R WR",
            "GF 50mm f/3.5 R LM WR",
            "GF 55mm f/1.7 R WR",
            "GF 63mm f/2.8 R WR",
            "GF 80mm f/1.7 R WR",
            "GF 110mm f/2 R LM WR",
            "GF 120mm f/4 R LM OIS WR Macro",
            "GF 250mm f/4 R LM OIS WR",
            "GF 32-64mm f/4 R LM WR",
            "GF 45-100mm f/4 R LM OIS WR",
            "GF 100-200mm f/5.6 R LM OIS WR",
            "GF 20-35mm f/4 R WR"
        ]
    },
    "Panasonic": {
        "cameras": [
            "S1R",
            "S1",
            "S1H",
            "S5",
            "S5 II",
            "S5 II X",
            "S9",
            "G9 II",
            "G9",
            "G99",
            "G100",
            "G95",
            "G85",
            "GX7 Mark III",
            "GX9",
            "GX85",
            "GF10",
            "GF9",
            "GF8",
            "GF7",
            "GH7",
            "GH6",
            "GH5 II",
            "GH5",
            "GH5S",
            "GH4",
            "BGH1"
        ],
        "lenses": [
            "LUMIX S 14-28mm f/4-5.6 Macro",
            "LUMIX S 16-35mm f/4",
            "LUMIX S 18mm f/1.8",
            "LUMIX S 20-60mm f/3.5-5.6",
            "LUMIX S 24mm f/1.8",
            "LUMIX S 24-105mm f/4 Macro O.I.S.",
            "LUMIX S 28-200mm f/4-7.1 Macro O.I.S.",
            "LUMIX S 35mm f/1.8",
            "LUMIX S 50mm f/1.8",
            "LUMIX S 70-200mm f/4 O.I.S.",
            "LUMIX S 85mm f/1.8",
            "LUMIX S 100mm f/2.8 Macro",
            "LUMIX S 70-300mm f/4.5-5.6 Macro O.I.S.",
            "LUMIX S 100-400mm f/4-6.3",
            "LUMIX S PRO 24-70mm f/2.8",
            "LUMIX S PRO 50mm f/1.4",
            "LUMIX S PRO 70-200mm f/2.8 O.I.S.",
            "LUMIX G X 12-35mm f/2.8 II",
            "LUMIX G X 35-100mm f/2.8 II",
            "LUMIX G 12-60mm f/2.8-4",
            "LUMIX G 12-60mm f/3.5-5.6",
            "LUMIX G 14-140mm f/3.5-5.6 II",
            "LUMIX G 45-150mm f/4-5.6",
            "LUMIX G 45-200mm f/4-5.6 II",
            "LUMIX G 100-300mm f/4-5.6 II",
            "LUMIX G 15mm f/1.7",
            "LUMIX G 20mm f/1.7 II",
            "LUMIX G 25mm f/1.7",
            "LUMIX G 42.5mm f/1.7",
            "LEICA DG 8-18mm f/2.8-4",
            "LEICA DG 12-60mm f/2.8-4",
            "LEICA DG 50-200mm f/2.8-4",
            "LEICA DG 25mm f/1.4 II",
            "LEICA DG 15mm f/1.7",
            "LEICA DG 200mm f/2.8",
            "LEICA DG 100-400mm f/4-6.3",
            "LEICA DG NOCTICRON 42.5mm f/1.2",
            "LUMIX G 7-14mm f/4",
            "LUMIX G 8mm f/3.5 Fisheye"
        ]
    },
    "Olympus": {
        "cameras": [
            "E-M1X",
            "E-M1 Mark III",
            "E-M1 Mark II",
            "E-M1",
            "E-M5 Mark III",
            "E-M5 Mark II",
            "E-M5",
            "E-M10 Mark IV",
            "E-M10 Mark III",
            "E-M10 Mark II",
            "E-M10",
            "PEN-F",
            "E-P7",
            "E-P5",
            "E-P3",
            "E-P2",
            "E-P1",
            "E-PL10",
            "E-PL9",
            "E-PL8",
            "E-PL7",
            "E-PL6",
            "E-PL5",
            "E-PL3",
            "E-PL2",
            "E-PL1"
        ],
        "lenses": [
            "M.Zuiko Digital ED 7-14mm f/2.8 PRO",
            "M.Zuiko Digital ED 8-25mm f/4 PRO",
            "M.Zuiko Digital ED 12-40mm f/2.8 PRO II",
            "M.Zuiko Digital ED 12-45mm f/4 PRO",
            "M.Zuiko Digital ED 12-100mm f/4 PRO",
            "M.Zuiko Digital ED 40-150mm f/2.8 PRO",
            "M.Zuiko Digital ED 40-150mm f/4 PRO",
            "M.Zuiko Digital ED 100-400mm f/5-6.3 IS",
            "M.Zuiko Digital ED 150-400mm f/4.5 TC1.25x IS PRO",
            "M.Zuiko Digital ED 75-300mm f/4.8-6.7 II",
            "M.Zuiko Digital ED 8mm f/1.8 Fisheye PRO",
            "M.Zuiko Digital 12mm f/2.0",
            "M.Zuiko Digital 17mm f/1.8",
            "M.Zuiko Digital ED 17mm f/1.2 PRO",
            "M.Zuiko Digital 20mm f/1.4 PRO",
            "M.Zuiko Digital 25mm f/1.8",
            "M.Zuiko Digital ED 25mm f/1.2 PRO",
            "M.Zuiko Digital 30mm f/3.5 Macro",
            "M.Zuiko Digital 45mm f/1.8",
            "M.Zuiko Digital ED 45mm f/1.2 PRO",
            "M.Zuiko Digital ED 60mm f/2.8 Macro",
            "M.Zuiko Digital ED 75mm f/1.8",
            "M.Zuiko Digital ED 300mm f/4 PRO",
            "M.Zuiko Digital ED 14-42mm f/3.5-5.6 II R",
            "M.Zuiko Digital ED 40-150mm f/4-5.6 R"
        ]
    },
    "Leica": {
        "cameras": [
            "M11",
            "M11-P",
            "M11-D",
            "M11 Monochrom",
            "M10",
            "M10-P",
            "M10-R",
            "M10 Monochrom",
            "M9",
            "M9-P",
            "M8",
            "M8.2",
            "M7",
            "M6",
            "M-A (Typ 127)",
            "MP",
            "M Monochrom (Typ 246)",
            "SL (Typ 601)",
            "SL2",
            "SL2-S",
            "SL2-S Reporter",
            "SL3",
            "SL3-S",
            "Q (Typ 116)",
            "Q2",
            "Q2 Monochrom",
            "Q3",
            "Q3 43",
            "Q3 Monochrom",
            "D-Lux 8",
            "D-Lux 7",
            "D-Lux 4",
            "X1",
            "X2",
            "X (Typ 113)",
            "TL",
            "TL2",
            "T (Typ 701)",
            "SOFORT",
            "SOFORT 2",
            "Leicaflex",
            "Leicaflex SL",
            "Leicaflex SL2",
            "R3",
            "R4",
            "R5",
            "R6",
            "R7",
            "R8",
            "R9"
        ],
        "lenses": [
            "Summicron-M 28mm f/2 ASPH.",
            "Summicron-M 35mm f/2 ASPH.",
            "Summicron-M 50mm f/2",
            "Summicron-M 90mm f/2 ASPH.",
            "APO-Summicron-M 35mm f/2 ASPH.",
            "APO-Summicron-M 50mm f/2 ASPH.",
            "APO-Summicron-M 75mm f/2 ASPH.",
            "APO-Summicron-M 90mm f/2 ASPH.",
            "Summilux-M 35mm f/1.4 ASPH. FLE",
            "Summilux-M 50mm f/1.4 ASPH.",
            "Summilux-M 75mm f/1.25",
            "Summilux-M 90mm f/1.5 ASPH.",
            "Elmarit-M 24mm f/2.8 ASPH.",
            "Elmarit-M 28mm f/2.8 ASPH.",
            "Elmar-M 50mm f/2.8",
            "Super-Elmar-M 21mm f/3.4 ASPH.",
            "APO-Summicron-SL 35mm f/2 ASPH.",
            "APO-Summicron-SL 50mm f/2 ASPH.",
            "APO-Summicron-SL 75mm f/2 ASPH.",
            "APO-Summicron-SL 90mm f/2 ASPH.",
            "Summicron-SL 35mm f/2",
            "Summicron-SL 50mm f/2",
            "Vario-Elmarit-SL 24-90mm f/2.8-4 ASPH.",
            "Vario-Elmarit-SL 90-280mm f/2.8-4",
            "Super-Vario-Elmar-SL 16-35mm f/3.5-4.5 ASPH.",
            "SL 24-70mm f/2.8 ASPH.",
            "SL 100-400mm f/5-6.3"
        ]
    },
    "Hasselblad": {
        "cameras": [
           "H3DII 39",
            "H3DII 50",
            "H4D-40",
            "H4D-50",
            "H4D-60",
            "H4D-200MS",
            "H5D-40",
            "H5D-50",
            "H5D-60",
            "H6D-50c",
            "H6D-100c",
            "H6D-400c MS",
            "1600F",
            "1000F",
            "500C",
            "500C/M",
            "500EL",
            "500EL/M",
            "503CW",
            "501C",
            "501CM",
            "SWC",
            "903SWC",
            "905SWC",
            "2000FC",
            "2003FCW",
            "201F",
            "202FA",
            "203FE",
            "205TCC",
            "205FCC",
            "HK-7",
            "XPAN",
            "XPAN II",
            "CFV II 50C",
            "907X",
            "907X 50C",
            "Lunar",
            "Stellar"
        ],
        "lenses": [
            "XCD 21mm f/4",
            "XCD 25mm f/2.5 V",
            "XCD 28mm f/4",
            "XCD 30mm f/3.5",
            "XCD 35-75mm f/3.5-4.5",
            "XCD 45mm f/4 P",
            "XCD 45mm f/3.5",
            "XCD 55mm f/2.5 V",
            "XCD 65mm f/2.8",
            "XCD 80mm f/1.9",
            "XCD 90mm f/3.2",
            "XCD 120mm f/4 Macro",
            "XCD 135mm f/2.8",
            "XCD 20-35mm f/4 E"
        ]
    },
    "DJI": {
        "cameras": [
            "Mavic 3",
            "Mavic 3 Pro",
            "Mavic 3 Classic",
            "Mavic 3 Cine",
            "Mavic 3E",
            "Mavic 3T",
            "Mavic Air 2",
            "Mavic Air 2S",
            "Mavic Mini",
            "Mini 2",
            "Mini 3",
            "Mini 3 Pro",
            "Mini 4 Pro",
            "Air 2S",
            "Air 3",
            "Air 3S",
            "Lito 1",
            "Lito X1",
            "Phantom 3",
            "Phantom 4",
            "Inspire 1",
            "Inspire 2",
            "Inspire 3",
            "Matrice 300 RTK",
            "Matrice 350 RTK",
            "Matrice 30",
            "Matrice 30T",
            "Mavic 3E",
            "Mavic 3T",
            "Phantom 4 RTK",
            "Osmo Pocket",
            "Osmo Pocket 2",
            "Osmo Pocket 3",
            "Osmo Action",
            "Osmo Action 2",
            "Osmo Action 3",
            "Osmo Action 4",
            "Osmo Action 5 Pro",
            "Osmo Action 6",
            "Osmo 360",
            "Osmo Nano",
            "Osmo Mobile 6",
            "Osmo Mobile 7",
            "Osmo Mobile 7P",
            "Osmo Mobile 8",
            "Osmo Mobile 8P",
            "Zenmuse X5S",
            "Zenmuse X7",
            "Zenmuse X9",
            "Zenmuse H20",
            "Zenmuse H20T",
            "Zenmuse P1",
            "Zenmuse L1",
            "Zenmuse L2",
            "Zenmuse Z30"
        ],
        "lenses": [
            "DJI DL 18mm F2.8 ASPH",
            "DJI DL 24mm F2.8 LS ASPH",
            "DJI DL 35mm F2.8 LS ASPH",
            "DJI DL 50mm F2.8 LS ASPH",
            "DJI DL 75mm F1.8",
            "DJI DL-S 16mm F2.8 ND ASPH",
            "DJI MFT 15mm f/1.7 ASPH",
            "Panasonic Lumix 15mm f/1.7",
            "Panasonic Lumix 14-42mm f/3.5-5.6 HD",
            "Olympus M.Zuiko 12mm f/2.0",
            "Olympus M.Zuiko 17mm f/1.8",
            "Olympus M.Zuiko 25mm f/1.8",
            "Olympus M.Zuiko 45mm f/1.8",
            "Olympus M.Zuiko 9-18mm f/4.0-5.6",
            "DJI Mavic 3 哈苏主摄 24mm 等效 f/2.8-f/11",
            "DJI Mavic 3 长焦 162mm 等效 f/4.4",
            "DJI Air 3S 主摄 24mm 等效 f/1.8",
            "DJI Air 3S 长焦 70mm 等效 f/2.8",
            "DJI Osmo Action 4 155° 超广角 f/2.8",
            "DJI Osmo Pocket 3 20mm 等效 f/2.0"
        ]
    },
    "GoPro": {
        "cameras": [
            "HERO12 Black",
            "HERO11 Black",
            "HERO10 Black",
            "HERO9 Black",
            "MAX 360"
        ],
        "lenses": ["Default"]  # GoPro 为固定镜头，无可换镜头
    }
}}

# 加载配置
if SETTINGS_PATH.exists():
    with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
        SETTINGS = json.load(f)
    for section, values in DEFAULT_SETTINGS.items():
        if section not in SETTINGS:
            SETTINGS[section] = values
        elif isinstance(values, dict):
            for k, v in values.items():
                if k not in SETTINGS[section]:
                    SETTINGS[section][k] = v
else:
    SETTINGS = DEFAULT_SETTINGS
    with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(SETTINGS, f, indent=2, ensure_ascii=False)

GUI_CFG = SETTINGS["gui"]
WM_CFG = SETTINGS["watermark"]
BRAND_ICONS = SETTINGS["brand_icons"]
MODEL_SHORT = SETTINGS["model_short_names"]
BRAND_FIX = SETTINGS["brand_fix_map"]
CAMERA_DB = SETTINGS["camera_database"]

try:
    RESAMPLE = Image.Resampling.LANCZOS
except:
    RESAMPLE = Image.LANCZOS

# ==================== 工具类 ====================
class FontManager:
    @staticmethod
    def get_system_fonts():
        fonts = []
        try:
            if platform.system() == "Windows":
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                     r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts")
                i = 0
                while True:
                    try:
                        name, path, _ = winreg.EnumValue(key, i)
                        if ".ttf" in path or ".ttc" in path:
                            fonts.append(name.split(" (TrueType)")[0])
                        i += 1
                    except:
                        break
            else:
                fonts = ["Arial", "Sans", "PingFang", "Microsoft YaHei"]
        except:
            fonts = ["Microsoft YaHei", "Arial", "Sans"]
        return sorted(list(set(fonts)))

class ExifReader:
    @staticmethod
    def _safe_str(val):
        return str(val).strip()

    @staticmethod
    def get_exif_full(image_path):
        info = {
            "make": "", "camera_model": "", "lens_model": "",
            "focal": "", "f": "", "exposure": "", "iso": "", "datetime": ""
        }
        try:
            with open(image_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)

            if 'Image Make' in tags:
                make_raw = ExifReader._safe_str(tags['Image Make']).upper()
                for orig, fixed in BRAND_FIX.items():
                    if orig in make_raw:
                        info["make"] = fixed
                        break
                else:
                    info["make"] = make_raw

            if 'Image Model' in tags:
                model = ExifReader._safe_str(tags['Image Model'])
                if model in MODEL_SHORT:
                    info["camera_model"] = MODEL_SHORT[model]
                else:
                    info["camera_model"] = model

            if 'EXIF LensModel' in tags:
                info["lens_model"] = ExifReader._safe_str(tags['EXIF LensModel'])

            if 'EXIF FocalLength' in tags:
                fl = tags['EXIF FocalLength']
                try:
                    fl_val = float(fl.values[0]) if hasattr(fl, 'values') else float(fl)
                except:
                    fl_val = str(fl)
                info["focal"] = f"{fl_val}mm"

            if 'EXIF FNumber' in tags:
                fn = tags['EXIF FNumber']
                try:
                    fn_val = float(fn.values[0]) if hasattr(fn, 'values') else float(fn)
                except:
                    fn_val = str(fn)
                info["f"] = f"f/{fn_val}"

            if 'EXIF ExposureTime' in tags:
                et = tags['EXIF ExposureTime']
                try:
                    et_val = float(et.values[0]) if hasattr(et, 'values') else float(et)
                    if et_val >= 1:
                        info["exposure"] = f"{et_val}s"
                    else:
                        info["exposure"] = f"1/{int(1/et_val)}s"
                except:
                    info["exposure"] = str(et)

            if 'EXIF ISOSpeedRatings' in tags:
                iso = str(tags['EXIF ISOSpeedRatings'])
                info["iso"] = f"ISO{iso}" if not iso.startswith("ISO") else iso

            if 'EXIF DateTimeOriginal' in tags:
                dt = str(tags['EXIF DateTimeOriginal']).replace(":", "-", 2)
                info["datetime"] = dt

        except:
            pass
        return info

class WatermarkGenerator:
    @staticmethod
    def get_font(name, size):
        try:
            if platform.system() == "Windows":
                font_paths = [
                    f"C:/Windows/Fonts/{name}.ttc",
                    f"C:/Windows/Fonts/{name}.ttf",
                    "C:/Windows/Fonts/msyh.ttc",
                    "C:/Windows/Fonts/simhei.ttf",
                    "C:/Windows/Fonts/arial.ttf"
                ]
                for p in font_paths:
                    if os.path.exists(p):
                        return ImageFont.truetype(p, size)
            else:
                for p in [
                    f"/System/Library/Fonts/{name}.ttc",
                    "/System/Library/Fonts/PingFang.ttc",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                ]:
                    if os.path.exists(p):
                        return ImageFont.truetype(p, size)
        except:
            pass
        return ImageFont.load_default()

    @staticmethod
    def resize_by_height(img, target_h):
        w, h = img.size
        ratio = target_h / h
        return img.resize((int(w*ratio), target_h), RESAMPLE)

    @staticmethod
    def load_brand_icon(brand):
        icon_dir = Path(__file__).parent / "icons"
        icon_dir.mkdir(exist_ok=True)
        icon_file = BRAND_ICONS.get(brand, None)
        if icon_file:
            icon_path = icon_dir / icon_file
            if icon_path.exists():
                icon = Image.open(icon_path).convert("RGBA")
                max_h = WM_CFG.get("icon_max_height", 140)
                return WatermarkGenerator.resize_by_height(icon, max_h)
        return Image.new("RGBA", (1, WM_CFG.get("icon_max_height", 140)), (0,0,0,0))

    @staticmethod
    def add_watermark(img_path, out_path, data, font_name):
        img = Image.open(img_path).convert("RGB")
        w, h = img.size
        bar_h = WM_CFG["bar_height"]
        bg = tuple(WM_CFG["background_color"])
        icon_left = WM_CFG["icon_margin_left"]
        icon_right = WM_CFG["icon_margin_right"]
        v_off = WM_CFG["vertical_center_offset"]

        new_img = Image.new("RGB", (w, h + bar_h), bg)
        new_img.paste(img, (0, 0))
        draw = ImageDraw.Draw(new_img)

        fc = WM_CFG["fonts"]
        colors = WM_CFG["colors"]
        stroke_en = WM_CFG["stroke"]["enabled"]
        stroke_w = WM_CFG["stroke"]["width"] if stroke_en else 0
        stroke_c = tuple(WM_CFG["stroke"]["fill"]) if stroke_en else None

        font_cam = WatermarkGenerator.get_font(font_name, fc["camera"])
        font_len = WatermarkGenerator.get_font(font_name, fc["lens"])
        font_name_f = WatermarkGenerator.get_font(font_name, fc["name"])
        font_param = WatermarkGenerator.get_font(font_name, fc["params"])
        font_time = WatermarkGenerator.get_font(font_name, fc["time"])

        icon = WatermarkGenerator.load_brand_icon(data["brand"])
        icon_y = h + (bar_h - icon.height)//2
        new_img.paste(icon, (icon_left, icon_y), icon)

        left_x = icon_left + icon.width + icon_right
        base_y = h + (bar_h//2) - v_off

        left_cfg = WM_CFG["left_text"]
        cam_pos = (left_x + left_cfg["camera"]["x_offset"], base_y + left_cfg["camera"]["y"])
        draw.text(cam_pos, data["camera"], fill=tuple(colors["camera"]), font=font_cam,
                  stroke_width=stroke_w, stroke_fill=stroke_c)

        lens_pos = (left_x + left_cfg["lens"]["x_offset"], base_y + left_cfg["lens"]["y"])
        draw.text(lens_pos, data["lens"], fill=tuple(colors["lens"]), font=font_len,
                  stroke_width=stroke_w, stroke_fill=stroke_c)

        if data["photo_name"]:
            name_pos = (left_x + left_cfg["name"]["x_offset"], base_y + left_cfg["name"]["y"])
            draw.text(name_pos, data["photo_name"], fill=tuple(colors["name"]), font=font_name_f,
                      stroke_width=stroke_w, stroke_fill=stroke_c)

        right_cfg = WM_CFG["right_text"]
        param_text = f"{data['focal']}  {data['f']}  {data['exp']}  {data['iso']}"
        time_text = f"{data['datetime']}"
        if data['location']:
            time_text += f" | {data['location']}"

        param_w = draw.textlength(param_text, font=font_param)
        time_w = draw.textlength(time_text, font=font_time)

        param_x = w + right_cfg["params"]["x_offset"] - param_w
        time_x = w + right_cfg["time"]["x_offset"] - time_w

        draw.text((param_x, base_y + right_cfg["params"]["y"]), param_text,
                  fill=tuple(colors["params"]), font=font_param,
                                    stroke_width=stroke_w, stroke_fill=stroke_c)
        draw.text((time_x, base_y + right_cfg["time"]["y"]), time_text,
                  fill=tuple(colors["time"]), font=font_time,
                  stroke_width=stroke_w, stroke_fill=stroke_c)

        new_img.save(out_path, quality=95)

                # 保存原始EXIF到输出图片
        try:
            exif_dict = piexif.load(img_path)
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, out_path)
        except Exception as e:
            print(f"EXIF保存失败 ({os.path.basename(img_path)}): {e}")

# ==================== 主程序界面 ====================
class PhotoWatermarkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("相机水印工具 v2.3")
        self.root.geometry(GUI_CFG.get("window_size", "1200x900"))
        
        # 设置窗口最小尺寸
        self.root.minsize(1000, 700)
        
        self.input_files = []
        self.current_index = -1
        self.output_path = tk.StringVar(value=str(Path.home() / "Desktop" / "水印输出"))
        self.selected_font = tk.StringVar(value="Microsoft YaHei")
        self.font_list = FontManager.get_system_fonts()
        if self.font_list:
            if "Microsoft YaHei" in self.font_list:
                self.selected_font.set("Microsoft YaHei")
            else:
                self.selected_font.set(self.font_list[0])

        # 参数变量 - 使用 tk.StringVar 确保可编辑
        self.brand_var = tk.StringVar()
        self.camera_var = tk.StringVar()
        self.lens_var = tk.StringVar()
        self.photo_name_var = tk.StringVar()
        self.focal_var = tk.StringVar()
        self.f_var = tk.StringVar()
        self.exp_var = tk.StringVar()
        self.iso_var = tk.StringVar()
        self.time_var = tk.StringVar()
        self.loc_var = tk.StringVar()

        self._init_ui()
        Path(self.output_path.get()).mkdir(parents=True, exist_ok=True)

    def _init_ui(self):
        # 设置整体风格
        style = ttk.Style()
        style.configure(".", font=(GUI_CFG["font_family"], GUI_CFG["font_size"]))
        
        # 主容器
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=1)
        
        # 使用 PanedWindow 实现左右分栏
        main_pw = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        main_pw.pack(fill=tk.BOTH, expand=1, padx=10, pady=5)

        # ========== 左侧：文件列表 ==========
        left_frame = ttk.Frame(main_pw, width=280)
        main_pw.add(left_frame, weight=0)
        
        # 标题
        ttk.Label(left_frame, text="📁 已添加照片", 
                 font=(GUI_CFG["font_family"], GUI_CFG["title_font_size"], "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        # 列表框
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=1)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.listbox = tk.Listbox(list_frame, 
                                  yscrollcommand=scrollbar.set, 
                                  selectmode=tk.SINGLE,
                                  font=(GUI_CFG["font_family"], GUI_CFG["font_size"]),
                                  bg="white",
                                  selectbackground="#0078D4",
                                  activestyle="none")
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        scrollbar.config(command=self.listbox.yview)
        self.listbox.bind('<<ListboxSelect>>', self.on_list_select)
        
        # 按钮
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=8)
        ttk.Button(btn_frame, text="➕ 添加图片", command=self.select_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑 删除选中", command=self.delete_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="📂 清空列表", command=self.clear_all).pack(side=tk.LEFT, padx=2)

        # ========== 右侧：预览和参数 ==========
        right_frame = ttk.Frame(main_pw)
        main_pw.add(right_frame, weight=1)

        # 输出路径
        path_frame = ttk.LabelFrame(right_frame, text="💾 输出设置")
        path_frame.pack(fill=tk.X, pady=(0, 5))
        path_inner = ttk.Frame(path_frame)
        path_inner.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(path_inner, text="保存路径：").pack(side=tk.LEFT)
        ttk.Entry(path_inner, textvariable=self.output_path, width=50).pack(side=tk.LEFT, padx=6)
        ttk.Button(path_inner, text="浏览...", command=self.select_out_dir).pack(side=tk.LEFT, padx=2)

        # 预览画布
        preview_frame = ttk.LabelFrame(right_frame, text="🖼 效果预览")
        preview_frame.pack(fill=tk.BOTH, expand=1, pady=(0, 5))
        
        # 预览控制按钮
        preview_ctrl = ttk.Frame(preview_frame)
        preview_ctrl.pack(fill=tk.X, padx=8, pady=4)
        ttk.Button(preview_ctrl, text="◀ 上一张", command=self.prev_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(preview_ctrl, text="下一张 ▶", command=self.next_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(preview_ctrl, text="🔄 刷新预览", command=self.show_preview).pack(side=tk.LEFT, padx=10)
        self.preview_label = ttk.Label(preview_ctrl, text="")
        self.preview_label.pack(side=tk.LEFT, padx=10)
        
        self.canvas = tk.Canvas(preview_frame, bg="#f5f5f5", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=1, padx=4, pady=4)

        # 参数编辑区域 - 使用 LabelFrame 分组
        param_frame = ttk.LabelFrame(right_frame, text="✏️ 水印参数（可手动修改任何字段）")
        param_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 创建三个子框架，让参数布局更清晰
        # 第一行：品牌、相机、镜头
        row1 = ttk.Frame(param_frame)
        row1.pack(fill=tk.X, padx=8, pady=4)
        
        ttk.Label(row1, text="品牌：", width=6).pack(side=tk.LEFT)
        self.cbo_brand = ttk.Combobox(row1, textvariable=self.brand_var, 
                                      values=list(CAMERA_DB.keys()), width=12, state="normal")
        self.cbo_brand.pack(side=tk.LEFT, padx=(0, 10))
        self.cbo_brand.bind("<<ComboboxSelected>>", self.on_brand_change)
        # 允许手动输入
        self.cbo_brand.bind("<KeyRelease>", lambda e: self.on_brand_change())
        
        ttk.Label(row1, text="相机：", width=6).pack(side=tk.LEFT)
        self.cbo_cam = ttk.Combobox(row1, textvariable=self.camera_var, width=15)
        self.cbo_cam.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row1, text="镜头：", width=6).pack(side=tk.LEFT)
        self.cbo_len = ttk.Combobox(row1, textvariable=self.lens_var, width=25)
        self.cbo_len.pack(side=tk.LEFT)
        
        # 第二行：照片名、焦距、光圈、快门、ISO
        row2 = ttk.Frame(param_frame)
        row2.pack(fill=tk.X, padx=8, pady=4)
        
        ttk.Label(row2, text="标题：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.photo_name_var, width=12).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row2, text="焦距：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.focal_var, width=8).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row2, text="光圈：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.f_var, width=8).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row2, text="快门：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.exp_var, width=10).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row2, text="ISO：", width=4).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.iso_var, width=10).pack(side=tk.LEFT)
        
        # 第三行：时间、地点、字体
        row3 = ttk.Frame(param_frame)
        row3.pack(fill=tk.X, padx=8, pady=4)
        
        ttk.Label(row3, text="时间：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row3, textvariable=self.time_var, width=22).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row3, text="地点：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row3, textvariable=self.loc_var, width=22).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row3, text="字体：", width=6).pack(side=tk.LEFT)
        self.font_cb = ttk.Combobox(row3, textvariable=self.selected_font, 
                                    values=self.font_list, width=20, state="readonly")
        self.font_cb.pack(side=tk.LEFT)
        self.font_cb.bind("<<ComboboxSelected>>", lambda e: self.show_preview())

                # 操作按钮
        action_frame = ttk.Frame(right_frame)
        action_frame.pack(fill=tk.X, pady=6)
        
        ttk.Button(action_frame, text="🔄 刷新预览", command=self.show_preview).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="🎨 添加水印(当前)", command=self.add_watermark_current).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="⚙ 设置编辑器", command=self.open_settings_editor).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="📷 水印工具", command=self.open_picmarker).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="📦 批量处理(全部)", command=self.start_batch).pack(side=tk.RIGHT, padx=2)
        
        self.progress = ttk.Progressbar(right_frame, orient=tk.HORIZONTAL)
        self.progress.pack(fill=tk.X, pady=(0, 3))
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(right_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X)

        # 绑定窗口大小改变事件，自动调整预览
        self.canvas.bind("<Configure>", lambda e: self.root.after(200, self.show_preview))

    # ---------- 图片导航 ----------
    def prev_image(self):
        if not self.input_files:
            return
        if self.current_index > 0:
            self.current_index -= 1
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.current_index)
            self.listbox.see(self.current_index)
            self._update_preview_for_current()

    def next_image(self):
        if not self.input_files:
            return
        if self.current_index < len(self.input_files) - 1:
            self.current_index += 1
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.current_index)
            self.listbox.see(self.current_index)
            self._update_preview_for_current()

    # ---------- 文件操作 ----------
    def select_files(self):
        files = filedialog.askopenfilenames(
            title="选择照片",
            filetypes=[
                ("图片文件", "*.jpg *.jpeg *.png *.tif *.tiff"),
                ("JPEG", "*.jpg *.jpeg"),
                ("PNG", "*.png"),
                ("所有文件", "*.*")
            ]
        )
        if not files:
            return
        
        added = 0
        for f in files:
            if f not in self.input_files:
                self.input_files.append(f)
                self.listbox.insert(tk.END, os.path.basename(f))
                added += 1
        
        if added > 0:
            self.status_var.set(f"已添加 {added} 张照片，共 {len(self.input_files)} 张")
            if self.current_index == -1:
                self.listbox.selection_set(0)
                self.current_index = 0
                self._update_preview_for_current()
            self.show_preview()

    def delete_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先选择要删除的照片")
            return
        
        idx = sel[0]
        filename = os.path.basename(self.input_files[idx])
        
        if messagebox.askyesno("确认删除", f"确定要删除 {filename} 吗？"):
            self.listbox.delete(idx)
            del self.input_files[idx]
            
            if not self.input_files:
                self.current_index = -1
                self.canvas.delete("all")
                self.status_var.set("列表已清空")
            else:
                if self.current_index >= len(self.input_files):
                    self.current_index = len(self.input_files) - 1
                self.listbox.selection_set(self.current_index)
                self._update_preview_for_current()

    def clear_all(self):
        if self.input_files and messagebox.askyesno("确认清空", "确定要清空所有照片吗？"):
            self.input_files = []
            self.current_index = -1
            self.listbox.delete(0, tk.END)
            self.canvas.delete("all")
            self.status_var.set("列表已清空")

    def on_list_select(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx != self.current_index:
            self.current_index = idx
            self._update_preview_for_current()

    def _update_preview_for_current(self):
        """更新当前照片的EXIF信息并刷新预览"""
        if self.current_index < 0 or self.current_index >= len(self.input_files):
            return
        
        path = self.input_files[self.current_index]
        filename = os.path.basename(path)
        self.status_var.set(f"当前: {filename} ({self.current_index+1}/{len(self.input_files)})")
        
        # 读取EXIF并填充参数
        info = ExifReader.get_exif_full(path)
        
        self.brand_var.set(info.get("make", ""))
        self.on_brand_change()
        self.camera_var.set(info.get("camera_model", ""))
        self.lens_var.set(info.get("lens_model", ""))
        self.focal_var.set(info.get("focal", ""))
        self.f_var.set(info.get("f", ""))
        self.exp_var.set(info.get("exposure", ""))
        self.iso_var.set(info.get("iso", ""))
        self.time_var.set(info.get("datetime", ""))
        
        # 自动预览
        self.root.after(100, self.show_preview)

    def on_brand_change(self, event=None):
        """品牌改变时更新相机和镜头下拉列表"""
        brand = self.brand_var.get().strip()
        if brand in CAMERA_DB:
            cams = CAMERA_DB[brand].get("cameras", [])
            lens = CAMERA_DB[brand].get("lenses", [])
            self.cbo_cam.config(values=cams)
            self.cbo_len.config(values=lens)
        else:
            # 即使是未知品牌，也保留手动输入的可能性
            pass

    def select_out_dir(self):
        d = filedialog.askdirectory(title="选择输出文件夹")
        if d:
            self.output_path.set(d)

    def get_data(self):
        """收集所有参数"""
        return {
            "brand": self.brand_var.get().strip(),
            "camera": self.camera_var.get().strip(),
            "lens": self.lens_var.get().strip(),
            "photo_name": self.photo_name_var.get().strip(),
            "focal": self.focal_var.get().strip(),
            "f": self.f_var.get().strip(),
            "exp": self.exp_var.get().strip(),
            "iso": self.iso_var.get().strip(),
            "datetime": self.time_var.get().strip(),
            "location": self.loc_var.get().strip()
        }

    def show_preview(self):
        """生成并显示预览"""
        if not self.input_files or self.current_index == -1:
            return
        
        try:
            os.makedirs(self.output_path.get(), exist_ok=True)
            tmp = Path(self.output_path.get()) / "_tmp_preview.jpg"
            
            WatermarkGenerator.add_watermark(
                self.input_files[self.current_index],
                str(tmp),
                self.get_data(),
                self.selected_font.get()
            )
            
            im = Image.open(tmp)
            cw = max(self.canvas.winfo_width(), 100)
            ch = max(self.canvas.winfo_height(), 100)
            
            # 计算缩放比例
            scale = min((cw-20)/im.width, (ch-20)/im.height, 1.0)
            new_size = (int(im.width*scale), int(im.height*scale))
            im = im.resize(new_size, RESAMPLE)
            
            self.preview_img = ImageTk.PhotoImage(im)
            self.canvas.delete("all")
            self.canvas.create_image(cw//2, ch//2, image=self.preview_img, anchor=tk.CENTER)
            
            # 清理临时文件
            tmp.unlink(missing_ok=True)
            
            self.preview_label.config(text=f"预览: {os.path.basename(self.input_files[self.current_index])}")
            
        except Exception as e:
            self.status_var.set(f"预览失败: {str(e)}")

    def add_watermark_current(self):
        """为当前图片单独添加水印"""
        if not self.input_files or self.current_index == -1:
            messagebox.showwarning("提示", "请先选择照片")
            return
        
        os.makedirs(self.output_path.get(), exist_ok=True)
        path = self.input_files[self.current_index]
        name = os.path.basename(path)
        out = os.path.join(self.output_path.get(), f"Watermark_{name}")
        
        try:
            WatermarkGenerator.add_watermark(path, out, self.get_data(), self.selected_font.get())
            self.status_var.set(f"✅ 已完成: {name}")
            messagebox.showinfo("完成", f"水印已保存到:\n{out}")
        except Exception as e:
            messagebox.showerror("错误", f"处理失败: {str(e)}")

    def start_batch(self):
        """批量处理所有图片"""
        if not self.input_files:
            messagebox.showwarning("提示", "请先添加照片")
            return
        
        if not messagebox.askyesno("确认批量处理", f"将处理 {len(self.input_files)} 张照片，是否继续？"):
            return
        
        os.makedirs(self.output_path.get(), exist_ok=True)
        data = self.get_data()
        font = self.selected_font.get()
        total = len(self.input_files)
        self.progress["maximum"] = total
        
        def worker():
            success = 0
            for i, f in enumerate(self.input_files):
                name = os.path.basename(f)
                out = os.path.join(self.output_path.get(), f"Watermark_{name}")
                try:
                    WatermarkGenerator.add_watermark(f, out, data, font)
                    success += 1
                except Exception as e:
                    pass
                
                self.progress["value"] = i + 1
                self.status_var.set(f"处理中... {i+1}/{total}")
                self.root.update()
            
            self.progress["value"] = 0
            self.status_var.set(f"✅ 完成！成功 {success}/{total}")
            messagebox.showinfo("批量处理完成", f"成功处理 {success}/{total} 张照片\n保存位置: {self.output_path.get()}")
        
        threading.Thread(target=worker, daemon=True).start()

    def open_settings_editor(self):
        """打开设置编辑器"""
        import subprocess
        editor_path = Path(__file__).parent / "edit.py"
        if editor_path.exists():
            subprocess.Popen(["python", str(editor_path)])
        else:
            messagebox.showerror("错误", f"未找到 {editor_path}")

    def open_picmarker(self):
        """打开Picmarker工具"""
        import subprocess
        marker_path = Path(__file__).parent / "Picmarker.py"
        if marker_path.exists():
            subprocess.Popen(["python", str(marker_path)])
        else:
            messagebox.showerror("错误", f"未找到 {marker_path}")

if __name__ == "__main__":
    # 检查并安装依赖
    try:
        import exifread
    except ImportError:
        print("正在安装依赖库...")
        os.system("python -m pip install Pillow exifread")
        import exifread
    
    root = tk.Tk()
    app = PhotoWatermarkApp(root)
    root.mainloop()
