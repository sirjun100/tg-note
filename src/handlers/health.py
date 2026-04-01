from __future__ import annotations

import logging
from typing import Any

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from src.security_utils import (
    check_whitelist,
    format_error_message,
    format_success_message,
    split_message_for_telegram,
)
from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)


def _split_quick_payload(payload: str) -> tuple[str | None, str]:
    """Optional leading `garmin|fatsecret|arboleaf` then body text."""
    p = payload.strip()
    if not p:
        return None, ""
    first, _, rest = p.partition(" ")
    low = first.strip().lower().rstrip(":")
    if low in ("garmin", "fatsecret", "arboleaf"):
        return low, rest.strip()
    return None, p


def _parse_source_arg(text: str | None) -> str | None:
    if not text:
        return None
    t = text.strip().lower()
    if not t:
        return None
    # allow "/health_import garmin"
    parts = t.split()
    if len(parts) >= 2 and parts[0].startswith("/health_import"):
        cand = parts[1].strip().lower()
        return cand if cand in ("garmin", "fatsecret", "arboleaf") else None
    return None


def _format_day_summary(day: dict[str, Any]) -> str:
    date = day["date"]
    lines: list[str] = [f"📈 健康 — {date}", ""]

    act = day.get("activity") or {}
    lines.append("🏃 活动 (Garmin)")
    if not any(act.get(k) is not None for k in ("steps", "distance_km", "active_calories_kcal", "avg_hr_bpm")):
        lines.append("-（未提供）")
    else:
        if act.get("steps") is not None:
            lines.append(f"- 步数：{act['steps']:,}")
        if act.get("distance_km") is not None:
            lines.append(f"- 距离：{act['distance_km']} km")
        if act.get("active_calories_kcal") is not None:
            lines.append(f"- 活动卡路里：{act['active_calories_kcal']:,} kcal")
        if act.get("avg_hr_bpm") is not None:
            lines.append(f"- 平均心率：{act['avg_hr_bpm']} bpm")
    lines.append("")

    nut = day.get("nutrition") or {}
    lines.append("🍽️ 营养 (FatSecret)")
    if not any(nut.get(k) is not None for k in ("calories_kcal", "protein_g", "carbs_g", "fat_g")):
        lines.append("-（未提供）")
    else:
        if nut.get("calories_kcal") is not None:
            lines.append(f"- 卡路里：{nut['calories_kcal']:,} kcal")
        macros = []
        if nut.get("protein_g") is not None:
            macros.append(f"{nut['protein_g']}g 蛋白质")
        if nut.get("carbs_g") is not None:
            macros.append(f"{nut['carbs_g']}g 碳水")
        if nut.get("fat_g") is not None:
            macros.append(f"{nut['fat_g']}g 脂肪")
        if macros:
            lines.append("- 宏量营养素：" + " / ".join(macros))
        top = nut.get("top_items") or []
        if top:
            lines.append("- 主要食物：")
            for name, kcal in top[:5]:
                lines.append(f"  - {name} ({kcal} kcal)")
    lines.append("")

    body = day.get("body") or {}
    lines.append("⚖️ 身体 (Arboleaf)")
    if not any(body.get(k) is not None for k in ("weight_kg", "body_fat_pct", "bmi")):
        lines.append("-（未提供）")
    else:
        if body.get("weight_kg") is not None:
            lines.append(f"- 体重：{body['weight_kg']} kg")
        if body.get("body_fat_pct") is not None:
            lines.append(f"- 体脂：{body['body_fat_pct']}%")
        if body.get("bmi") is not None:
            lines.append(f"- BMI：{body['bmi']}")

    return "\n".join(lines).strip()


def _format_week_summary(week: dict[str, Any]) -> str:
    roll = week.get("rollup") or {}
    lines = [f"📈 健康周 — {week['start_date']} → {week['end_date']}", ""]
    lines.append("🏃 活动")
    lines.append(f"- 锻炼：{roll.get('workouts', 0)}")
    if roll.get("steps") is not None:
        lines.append(f"- 步数：{roll['steps']:,}")
    if roll.get("distance_km") is not None:
        lines.append(f"- 距离：{roll['distance_km']} km")
    if roll.get("active_calories_kcal") is not None:
        lines.append(f"- 活动卡路里：{roll['active_calories_kcal']:,} kcal")
    lines.append("")

    lines.append("🍽️ 营养")
    if roll.get("avg_calories_kcal") is None:
        lines.append("-（未提供）")
    else:
        lines.append(f"- 平均卡路里：{roll['avg_calories_kcal']:,} kcal/天")
        macro_bits = []
        if roll.get("avg_protein_g") is not None:
            macro_bits.append(f"{roll['avg_protein_g']}g 蛋白质")
        if roll.get("avg_carbs_g") is not None:
            macro_bits.append(f"{roll['avg_carbs_g']}g 碳水")
        if roll.get("avg_fat_g") is not None:
            macro_bits.append(f"{roll['avg_fat_g']}g 脂肪")
        if macro_bits:
            lines.append("- 平均宏量营养素：" + " / ".join(macro_bits))
    lines.append("")

    lines.append("⚖️ 身体")
    if roll.get("weight_trend_kg") is None:
        lines.append("-（未提供）")
    else:
        delta = roll["weight_trend_kg"]
        sign = "+" if isinstance(delta, (int, float)) and delta > 0 else ""
        lines.append(f"- 体重趋势：{sign}{delta} kg")
    return "\n".join(lines).strip()


