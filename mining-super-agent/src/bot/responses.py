"""
Response Templates
===================
All bot responses in Swahili (primary), English, and Luo.

The bot should feel like talking to a knowledgeable friend,
NOT reading a technical manual.

Every mineral identification includes a disclaimer:
"Hii si uthibitisho wa maabara" — this is NOT lab confirmation.
"""

from typing import Any


# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------
# Key → {lang: template}
# Placeholders use Python .format() syntax: {name}, {mineral}, etc.

_TEMPLATES: dict[str, dict[str, str]] = {

    # === Welcome / Onboarding ===
    "welcome": {
        "sw": (
            "⛏️ Karibu {name}!\n\n"
            "Mimi ni msaidizi wako wa madini. Nitakusaidia:\n"
            "• Kutambua madini kutoka picha\n"
            "• Kupata bei za madini\n"
            "• Kuchambua eneo lako la GPS\n"
            "• Kujibu maswali kuhusu sheria za madini\n\n"
            "Sema tu kama unavyosema na rafiki — sio amri! "
            "Mfano: \"Nataka kujua kama kuna dhahabu kwenye shamba yangu\"\n\n"
            "Tuma picha, sauti, au mahali ulipo (GPS) nikuamshe. "
            "Chagua lugha yako hapo chini 👇"
        ),
        "en": (
            "⛏️ Welcome {name}!\n\n"
            "I'm your mining assistant. I can help you:\n"
            "• Identify minerals from photos\n"
            "• Get current commodity prices\n"
            "• Analyze your GPS location geology\n"
            "• Answer questions about mining law\n\n"
            "Talk to me like a friend — no commands needed!\n"
            "Example: \"Is there gold on my land?\"\n\n"
            "Send a photo, voice message, or your GPS location to get started. "
            "Choose your language below 👇"
        ),
        "luo": (
            "⛏️ Maribé {name}!\n\n"
            "An gi wuod gi thur gi minera. An ka gi konyi:\n"
            "• Nen gi minera e chiro\n"
            "• Ngiyo gi minera\n"
            "• Tich en gi GPS\n"
            "• Peny gi chiero gi minera\n\n"
            "Wach kaka in wach gi munde — ok onyiso komandi!\n"
            "Yudo: \"En gi dhahabu e shamba na?\"\n\n"
            "Oro chiro, suono, kata GPS in chakiel. "
            "Yer dholuo ne ng'eyo e kendo 👇"
        ),
    },

    # === Help ===
    "help": {
        "sw": (
            "🤝 *Mimi naweza kukusaidia kwa mambo haya:*\n\n"
            "📸 *Tuma Picha* — Nitambue aina ya mwamba au madini\n"
            "🎤 *Tuma Sauti* — Nisikilize na nikujibu\n"
            "📍 *Tuma GPS* — Nichambue eneo lako\n"
            "📄 *Tuma Document* — Nisome ripoti yako\n\n"
            "💬 *Ona tu kwa Kiswahili* — mfano:\n"
            "• \"Bei ya dhahabu sasa hivi ni ngapi?\"\n"
            "• \"Nataka kujua kama kuna shaba kwenye shamba langu\"\n"
            "• \"Leseni ya madini inapatikana wapi?\"\n\n"
            "Sio lazima uandike amri — ongea tu kama rafiki! 😊"
        ),
        "en": (
            "🤝 *Here's what I can help with:*\n\n"
            "📸 *Send a Photo* — I'll identify the mineral/rock\n"
            "🎤 *Send Voice* — I'll listen and respond\n"
            "📍 *Send GPS* — I'll analyze your area's geology\n"
            "📄 *Send Document* — I'll read your report\n\n"
            "💬 *Just talk naturally* — for example:\n"
            "• \"What's the current gold price?\"\n"
            "• \"Is there copper on my land?\"\n"
            "• \"Where do I get a mining license?\"\n\n"
            "No commands needed — just chat like a friend! 😊"
        ),
        "luo": (
            "🤝 *Ka an gi konyi gi tiende magi:*\n\n"
            "📸 *Oro Chiro* — An nen minera\n"
            "🎤 *Oro Suono* — An gi wach\n"
            "📍 *Oro GPS* — An tich gi ene\n"
            "📄 *Oro Document* — An gi puonj\n\n"
            "💬 *Wach kaka in wach gi munde* — yudo:\n"
            "• \"Ngiyo gi dhahabu saa ni?\"\n"
            "• \"En gi shaba e shamba na?\"\n"
            "• \"Leseni gi minera neni osumbwo?\"\n\n"
            "Ok komandi — wach kaka munde! 😊"
        ),
    },

    # === Language selection ===
    "choose_language": {
        "sw": "Chagua lugha unayopendelea:",
        "en": "Choose your preferred language:",
        "luo": "Yer dhuluo ne in pendwo:",
    },

    "language_set": {
        "sw": "✅ Kiswahili kimechaguliwa. Sasa ongea Kiswahili! 🇹🇿",
        "en": "✅ English selected. Let's go! 🇬🇧",
        "luo": "✅ Dholuo osetiyo. Wach dholuo! 🇰🇪",
    },

    # === Greetings ===
    "greeting_reply": {
        "sw": (
            "Habari {name}! 😊\n"
            "Sasa, nikusaidie nini leo? "
            "Tuma picha ya mwamba, sauti, au GPS — au tuulize swali lolote kuhusu madini."
        ),
        "en": (
            "Hey {name}! 😊\n"
            "What can I help you with today? "
            "Send a rock photo, voice message, or GPS — or just ask any mining question."
        ),
        "luo": (
            "Mara {name}! 😊\n"
            "In ka konyi ni? "
            "Oro chiro gi mwamba, suono, kata GPS — kata peni gi swali moloyo gi minera."
        ),
    },

    # === Thanks ===
    "thanks_reply": {
        "sw": "Karibu sana! 😊 Nikitajiwa tena, niambie tu.",
        "en": "You're welcome! 😊 Just ask anytime you need help.",
        "luo": "Oyawore! 😊 Ka in tiyo gi konyo, nyisa.",
    },

    # === About me ===
    "about_me": {
        "sw": (
            "Mimi ni msaidizi wa madini, aliyetengenezwa kukusaidia wewe — "
            "mchimbaji mdogo nchini Kenya.\n\n"
            "Ninaweza:\n"
            "• Kutambua madini kutoka picha (si uthibitisho wa maabara!)\n"
            "• Kupata bei za madini duniani\n"
            "• Kuchambua eneo lako kwa data ya kijiolojia\n"
            "• Kujibu maswali kuhusu sheria za madini Kenya\n\n"
            "Lengo langu: Kukupa taarifa sahihi ili usidanganywe na "
            "makampuni ya nchi za nje yanayotaka kununua shamba lako kwa bei ndogo.\n\n"
            "Ongea nami kama rafiki — sio kama mashine! 😊"
        ),
        "en": (
            "I'm a mining assistant built to help small-scale miners in Kenya.\n\n"
            "I can:\n"
            "• Identify minerals from photos (NOT lab-grade!)\n"
            "• Get real-time commodity prices\n"
            "• Analyze your location's geology\n"
            "• Answer questions about Kenya mining law\n\n"
            "My goal: Give you accurate info so you're not exploited by "
            "foreign companies offering pennies for your land.\n\n"
            "Talk to me like a friend — not a machine! 😊"
        ),
        "luo": (
            "An gi wuod gi thur gi minera, otim gi konyi — "
            "japiny gi minera e Kenya.\n\n"
            "An ka:\n"
            "• Nen gi minera e chiro (ok lab!)\n"
            "• Ngiyo gi minera\n"
            "• Tich gi ene gi GPS\n"
            "• Peny gi chiero gi minera e Kenya\n\n"
            "Paro: Miyo gi wach maber ka in ok odagi gi "
            "makampun gi piny machiegni.\n\n"
            "Wach kaka munde — ok kaka mashin! 😊"
        ),
    },

    # === Thinking / Processing ===
    "thinking": {
        "sw": "🤔 Nikichambua…",
        "en": "🤔 Analyzing…",
        "luo": "🤔 An tiyo gi tich…",
    },

    # === Photo analysis ===
    "photo_analyzing": {
        "sw": "📸 Naichambua picha yako… sekunde chache tu.",
        "en": "📸 Analyzing your photo… just a moment.",
        "luo": "📸 An tich gi chiro… miniti moko.",
    },

    "photo_saved": {
        "sw": "📸 Picha imehifadhiwa. Naichambua sasa…",
        "en": "📸 Photo saved. Analyzing now…",
        "luo": "📸 Chiro osehifadhi. An ticho…",
    },

    # === Mineral identification ===
    "mineral_result_header": {
        "sw": "🔬 *Matokeo ya Uchambuzi wa Mwamba:*",
        "en": "🔬 *Rock Analysis Results:*",
        "luo": "🔬 *Tich gi Mwamba:*",
    },

    "mineral_result_line": {
        "sw": "• {mineral} ({mineral_en}) — uhakika: {confidence}%",
        "en": "• {mineral_en} ({mineral}) — confidence: {confidence}%",
        "luo": "• {mineral} — {confidence}%",
    },

    "mineral_disclaimer": {
        "sw": (
            "⚠️ *MUHIMU:* Hii si uthibitisho wa maabara. "
            "Matokeo haya ni ya awali tu. Kwa uthibitisho kamili, "
            "hitaji sampuli kupelekwa maabara ya kijiolojia."
        ),
        "en": (
            "⚠️ *IMPORTANT:* This is NOT lab confirmation. "
            "These results are preliminary. For full verification, "
            "samples must be sent to a geological laboratory."
        ),
        "luo": (
            "⚠️ *NGIMA:* Mani ok ne lab. "
            "Tich magi ng'eny gi mathoth. Gi tich maber, "
            "sampul odu gi lab gi minera."
        ),
    },

    "mineral_low_confidence": {
        "sw": (
            "⚠️ Uhakika ni wa chini sana. "
            "Pendekezo: Tuma picha zaidi za mwamba huo kutoka pande tofauti, "
            "au tuma sampuli kwa maabara."
        ),
        "en": (
            "⚠️ Confidence is very low. "
            "Recommendation: Send more photos from different angles, "
            "or send a sample to a laboratory."
        ),
        "luo": (
            "⚠% Uhakika ni mnyalo. "
            "Pendekezo: Oro chiro moloyo gi mwamba man, "
            "kat or sampul gi lab."
        ),
    },

    "mineral_unclear": {
        "sw": (
            "🤔 Siwezi kutambua madini haya kwa uhakika kutoka kwenye picha hii.\n\n"
            "Tafadhali:\n"
            "• Tuma picha ya karibu zaidi\n"
            "• Hakikisha mwanga ni mzuri\n"
            "• Onyesha ukubwa wa mwamba (weka kitu karibu yake)\n\n"
            "Najaribu tena na picha bora zaidi."
        ),
        "en": (
            "🤔 I can't identify this mineral with confidence from this photo.\n\n"
            "Please:\n"
            "• Send a closer photo\n"
            "• Make sure lighting is good\n"
            "• Show scale (place something nearby)\n\n"
            "I'll try again with a better photo."
        ),
        "luo": (
            "🤔 Ok an ka nen minera man gi chiro man.\n\n"
            "Chiro:\n"
            "• Oro chiro malit\n"
            "• Miyo wang' maber\n"
            "• Nyis ukub gi mwamba\n\n"
            "An gi tem gi chiro maber."
        ),
    },

    "mineral_confirmed": {
        "sw": "✅ Umekubali: {mineral}. Nitakumbuka hii kwa ripoti yako.",
        "en": "✅ Confirmed: {mineral}. I'll remember this for your report.",
        "luo": "✅ Osetimo: {mineral}. An gi kum gi man gi ripot ne.",
    },

    "mineral_retry_prompt": {
        "sw": "📸 Tuma picha nyingine ya mwamba huo — nitajaribu tena.",
        "en": "📸 Send another photo of the rock — I'll try again.",
        "luo": "📸 Oro chiro moloyo gi mwamba — an gi tem.",
    },

    # === Price information ===
    "price_loading": {
        "sw": "💰 Napata bei za madini sasa hivi…",
        "en": "💰 Fetching current prices…",
        "luo": "💰 An ng'eny gi ngiyo…",
    },

    "price_info": {
        "sw": (
            "💰 *Bei za Madini Sasa Hivi:*\n\n"
            "🥇 Dhahabu (Gold): ~$3,300/oz\n"
            "🥈 Shaba (Copper): ~$9,500/tani\n"
            "🔩 Iron Ore: ~$110/tani\n\n"
            "⚠️ Bei hizi zinaweza kubadilika. "
            "Hizi ni bei za soko la dunia. "
            "Bei ya ndani Kenya inaweza kuwa tofauti.\n\n"
            "Unataka kujua bei ya madini gani?"
        ),
        "en": (
            "💰 *Current Commodity Prices:*\n\n"
            "🥇 Gold: ~$3,300/oz\n"
            "🥈 Copper: ~$9,500/tonne\n"
            "🔩 Iron Ore: ~$110/tonne\n\n"
            "⚠️ Prices fluctuate. These are global market prices. "
            "Local Kenyan prices may differ.\n\n"
            "Want to know about a specific mineral?"
        ),
        "luo": (
            "💰 *Ngiyo gi Minera:*\n\n"
            "🥇 Dhahabu: ~$3,300/oz\n"
            "🥈 Shaba: ~$9,500/tani\n"
            "🔩 Iron Ore: ~$110/tani\n\n"
            "⚠% Ngiyo gi piny ng'eny gi lweny. "
            "Man gi ngiyo gi dunia. "
            "Ngiyo gi Kenya en ka to gi.\n\n"
            "In pend gi ngiyo gi minera mane?"
        ),
    },

    "price_loading_done": {
        "sw": "💰 *Bei za Madini:*",
        "en": "💰 *Commodity Prices:*",
        "luo": "💰 *Ngiyo gi Minera:*",
    },

    # === Legal information ===
    "legal_info": {
        "sw": (
            "⚖️ *Sheria za Madini Kenya:*\n\n"
            "Kwa mujibu wa Mining Act 2016:\n\n"
            "1. *Leseni ya Kuchimba (Mining License)* — Inahitajika kwa uchimbaji wowote\n"
            "2. *Leseni ya Kuchunguza (Prospecting License)* — Kwa kutafuta madini\n"
            "3. *Haki za Wamiliki wa Ardhi* — Wana haki ya kujadili bei\n\n"
            "⚠️ Muhimu: Mchina yeyote anayekuja kununua shamba lako "
            "anapaswa kupata leseni kutoka county. "
            "Huna haki ya kuuza madini yasiyo yako — ardhi ni yako, "
            "lakini madini ni ya serikali chini ya sheria.\n\n"
            "Unataka kujua zaidi kuhusu leseni au haki zako?"
        ),
        "en": (
            "⚖️ *Kenya Mining Law:*\n\n"
            "Under the Mining Act 2016:\n\n"
            "1. *Mining License* — Required for any extraction\n"
            "2. *Prospecting License* — For exploration\n"
            "3. *Landowner Rights* — You have the right to negotiate\n\n"
            "⚠️ Important: Any foreigner wanting to buy your land "
            "must have a license from the county. "
            "You don't own the minerals — the land is yours, "
            "but minerals belong to the government by law.\n\n"
            "Want to know more about licensing or your rights?"
        ),
        "luo": (
            "⚖️ *Chiero gi Minera Kenya:*\n\n"
            "Gi Mining Act 2016:\n\n"
            "1. *Leseni gi Minera* — Dhi gi minera moloyo\n"
            "2. *Leseni gi Tich* — Gi tich gi minera\n"
            "3. *Haki gi Japiny gi Shamba* — Haki gi nego\n\n"
            "⚠️ Ngima: Machiegni moloyo gi piny "
            "ongeyo leseni gi county. "
            "Minera ok ne gi — shamba ne gi, "
            "minera ne gi serikali gi chiero.\n\n"
            "In pend gi ng'eyo moloyo gi leseni kata haki ne?"
        ),
    },

    # === Location analysis ===
    "location_analyzing": {
        "sw": (
            "📍 Eneo lako: {lat}, {lon}\n"
            "Naichambua data ya kijiolojia…"
        ),
        "en": (
            "📍 Your location: {lat}, {lon}\n"
            "Analyzing geological data…"
        ),
        "luo": (
            "📍 Ene ne: {lat}, {lon}\n"
            "An tich gi data gi minera…"
        ),
    },

    "location_header": {
        "sw": "📍 *Uchambuzi wa Eneo: {lat}, {lon}*",
        "en": "📍 *Geological Assessment: {lat}, {lon}*",
        "luo": "📍 *Tich gi Ene: {lat}, {lon}*",
    },

    "location_disclaimer": {
        "sw": (
            "⚠️ *Kumbuka:* Hii ni tathmini ya awali kwa msingi wa data ya kijiolojia. "
            "Kwa uchunguzi kamili, hitaji mtaalamu wa kijiolojia aje eneo lako."
        ),
        "en": (
            "⚠️ *Note:* This is a preliminary assessment based on geological data. "
            "For full exploration, hire a qualified geologist to visit your site."
        ),
        "luo": (
            "⚠️ *Pwod:* Man gi tich gi mathoth gi data gi minera. "
            "Gi tich maber, golo munde gi minera ka owe ene ne."
        ),
    },

    "geological_region": {
        "sw": "🌍 *Eneo:* {region}",
        "en": "🌍 *Region:* {region}",
        "luo": "🌍 *Ene:* {region}",
    },

    "geological_known_minerals": {
        "sw": "⛏️ *Madini yanayojulikana eneo hili:*\n{minerals}",
        "en": "⛏️ *Known minerals in this area:*\n{minerals}",
        "luo": "⛏️ *Minera gi ene man:*\n{minerals}",
    },

    "geological_formation": {
        "sw": "🪨 *Mwamba wa Kijiolojia:*\n{geology}",
        "en": "🪨 *Geological Formation:*\n{geology}",
        "luo": "🪨 *Mwamba gi Kijiolojia:*\n{geology}",
    },

    "geological_recommendation": {
        "sw": "💡 *Pendekezo:*\n{recommendation}",
        "en": "💡 *Recommendation:*\n{recommendation}",
        "luo": "💡 *Pendekezo:*\n{recommendation}",
    },

    # === Voice ===
    "voice_transcribing": {
        "sw": "🎤 Nasikiliza sauti yako…",
        "en": "🎤 Listening to your voice…",
        "luo": "🎤 An gi wach ne…",
    },

    "voice_transcribed": {
        "sw": "🎤 *Sauti yako:* \"{transcript}\"\n\nSasa nikujibu…",
        "en": "🎤 *You said:* \"{transcript}\"\n\nLet me respond…",
        "luo": "🎤 *Wach ne:* \"{transcript}\"\n\nAn penyo…",
    },

    "voice_transcription_failed": {
        "sw": "😔 Samahani, siwezi kusikiliza sauti yako. Tafadhali jaribu tena au andika ujumbe.",
        "en": "😔 Sorry, I couldn't understand your voice. Please try again or type a message.",
        "luo": "😔 Mor, ok an ka wach ne. Tem kata type.",
    },

    # === Document ===
    "document_processing": {
        "sw": "📄 Nasoma document yako: {filename}…",
        "en": "📄 Reading your document: {filename}…",
        "luo": "📄 An gi puonj gi doc: {filename}…",
    },

    "document_too_large": {
        "sw": "📄 Document ni kubwa sana (zaidi ya 20MB). Tafadhali tuma file ndogo zaidi.",
        "en": "📄 Document is too large (over 20MB). Please send a smaller file.",
        "luo": "📄 Doc ni yat (koro 20MB). Oro file mnyalo.",
    },

    "document_unsupported": {
        "sw": "📄 Samahani, siwezi kusoma file ya aina hii ({filename}). Nitumie PDF au picha.",
        "en": "📄 Sorry, I can't read this file type ({filename}). Send me a PDF or image.",
        "luo": "📄 Mor, ok an ka puonj file man ({filename}). Oro PDF kata chiro.",
    },

    "document_image_redirect": {
        "sw": "📸 Hii ni picha! Nitumie kama picha moja kwa moja — nitakutambua madini.",
        "en": "📸 This is an image! Send it as a photo directly — I'll identify the minerals.",
        "luo": "📸 Man gi chiro! Oro kaka chiro — an nen minera.",
    },

    "document_pdf_summary": {
        "sw": (
            "📄 *Muhtasari wa Document:*\n\n"
            "• Kurasa: {pages}\n"
            "• Maneno: {word_count}\n\n"
            "*Muhtasari:*\n{preview}"
        ),
        "en": (
            "📄 *Document Summary:*\n\n"
            "• Pages: {pages}\n"
            "• Words: {word_count}\n\n"
            "*Preview:*\n{preview}"
        ),
        "luo": (
            "📄 *Muhtasari gi Doc:*\n\n"
            "• Kurasa: {pages}\n"
            "• Wach: {word_count}\n\n"
            "*Preview:*\n{preview}"
        ),
    },

    "document_pdf_empty": {
        "sw": "📄 Document haina maandishi. Tafadhali tuma document yenye maandishi.",
        "en": "📄 This document has no text content. Please send a text-based document.",
        "luo": "📄 Doc man ok gi wach. Oro doc gi wach.",
    },

    "document_pdf_no_parser": {
        "sw": "📄 Samahani, siwezi kusoma PDF sasa hivi. Tafadhali jaribu baadaye.",
        "en": "📄 Sorry, I can't read PDFs right now. Please try again later.",
        "luo": "📄 Mor, ok an ka puonj PDF saa. Tem e mae.",
    },

    "document_pdf_error": {
        "sw": "📄 Samahani, kuna hitilafu katika kusoma PDF. Tafadhali jaribu tena.",
        "en": "📄 Sorry, there was an error reading the PDF. Please try again.",
        "luo": "📄 Mor, error e puonj PDF. Tem.",
    },

    # === Report ===
    "report_header": {
        "sw": "📊 *Ripoti ya Uchambuzi Wako:*",
        "en": "📊 *Your Analysis Report:*",
        "luo": "📊 *Ripot ne:*",
    },

    "no_history": {
        "sw": "📭 Bado hujafanya uchambuzi wowote. Tuma picha au GPS uanze!",
        "en": "📭 No analysis done yet. Send a photo or GPS to start!",
        "luo": "📭 Ok tich kata mano. Oro chiro kata GPS!",
    },

    "no_analysis": {
        "sw": "📭 Hakuna matokeo ya uchambuzi bado.",
        "en": "📭 No analysis results yet.",
        "luo": "📭 Ok gi tich kata.",
    },

    # === Rate limiting ===
    "rate_limited": {
        "sw": "⏳ Pole, tumefikia kikomo. Subiri dakika moja kisha jaribu tena.",
        "en": "⏳ Sorry, rate limit reached. Wait a minute and try again.",
        "luo": "⏳ Mor, limit osebiro. Sur miniti kata tem.",
    },

    # === Errors ===
    "error_generic": {
        "sw": "😔 Samahani, kuna hitilafu. Tafadhali jaribu tena baada ya muda mfupi.",
        "en": "😔 Sorry, something went wrong. Please try again in a moment.",
        "luo": "😔 Mor, error osebiro. Tem e mae.",
    },

    "error_agent": {
        "sw": "😔 Samahani, mfumo wa uchambuzi haujapatikana sasa hivi. Jaribu tena baadaye.",
        "en": "😔 Sorry, the analysis system is currently unavailable. Try again later.",
        "luo": "😔 Mor, tich gi minera ok e saa. Tem e mae.",
    },

    "error_photo": {
        "sw": "😔 Samahani, picha haijachambuliwa. Tafadhali tuma picha nyingine.",
        "en": "😔 Sorry, the photo couldn't be processed. Please send another one.",
        "luo": "😔 Mor, chiro ok osetimo. Oro chiro moko.",
    },

    "error_voice": {
        "sw": "😔 Samahani, sauti haijasikilizwa. Tafadhali jaribu tena au andika.",
        "en": "😔 Sorry, the voice message couldn't be processed. Try again or type.",
        "luo": "😔 Mor, suono ok osewacho. Tem kata type.",
    },

    "error_location": {
        "sw": "😔 Samahani, GPS haikupatikana. Tafadhali tuma tena.",
        "en": "😔 Sorry, location data wasn't received. Please send again.",
        "luo": "😔 Mor, GPS ok osebiro. Tem.",
    },

    "error_location_analysis": {
        "sw": "😔 Samahani, uchambuzi wa eneo haujafanikiwa. Tafadhali jaribu tena.",
        "en": "😔 Sorry, location analysis failed. Please try again.",
        "luo": "😔 Mor, tich gi ene ok osebiro. Tem.",
    },

    "error_document": {
        "sw": "😔 Samahani, document haikuchambuliwa. Tafadhali tuma tena.",
        "en": "😔 Sorry, the document couldn't be processed. Please send again.",
        "luo": "😔 Mor, doc ok osebiro. Tem.",
    },

    # === Admin ===
    "admin_stats": {
        "sw": (
            "📊 *Takwimu za Mfumo:*\n\n"
            "👥 Watumiaji: {total_users}\n"
            "🟢 Active sasa: {active_users}\n"
            "💬 Jumla ya ujumbe: {total_messages}\n"
        ),
        "en": (
            "📊 *System Stats:*\n\n"
            "👥 Total users: {total_users}\n"
            "🟢 Active now: {active_users}\n"
            "💬 Total messages: {total_messages}\n"
        ),
        "luo": (
            "📊 *Takwimu:*\n\n"
            "👥 Japiny: {total_users}\n"
            "🟢 Saa: {active_users}\n"
            "💬 Wach moloyo: {total_messages}\n"
        ),
    },

    # === Quick action labels ===
    "action_price": {
        "sw": "💰 Bei za Madini",
        "en": "💰 Commodity Prices",
        "luo": "💰 Ngiyo gi Minera",
    },

    "action_report": {
        "sw": "📊 Ripoti",
        "en": "📊 Report",
        "luo": "📊 Ripot",
    },

    "action_help": {
        "sw": "❓ Msaada",
        "en": "❓ Help",
        "luo": "❓ Konyo",
    },

    # === Mineral analysis pending (placeholder) ===
    "mineral_analysis_pending": {
        "sw": (
            "🔬 Naichambua swali lako kuhusu madini…\n\n"
            "Mfumo wa uchambuzi wa AI unajengwa. "
            "Hivi karibuni utapata majibu kamili ya kijiolojia.\n\n"
            "Kwa sasa, tuma picha ya mwamba — "
            "nitajaribu kutambua aina ya madini."
        ),
        "en": (
            "🔬 Analyzing your mineral question…\n\n"
            "The AI analysis system is being built. "
            "Soon you'll get full geological answers.\n\n"
            "For now, send a photo of the rock — "
            "I'll try to identify the minerals."
        ),
        "luo": (
            "🔬 An tich gi swali ne gi minera…\n\n"
            "Tich gi AI ng'eyo e. "
            "E mae in ka pen gi wach maber gi minera.\n\n"
            "Saa, oro chiro gi mwamba — "
            "an tem gi nen minera."
        ),
    },

    # === Report loading ===
    "report_loading": {
        "sw": "📊 Ninatengeneza ripoti yako…",
        "en": "📊 Generating your report…",
        "luo": "📊 An ripot ne…",
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_response(key: str, lang: str = "sw", **kwargs: Any) -> str:
    """
    Get a localized response template and fill in placeholders.

    Falls back: requested lang → Swahili → English → key name.
    """
    template_dict = _TEMPLATES.get(key)
    if not template_dict:
        return f"[{key}]"

    # Fallback chain
    template = template_dict.get(lang) or template_dict.get("sw") or template_dict.get("en")
    if not template:
        return f"[{key}]"

    try:
        return template.format(**kwargs)
    except KeyError:
        # If a placeholder is missing, return the raw template
        return template


def get_all_keys() -> list[str]:
    """Return all registered response keys (for testing)."""
    return list(_TEMPLATES.keys())


def get_supported_languages() -> list[str]:
    """Return all supported language codes."""
    return ["sw", "en", "luo"]
