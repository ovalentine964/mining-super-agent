"""
Location Handler
================
When a miner shares their GPS location:
1. Extract latitude / longitude
2. Query the geological database (PostGIS)
3. Run satellite analysis if available
4. Return a geological assessment of their area
"""

import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from bot.conversation import ConversationManager
from bot.middleware.language import LanguageMiddleware
from bot.responses import get_response

logger = logging.getLogger(__name__)


async def handle_location(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    conv_manager: ConversationManager,
    lang_middleware: LanguageMiddleware,
    lang: str,
) -> None:
    """Process a shared GPS location."""
    user_id = update.effective_user.id
    location = update.message.location

    if not location:
        await update.message.reply_text(get_response("error_location", lang=lang))
        return

    lat = location.latitude
    lon = location.longitude

    logger.info("Location from user %s: lat=%.6f, lon=%.6f", user_id, lat, lon)

    thinking_msg = await update.message.reply_text(
        get_response("location_analyzing", lang=lang, lat=lat, lon=lon)
    )

    try:
        # Query geological data for this location
        assessment = await _geological_assessment(lat, lon, lang)

        # Format the response
        response = get_response("location_header", lang=lang, lat=lat, lon=lon)
        response += "\n\n" + assessment
        response += "\n\n" + get_response("location_disclaimer", lang=lang)

        await thinking_msg.edit_text(response)

        # Store in conversation history
        conv_manager.add_message(
            user_id,
            "user",
            f"[Location] {lat}, {lon}",
            lang=lang,
            intent="location_query",
        )
        conv_manager.add_message(
            user_id,
            "assistant",
            response,
            lang=lang,
            intent="geological_assessment",
        )

    except Exception as exc:
        logger.exception("Location analysis failed for user %s: %s", user_id, exc)
        await thinking_msg.edit_text(
            get_response("error_location_analysis", lang=lang)
        )


async def _geological_assessment(lat: float, lon: float, lang: str) -> str:
    """
    Run geological analysis for a GPS coordinate.

    Pipeline:
    1. Query PostGIS for nearby geological units
    2. Check for known mineral occurrences
    3. Query satellite alteration data (Sentinel-2)
    4. Compile a human-readable assessment

    For now, returns a structured placeholder with regional context.
    """
    # TODO: Wire to Geological Agent + Satellite Agent
    # This would call:
    #   from geological.db import query_nearby_units
    #   from satellite.analysis import analyze_sentinel2
    #   results = await asyncio.gather(query_nearby_units(lat, lon), analyze_sentinel2(lat, lon))

    # Regional knowledge placeholder for Migori County / Lake Victoria Gold Belt
    region = _identify_region(lat, lon)

    assessment = get_response("geological_region", lang=lang, region=region["name"])

    if region.get("known_minerals"):
        minerals_str = ", ".join(region["known_minerals"])
        assessment += "\n\n" + get_response(
            "geological_known_minerals", lang=lang, minerals=minerals_str
        )

    if region.get("geology"):
        assessment += "\n\n" + get_response(
            "geological_formation", lang=lang, geology=region["geology"]
        )

    if region.get("recommendation"):
        assessment += "\n\n" + get_response(
            "geological_recommendation", lang=lang, recommendation=region["recommendation"]
        )

    return assessment