def register_health_handlers(application: Any, orch: TelegramOrchestrator) -> None:
    async def health_import_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ 抱歉，您没有使用此机器人的权限。")
            return

        await msg.reply_text(
            "发送带有标题 `/health_import` 的 CSV 文件（可选 `garmin|fatsecret|arboleaf`），"
            "或使用 `/health_import_quick <文本>` 进行粘贴。",
            parse_mode=None,
        )

    async def health_import_quick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ 抱歉，您没有使用此机器人的权限。")
            return

        text = msg.text or ""
        parts = text.split(None, 1)
        payload = parts[1] if len(parts) > 1 else ""
        hint, body = _split_quick_payload(payload)
        if not body.strip():
            await msg.reply_text(format_error_message("在命令后粘贴文本。"))  # type: ignore[arg-type]
            return

        today = orch.health_service.today_str(user.id, orch.logging_service)
        result = orch.health_service.import_pasted_text(
            user_id=user.id,
            text=body,
            default_date=today,
            source_hint=hint,
            message_id=msg.message_id,
        )
        if result.parsed_rows == 0:
            await msg.reply_text(
                format_error_message(
                    "无法解析该文本。尝试：`garmin` — 步数、距离 km、卡路里；"
                    "`fatsecret` — 卡路里/宏量营养素；`arboleaf` — 体重 kg、体脂。"
                    "或发送带有标题 /health_import 的 CSV 文件。",
                )
            )
            return
        lines = [
            format_success_message("导入已保存。"),
            f"检测到：{result.detected_source or '未知'}",
            f"已解析：{result.parsed_rows} 行，覆盖 {result.date_count} 天",
            f"已插入：{result.inserted_rows}（重复已跳过：{result.deduped_skipped}）",
            "",
            "预览：",
            *(result.preview_lines or ["（无行）"]),
        ]
        await msg.reply_text("\n".join(lines))

    async def _handle_import_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            return
        doc = msg.document
        if not doc:
            return

        caption = (msg.caption or "").strip()
        if not caption.lower().startswith("/health_import"):
            return

        source_hint = _parse_source_arg(caption)

        status = await msg.reply_text("正在解析导入…")
        try:
            tg_file = await doc.get_file()
            data = await tg_file.download_as_bytearray()
            user_tz = orch.health_service.user_timezone(user.id, orch.logging_service)
            result = orch.health_service.import_csv_bytes(
                user_id=user.id,
                csv_bytes=bytes(data),
                filename=doc.file_name,
                user_timezone=user_tz,
                source_hint=source_hint,
                message_id=msg.message_id,
            )
            lines = [
                format_success_message("导入已保存。"),
                f"检测到：{result.detected_source or '未知'}",
                f"已解析：{result.parsed_rows} 行，覆盖 {result.date_count} 天",
                f"已插入：{result.inserted_rows}（重复已跳过：{result.deduped_skipped}）",
                "",
                "预览：",
                *(result.preview_lines or ["（无行）"]),
            ]
            await status.edit_text("\n".join(lines))
        except Exception as exc:
            logger.exception("Health import failed: %s", exc)
            await status.edit_text(format_error_message("导入失败。尝试不同的导出或来源提示。"))

    async def health_today_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ 抱歉，您没有使用此机器人的权限。")
            return
        date = orch.health_service.today_str(user.id, orch.logging_service)
        day = orch.health_service.summarize_day(user_id=user.id, date=date)
        text = _format_day_summary(day)
        for chunk in split_message_for_telegram(text):
            await msg.reply_text(chunk)

    async def health_week_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ 抱歉，您没有使用此机器人的权限。")
            return
        end = orch.health_service.today_str(user.id, orch.logging_service)
        week = orch.health_service.summarize_last_7_days(user_id=user.id, end_date=end)
        text = _format_week_summary(week)
        for chunk in split_message_for_telegram(text):
            await msg.reply_text(chunk)

    async def health_last_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ 抱歉，您没有使用此机器人的权限。")
            return
        last = orch.health_store.get_last_rows_by_source(user.id)
        if not last:
            await msg.reply_text("尚未保存健康数据。")
            return
        lines = ["每个来源的最后捕获："]
        for src, info in last.items():
            lines.append(f"- {src}：{info.get('date')}（{info.get('row_type')}）")
        await msg.reply_text("\n".join(lines))

    application.add_handler(CommandHandler("health_import", health_import_cmd))
    application.add_handler(CommandHandler("health_import_quick", health_import_quick_cmd))
    application.add_handler(CommandHandler("health_today", health_today_cmd))
    application.add_handler(CommandHandler("health_week", health_week_cmd))
    application.add_handler(CommandHandler("health_last", health_last_cmd))

    # CSV uploads for /health_import via caption
    application.add_handler(MessageHandler(filters.Document.ALL, _handle_import_document))

    logger.info("Health handlers registered")

