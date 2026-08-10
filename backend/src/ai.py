"""
AI-related functions for transcript analysis with enhanced precision and virality scoring.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
import asyncio
import logging
import os
import re

from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic import AliasChoices, BaseModel, Field, field_validator

from .config import Config, get_config
from .runtime_settings import apply_settings_to_process_env

logger = logging.getLogger(__name__)

IDEAL_CLIP_MIN_SECONDS = int(os.getenv("IDEAL_CLIP_MIN_SECONDS", "20"))
IDEAL_CLIP_MAX_SECONDS = int(os.getenv("IDEAL_CLIP_MAX_SECONDS", "90"))
MIN_ACCEPTED_CLIP_SECONDS = int(os.getenv("MIN_ACCEPTED_CLIP_SECONDS", "6"))
MAX_ACCEPTED_CLIP_SECONDS = int(os.getenv("MAX_ACCEPTED_CLIP_SECONDS", "180"))
TRANSCRIPT_ANALYSIS_CACHE_VERSION = "duration-categories-v2"
HOOK_TITLE_MAX_CHARS = 64
HOOK_TITLE_MAX_WORDS = 10
TRANSCRIPT_SPAN_RE = re.compile(
    r"^\[(?P<start>\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*"
    r"(?P<end>\d{1,2}:\d{2}(?::\d{2})?)\]\s*(?P<text>.*)$"
)

# Duration categories for multi-format viral content generation
DURATION_CATEGORIES = {
    "micro": (6, 15),
    "short": (15, 30),
    "medium": (30, 60),
    "standard": (60, 120),
    "extended": (120, 180),
}


def compute_duration_category(duration_seconds: float) -> str:
    """Return the duration category id for a given clip length."""
    if duration_seconds < 15:
        return "micro"
    if duration_seconds < 30:
        return "short"
    if duration_seconds < 60:
        return "medium"
    if duration_seconds < 120:
        return "standard"
    return "extended"


class ViralityAnalysis(BaseModel):
    """Detailed virality breakdown for a segment."""

    hook_score: int = Field(
        default=15,
        description="How strong is the opening hook (0-25)",
        ge=0,
        le=25,
    )
    engagement_score: int = Field(
        default=15,
        description="How engaging/entertaining is the content (0-25)",
        ge=0,
        le=25,
    )
    value_score: int = Field(
        default=15,
        description="Educational/informational value (0-25)",
        ge=0,
        le=25,
    )
    shareability_score: int = Field(
        default=15,
        description="Likelihood of being shared (0-25)",
        ge=0,
        le=25,
    )
    total_score: int = Field(
        default=60,
        description="Combined virality score (0-100)",
        ge=0,
        le=100,
    )
    hook_type: Optional[
        Literal["question", "statement", "statistic", "story", "contrast", "none"]
    ] = Field(
        default="none",
        description="Type of hook: question, statement, statistic, story, contrast, or none",
    )
    virality_reasoning: str = Field(
        default="The model did not provide a detailed virality breakdown.",
        description="Explanation of the virality score",
    )


def _default_virality_analysis() -> ViralityAnalysis:
    return ViralityAnalysis()


class TranscriptSegment(BaseModel):
    """Represents a relevant segment of transcript with precise timing and virality analysis."""

    start_time: str = Field(description="Start timestamp in MM:SS format")
    end_time: str = Field(description="End timestamp in MM:SS format")
    text: str = Field(
        validation_alias=AliasChoices("text", "segment"),
        description=(
            "Transcript text taken only from the selected timestamp range. "
            "Keep it verbatim or near-verbatim, and do not paraphrase or merge non-contiguous lines."
        )
    )
    relevance_score: float = Field(
        default=0.75,
        description="Relevance score from 0.0 to 1.0", ge=0.0, le=1.0
    )
    reasoning: str = Field(
        default="Selected by the AI model as a clip candidate.",
        description=(
            "Brief factual explanation of why this exact segment works as a clip. "
            "Base it only on the provided transcript content."
        )
    )
    virality: ViralityAnalysis = Field(
        default_factory=_default_virality_analysis,
        description="Detailed virality score breakdown",
    )
    hook_title: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("hook_title", "title", "headline"),
        description=(
            "Short punchy on-screen title for the clip (3-9 words). Grounded in "
            "the segment content, no hashtags, no emojis, no surrounding quotes."
        ),
    )
    duration_category: Optional[str] = Field(
        default=None,
        description=(
            "Target duration bucket: micro (6-15s), short (15-30s), "
            "medium (30-60s), standard (60-120s), extended (120-180s)"
        ),
    )

    @field_validator("relevance_score", mode="before")
    @classmethod
    def _coerce_percent_relevance_score(cls, value: Any) -> Any:
        if value is None:
            return value
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return value
        if numeric_value > 1 and numeric_value <= 100:
            return numeric_value / 100
        return value


class BRollOpportunity(BaseModel):
    """Identifies an opportunity to insert B-roll footage."""

    timestamp: str = Field(
        default="00:00",
        validation_alias=AliasChoices("timestamp", "segment_start_time", "start_time"),
        description="When to insert B-roll (MM:SS format)",
    )
    duration: float = Field(
        default=3.0,
        description="How long to show B-roll (2-5 seconds)",
        ge=2.0,
        le=5.0,
    )
    search_term: str = Field(
        default="related visual",
        validation_alias=AliasChoices("search_term", "broll", "visual", "query"),
        description="Keyword to search for B-roll footage",
    )
    context: str = Field(
        default="Suggested B-roll opportunity from the model.",
        validation_alias=AliasChoices("context", "description"),
        description="What's being discussed at this point",
    )

    @field_validator("search_term", "context", mode="before")
    @classmethod
    def _coerce_textish_value(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            return ", ".join(str(item) for item in value if item is not None)
        return str(value)


class TranscriptAnalysis(BaseModel):
    """Analysis result for transcript segments with virality and B-roll opportunities."""

    most_relevant_segments: List[TranscriptSegment]
    summary: str = Field(description="Brief summary of the video content")
    key_topics: List[str] = Field(description="List of main topics discussed")
    broll_opportunities: Optional[List[BRollOpportunity]] = Field(
        default=None, description="Opportunities to insert B-roll footage"
    )


# Enhanced system prompt with virality scoring and B-roll detection
transcript_analysis_system_prompt = """You are an expert transcript analyst for short-form video editing.

