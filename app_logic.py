import json
import os
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
STORIES_PATH = ROOT / "data" / "panchatantra_stories.json"
PROMPT_PATH = ROOT / "prompts" / "companion_system_prompt.txt"

LANGUAGES = {
    "English": "en-IN",
    "Telugu": "te-IN",
    "Marathi": "mr-IN",
    "Hindi": "hi-IN",
    "Tamil": "ta-IN",
    "Kannada": "kn-IN",
    "Bengali": "bn-IN",
    "Gujarati": "gu-IN",
    "Malayalam": "ml-IN",
    "Punjabi": "pa-IN",
    "Odia": "od-IN",
}

AGE_GUIDANCE = {
    "5–7 years": "Use very short sentences, familiar words, and one small idea at a time.",
    "8–10 years": "Use clear, friendly sentences and concrete examples; keep questions simple.",
    "11–13 years": "Use respectful, natural language with a little more nuance, without sounding formal.",
}

STORY_KEYS = {
    "monkey_crocodile": (
        "friend", "friendship", "trust", "tricked", "trick", "betray",
        "shared", "తప్పు", "స్నేహిత", "भरोसा", "दोस्त", "मित्र", "நண்பர்",
        "ಸ್ನೇಹಿತ", "বন্ধু", "મિત્ર", "സുഹൃത്ത്", "ਮਿੱਤਰ", "ମିତ୍ର",
    ),
    "lion_rabbit": (
        "scared", "afraid", "fear", "brave", "courage", "problem", "bully",
        "भय", "डर", "ధైర్య", "భయం", "தைரியம்", "ಧೈರ್ಯ", "সাহস",
        "હિંમત", "ധൈര്യം", "ਹਿੰਮਤ", "ସାହସ",
    ),
    "tortoise_geese": (
        "patience", "impulsive", "interrupt", "couldn't stop talking",
        "said too much", "self-control", "కోపం", "మాట్లాడ", "बोल",
        "धैर्य", "பேச", "ಮಾತು", "কথা", "વાત", "സംസാര", "ਗੱਲ", "କଥା",
    ),
    "blue_jackal": (
        "lied", "lie", "honest", "truth", "pretend", "mistake", "broke",
        "చెప్పలేదు", "అబద్ధం", "झूठ", "सच", "खोटं", "உண்மை", "ಸುಳ್ಳು",
        "মিথ্যা", "સાચું", "കള്ളം", "ਝੂਠ", "ମିଛ",
    ),
    "loyal_mongoose": (
        "jumped to conclusions", "misunderstood", "assumed", "check first",
        "reacted quickly", "angry", "చూసుకో", "కోపం", "गलत समझ",
        "जल्दी", "தவறாக", "கோபம்", "ತಪ್ಪಾಗಿ", "রাগ", "غلط", "ખોટું",
        "തെറ്റിദ്ധരിച്ചു", "ਗਲਤ", "ଭୁଲ",
    ),
}

SAFETY_TERMS = (
    "hurt me", "hurting me", "touch me", "touching me", "abuse", "abused",
    "hit me", "hitting me", "threatened me", "threatening me", "bullying me",
    "bully me", "want to die", "kill myself", "hurt myself", "self harm",
    "unsafe at home", "not safe", "scared to go home", "someone told me to keep it secret",
    "నన్ను కొట్ట", "నన్ను తాక", "చంపుకోవాల", "నేను సురక్షితంగా లేను",
    "मुझे मार", "मुझे छू", "मरना चाहता", "मरना चाहती", "सुरक्षित नहीं",
    "என்னை அடிக்க", "என்னை தொட", "வாழ விரும்பவில்லை", "பாதுகாப்பாக இல்லை",
    "ನನಗೆ ಹೊಡೆ", "ನನ್ನನ್ನು ಮುಟ್ಟ", "ಬದುಕಲು ಇಷ್ಟವಿಲ್ಲ",
    "আমাকে মারে", "আমাকে ছোঁ", "বাঁচতে চাই না",
    "મને મારે", "મને અડે", "જીવવું નથી",
    "എന്നെ അടിക്ക", "എന്നെ തൊട", "ജീവിക്കേണ്ട",
    "ਮੈਨੂੰ ਮਾਰ", "ਮੈਨੂੰ ਛੂ", "ਜੀਣਾ ਨਹੀਂ",
    "ମୋତେ ମାର", "ମୋତେ ଛୁଅ", "ବଞ୍ଚିବାକୁ ଚାହୁଁନି",
)


def load_stories(path: Path = STORIES_PATH) -> list[dict[str, Any]]:
    stories = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(stories, list) or len(stories) != 5:
        raise ValueError("The local story library must contain exactly five stories.")
    required = {
        "story_id", "title", "source_name", "source_reference",
        "original_story_text", "short_summary", "central_values",
        "possible_real_life_dilemmas", "positive_behaviours_to_recognize",
        "alternative_choices", "reflection_questions",
        "interactive_story_beats", "ending_options", "age_adaptation_notes",
        "cultural_context", "content_review_status",
    }
    for story in stories:
        missing = required - story.keys()
        if missing:
            raise ValueError(f"Story {story.get('story_id', 'unknown')} is missing required fields.")
    return stories


def select_relevant_story(
    text: str, stories: list[dict[str, Any]] | None = None
) -> dict[str, Any] | None:
    normalized = re.sub(r"\s+", " ", text.casefold())
    if not normalized.strip():
        return None
    available = {story["story_id"]: story for story in (stories or load_stories())}
    scores = {
        story_id: sum(1 for term in terms if term.casefold() in normalized)
        for story_id, terms in STORY_KEYS.items()
    }
    story_id, score = max(scores.items(), key=lambda item: item[1])
    if score == 0:
        return None
    return available.get(story_id)


def classify_safety_concern(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.casefold())
    return any(term.casefold() in normalized for term in SAFETY_TERMS)


def prepare_system_prompt(
    language: str,
    age_band: str,
    story: dict[str, Any] | None = None,
    safety_concern: bool = False,
) -> str:
    prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()
    prompt += (
        "\n\nSESSION SETTINGS (application data):\n"
        f"- Reply language: {language}. Reply in this language unless the child asks otherwise.\n"
        f"- Age band: {age_band}. {AGE_GUIDANCE[age_band]}\n"
        "- Keep the reply concise, usually two to five short sentences.\n"
    )
    if story:
        prompt += (
            "\nA local story may be relevant. Ask permission before introducing it, and use only "
            "the separate local story reference data supplied with this request."
        )
    if safety_concern:
        prompt += (
            "\n\nSAFETY OVERRIDE: This message may describe harm, danger, serious bullying, "
            "or self-harm. Set aside ordinary moral reflection and story matching. Respond "
            "calmly in the selected language, validate that the child deserves help, and "
            "encourage telling a trusted, safe adult now. If danger is immediate, tell them "
            "to ask that adult to contact local emergency services. Do not ask for details, "
            "promise secrecy, or investigate."
        )
    return prompt


def format_history(history: list[dict[str, str]], max_messages: int = 12) -> list[dict[str, str]]:
    clean = [
        {"role": item["role"], "content": item["content"]}
        for item in history
        if item.get("role") in {"user", "assistant"}
        and isinstance(item.get("content"), str)
        and item["content"].strip()
    ]
    return clean[-max_messages:]


def read_local_api_key() -> str | None:
    key = os.environ.get("SARVAM_API_KEY", "").strip()
    if key:
        return key
    env_file = ROOT / ".env"
    if not env_file.exists():
        return None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition("=")
        if separator and name.strip() == "SARVAM_API_KEY":
            return value.strip().strip("\"'") or None
    return None
