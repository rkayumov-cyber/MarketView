"""SectionEnhancer — replaces rule-based text with LLM-generated prose."""

from __future__ import annotations

import logging

from src.llm.client import LLMClient
from src.llm.prompts import (
    SYSTEM_PROMPT,
    pulse_narrative_prompt,
    pulse_takeaways_prompt,
    macro_outlook_prompt,
    macro_themes_prompt,
    sentiment_narrative_prompt,
    forward_lesson_prompt,
)
from src.reports.models import (
    ForwardSection,
    MacroSection,
    PulseSection,
    SentimentSection,
)

logger = logging.getLogger(__name__)


class SectionEnhancer:
    """Enhances rule-based report sections with LLM-generated text.

    Every enhancement is wrapped in try/except — on failure the original
    rule-based content is preserved unchanged.
    """

    def __init__(self, client: LLMClient) -> None:
        self._client = client

    # ── Pulse ────────────────────────────────────────────────

    async def enhance_pulse(
        self,
        pulse: PulseSection,
        research_context: list | None = None,
    ) -> PulseSection:
        updates: dict = {}

        # Enhance big_narrative
        try:
            divergence_descs = [d.description for d in pulse.divergences]
            sentiment_score = (
                pulse.sentiment.overall_score if pulse.sentiment else None
            )
            prompt = pulse_narrative_prompt(
                regime=pulse.regime.regime,
                confidence=pulse.regime.confidence,
                signals=pulse.regime.signals,
                sentiment_score=sentiment_score,
                divergences=divergence_descs or None,
                research_context=research_context,
            )
            narrative = await self._client.generate(prompt, SYSTEM_PROMPT)
            if narrative.strip():
                updates["big_narrative"] = narrative.strip()
        except Exception as e:
            logger.warning("LLM pulse narrative failed, keeping rule-based: %s", e)

        # Enhance key_takeaways
        try:
            prompt = pulse_takeaways_prompt(
                regime=pulse.regime.regime,
                big_narrative=updates.get("big_narrative", pulse.big_narrative),
                existing_takeaways=pulse.key_takeaways,
            )
            raw = await self._client.generate(prompt, SYSTEM_PROMPT)
            lines = [
                line.lstrip("- ").strip()
                for line in raw.strip().splitlines()
                if line.strip().startswith("-")
            ]
            if lines:
                updates["key_takeaways"] = lines
        except Exception as e:
            logger.warning("LLM pulse takeaways failed, keeping rule-based: %s", e)

        return pulse.model_copy(update=updates) if updates else pulse

    # ── Macro ────────────────────────────────────────────────

    async def enhance_macro(
        self,
        macro: MacroSection,
        research_context: list | None = None,
    ) -> MacroSection:
        updates: dict = {}

        # Enhance global_outlook
        try:
            prompt = macro_outlook_prompt(
                us_headline=macro.us.headline if macro.us else None,
                eu_headline=macro.eu.headline if macro.eu else None,
                asia_headline=macro.asia.headline if macro.asia else None,
                existing_outlook=macro.global_outlook,
                research_context=research_context,
            )
            outlook = await self._client.generate(prompt, SYSTEM_PROMPT)
            if outlook.strip():
                updates["global_outlook"] = outlook.strip()
        except Exception as e:
            logger.warning("LLM macro outlook failed, keeping rule-based: %s", e)

        # Enhance themes
        try:
            prompt = macro_themes_prompt(
                existing_themes=macro.themes,
                outlook=updates.get("global_outlook", macro.global_outlook),
            )
            raw = await self._client.generate(prompt, SYSTEM_PROMPT)
            lines = [
                line.lstrip("- ").strip()
                for line in raw.strip().splitlines()
                if line.strip().startswith("-")
            ]
            if lines:
                updates["themes"] = lines
        except Exception as e:
            logger.warning("LLM macro themes failed, keeping rule-based: %s", e)

        return macro.model_copy(update=updates) if updates else macro

    # ── Sentiment ─────────────────────────────────────────────

    async def enhance_sentiment(
        self,
        sent: SentimentSection,
        research_context: list | None = None,
    ) -> SentimentSection:
        updates: dict = {}

        try:
            sub_summaries = [
                f"r/{b.subreddit}: score {b.sentiment_score:+.2f}, "
                f"{b.bullish_ratio:.0%} bullish, {b.post_count} posts"
                for b in sent.subreddit_breakdowns
            ]
            prompt = sentiment_narrative_prompt(
                overall_score=sent.overall_score,
                bullish_ratio=sent.bullish_ratio,
                total_posts=sent.total_posts,
                trending_tickers=sent.trending_tickers,
                subreddit_summaries=sub_summaries,
                contrarian_signals=sent.contrarian_signals,
                research_context=research_context,
            )
            narrative = await self._client.generate(prompt, SYSTEM_PROMPT)
            if narrative.strip():
                updates["narrative"] = narrative.strip()
        except Exception as e:
            logger.warning("LLM sentiment narrative failed, keeping rule-based: %s", e)

        return sent.model_copy(update=updates) if updates else sent

    # ── Forward ──────────────────────────────────────────────

    async def enhance_forward(
        self,
        forward: ForwardSection,
        research_context: list | None = None,
    ) -> ForwardSection:
        updates: dict = {}

        try:
            event_summaries = [
                f"{e.date}: {e.event} ({e.importance})"
                for e in forward.upcoming_events[:5]
            ]
            prompt = forward_lesson_prompt(
                events=event_summaries,
                outlier_event=forward.outlier_event.event,
                existing_lesson=forward.lesson_of_the_day,
                research_context=research_context,
            )
            lesson = await self._client.generate(prompt, SYSTEM_PROMPT)
            if lesson.strip():
                updates["lesson_of_the_day"] = lesson.strip()
        except Exception as e:
            logger.warning("LLM forward lesson failed, keeping rule-based: %s", e)

        return forward.model_copy(update=updates) if updates else forward
