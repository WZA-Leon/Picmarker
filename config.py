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
        # ===== 核心基准：唯一缩放参考，所有像素参数都对应 base_width 下的尺寸 =====
        "base_width": 3000,
        "base_bar_height": 180,      # 基准宽度下的边框高度（像素），替代原百分比

        "background_color": [255, 255, 255],
        "icon_margin_left": 40,
        "icon_margin_right": 40,

        "left_text": {
            "camera": {"x_offset": 0, "y": -55},
            "lens": {"x_offset": 0, "y": 0},
            "name": {"x_offset": 0, "y": 60}
        },
        "right_text": {
            "params": {"x_offset": -40, "y": -55},
            "time": {"x_offset": -40, "y": 0}
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
                elif isinstance(v, dict) and isinstance(settings[section][k], dict):
                    # 递归合并嵌套子键（如 left_text/right_text 内部的 y 值），以默认值为准
                    for sub_k, sub_v in v.items():
                            settings[section][k][sub_k] = sub_v

    # ===== 旧配置自动迁移：百分比 → 像素基准 =====
    wm = settings["watermark"]
    if "base_bar_height" not in wm and "bar_height_percent" in wm:
        base_h = wm.get("base_height", 2000)
        wm["base_bar_height"] = int(base_h * wm["bar_height_percent"] / 100)
    # 清理废弃字段
    wm.pop("bar_height_percent", None)
    wm.pop("base_height", None)

    return settings


SETTINGS = load_settings()

# 常用配置快捷方式
GUI_CFG = SETTINGS["gui"]
WM_CFG = SETTINGS["watermark"]
BRAND_ICONS = SETTINGS["brand_icons"]
MODEL_SHORT = SETTINGS["model_short_names"]
BRAND_FIX = SETTINGS["brand_fix_map"]
CAMERA_DB = SETTINGS["camera_database"]