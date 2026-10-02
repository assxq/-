"""Script generation with Claude (or a deterministic mock for offline runs)."""
from __future__ import annotations
import json, re

SYSTEM = """You write 30-45 second YouTube Shorts scripts for an English-language channel that TESTS AI tools on camera-less screen recordings.
Hard rules:
- The video must show a REAL run of the tool. Put the exact steps a person must perform and record in "demo_steps". Never invent results; narrate only what the demo will show, with placeholders like <RESULT> where the real number/output goes.
- Include one honest limitation or failure observed or likely ("limitation").
- Hook: <= 14 words, states the concrete outcome in the first sentence.
- Total narration 70-110 words, short sentences, plain English (grade 7).
- No hype, no income claims, no medical/legal/financial advice. If the topic touches law, health, money, add a one-line "disclaimer".
- Original angle: say what you tested and what a viewer should do differently.
Return ONLY JSON with keys: title (<=70 chars), hook, beats [{narration,on_screen}], demo_steps [str], limitation, cta, disclaimer (string, may be empty), description, tags [str]."""


def _extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON in model output")
    return json.loads(m.group(0))


def generate(topic: str, cfg: dict, avoid_titles: list[str] | None = None, mock: bool = False) -> dict:
    if mock:
        return mock_script(topic)
    import anthropic  # needs ANTHROPIC_API_KEY
    client = anthropic.Anthropic()
    avoid = "\nDo not repeat angles of these past titles: " + "; ".join(avoid_titles[-20:]) if avoid_titles else ""
    msg = client.messages.create(
        model=cfg["llm"]["model"], max_tokens=cfg["llm"].get("max_tokens", 1500), system=SYSTEM,
        messages=[{"role": "user", "content": f"Topic: {topic}{avoid}"}])
    return _extract_json("".join(b.text for b in msg.content if b.type == "text"))


def mock_script(topic: str) -> dict:
    """Deterministic placeholder so the pipeline can be exercised without API keys."""
    return {
        "title": f"I tested this: {topic}"[:70],
        "hook": f"I tried {topic[:40]} so you do not have to.",
        "beats": [
            {"narration": "I ran the tool on a real task and timed it.", "on_screen": "Real test"},
            {"narration": "Here is the exact prompt I used. Copy it from the screen.", "on_screen": "The prompt"},
            {"narration": "The result was <RESULT>. That saved me real minutes.", "on_screen": "Result"},
            {"narration": "It is not perfect, so always check the numbers yourself.", "on_screen": "Check it"},
        ],
        "demo_steps": ["Open the tool", "Paste the prompt", "Record the full run with a visible timer"],
        "limitation": "It can get details wrong, so verify the output.",
        "cta": "Comment what I should test next.",
        "disclaimer": "",
        "description": f"Testing {topic}. Real run, real result.",
        "tags": ["AI", "AItools", "productivity"],
    }
