"""
Document Handler
================
When a miner sends a document (PDF report, etc.):
1. Download and inspect the file
2. Process based on type (PDF → extract text, image → mineral ID)
3. Return analysis or confirmation
"""

import logging
import tempfile
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from bot.conversation import ConversationManager
from bot.middleware.language import LanguageMiddleware
from bot.responses import get_response

logger = logging.getLogger(__name__)

DOC_DIR = Path(tempfile.gettempdir()) / "mining-agent-docs"
DOC_DIR.mkdir(parents=True, exist_ok=True)


async def handle_document(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    conv_manager: ConversationManager,
    lang_middleware: LanguageMiddleware,
    lang: str,
) -> None:
    """Process a document message."""
    user_id = update.effective_user.id
    document = update.message.document

    if not document:
        await update.message.reply_text(get_response("error_document", lang=lang))
        return

    file_name = document.file_name or "unknown"
    mime_type = document.mime_type or "application/octet-stream"
    file_size = document.file_size or 0

    logger.info(
        "Document from user %s: %s (%s, %d bytes)",
        user_id, file_name, mime_type, file_size,
    )

    # Size limit: 20 MB
    max_size = 20 * 1024 * 1024
    if file_size > max_size:
        await update.message.reply_text(
            get_response("document_too_large", lang=lang)
        )
        return

    thinking_msg = await update.message.reply_text(
        get_response("document_processing", lang=lang, filename=file_name)
    )

    try:
        # Download the file
        file = await context.bot.get_file(document.file_id)
        doc_path = DOC_DIR / f"{user_id}_{document.file_unique_id}_{file_name}"
        await file.download_to_drive(str(doc_path))

        # Process based on type
        if mime_type == "application/pdf" or file_name.lower().endswith(".pdf"):
            result = await _process_pdf(doc_path, lang)
        elif mime_type.startswith("image/"):
            result = get_response("document_image_redirect", lang=lang)
        else:
            result = get_response("document_unsupported", lang=lang, filename=file_name)

        await thinking_msg.edit_text(result)

        # Store in history
        conv_manager.add_message(
            user_id,
            "user",
            f"[Document] {file_name}",
            lang=lang,
            intent="document_upload",
        )
        conv_manager.add_message(
            user_id,
            "assistant",
            result,
            lang=lang,
            intent="document_result",
        )

    except Exception as exc:
        logger.exception("Document processing failed for user %s: %s", user_id, exc)
        await thinking_msg.edit_text(
            get_response("error_document", lang=lang)
        )


async def _process_pdf(pdf_path: Path, lang: str) -> str:
    """
    Process a PDF document.

    Extracts text and provides a summary. In production this would
    feed into the RAG pipeline for analysis.
    """
    try:
        import pdfplumber

        text_content = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages[:10]:  # Limit to first 10 pages
                text = page.extract_text()
                if text:
                    text_content.append(text)

        if not text_content:
            return get_response("document_pdf_empty", lang=lang)

        full_text = "\n".join(text_content)
        word_count = len(full_text.split())

        # TODO: Send to RAG pipeline for deep analysis
        # For now, return a summary
        preview = full_text[:500] + ("…" if len(full_text) > 500 else "")

        return get_response(
            "document_pdf_summary",
            lang=lang,
            word_count=word_count,
            pages=len(text_content),
            preview=preview,
        )

    except ImportError:
        logger.warning("pdfplumber not installed")
        return get_response("document_pdf_no_parser", lang=lang)
    except Exception as exc:
        logger.error("PDF processing failed: %s", exc)
        return get_response("document_pdf_error", lang=lang)