Your job is extraction and ranking, not creative rewriting. You must stay fully grounded in the transcript and choose the best clip candidates that already exist in the source material.

OUTPUT CONTRACT:
- Return valid JSON only. Do not output Markdown, headings, bullets, prose, code fences, explanations, or commentary outside the JSON object.
- The top-level JSON object must include: "most_relevant_segments", "summary", and "key_topics".
- Only include "broll_opportunities" when B-roll was requested.
- Each item in "most_relevant_segments" must include: "start_time", "end_time", "text", "relevance_score", "reasoning", "virality", "hook_title", and "duration_category".
- Do not use "segment" as an output field. Use "text".
- "virality" must include: "hook_score", "engagement_score", "value_score", "shareability_score", "total_score", "hook_type", and "virality_reasoning".
- "duration_category" must be one of: "micro", "short", "medium", "standard", "extended".
- Every returned segment must be 6-180 seconds long.

CORE OBJECTIVES:
1. Identify segments that would be compelling on social media platforms
2. Focus on complete thoughts, insights, or entertaining moments
3. Prioritize content with hooks, emotional moments, or valuable information
4. Each segment should be engaging and worth watching
5. Score each segment's viral potential with detailed breakdown

GROUNDING RULES:
1. Use only the provided transcript lines and timestamps
2. Never invent facts, tone, context, or transitions that are not present
3. Treat this as span selection over a timestamped transcript, not open-ended summarization
4. Each selected segment must map to one contiguous range in the transcript
5. segment.text must match the chosen span closely and must not include content from outside the chosen range
6. Do not stitch together distant moments into one clip
7. If a speaker label appears, use it only if it is part of the spoken content and helps clarity

CONTENT NEUTRALITY RULES:
1. This is clipping software for legitimate editing workflows
2. Do not judge, moralize, or downgrade a segment just because the topic is controversial, sensitive, adult, political, criminal, medical, or otherwise intense
3. Evaluate segments only on clip quality: clarity, self-contained value, hook strength, emotional impact, specificity, and shareability
4. Do not refuse analysis just because the speaker describes risky, offensive, or uncomfortable subject matter
5. Only downgrade a segment when the transcript itself is weak, confusing, repetitive, unusable, or a poor standalone clip

SEGMENT SELECTION CRITERIA:
1. STRONG HOOKS: Attention-grabbing opening lines
2. VALUABLE CONTENT: Tips, insights, interesting facts, stories
3. EMOTIONAL MOMENTS: Excitement, surprise, humor, inspiration
4. COMPLETE THOUGHTS: Self-contained ideas that make sense alone
5. ENTERTAINING: Content people would want to share
6. HIGH SIGNAL: Prefer specific, concrete language over vague discussion
7. LOW FILLER: Avoid greetings, sponsor reads, repeated setup, throat-clearing, and housekeeping unless they are unusually compelling

WHAT A GOOD CLIP FEELS LIKE:
- A viewer should understand and care without the original title, thumbnail, or previous context
- Prefer a complete mini-story or argument: setup, tension or claim, specific detail, and payoff
- Expand a great short moment to nearby contiguous lines when that adds needed setup, stakes, or payoff
- Strong picks include contrarian claims, mistakes or lessons, concrete examples, before/after moments, frameworks, surprising results, emotionally charged reactions, and complete answers to interesting questions
- Bad picks include intros, sponsor or CTA sections, vague setup, contextless quote fragments, repeated points, definitions without payoff, meandering background, and answer fragments that require unseen context

VIRALITY SCORING (0-100 total, from four 0-25 subscores):
For each segment, provide a detailed virality breakdown:

1. HOOK STRENGTH (0-25):
   - 20-25: Immediately grabs attention (surprising fact, bold claim, intriguing question)
   - 15-19: Good opener that creates curiosity
   - 10-14: Decent start but could be stronger
   - 0-9: Weak or no hook

2. ENGAGEMENT (0-25):
   - 20-25: Highly entertaining, emotional, or dramatic
   - 15-19: Interesting and holds attention
   - 10-14: Moderately engaging
   - 0-9: Flat or boring delivery

3. VALUE (0-25):
   - 20-25: Actionable insights, unique knowledge, or transformative ideas
   - 15-19: Useful information most people don't know
   - 10-14: Somewhat informative
   - 0-9: Common knowledge or filler content

4. SHAREABILITY (0-25):
   - 20-25: "I need to send this to someone" content
   - 15-19: Content worth bookmarking
   - 10-14: Nice but not share-worthy
   - 0-9: Generic content

HOOK TITLES ("hook_title" per segment):
- Write a short on-screen headline (3-9 words) that is burned into the top of the clip
- It must make a scrolling viewer stop: a bold claim, curiosity gap, number, or stakes taken directly from the segment
- Stay grounded: only promise what the clip actually delivers; never invent facts or numbers
- Do not simply repeat the first spoken words verbatim; reframe them as a headline
- Plain text only: no hashtags, no emojis, no quotes around the title
- Good examples: "The $40k mistake I keep seeing", "Why nobody tells you this about VC", "Do this before your next interview"

HOOK TYPES to identify:
- "question": Opens with a question that creates curiosity
- "statement": Bold claim or surprising statement
- "statistic": Uses compelling numbers or data
- "story": Starts with narrative/anecdote
- "contrast": Before/after or problem/solution framing
- "none": No clear hook pattern

B-ROLL OPPORTUNITIES:
Identify 2-4 moments in each segment where B-roll footage could enhance the video:
- When specific objects, places, or concepts are mentioned
- During explanations that could benefit from visual illustration
- At emotional peaks that could use supporting imagery
- Use simple, searchable keywords (e.g., "coffee shop", "laptop coding", "money stack")