def _identify_region(lat: float, lon: float) -> dict:
    """
    Identify the geological region from coordinates.

    Covers the key mining areas in Kenya, with a focus on
    Migori County (Valentine's area) and the Lake Victoria Gold Belt.
    """
    # Migori County / Nyatike area (Valentine's land)
    if -1.10 <= lat <= -0.90 and 34.10 <= lon <= 34.50:
        return {
            "name": "Nyatike, Migori County — Ziwa la Victoria Gold Belt",
            "known_minerals": ["Dhahabu (Gold)", "Shaba (Copper)", "Pyrite", "Quartz"],
            "geology": (
                "Eneo hili lipo kwenye Mkoa wa Migori Greenstone Belt. "
                "Miamba ya kijani (greenstone) yenye umri wa bilioni 2.7-2.8 "
                "inajulikana kuwa na madini ya dhahabu na shaba. "
                "Mfumo wa Nyanzian unajumuisha quartz veins, banded iron formations, "
                "na volcanic rocks ambazo mara nyingi zina dhahabu."
            ),
            "recommendation": (
                "Eneo hili lina uwezekano mkubwa wa kuwa na madini. "
                "Pendekezo: Anza na sampuli za mwamba (rock sampling) kwenye "
                "maeneo ya quartz veins. Tuma picha za miamba unayoiona "
                "nitakusaidia kutambua."
            ),
        }

    # Kakamega Gold Belt
    if 0.10 <= lat <= 0.40 and 34.50 <= lon <= 35.10:
        return {
            "name": "Kakamega — Gold Belt",
            "known_minerals": ["Dhahabu (Gold)", "Quartz", "Pyrite"],
            "geology": (
                "Kakamega Gold Belt ni mojawapo ya maeneo yenye dhahabu "
                "nchini Kenya. Miamba ya Archaean greenstone ina quartz veins "
                "zenye dhahabu."
            ),
            "recommendation": (
                "Eneo hili lina historia ndefu ya uchimbaji wa dhahabu. "
                "Sampuli za quartz veins zinaweza kuonyesha uwepo wa dhahabu."
            ),
        }

    # Kwale — Titanium / Rare Earths
    if -4.30 <= lat <= -3.90 and 39.30 <= lon <= 39.80:
        return {
            "name": "Kwale — Pwani ya Kenya",
            "known_minerals": ["Rutile (Titanium)", "Zircon", "Ilmenite", "Rare Earths"],
            "geology": (
                "Eneo la Kwale lina mchanga wa pwani (heavy mineral sands) "
                "wenye rutile, zircon, na ilmenite. Base Resources "
                "inachimba hapa."
            ),
            "recommendation": (
                "Madini ya pwani yanapatikana kwenye mchanga. "
                "Sampuli za mchanga wa pwani zinaweza kuonyesha uwepo wa madini haya."
            ),
        }

    # Turkana — Oil / Geothermal
    if 2.50 <= lat <= 4.50 and 34.50 <= lon <= 36.50:
        return {
            "name": "Turkana — Kaskazini mwa Kenya",
            "known_minerals": ["Mafuta (Oil)", "Soda Ash", "Geothermal"],
            "geology": (
                "Mfumo wa Rift Valley hapa una mafuta na rasilimali za geothermal. "
                "Lake Turkana yenyewe ina miamba ya volkenik."
            ),
            "recommendation": (
                "Eneo hili lina uwezo wa mafuta na geothermal. "
                "Lakini inahitaji utaalamu wa hali ya juu kuchunguza."
            ),
        }

    # Taita Taveta — Gemstones
    if -3.80 <= lat <= -3.20 and 38.30 <= lon <= 39.00:
        return {
            "name": "Taita Taveta — Gemstones",
            "known_minerals": ["Ruby (Yakuti)", "Sapphire", "Garnet", "Tourmaline"],
            "geology": (
                "Eneo hili lina miamba ya metamorphic inayojulikana "
                "kuwa na vito (gemstones) kama ruby na sapphire."
            ),
            "recommendation": (
                "Vito vinapatikana kwenye miamba ya metamorphic. "
                "Sampuli za miamba ya gneiss zinaweza kuonyesha uwepo wa vito."
            ),
        }

    # Default — unknown area
    return {
        "name": f"Eneo la GPS ({lat:.4f}, {lon:.4f})",
        "known_minerals": [],
        "geology": (
            "Tafadhali tuma picha za miamba eneo lako nitakusaidia "
            "kutambua aina ya miamba na madini yanayoweza kuwepo."
        ),
        "recommendation": (
            "Tuma picha za miamba na maelezo ya eneo lako — "
            "nitachambua na kukupa ripoti kamili."
        ),
    }
