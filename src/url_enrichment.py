"""
URL enrichment helpers for note creation.

Extracts text and metadata from URLs so the LLM can generate
better tags and richer note bodies.
"""

from __future__ import annotations

import html
import json
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

URL_PATTERN = re.compile(r"(https?://[^\s<>()]+)", re.IGNORECASE)


def extract_urls(text: str) -> List[str]:
    """Extract HTTP(S) URLs from user text."""
    if not text:
        return []
    urls = [m.group(1).rstrip(".,);]") for m in URL_PATTERN.finditer(text)]
    seen = set()
    deduped: List[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


def _extract_meta(html_text: str, names: List[str]) -> Optional[str]:
    for name in names:
        pattern = (
            rf'<meta[^>]+(?:name|property)=["\']{re.escape(name)}["\'][^>]*content=["\'](.*?)["\']'
        )
        m = re.search(pattern, html_text, re.IGNORECASE | re.DOTALL)
        if m:
            value = html.unescape(m.group(1)).strip()
            if value:
                return value
    return None


def _extract_text(html_text: str, max_chars: int = 4000) -> str:
    clean = re.sub(r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>", " ", html_text, flags=re.IGNORECASE)
    clean = re.sub(r"<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = html.unescape(clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:max_chars]


# Recipe detection: keywords and site domains (host contains).
RECIPE_KEYWORDS = (
    "recipe", "recipes", "/recipe/", "ingredient", "prep time", "cook time",
    "recipe instructions", "cooking instructions", "directions",
    "recette", "recettes", "/recette/", "ingrédients", "préparation", "cuisson",
    "étapes", "instructions",
)
RECIPE_DOMAINS = (
    "ricardo", "recettesduquebec", "recettes.qc.ca", "coupdepouce", "metro",
    "ici.radio-canada", "allrecipes", "bonappetit", "epicurious", "bbcgoodfood",
    "seriouseats", "foodnetwork", "delish", "tasty", "thekitchn",
    "marmiton", "750g", "cuisineactuelle", "journaldesfemmes", "chefsimon",
)


def _classify_url_type(url: str, title: str, extracted_text: str) -> str:
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()
    haystack = f"{host} {path} {title.lower()} {extracted_text[:500].lower()}"

    if any(kw in haystack for kw in RECIPE_KEYWORDS):
        return "recipe"
    if any(dom in host for dom in RECIPE_DOMAINS):
        return "recipe"
    if any(x in haystack for x in ["youtube.com", "youtu.be", "vimeo", "watch?v=", "/video/", "podcast", "spotify.com/show"]):
        return "media"
    if any(x in haystack for x in ["docs.", "/docs", "tutorial", "guide", "how to", "playbook", "checklist", "framework"]):
        return "actionable"
    return "knowledge"


def _template_for_url_type(url_type: str) -> Dict[str, str]:
    if url_type == "media":
        return {
            "template_id": "1",
            "template_name": "Quick Capture",
            "instructions": (
                "Use Template 1 - Quick Capture with sections: "
                "'Source', 'Why this matters', 'Key points'. "
                "Keep concise and practical."
            ),
        }
    if url_type == "actionable":
        return {
            "template_id": "3",
            "template_name": "Action-Oriented",
            "instructions": (
                "Use Template 3 - Action-Oriented with sections: "
                "'Source', 'What I learned', 'Actions to test', 'Decision'. "
                "Include actionable checkboxes when relevant."
            ),
        }
    if url_type == "recipe":
        return {
            "template_id": "4",
            "template_name": "Recipe",
            "instructions": (
                "Use Template 4 - Recipe with sections: "
                "'Source' (URL and site name), 'Ingredients' (bulleted list), "
                "'Preparation' (steps before cooking), 'Cooking' (cooking steps), "
                "'Nutrition' (calories and macros: protein, carbs, fat; optionally fiber — "
                "use the provided nutrition data when present, otherwise estimate from the ingredient list and label as 'estimated'), "
                "and optionally 'Notes'. "
                "Ingredients and steps must be taken from the provided structured data when present, "
                "otherwise extracted from the extracted page text."
            ),
        }
    return {
        "template_id": "2",
        "template_name": "Knowledge Enrichment",
        "instructions": (
            "Use Template 2 - Knowledge Enrichment with sections: "
            "'Source Metadata', 'Executive Summary', 'Main Ideas', "
            "'Notable Excerpts', 'My Context'."
        ),
    }


def _find_recipe_in_json(obj: Any) -> Optional[Dict[str, Any]]:
    """Return first Recipe object from JSON-LD structure (supports @graph and single object)."""
    if not isinstance(obj, dict):
        return None
    at_type = obj.get("@type")
    if isinstance(at_type, str) and at_type == "Recipe":
        return obj
    if isinstance(at_type, list) and "Recipe" in at_type:
        return obj
    graph = obj.get("@graph")
    if isinstance(graph, list):
        for item in graph:
            found = _find_recipe_in_json(item)
            if found:
                return found
    return None


def _normalize_recipe_instructions(instructions: Any) -> List[str]:
    """Turn schema.org recipeInstructions into a list of step strings."""
    if instructions is None:
        return []
    if isinstance(instructions, str):
        return [instructions] if instructions.strip() else []
    if not isinstance(instructions, list):
        return []
    steps: List[str] = []
    for step in instructions:
        if isinstance(step, str):
            if step.strip():
                steps.append(step.strip())
        elif isinstance(step, dict):
            text = step.get("text") or step.get("name")
            if isinstance(text, str) and text.strip():
                steps.append(text.strip())
    return steps


def _extract_nutrition(nutrition: Any) -> Optional[Dict[str, str]]:
    """Extract calories and macros from schema.org NutritionInformation. Pass through as-is (strings)."""
    if not isinstance(nutrition, dict):
        return None
    out: Dict[str, str] = {}
    for schema_key, our_key in (
        ("calorieContent", "calories"),
        ("proteinContent", "protein"),
        ("carbohydrateContent", "carbohydrates"),
        ("fatContent", "fat"),
        ("fiberContent", "fiber"),
    ):
        val = nutrition.get(schema_key)
        if isinstance(val, str) and val.strip():
            out[our_key] = val.strip()
    return out if out else None


def _parse_recipe_jsonld(html_text: str) -> Optional[Dict[str, Any]]:
    """
    Scan HTML for application/ld+json, find a Recipe object, return extracted fields.
    Returns dict with recipe_title, recipe_ingredients, recipe_instructions, recipe_nutrition
    or None if no Recipe found.
    """
    pattern = re.compile(
        r'<script[^>]+type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.IGNORECASE | re.DOTALL,
    )
    for block in pattern.finditer(html_text):
        raw = block.group(1).strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        recipe = _find_recipe_in_json(data)
        if not recipe:
            continue
        title = recipe.get("name")
        recipe_title = title.strip() if isinstance(title, str) and title.strip() else None
        ingredients_raw = recipe.get("recipeIngredient")
        recipe_ingredients: List[str] = []
        if isinstance(ingredients_raw, list):
            for ing in ingredients_raw:
                if isinstance(ing, str) and ing.strip():
                    recipe_ingredients.append(ing.strip())
        recipe_instructions = _normalize_recipe_instructions(recipe.get("recipeInstructions"))
        recipe_nutrition = _extract_nutrition(recipe.get("nutrition"))
        recipe_image_url: Optional[str] = None
        img = recipe.get("image")
        if isinstance(img, str) and img.strip().startswith("http"):
            recipe_image_url = img.strip()
        elif isinstance(img, list) and img:
            first = img[0]
            if isinstance(first, str) and first.strip().startswith("http"):
                recipe_image_url = first.strip()
            elif isinstance(first, dict) and first.get("url"):
                recipe_image_url = first["url"].strip()
        return {
            "recipe_title": recipe_title,
            "recipe_ingredients": recipe_ingredients,
            "recipe_instructions": recipe_instructions,
            "recipe_nutrition": recipe_nutrition,
            "recipe_image_url": recipe_image_url,
        }
    return None


def _is_challenge_page(html_text: str, title: str) -> bool:
    """
    Detect Cloudflare (and similar) security/challenge pages.
    Screenshot of these would show "Just a moment" or verification, not real content.
    """
    if not html_text:
        return False
    text_lower = html_text[:50_000].lower()
    title_lower = (title or "").lower()
    indicators = [
        "cloudflare",
        "just a moment",
        "checking your browser",
        "performing security verification",
        "security verification",
        "verifies you are not a bot",
        "cf-browser-verification",
        "challenge-running",
        "ddos protection by cloudflare",
        "attention required",
        "enable javascript and cookies",
    ]
    for phrase in indicators:
        if phrase in text_lower or phrase in title_lower:
            return True
    return False


async def fetch_url_context(url: str) -> Dict[str, Any]:
    """
    Fetch and parse URL metadata/content for LLM enrichment.

    Returns a dict safe to pass into LLM context.
    """
    result: Dict[str, Any] = {
        "url": url,
        "final_url": url,
        "domain": urlparse(url).netloc.lower(),
        "title": "",
        "description": "",
        "author": "",
        "published_at": "",
        "content_type": "knowledge",
        "template_id": "2",
        "template_name": "Knowledge Enrichment",
        "template_instructions": "",
        "extracted_text": "",
        "error": "",
        "skip_screenshot": False,
    }

    try:
        timeout = httpx.Timeout(12.0, connect=6.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            final_url = str(resp.url)
            html_text = resp.text[:300_000]

        title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
        title = html.unescape(title_match.group(1)).strip() if title_match else ""
        if not title:
            title = _extract_meta(html_text, ["og:title", "twitter:title"]) or ""

        # Skip screenshot when page is a Cloudflare (or similar) security challenge
        if _is_challenge_page(html_text, title):
            result["skip_screenshot"] = True

        description = _extract_meta(
            html_text,
            ["description", "og:description", "twitter:description"],
        ) or ""
        author = _extract_meta(html_text, ["author", "article:author", "og:article:author"]) or ""
        published = _extract_meta(
            html_text,
            ["article:published_time", "publish_date", "date", "dc.date"],
        ) or ""
        extracted_text = _extract_text(html_text)

        recipe_data = _parse_recipe_jsonld(html_text)
        if recipe_data is not None:
            content_type = "recipe"
        else:
            content_type = _classify_url_type(final_url, title, extracted_text)

        template = _template_for_url_type(content_type)

        result.update(
            {
                "final_url": final_url,
                "domain": urlparse(final_url).netloc.lower(),
                "title": title,
                "description": description,
                "author": author,
                "published_at": published,
                "content_type": content_type,
                "template_id": template["template_id"],
                "template_name": template["template_name"],
                "template_instructions": template["instructions"],
                "extracted_text": extracted_text,
            }
        )

        if content_type == "recipe":
            result["recipe_title"] = recipe_data["recipe_title"] if recipe_data else None
            result["recipe_ingredients"] = recipe_data["recipe_ingredients"] if recipe_data else []
            result["recipe_instructions"] = recipe_data["recipe_instructions"] if recipe_data else []
            result["recipe_nutrition"] = recipe_data["recipe_nutrition"] if recipe_data else None
            img_url = (recipe_data or {}).get("recipe_image_url") if recipe_data else None
            if img_url:
                result["image_url"] = img_url
        if not result.get("image_url"):
            og_image = _extract_meta(html_text, ["og:image", "twitter:image"])
            if og_image and og_image.strip().startswith("http"):
                result["image_url"] = og_image.strip()
    except Exception as exc:
        logger.warning("Failed to fetch URL context for %s: %s", url, exc)
        result["error"] = str(exc)

    return result