DURATION CATEGORY DISTRIBUTION:
Spread your selections across these duration categories. For each segment, set "duration_category" to the matching bucket.
- "micro" (6-15s): Quick-hit moments — one powerful line, a reaction, or a punchy fact. Best for Stories and ads.
- "short" (15-30s): Compact standalone clips — one idea, one hook, one payoff. Best for YouTube Shorts, Reels.
- "medium" (30-60s): Standard short-form — complete mini-story with setup and payoff. Best for TikTok, YouTube Shorts.
- "standard" (60-120s): Deeper dives — full explanation, multi-point argument, or compelling narrative. Best for Twitter/X, LinkedIn.
- "extended" (120-180s): Long-form excerpts — detailed breakdown, interview segment, or tutorial. Best for YouTube, podcast clips.

Try to select at least one clip from each applicable category when the content supports it. Not every category will be available in every video — skip a category only if the content genuinely doesn't support a quality clip at that length. Prioritize quality over quota, but actively look for opportunities in every category.

TIMING GUIDELINES:
- Micro clips (6-15s): Grab ONE punchy moment — a killer one-liner, a surprising fact, or a reaction
- Short clips (15-30s): One clear idea with a hook and payoff
- Medium clips (30-60s): Complete mini-story: setup, tension, payoff
- Standard clips (60-120s): Full explanation or argument with supporting detail
- Extended clips (120-180s): Deep dive, multi-point discussion, or narrative arc
- Focus on natural content boundaries rather than arbitrary time limits
- Start at the hook or the minimum setup needed to make the hook land, and end after the payoff
- If a highlight is only one good line, it can be a micro/short clip — don't force-expand it
- Stop expanding when the topic drifts, the speaker repeats the same point, or the clip loses momentum

TIMESTAMP REQUIREMENTS - EXTREMELY IMPORTANT:
- Use EXACT timestamps as they appear in the transcript
- Never modify timestamp format (keep MM:SS structure)
- start_time MUST be LESS THAN end_time (start_time < end_time)
- MINIMUM segment duration: 6 seconds (end_time - start_time >= 6 seconds)
- Look at transcript ranges like [02:25 - 02:35] and use different start/end times
- NEVER use the same timestamp for both start_time and end_time
- Example: start_time: "02:25", end_time: "02:35" (NOT "02:25" and "02:25")

SCORING AND OUTPUT RULES:
- relevance_score should reflect how well the segment works as a standalone short clip, not just whether the topic is generally important
- Penalize clips that are only quotable but not self-contained, too generic, missing setup, missing payoff, or padded with filler
- virality_reasoning and reasoning should cite what is actually present in the chosen span
- summary and key_topics must also stay grounded in the transcript and should not add outside interpretation

Find as many compelling segments as possible (from 5 up to 30 or more for longer videos) that would work well as standalone clips, spread across different duration categories. Quality over quantity: choose fewer stronger segments over filling a quota, but don't artificially restrict the number of excellent clips. Every selected segment must be accurate, self-contained, have proper time ranges, and score high on virality metrics.

CLIP QUANTITY RULES — CRITICAL:
- Do NOT set a cap on how many clips you return. If a 1-hour video has 25 great moments, return all 25.
- For videos under 10 minutes: aim for at least 5 clips.
- For videos 10-30 minutes: aim for 8-15 clips.
- For videos 30-60 minutes: aim for 12-25 clips.
- For videos over 60 minutes: aim for 20+ clips.
- Scan the entire transcript from start to finish. Do not stop scanning after finding a few clips.
- Every format bucket (micro, short, medium, standard, extended) should have at least 1 clip if the content supports it.
- Pay special attention to Micro clips (6-15s): If there is a highly punchy killer one-liner, quick reaction, or stand-alone surprising statement inside a longer segment, extract it as an independent Micro clip in addition to the longer segment.
- The goal is to saturate the output with every clip-worthy moment, not to pick only the absolute best few."""



# Lazy-loaded agent to avoid import-time failures when API keys aren't set
_transcript_agent: Optional[Agent[None, TranscriptAnalysis]] = None
_transcript_agent_signature: Optional[tuple[str | None, ...]] = None

SUPPORTED_LLM_PROVIDERS = {"google", "google-gla", "openai", "anthropic", "ollama"}


def _split_llm_name(model_name: str) -> tuple[str, str | None]:
    if ":" not in model_name:
        return model_name.strip().lower(), None

    provider, provider_model_name = model_name.split(":", 1)
    return provider.strip().lower(), provider_model_name.strip() or None


def _get_missing_llm_key_error(model_name: str, runtime_config: Config) -> Optional[str]:
    """Return a clear configuration error when the selected LLM key is missing."""
    provider, provider_model_name = _split_llm_name(model_name)

    if provider not in SUPPORTED_LLM_PROVIDERS:
        return (
            f"Unsupported LLM provider '{provider}'. "
            "Use google-gla:*, openai:*, anthropic:*, or ollama:*."
        )

    if not provider_model_name:
        return (
            "Selected LLM is missing a model name. "
            "Use the format provider:model, for example ollama:gpt-oss:20b."
        )

    if provider in {"google", "google-gla"} and not runtime_config.google_api_key:
        return (
            "Selected LLM provider is Google, but GOOGLE_API_KEY is not set. "
            "Set GOOGLE_API_KEY or set LLM to openai:* / anthropic:* / ollama:* with the matching API key."
        )

    if provider == "openai" and not runtime_config.openai_api_key:
        return (
            "Selected LLM provider is OpenAI, but OPENAI_API_KEY is not set. "
            "Set OPENAI_API_KEY or choose another provider with a matching API key."
        )

    if provider == "anthropic" and not runtime_config.anthropic_api_key:
        return (
            "Selected LLM provider is Anthropic, but ANTHROPIC_API_KEY is not set. "
            "Set ANTHROPIC_API_KEY or choose another provider with a matching API key."
        )

    if provider == "ollama":
        # Ollama can run locally without an API key. OLLAMA_BASE_URL/OLLAMA_API_KEY
        # are optional and passed through as environment variables.
        return None

    return None


def _build_transcript_model(runtime_config: Config) -> Model | str:
    provider, provider_model_name = _split_llm_name(runtime_config.llm)
    if provider != "ollama":
        return runtime_config.llm

    if not provider_model_name:
        raise RuntimeError(
            "Selected LLM provider is Ollama, but no model name was provided. "
            "Use the format ollama:<model>, for example ollama:gpt-oss:20b."
        )

    return OllamaModel(
        provider_model_name,
        provider=OllamaProvider(
            base_url=runtime_config.resolve_ollama_base_url(),
            api_key=runtime_config.ollama_api_key,
        ),
    )


def get_transcript_agent() -> Agent[None, TranscriptAnalysis]:
    """Get or create the transcript analysis agent (lazy initialization)."""
    global _transcript_agent, _transcript_agent_signature
    runtime_config = get_config()
    provider, _ = _split_llm_name(runtime_config.llm)
    signature = (
        runtime_config.llm,
        runtime_config.openai_api_key,
        runtime_config.google_api_key,
        runtime_config.anthropic_api_key,
        runtime_config.ollama_base_url,
        runtime_config.ollama_api_key,
    )
    if _transcript_agent is None or _transcript_agent_signature != signature:
        apply_settings_to_process_env(runtime_config.as_runtime_settings())
        config_error = _get_missing_llm_key_error(runtime_config.llm, runtime_config)
        if config_error:
            raise RuntimeError(config_error)

        _transcript_agent = Agent[None, TranscriptAnalysis](
            model=_build_transcript_model(runtime_config),
            output_type=TranscriptAnalysis,
            system_prompt=transcript_analysis_system_prompt,
            # Some local Ollama/OpenAI-compatible endpoints can return formatted
            # prose before settling on schema-valid JSON. Keep retries limited
            # while still allowing enough repair attempts for local models.
            output_retries=2 if provider == "ollama" else 2,
        )
        _transcript_agent_signature = signature
    return _transcript_agent


def build_transcript_analysis_prompt(
    transcript: str, include_broll: bool = False, clip_signals: str | None = None
) -> str:
    """Build the grounded task prompt for transcript analysis."""
    broll_instruction = ""
    if include_broll:
        broll_instruction = (
            "\n5. Also identify B-roll opportunities for each chosen segment where stock footage could enhance the visual appeal."
        )
    signal_section = ""
    if clip_signals:
        signal_section = (
            "\n\nAdditional deterministic signals from transcript/audio analysis:\n"
            f"{clip_signals}\n\n"
            "Use these as hints only. They should influence ranking, but every final segment "
            "must still be a coherent contiguous transcript range."
        )

    return f"""Analyze this video transcript and identify the most engaging segments for short-form content.

