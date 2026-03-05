# Feature Request: FR-030 - Photo/Screenshot OCR Capture

**Status**: ✅ Completed
**Priority**: 🟡 Medium
**Story Points**: 5
**Created**: 2026-03-05
**Updated**: 2026-03-05
**Assigned Sprint**: Sprint 11

## Description

Enable users to send photos (whiteboards, documents, handwritten notes, screenshots, receipts) and have the bot extract text via OCR, then create a Joplin note with both the image and extracted text. This expands capture modalities beyond typed text and URLs.

## User Story

As a user who encounters information in visual form,
I want to photograph whiteboards, documents, or handwritten notes and have them saved to Joplin,
so that I can capture knowledge without manually transcribing.

## Acceptance Criteria

- [ ] Sending a photo triggers OCR processing
- [ ] Extracted text is included in the note body
- [ ] Original image is attached to the Joplin note
- [ ] LLM classifies/routes the content (folder, tags) based on extracted text
- [ ] User can add caption to photo for additional context
- [ ] Works with: screenshots, whiteboard photos, documents, handwritten notes
- [ ] Handles photos with no text gracefully ("No text detected")
- [ ] Multiple photos can be sent in sequence
- [ ] Processing indicator shown while OCR runs

## Business Value

Much valuable information exists in visual form:
- Whiteboard diagrams from meetings
- Handwritten notes and sketches
- Screenshots of errors, UI, or conversations
- Business cards, receipts, documents
- Book pages, articles, signs

OCR capture removes the friction of manual transcription and ensures visual content enters the Second Brain.

## Technical Requirements

### 1. OCR Provider — Decision

**Selected: Gemini 1.5 Flash** (via existing `GEMINI_API_KEY`)

We already use Gemini for recipe image generation (`src/recipe_image.py`), so the API key and billing are in place. Gemini does far more than raw OCR — it understands context, classifies content, and can extract structured data (receipt fields, business card contacts, etc.) in a single call.

| Provider | Cost | Quality | Status |
|----------|------|---------|--------|
| **Gemini 1.5 Flash** | **Free tier** (15 RPM, ~1M tokens/day) | Excellent — OCR + context understanding | **Selected** — key already configured |
| Tesseract (local) | Free | Decent for print, poor for handwriting | Rejected — adds ~150MB to image, 1GB RAM tight on Fly.io |
| OpenAI GPT-4o | ~$2.50/1K images | Excellent | Rejected — extra cost, different provider |
| Google Cloud Vision | ~$1.50/1K images | Excellent raw OCR | Rejected — another GCP service, no context understanding |
| AWS Textract | ~$1.50/1K pages | Great for documents | Rejected — AWS dependency |

**Why Gemini wins:**
- Zero incremental cost (free tier covers personal use)
- Zero infrastructure (no Tesseract install, no Docker image bloat, no RAM pressure)
- Context-aware — not just OCR but understanding (a receipt returns merchant/amount/date, a business card returns contact fields)
- Same pattern as existing `src/recipe_image.py` — proven integration

### 2. Processing Flow

```
User sends photo
       │
       ▼
┌──────────────────────┐
│ Download image from  │
│ Telegram             │
└──────────────────────┘
       │
       ▼
┌──────────────────────┐
│ Send to Gemini Flash │
│ (OCR + classify)     │
└──────────────────────┘
       │
       ▼
┌──────────────────────┐
│ Extract text result  │
└──────────────────────┘
       │
       ▼
┌──────────────────────┐
│ LLM classifies       │
│ (folder, tags, title)│
└──────────────────────┘
       │
       ▼
┌──────────────────────┐
│ Create Joplin note   │
│ with image + text    │
└──────────────────────┘
       │
       ▼
┌──────────────────────┐
│ Confirm to user      │
└──────────────────────┘
```

### 3. Gemini Vision OCR Implementation

```python
async def extract_text_from_image(image_bytes: bytes) -> dict:
    """Extract text and classify image content using Gemini 1.5 Flash."""

    import base64
    base64_image = base64.b64encode(image_bytes).decode('utf-8')

    settings = get_settings()
    api_key = settings.google.gemini_api_key

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{
            "parts": [
                {
                    "text": """Extract all text from this image.

Return a JSON object with:
- "text": The extracted text, preserving structure where possible
- "type": One of "document", "whiteboard", "handwritten", "screenshot", "receipt", "business_card", "other"
- "summary": A one-line summary of what this image contains
- "suggested_title": A good title for a note about this content
- "structured_data": Optional dict with extracted fields (e.g. merchant/amount/date for receipts, name/email/phone for business cards)

If no text is visible, return {"text": "", "type": "image", "summary": "Image with no text", "suggested_title": "Photo capture"}"""
                },
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": base64_image
                    }
                }
            ]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)
```

Gemini handles OCR and classification in one call — no separate LLM step needed for routing. The `structured_data` field enables richer note content for receipts, business cards, etc.

### 5. Note Format with Image

```markdown
# Whiteboard Notes - Sprint Planning

📷 *Captured from photo*

## Extracted Text

[OCR extracted text here, preserving structure]

## Original Image

![Captured image](:/resource_id_here)

---
*Captured via photo on 2026-03-05*
```

### 6. Joplin Image Attachment

