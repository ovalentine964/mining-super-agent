"""
Inline Keyboards
================
Telegram inline keyboards for quick actions and interactive flows.

All keyboard labels are localized.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.responses import get_response


def language_selection_keyboard() -> InlineKeyboardMarkup:
    """Language picker shown during onboarding."""
    buttons = [
        [
            InlineKeyboardButton("🇹🇿 Kiswahili", callback_data="quick_swahili"),
            InlineKeyboardButton("🇬🇧 English", callback_data="quick_english"),
        ],
        [
            InlineKeyboardButton("🇰🇪 Dholuo", callback_data="quick_luo"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def quick_actions_keyboard(lang: str = "sw") -> InlineKeyboardMarkup:
    """Quick-action buttons shown below responses."""
    buttons = [
        [
            InlineKeyboardButton(
                get_response("action_price", lang=lang),
                callback_data="action_price",
            ),
            InlineKeyboardButton(
                get_response("action_report", lang=lang),
                callback_data="action_report",
            ),
        ],
        [
            InlineKeyboardButton(
                get_response("action_help", lang=lang),
                callback_data="action_help",
            ),
            InlineKeyboardButton(
                "🌐 Lugha" if lang == "sw" else "🌐 Language" if lang == "en" else "🌐 Dhuluo",
                callback_data="action_language",
            ),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def help_keyboard(lang: str = "sw") -> InlineKeyboardMarkup:
    """Help page quick actions."""
    buttons = [
        [
            InlineKeyboardButton(
                "📸 " + ("Tuma Picha" if lang == "sw" else "Send Photo" if lang == "en" else "Oro Chiro"),
                callback_data="help_photo",
            ),
            InlineKeyboardButton(
                "🎤 " + ("Tuma Sauti" if lang == "sw" else "Send Voice" if lang == "en" else "Oro Suono"),
                callback_data="help_voice",
            ),
        ],
        [
            InlineKeyboardButton(
                "📍 " + ("Tuma GPS" if lang == "sw" else "Send GPS" if lang == "en" else "Oro GPS"),
                callback_data="help_gps",
            ),
            InlineKeyboardButton(
                get_response("action_price", lang=lang),
                callback_data="action_price",
            ),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def mineral_id_keyboard(lang: str = "sw") -> InlineKeyboardMarkup:
    """
    Shown after mineral identification.

    Lets the user confirm the result or request a retry.
    """
    buttons = [
        [
            InlineKeyboardButton(
                "✅ " + ("Sawa" if lang == "sw" else "Correct" if lang == "en" else "Ber"),
                callback_data="mineral_confirm_ok",
            ),
            InlineKeyboardButton(
                "🔄 " + ("Jaribu Tena" if lang == "sw" else "Try Again" if lang == "en" else "Tem"),
                callback_data="mineral_retry",
            ),
        ],
        [
            InlineKeyboardButton(
                "📊 " + ("Ripoti" if lang == "sw" else "Report" if lang == "en" else "Ripot"),
                callback_data="action_report",
            ),
            InlineKeyboardButton(
                "💰 " + ("Bei" if lang == "sw" else "Price" if lang == "en" else "Ngiyo"),
                callback_data="action_price",
            ),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def mineral_options_keyboard(minerals: list[dict], lang: str = "sw") -> InlineKeyboardMarkup:
    """
    When multiple minerals are detected, let the user pick which one
    to learn more about.

    `minerals` = [{"name_en": "Gold", "name_sw": "Dhahabu", "confidence": 0.62}, ...]
    """
    buttons = []
    for m in minerals:
        label = m.get("name_sw" if lang != "en" else "name_en", m["name_en"])
        conf = int(m["confidence"] * 100)
        buttons.append([
            InlineKeyboardButton(
                f"{label} ({conf}%)",
                callback_data=f"mineral_info_{m['name_en'].lower()}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔄 " + ("Picha Nyingine" if lang == "sw" else "Another Photo" if lang == "en" else "Chiro Moko"),
            callback_data="mineral_retry",
        ),
    ])

    return InlineKeyboardMarkup(buttons)