The transcript is formatted as one line per timestamped span, for example:
[00:12 - 00:21] Spoken text here
[00:21 - 00:35] More spoken text here

Follow this workflow:
1. Read the transcript as a sequence of timestamped spans.
2. Select only contiguous ranges that already exist in the transcript.
3. Prefer moments with a strong hook, clear payoff, emotional charge, or concrete value.
4. For each chosen segment, use the earliest timestamp in the selected range as start_time and the latest timestamp in the selected range as end_time.{broll_instruction}

- Choose as many segments as possible (from 5 up to 30 or more for longer videos) that would work well as standalone clips, spread across different duration categories (micro, short, medium, standard, extended).
- IMPORTANT: Do NOT cap or limit the number of clips you return. More clips = better. If the video is long, return 20-30+ clips.
- Do not artificially limit or cap the number of excellent clips you identify.
- Scan the ENTIRE transcript from beginning to end before finalizing your output.
- Try to include at least 1 clip from each duration category when the content supports it.
- Micro (6-15s): punchy moments, killer one-liners, quick reactions. If a longer segment contains a killer one-liner, extract that one-liner separately as a Micro clip too!
- Short (15-30s): one idea with hook and payoff
- Medium (30-60s): complete mini-story
- Standard (60-120s): full explanation or narrative
- Extended (120-180s): deep dive, multi-point discussion, or narrative arcs
- Skip weak standalone picks: intros, sponsor reads, CTAs, contextless quotes, repeated points, vague setup, and answer fragments that require prior context.
- Before returning a segment, ask whether a viewer would understand and care without seeing the rest of the source video.

Critical accuracy requirements:
- Do not fabricate or embellish content.
- Do not use timestamps that are not present in the transcript.
- Do not merge separate non-contiguous moments into one segment.
- segment.text must reflect only the spoken content inside the selected time range.
- If a span lacks enough context to stand alone, expand to nearby contiguous lines rather than guessing.
- If there is a tradeoff between "viral" and "accurate", choose accuracy.
- Do not reject or penalize a segment simply because of the subject matter; stay content-neutral and assess clip quality only.
{signal_section}

JSON-only output requirements:
- Return one valid JSON object and nothing else.
- No Markdown, headings, bullets, code fences, or explanatory text outside JSON.
- Top-level keys: "most_relevant_segments", "summary", "key_topics"{', "broll_opportunities"' if include_broll else ''}.
- Segment keys: "start_time", "end_time", "text", "relevance_score", "reasoning", "virality", "hook_title", "duration_category".
- "hook_title" is a 3-9 word plain-text headline for the clip, grounded in the segment (no hashtags, emojis, or quotes).
- "duration_category" is one of: "micro", "short", "medium", "standard", "extended".
- Virality keys: "hook_score", "engagement_score", "value_score", "shareability_score", "total_score", "hook_type", "virality_reasoning".
- Do not return segments shorter than {MIN_ACCEPTED_CLIP_SECONDS} seconds or longer than {MAX_ACCEPTED_CLIP_SECONDS} seconds.

