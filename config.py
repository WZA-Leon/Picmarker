# config.py
import json
from pathlib import Path

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
        "bar_height_percent": 15,
        "base_height": 2000,
        "base_width": 3000,
        "background_color": [255, 255, 255],
        "icon_margin_left": 40,
        "icon_margin_right": 40,
                "left_text": {
            "camera": {"x_offset": 0, "y": -55},
            "lens": {"x_offset": 0, "y": 10},
            "name": {"x_offset": 0, "y": 60}
        },
        "right_text": {
            "params": {"x_offset": -40, "y": -55},
            "time": {"x_offset": -40, "y": 10}
        },
        "fonts": {
            "camera": 44,
            "lens": 34,
            "name": 38,
            "params": 44,
            "time": 34
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
    "brand_icons": {},
    "model_short_names": {},
    "brand_fix_map": {},
    "camera_database": {}
}


def load_settings():
    if SETTINGS_PATH.exists():
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
            settings = json.load(f)
    else:
        settings = DEFAULT_SETTINGS
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    # 补全缺失的顶层键
    for section, values in DEFAULT_SETTINGS.items():
        if section not in settings:
            settings[section] = values
        elif isinstance(values, dict):
            for k, v in values.items():
                if k not in settings[section]:
                    settings[section][k] = v
    return settings


SETTINGS = load_settings()

# 常用配置快捷方式
GUI_CFG = SETTINGS["gui"]
WM_CFG = SETTINGS["watermark"]
BRAND_ICONS = SETTINGS["brand_icons"]
MODEL_SHORT = SETTINGS["model_short_names"]
BRAND_FIX = SETTINGS["brand_fix_map"]
CAMERA_DB = SETTINGS["camera_database"]