```python
async def create_note_with_image(
    title: str,
    body: str,
    image_bytes: bytes,
    folder_id: str,
    tags: list[str],
    joplin_client: JoplinClient
) -> str:
    """Create note with attached image."""

    # First create the resource (image attachment)
    resource = await joplin_client.create_resource(
        image_bytes,
        filename="capture.jpg",
        mime_type="image/jpeg"
    )

    # Add image reference to body
    body_with_image = f"{body}\n\n## Original Image\n\n![Captured image](:/{resource['id']})"

    # Create the note
    note = await joplin_client.create_note(
        title=title,
        body=body_with_image,
        parent_id=folder_id,
        tags=tags
    )

    return note['id']
```

### 7. Caption Handling

If user adds caption to photo:

```python
async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo with optional caption."""
    message = update.effective_message

    # Get largest photo size
    photo = message.photo[-1]  # Largest resolution
    photo_file = await photo.get_file()
    image_bytes = await photo_file.download_as_bytearray()

    # Caption provides additional context
    caption = message.caption or ""

    # OCR the image
    ocr_result = await extract_text_from_image(bytes(image_bytes))

    # Combine caption + extracted text for classification
    full_context = f"{caption}\n\n{ocr_result['text']}"

    # ... continue with classification and note creation
```

### 8. Processing Indicator

```python
async def handle_photo_with_progress(message: Message, ...):
    """Show progress while processing."""

    # Send "processing" message
    status_msg = await message.reply_text("🔍 Processing image...")

    try:
        # OCR
        await status_msg.edit_text("🔍 Extracting text...")
        ocr_result = await extract_text_from_image(image_bytes)

        # Classification
        await status_msg.edit_text("🧠 Classifying content...")
        decision = await classify_content(ocr_result['text'])

        # Note creation
        await status_msg.edit_text("📝 Creating note...")
        note_id = await create_note_with_image(...)

        # Final confirmation
        await status_msg.edit_text(
            f"✅ Saved: **{decision.title}**\n"
            f"📁 {folder_name}\n"
            f"📷 {ocr_result['type'].title()} captured"
        )

    except Exception as e:
        await status_msg.edit_text(f"❌ Error processing image: {str(e)}")
```

## Implementation

### Key Files to Create

| File | Purpose |
|------|---------|
| `src/ocr_service.py` | OCR processing logic |
| `src/handlers/photo.py` | Photo message handlers |
| `tests/test_ocr.py` | Unit tests |

### Key Files to Modify

| File | Changes |
|------|---------|
| `src/handlers/core.py` | Register photo handler |
| `src/joplin_client.py` | Add create_resource method |
| `src/recipe_image.py` | Reference for Gemini API pattern (retry, error handling) |

### Joplin Resource API

```python
async def create_resource(
    self,
    data: bytes,
    filename: str,
    mime_type: str
) -> dict:
    """Upload a resource (attachment) to Joplin."""

    # Joplin expects multipart form data
    files = {
        'data': (filename, data, mime_type),
        'props': (None, json.dumps({'filename': filename}))
    }

    response = await self._post("/resources", files=files)
    return response
```

## Testing

### Unit Tests

- [ ] Test OCR extraction (mock provider)
- [ ] Test note creation with image attachment
- [ ] Test caption integration
- [ ] Test no-text image handling
- [ ] Test image download from Telegram
- [ ] Test progress indicator updates

### Manual Testing Scenarios

| Input | Expected |
|-------|----------|
| Photo of whiteboard | Text extracted, note created, image attached |
| Screenshot with text | Text extracted, classified appropriately |
| Photo with caption "Meeting notes" | Caption influences title/folder |
| Photo with no text (landscape) | "No text detected", still saves image |
| Handwritten note | Attempts extraction (quality varies) |
| Receipt/document | Text extracted, possibly tagged "receipt" |

## Dependencies

- FR-005: Joplin REST API Client (required)
- FR-006: LLM Integration (required - for classification fallback)
- Gemini API key (already configured via `GEMINI_API_KEY`)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Poor OCR quality | Inform user, suggest clearer photo |
| Large images slow to process | Resize before sending to Gemini, show progress |
| Gemini free tier rate limit (15 RPM) | Retry with backoff (same pattern as `src/recipe_image.py`); sufficient for personal use |
| Handwriting hard to read | Gemini handles handwriting well; set expectations for messy scripts |
| Privacy (cloud processing) | Gemini processes images transiently; document in user guide |

## Future Enhancements

- [ ] Document scanning mode (multi-page PDF creation)
- [ ] Business card parsing (extract name, email, phone)
- [ ] Receipt parsing (extract merchant, amount, date)
- [ ] Diagram/chart interpretation
- [ ] Math equation recognition (LaTeX output)
- [ ] Translation of foreign language text
- [ ] Batch photo processing

## Notes

- Gemini 1.5 Flash does OCR + classification + structured extraction in one call — no separate LLM routing step needed
- Reuse the retry/429-handling pattern from `src/recipe_image.py`
- Consider image resizing to reduce upload time (Gemini accepts up to 20MB but smaller is faster)
- Joplin resources need proper cleanup if note creation fails
- See [API Reference](../../../docs/api-reference.md) for Gemini capabilities and limits

## History

- 2026-03-05 - Feature request created
- 2026-03-05 - Updated: Gemini 1.5 Flash selected as OCR provider (replaces GPT-4V recommendation)