Transcript:
{transcript}"""


def sanitize_hook_title(raw: Optional[str]) -> Optional[str]:
    """Normalize an AI-provided hook title for on-screen rendering.

    Strips wrapping quotes/markdown, collapses whitespace, drops hashtags, and
    trims to a word-boundary length cap. Returns None when nothing usable is
    left so callers can simply skip the overlay.
    """
    if not raw:
        return None
    title = str(raw).strip()
    title = title.strip("\"'`“”‘’").strip()
    title = re.sub(r"#\w+", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    # Drop trailing sentence punctuation but keep ?/! (they carry the hook).
    title = title.rstrip(".,;:-–— ").strip()
    if not title:
        return None

    words = title.split()
    if len(words) > HOOK_TITLE_MAX_WORDS:
        words = words[:HOOK_TITLE_MAX_WORDS]
        title = " ".join(words)
    if len(title) > HOOK_TITLE_MAX_CHARS:
        clipped = title[: HOOK_TITLE_MAX_CHARS + 1]
        cut = clipped.rfind(" ")
        title = (clipped[:cut] if cut > 20 else title[:HOOK_TITLE_MAX_CHARS]).rstrip(
            ".,;:-–— "
        )
    return title or None


def _parse_transcript_timestamp_seconds(timestamp: str) -> int:
    """Parse MM:SS or HH:MM:SS transcript timestamps into seconds."""
    parts = [int(part) for part in timestamp.split(":")]
    if len(parts) == 2:
        minutes, seconds = parts
        return minutes * 60 + seconds
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds
    raise ValueError(f"Unsupported timestamp format: {timestamp}")


def _format_transcript_timestamp(seconds: int) -> str:
    """Format seconds as a transcript timestamp."""
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _parse_transcript_spans(transcript: str) -> list[dict[str, Any]]:
    """Parse timestamped transcript lines into spans."""
    spans = []
    for line in transcript.splitlines():
        match = TRANSCRIPT_SPAN_RE.match(line.strip())
        if not match:
            continue
        try:
            start_seconds = _parse_transcript_timestamp_seconds(match.group("start"))
            end_seconds = _parse_transcript_timestamp_seconds(match.group("end"))
        except ValueError:
            continue
        if end_seconds <= start_seconds:
            continue
        spans.append(
            {
                "start": start_seconds,
                "end": end_seconds,
                "text": match.group("text").strip(),
            }
        )
    return spans


def _extract_transcript_text(
    transcript_spans: list[dict[str, Any]], start_seconds: int, end_seconds: int
) -> str:
    """Return transcript text overlapping a selected time range."""
    selected_text = [
        span["text"]
        for span in transcript_spans
        if span["text"]
        and span["end"] > start_seconds
        and span["start"] < end_seconds
    ]
    return " ".join(selected_text).strip()


def _choose_repaired_bounds(
    transcript_spans: list[dict[str, Any]], start_seconds: int, end_seconds: int
) -> tuple[int, int] | None:
    """Repair model-selected bounds to the nearest acceptable contiguous range."""
    if not transcript_spans:
        return None

    starts = sorted({span["start"] for span in transcript_spans})
    ends = sorted({span["end"] for span in transcript_spans})
    current_duration = end_seconds - start_seconds

    if current_duration > MAX_ACCEPTED_CLIP_SECONDS:
        target_end = start_seconds + IDEAL_CLIP_MAX_SECONDS
        candidate_ends = [
            candidate
            for candidate in ends
            if start_seconds + MIN_ACCEPTED_CLIP_SECONDS
            <= candidate
            <= min(target_end, end_seconds)
        ]
        if candidate_ends:
            return start_seconds, max(candidate_ends)
        if start_seconds + MIN_ACCEPTED_CLIP_SECONDS <= target_end:
            return start_seconds, target_end
        return None

    if current_duration < MIN_ACCEPTED_CLIP_SECONDS:
        candidate_ranges: list[tuple[int, int, int]] = []
        for candidate_start in starts:
            if candidate_start > start_seconds:
                continue
            for candidate_end in ends:
                if candidate_end < end_seconds:
                    continue
                duration = candidate_end - candidate_start
                if MIN_ACCEPTED_CLIP_SECONDS <= duration <= MAX_ACCEPTED_CLIP_SECONDS:
                    extra_context = (start_seconds - candidate_start) + (
                        candidate_end - end_seconds
                    )
                    ideal_penalty = 0
                    if duration < IDEAL_CLIP_MIN_SECONDS:
                        ideal_penalty = IDEAL_CLIP_MIN_SECONDS - duration
                    elif duration > IDEAL_CLIP_MAX_SECONDS:
                        ideal_penalty = duration - IDEAL_CLIP_MAX_SECONDS
                    candidate_ranges.append(
                        (ideal_penalty * 1000 + extra_context, candidate_start, candidate_end)
                    )
        if candidate_ranges:
            _, repaired_start, repaired_end = min(candidate_ranges)
            return repaired_start, repaired_end

    return None


def _repair_segment_bounds(
    segment: TranscriptSegment,
    transcript_spans: list[dict[str, Any]],
    start_seconds: int,
    end_seconds: int,
) -> tuple[int, int] | None:
    """Adjust near-miss model ranges to usable transcript-aligned bounds."""
    repaired_bounds = _choose_repaired_bounds(
        transcript_spans,
        start_seconds,
        end_seconds,
    )
    if not repaired_bounds:
        return None

    repaired_start, repaired_end = repaired_bounds
    segment.start_time = _format_transcript_timestamp(repaired_start)
    segment.end_time = _format_transcript_timestamp(repaired_end)
    repaired_text = _extract_transcript_text(
        transcript_spans,
        repaired_start,
        repaired_end,
    )
    if repaired_text:
        segment.text = repaired_text
    logger.info(
        "Repaired segment duration: %s-%s -> %s-%s",
        _format_transcript_timestamp(start_seconds),
        _format_transcript_timestamp(end_seconds),
        segment.start_time,
        segment.end_time,
    )
    return repaired_start, repaired_end


def get_google_fallback_models(primary_model: str) -> list[str]:
    default_list = [
        "google-gla:gemini-3-flash",
        "google-gla:gemini-3-flash-preview",
        "google-gla:gemini-3.5-flash",
        "google-gla:gemini-3.1-flash-lite",
        "google-gla:gemini-2.5-flash",
        "google-gla:gemini-3.6-flash",
        "google-gla:gemini-2.5-flash-lite",
    ]
    # Ensure primary_model is first, and no duplicates
    models = [primary_model]
    for m in default_list:
        if m not in models and m != primary_model:
            norm = lambda x: x.replace("-preview", "")
            if not any(norm(existing) == norm(m) for existing in models):
                models.append(m)
    return models


async def get_most_relevant_parts_by_transcript(
    transcript: str, include_broll: bool = False, clip_signals: str | None = None
) -> TranscriptAnalysis:
    """Get the most relevant parts of a transcript with virality scoring and optional B-roll detection."""
    logger.info(
        f"Starting AI analysis of transcript ({len(transcript)} chars), include_broll={include_broll}"
    )

    runtime_config = get_config()
    provider, _ = _split_llm_name(runtime_config.llm)
    
    models_to_try = [runtime_config.llm]
    if provider == "google-gla":
        models_to_try = get_google_fallback_models(runtime_config.llm)

    last_err = None
    analysis = None
    for idx, model_name in enumerate(models_to_try):
        try:
            logger.info(f"Attempting transcript analysis with model: {model_name} (attempt {idx + 1}/{len(models_to_try)})")
            agent = get_transcript_agent()
            result = await agent.run(
                build_transcript_analysis_prompt(
                    transcript=transcript,
                    include_broll=include_broll,
                    clip_signals=clip_signals,
                ),
                model=model_name
            )
            analysis = result.output
            logger.info(f"AI analysis completed successfully with model: {model_name}")
            break
        except Exception as e:
            logger.warning(f"Model {model_name} failed for transcript analysis: {e}")
            last_err = e
            if idx < len(models_to_try) - 1:
                await asyncio.sleep(2.0)
    else:
        logger.error(f"All models failed for transcript analysis. Last error: {last_err}")
        raise RuntimeError(f"Transcript analysis failed on all models: {str(last_err)}") from last_err

    try:
        # Validation with virality data handling
        validated_segments = []
        transcript_spans = _parse_transcript_spans(transcript)
        for segment in analysis.most_relevant_segments:
            # Validate text content
            if not segment.text.strip() or len(segment.text.split()) < 3:
                logger.warning(
                    f"Skipping segment with insufficient content: '{segment.text[:50]}...'"
                )
                continue

            # Validate timestamps - CRITICAL: start and end must be different
            if segment.start_time == segment.end_time:
                logger.warning(
                    f"Skipping segment with identical start/end times: {segment.start_time}"
                )
                continue

            # Parse timestamps to validate duration
            try:
                start_seconds = _parse_transcript_timestamp_seconds(
                    segment.start_time
                )
                end_seconds = _parse_transcript_timestamp_seconds(segment.end_time)

                duration = end_seconds - start_seconds

                if duration < MIN_ACCEPTED_CLIP_SECONDS or duration > MAX_ACCEPTED_CLIP_SECONDS:
                    repaired_bounds = _repair_segment_bounds(
                        segment,
                        transcript_spans,
                        start_seconds,
                        end_seconds,
                    )
                    if repaired_bounds:
                        start_seconds, end_seconds = repaired_bounds
                        duration = end_seconds - start_seconds

                if duration <= 0:
                    logger.warning(
                        f"Skipping segment with invalid duration: {segment.start_time} to {segment.end_time} = {duration}s"
                    )
                    continue

                if duration < MIN_ACCEPTED_CLIP_SECONDS:
                    logger.warning(
                        f"Skipping segment too short: {duration}s (min {MIN_ACCEPTED_CLIP_SECONDS}s required)"
                    )
                    continue

                if duration > MAX_ACCEPTED_CLIP_SECONDS:
                    logger.warning(
                        f"Skipping segment too long: {duration}s (max {MAX_ACCEPTED_CLIP_SECONDS}s allowed)"
                    )
                    continue

                # Validate virality scores
                if segment.virality:
                    # Ensure total score is sum of subscores
                    calculated_total = (
                        segment.virality.hook_score
                        + segment.virality.engagement_score
                        + segment.virality.value_score
                        + segment.virality.shareability_score
                    )
                    if segment.virality.total_score != calculated_total:
                        logger.warning(
                            f"Correcting virality total: {segment.virality.total_score} -> {calculated_total}"
                        )
                        segment.virality.total_score = calculated_total

                segment.hook_title = sanitize_hook_title(segment.hook_title)

                # Auto-assign duration_category if AI didn't provide one
                if not segment.duration_category or segment.duration_category not in DURATION_CATEGORIES:
                    segment.duration_category = compute_duration_category(duration)

                validated_segments.append(segment)
                virality_info = (
                    f", virality={segment.virality.total_score}"
                    if segment.virality
                    else ""
                )
                logger.info(
                    f"Validated segment: {segment.start_time}-{segment.end_time} ({duration}s, {segment.duration_category}){virality_info}"
                )

            except (ValueError, IndexError) as e:
                logger.warning(
                    f"Skipping segment with invalid timestamp format: {segment.start_time}-{segment.end_time}: {e}"
                )
                continue

        # Sort by virality score (primary) then relevance (secondary)
        validated_segments.sort(
            key=lambda x: (
                x.virality.total_score if x.virality else 0,
                x.relevance_score,
            ),
            reverse=True,
        )

        final_analysis = TranscriptAnalysis(
            most_relevant_segments=validated_segments,
            summary=analysis.summary,
            key_topics=analysis.key_topics,
            broll_opportunities=analysis.broll_opportunities if include_broll else None,
        )

        logger.info(f"Selected {len(validated_segments)} segments for processing")

        # Log category distribution
        cat_dist: dict[str, int] = {}
        for seg in validated_segments:
            cat = seg.duration_category or "unknown"
            cat_dist[cat] = cat_dist.get(cat, 0) + 1
        logger.info(f"Category distribution: {cat_dist}")

        if validated_segments:
            top = validated_segments[0]
            logger.info(
                f"Top segment - relevance: {top.relevance_score:.2f}, virality: {top.virality.total_score if top.virality else 'N/A'}"
            )

        return final_analysis

    except Exception as e:
        logger.error(f"Error in transcript analysis: {e}")
        raise RuntimeError(f"Transcript analysis failed: {str(e)}") from e


def get_most_relevant_parts_sync(transcript: str) -> TranscriptAnalysis:
    """Synchronous wrapper for the async function."""
    return asyncio.run(get_most_relevant_parts_by_transcript(transcript))


class InstagramMetadata(BaseModel):
    hook_options: List[str] = Field(description="3 compelling hook/title options optimized for Instagram Reels (under 10 words each)")
    best_cover_text: str = Field(description="Best on-video cover text to display on the Reels cover image/video to maximize CTR")
    caption: str = Field(description="Instagram Reel caption. Hook the reader in first 5 words, keep paragraphs short, include space for tags/mentions.")
    hashtags: List[str] = Field(description="5 to 8 niche-specific, relevant hashtags (without the leading '#' sign). NO generic spam.")
    keywords: List[str] = Field(description="3 to 5 SEO/search keywords relevant to the Reels algorithm")
    cta: str = Field(description="Strong, natural Call-To-Action (CTA)")

class TikTokMetadata(BaseModel):
    hook_options: List[str] = Field(description="3 hook/title options optimized for TikTok's fast-paced style")
    caption: str = Field(description="TikTok caption. Punchy, native, short, using keywords naturally.")
    hashtags: List[str] = Field(description="5 to 8 hyper-relevant TikTok hashtags (without the leading '#' sign). NO generic tags.")
    keywords: List[str] = Field(description="3 to 5 TikTok search/SEO keywords")
    cta: str = Field(description="Call-To-Action optimized for TikTok")

class YouTubeMetadata(BaseModel):
    title_options: List[str] = Field(description="3 SEO-friendly title options under 60 characters")
    best_title: str = Field(description="The single best, highly-clickable and searchable title")
    description: str = Field(description="Short keyword-rich description (1-2 sentences)")
    hashtags: List[str] = Field(description="3 to 5 relevant hashtags (without the leading '#' sign)")
    keywords: List[str] = Field(description="3 to 5 SEO keywords for YouTube Shorts search")
    cta: str = Field(description="Call-To-Action")

class FacebookMetadata(BaseModel):
    title: str = Field(description="Hook or title optimized for Facebook Reels")
    caption: str = Field(description="Facebook caption, tailored for Facebook Reels/Feed")
    hashtags: List[str] = Field(description="3 to 5 relevant hashtags (without the leading '#' sign)")
    cta: str = Field(description="Strong Facebook-oriented CTA")

class SnapchatMetadata(BaseModel):
    hook: str = Field(description="Short, snappy hook/title under 6 words")
    caption: str = Field(description="Very short caption suited for Snapchat Spotlight/Stories")
    hashtags: List[str] = Field(description="2 to 4 relevant hashtags (without the leading '#' sign)")

class PinterestMetadata(BaseModel):
    title: str = Field(description="SEO-friendly Board/Pin Title (under 100 characters)")
    description: str = Field(description="Pin Description containing search keywords naturally (under 500 characters)")
    keywords: List[str] = Field(description="3 to 5 Pinterest search keywords/tags")

class XThreadsMetadata(BaseModel):
    post: str = Field(description="Short post accompanying the video clip (under 280 characters, suitable for X/Threads. High punchiness, zero fluff.)")


class SocialMediaPack(BaseModel):
    instagram: InstagramMetadata = Field(description="Optimized for Instagram Reels")
    tiktok: TikTokMetadata = Field(description="Optimized for TikTok")
    youtube: YouTubeMetadata = Field(description="Optimized for YouTube Shorts")
    facebook: FacebookMetadata = Field(description="Optimized for Facebook Reels")
    snapchat: SnapchatMetadata = Field(description="Optimized for Snapchat")
    pinterest: PinterestMetadata = Field(description="Optimized for Pinterest")
    x_threads: XThreadsMetadata = Field(description="Optimized for X (Twitter) and Threads")


social_media_system_prompt = """You are a world-class social media strategist and copywriting expert.
Your job is to generate a comprehensive, highly optimized 'Social Media Post Pack' for a video clip based on its transcript text and the on-screen headline hook.
You will write platform-optimized copy for YouTube (Shorts), TikTok, Instagram (Reels), Facebook Reels, Snapchat, Pinterest, and X (formerly Twitter) / Threads.

Optimization Rules to Follow Strictly:
1. Optimize for curiosity, watch time, completion, rewatches, shares, saves, and follows.
2. Make the first words highly compelling without misleading the viewer (never invent facts or use misleading clickbait).
3. Use platform-native wording; do not copy the same caption everywhere. Tailor formatting and tone to each platform's culture and guidelines.
4. Use relevant keywords naturally for search/discovery.
5. Use only relevant hashtags; avoid generic hashtag spam such as #viral, #fyp, #trending unless genuinely relevant.
6. Optimize language and references for the most relevant high-value/Tier-1 audiences (US, Canada, UK, Australia, Western Europe, etc.) when appropriate.
7. Consider the video's topic, emotion, niche, audience, cultural relevance, and likely viewer intent.
8. Prioritize audience quality over meaningless views.
9. Keep titles and captions concise and natural.
10. Return clean, copy-paste-ready output with no unnecessary explanation. Format the output strictly as JSON matching the requested schema. Do not output markdown, explanations, or commentary outside the JSON object."""

_social_agent: Optional[Agent[None, SocialMediaPack]] = None
_social_agent_signature = None


def get_social_agent() -> Agent[None, SocialMediaPack]:
    """Get or create the social media copywriter agent (lazy initialization)."""
    global _social_agent, _social_agent_signature
    runtime_config = get_config()
    signature = (
        runtime_config.llm,
        runtime_config.openai_api_key,
        runtime_config.google_api_key,
        runtime_config.anthropic_api_key,
        runtime_config.ollama_base_url,
        runtime_config.ollama_api_key,
    )
    if _social_agent is None or _social_agent_signature != signature:
        apply_settings_to_process_env(runtime_config.as_runtime_settings())
        config_error = _get_missing_llm_key_error(runtime_config.llm, runtime_config)
        if config_error:
            raise RuntimeError(config_error)

        _social_agent = Agent[None, SocialMediaPack](
            model=_build_transcript_model(runtime_config),
            output_type=SocialMediaPack,
            system_prompt=social_media_system_prompt,
            output_retries=2,
        )
        _social_agent_signature = signature
    return _social_agent


def build_dynamic_social_fallback(clip_text: str, hook_title: Optional[str] = None) -> SocialMediaPack:
    import re
    title = hook_title or "Viral Clip"
    clean_title = re.sub(r'[^\w\s]', '', title)
    title_words = [
        w.lower()
        for w in clean_title.split()
        if len(w) > 3 and w.lower() not in {"this", "that", "with", "from", "your", "what", "about"}
    ]
    
    # Capitalize title words for hashtags
    custom_tags = [w.capitalize() for w in title_words[:3]]
    if not custom_tags:
        custom_tags = ["Clips"]

    # Extract dynamic caption/description
    # Try to grab the first two sentences or first 250 characters
    sentences = re.split(r'(?<=[.!?])\s+', clip_text.strip())
    if len(sentences) >= 2:
        fallback_desc = " ".join(sentences[:2])
    else:
        fallback_desc = clip_text.strip()
    
    if len(fallback_desc) > 300:
        fallback_desc = fallback_desc[:297] + "..."

    # Form hook variants
    hooks = [
        title,
        f"The Truth About {title}" if not title.lower().startswith("why") else f"Understanding {title}",
        f"This is {title.lower()}" if not title.lower().startswith("how") else f"Exactly {title.lower()}"
    ]
    hooks = [h[:60] for h in hooks]

    # Form keywords
    keywords = title_words + ["viral", "shorts", "value", "insights"]
    keywords = list(dict.fromkeys(keywords))[:5] # deduplicate

    return SocialMediaPack(
        instagram=InstagramMetadata(
            hook_options=hooks,
            best_cover_text=title,
            caption=fallback_desc,
            hashtags=custom_tags + ["Reels", "Trending", "Clips"],
            keywords=keywords,
            cta="Double tap if you agree & follow for more!"
        ),
        tiktok=TikTokMetadata(
            hook_options=hooks,
            caption=fallback_desc,
            hashtags=custom_tags + ["Fyp", "ForYou", "ViralClips"],
            keywords=keywords,
            cta="Follow for daily value bombs!"
        ),
        youtube=YouTubeMetadata(
            title_options=hooks,
            best_title=title,
            description=f"{fallback_desc}\n\nSubscribe for more daily shorts!",
            hashtags=custom_tags + ["Shorts", "YouTubeShorts"],
            keywords=keywords,
            cta="Subscribe to the channel!"
        ),
        facebook=FacebookMetadata(
            title=title,
            caption=fallback_desc,
            hashtags=custom_tags + ["FacebookReels", "Reels"],
            cta="Share this reel with someone who needs to hear it!"
        ),
        snapchat=SnapchatMetadata(
            hook=title[:30],
            caption=fallback_desc[:150],
            hashtags=custom_tags + ["Spotlight", "Snap"]
        ),
        pinterest=PinterestMetadata(
            title=title[:90],
            description=fallback_desc[:450],
            keywords=keywords
        ),
        x_threads=XThreadsMetadata(
            post=f"{title}\n\n{fallback_desc[:200]}\n\nWhat do you think?"
        )
    )


async def generate_social_media_pack(clip_text: str, hook_title: Optional[str] = None) -> SocialMediaPack:
    """Generate social media sharing templates for a clip's transcript."""
    logger.info("Generating social media post pack for clip")
    if not clip_text or not clip_text.strip():
        # Return an empty pack if no text
        return SocialMediaPack(
            instagram=InstagramMetadata(hook_options=[], best_cover_text="", caption="", hashtags=[], keywords=[], cta=""),
            tiktok=TikTokMetadata(hook_options=[], caption="", hashtags=[], keywords=[], cta=""),
            youtube=YouTubeMetadata(title_options=[], best_title="", description="", hashtags=[], keywords=[], cta=""),
            facebook=FacebookMetadata(title="", caption="", hashtags=[], cta=""),
            snapchat=SnapchatMetadata(hook="", caption="", hashtags=[]),
            pinterest=PinterestMetadata(title="", description="", keywords=[]),
            x_threads=XThreadsMetadata(post="")
        )

    runtime_config = get_config()
    provider, _ = _split_llm_name(runtime_config.llm)
    
    models_to_try = [runtime_config.llm]
    if provider == "google-gla":
        models_to_try = get_google_fallback_models(runtime_config.llm)

    last_err = None
    max_attempts_per_model = 2
    
    for model_name in models_to_try:
        for attempt in range(max_attempts_per_model):
            try:
                logger.info(f"Attempting social media generation with model: {model_name} (attempt {attempt + 1}/{max_attempts_per_model})")
                agent = get_social_agent()
                prompt = f"Clip Transcript:\n{clip_text}"
                if hook_title:
                    prompt += f"\n\nOn-Screen Title Hook:\n{hook_title}"
                prompt += "\n\nGenerate the platform-optimized metadata for YouTube, TikTok, Instagram, Facebook, Snapchat, Pinterest, and X/Threads according to the specified schemas."
                
                result = await agent.run(prompt, model=model_name)
                return result.output
            except Exception as e:
                err_msg = str(e).lower()
                is_transient = any(
                    x in err_msg 
                    for x in ["429", "quota", "rate limit", "resource_exhausted", "timeout", "500", "502", "503", "504", "overloaded"]
                )
                last_err = e
                if is_transient:
                    if attempt < max_attempts_per_model - 1:
                        delay = (2 ** attempt) * 3 + 1.0
                        logger.warning(f"Transient error with model {model_name} (attempt {attempt + 1}/{max_attempts_per_model}): {e}. Retrying in {delay:.1f}s...")
                        await asyncio.sleep(delay)
                    else:
                        logger.warning(f"Model {model_name} exhausted all attempts due to rate limits. Trying next fallback model...")
                        await asyncio.sleep(1.0)
                        break
                else:
                    logger.warning(f"Non-transient error with model {model_name}: {e}. Trying next fallback model...")
                    await asyncio.sleep(1.0)
                    break
    else:
        logger.error(f"All models failed for social media pack generation. Last error: {last_err}")
        return build_dynamic_social_fallback(clip_text, hook_title)


