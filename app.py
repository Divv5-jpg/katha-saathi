import json
import hashlib

import streamlit as st

from app_logic import (
    LANGUAGES,
    STORIES_PATH,
    classify_safety_concern,
    load_stories,
    prepare_system_prompt,
    read_local_api_key,
    select_relevant_story,
)
from services.sarvam_client import (
    SarvamServiceError,
    chat_completion,
    create_client,
    speech_to_text,
    text_to_speech,
    translate_story_beat,
)


st.set_page_config(
    page_title="Katha Saathi — stories and thoughtful moments",
    page_icon="📚",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root { --cream:#FAF7F2; --green:#315b45; --deep:#234334; --terracotta:#b96f52; --ink:#2B2B2B; }
    .stApp { background:var(--cream); color:var(--ink); }
    .stApp, .stApp p, .stApp label, .stApp .stMarkdown,
    [data-testid="stChatMessage"], [data-testid="stChatMessage"] * {
      color:var(--ink);
    }
    [data-testid="stSidebar"] { background:#f1ead9; }
    .hero { background:linear-gradient(135deg,#e9f0df,#f7e8d8); border:1px solid #e4ddcc;
      border-radius:24px; padding:2rem; margin-bottom:1rem; }
    .hero h1 { color:var(--deep); font-size:2.55rem; margin:0; }
    .hero p { font-size:1.1rem; max-width:720px; }
    .story-card { background:#fffdf8; border:1px solid #e8dfcf; border-radius:18px;
      padding:1.15rem; min-height:170px; box-shadow:0 5px 18px #342c1710; }
    .note { color:#536454; font-size:.92rem; }
    div.stButton > button { border-radius:14px; border-color:#c9d2c4; }
    div.stButton > button[kind="primary"] { background:var(--green); border-color:var(--green); }
    [data-testid="stChatMessage"] { border-radius:16px; }
    @media (max-width:700px) { .hero { padding:1.25rem; } .hero h1 { font-size:2rem; } }
    </style>
    """,
    unsafe_allow_html=True,
)


def initialize_state() -> None:
    defaults = {
        "page": "Welcome",
        "messages": [],
        "selected_story_id": None,
        "story_beat_index": 0,
        "story_choices": [],
        "achievements": [],
        "processed_voice_recording": None,
        "voice_recording_error": None,
        "audio_replies": {},
        "translated_story_beats": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_conversation() -> None:
    st.session_state.messages = []
    st.session_state.selected_story_id = None
    st.session_state.story_beat_index = 0
    st.session_state.story_choices = []
    st.session_state.story_last_response = None
    st.session_state.story_safety_paused = False
    st.session_state.achievements = []
    st.session_state.processed_voice_recording = None
    st.session_state.voice_recording_error = None
    st.session_state.audio_replies = {}
    st.session_state.voice_transcript = None
    st.session_state.translated_story_beats = {}


def start_new_conversation() -> None:
    reset_conversation()
    st.session_state.page = "Welcome"


def start_story(story_id: str) -> None:
    st.session_state.selected_story_id = story_id
    st.session_state.story_beat_index = 0
    st.session_state.story_choices = []
    st.session_state.page = "Interactive story"
    if "Story Explorer" not in st.session_state.achievements:
        st.session_state.achievements.append("Story Explorer")


def open_chat_with(text: str) -> None:
    st.session_state.page = "Companion"
    send_message(text)


def get_client():
    key = read_local_api_key()
    if not key:
        try:
            key = st.secrets.get("SARVAM_API_KEY", "")
        except st.errors.StreamlitSecretNotFoundError:
            key = ""
    return create_client(key or "")


def send_message(text: str) -> None:
    message = text.strip()
    if not message:
        return
    history = st.session_state.messages
    history.append({"role": "user", "content": message})
    safety = classify_safety_concern(message)
    selected_story = None if safety else select_relevant_story(message)
    try:
        client = get_client()
        prompt = prepare_system_prompt(
            st.session_state.language,
            st.session_state.age_band,
            story=selected_story,
            safety_concern=safety,
        )
        with st.spinner("Katha Saathi is listening…"):
            reply = chat_completion(
                client,
                prompt,
                history[:-1],
                message,
                story_context=selected_story,
            )
        history.append({"role": "assistant", "content": reply})
        del history[:-24]
    except SarvamServiceError as exc:
        history.append(
            {
                "role": "assistant",
                "content": "I’m here, but I can’t reach my story helper right now. Your message is still here; please try again in a little while.",
            }
        )
        del history[:-24]
        st.warning(str(exc))


def render_welcome(stories: list[dict]) -> None:
    st.markdown(
        """
        <div class="hero">
          <h1>📚 Katha Saathi</h1>
          <p>A gentle story companion for big feelings, little wins, and everything in between.
          You can share as much or as little as you like.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.subheader("What would you like to talk about?")
    cols = st.columns(2)
    suggestions = [
        "I had a good day and helped someone.",
        "Something happened with a friend and I feel upset.",
        "I made a mistake and I’m not sure what to do.",
        "I just want to hear a story.",
    ]
    for index, suggestion in enumerate(suggestions):
        with cols[index % 2]:
            st.button(
                suggestion,
                key=f"welcome_{index}",
                use_container_width=True,
                on_click=open_chat_with,
                args=(suggestion,),
            )
    st.markdown("---")
    st.subheader("Stories to explore")
    st.caption("Browse any story without sharing anything personal.")
    render_story_cards(stories[:3])
    st.caption("These are provisional retellings. No source edition was supplied for verification.")


def render_story_cards(stories: list[dict]) -> None:
    icons = {
        "monkey_crocodile": "🐒",
        "lion_rabbit": "🦁",
        "tortoise_geese": "🐢",
        "blue_jackal": "🐺",
        "loyal_mongoose": "🦦",
    }
    for offset in range(0, len(stories), 2):
        columns = st.columns(2)
        for column, story in zip(columns, stories[offset : offset + 2]):
            with column:
                st.markdown(
                    f"""
                    <div class="story-card">
                      <h3>{icons.get(story['story_id'], '📖')} {story['title']}</h3>
                      <p>{story['short_summary']}</p>
                      <p class="note">Themes: {", ".join(story['central_values'])}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.button(
                    "Explore this story",
                    key=f"story_{story['story_id']}",
                    use_container_width=True,
                    on_click=start_story,
                    args=(story["story_id"],),
                )


def render_library(stories: list[dict]) -> None:
    st.title("The story library")
    st.write("Choose a story just because you are curious. You do not need to share a personal story.")
    render_story_cards(stories)
    st.info(
        "Story source note: no source document was supplied, so all five retellings are marked "
        "provisional and should be checked against your chosen edition before publication."
    )


def render_story_mode(stories: list[dict]) -> None:
    story = next(
        (item for item in stories if item["story_id"] == st.session_state.selected_story_id),
        None,
    )
    if not story:
        st.info("Choose a story from the library to begin.")
        return
    st.title(f"📖 {story['title']}")
    st.caption("A provisional retelling · You can pause or leave whenever you like.")
    beats = story["interactive_story_beats"]
    index = st.session_state.story_beat_index
    st.progress(min(index, len(beats)) / len(beats), text=f"Story step {min(index + 1, len(beats))} of {len(beats)}")
    if st.session_state.get("story_last_response"):
        st.info(st.session_state.story_last_response)
    if st.session_state.get("story_safety_paused"):
        st.warning("The story is paused. You can continue in the companion or choose another story.")
        return
    if index >= len(beats):
        st.success("That is one place to pause. The story does not need a perfect ending.")
        st.subheader("What would you like to do?")
        for choice_index, option in enumerate(story["ending_options"]):
            if st.button(option, key=f"ending_{choice_index}", use_container_width=True):
                if "companion" in option.casefold():
                    st.session_state.page = "Companion"
                elif "another" in option.casefold() or "different" in option.casefold():
                    st.session_state.page = "Story library"
                else:
                    st.session_state.selected_story_id = None
                st.rerun()
        return

    source_beat = beats[index]
    beat = source_beat
    if st.session_state.language != "English":
        cache_key = f"{st.session_state.language}:{story['story_id']}:{index}"
        translated = st.session_state.translated_story_beats.get(cache_key)
        if translated is None:
            try:
                with st.spinner("Preparing this story in your language…"):
                    translated = translate_story_beat(
                        get_client(),
                        story["title"],
                        source_beat,
                        st.session_state.language,
                    )
                st.session_state.translated_story_beats[cache_key] = translated
            except SarvamServiceError as exc:
                st.warning(str(exc))
                st.info("The story has not been shown in another language. You can retry or switch languages.")
                return
        beat = translated
    st.markdown(f'<div class="story-card"><p>{beat["passage"]}</p></div>', unsafe_allow_html=True)
    st.subheader(beat["decision_point"])
    labels = [choice["label"] for choice in beat["choices"]]
    selected_label = st.radio("Pick an idea, or write your own:", labels, key=f"choice_{story['story_id']}_{index}")
    own_idea = st.text_input(beat["open_ended_option"], key=f"own_idea_{story['story_id']}_{index}")
    if st.button("Continue the story", type="primary"):
        chosen_text = own_idea.strip() or selected_label
        choice_index = next(
            (choice_index for choice_index, choice in enumerate(beat["choices"]) if choice["label"] == selected_label),
            None,
        )
        selected_choice = source_beat["choices"][choice_index] if choice_index is not None else None
        safety = classify_safety_concern(chosen_text)
        if own_idea.strip():
            try:
                prompt = prepare_system_prompt(
                    st.session_state.language,
                    st.session_state.age_band,
                    story=None if safety else story,
                    safety_concern=safety,
                )
                response = chat_completion(
                    get_client(),
                    prompt,
                    [],
                    (
                        f"The child shared: {chosen_text}\n"
                        if safety
                        else (
                            f"Story choice (the child's own idea): {chosen_text}\n"
                            "Acknowledge the idea without judging it. Do not add or change story events. "
                            "Keep your response to one short, kind sentence."
                        )
                    ),
                    story_context=None if safety else {
                        "title": story["title"],
                        "current_passage": source_beat["passage"],
                        "choices_and_local_consequences": source_beat["choices"],
                        "previous_choices": st.session_state.story_choices,
                    },
                )
            except SarvamServiceError as exc:
                st.warning(str(exc))
                return
        else:
            response = (
                beat["choices"][choice_index]["consequence"]
                if choice_index is not None
                else ""
            )
        st.session_state.story_choices.append(
            {"story_id": story["story_id"], "choice": chosen_text}
        )
        st.session_state.story_safety_paused = safety
        st.session_state.story_beat_index = (
            len(beats) if safety else st.session_state.story_beat_index + 1
        )
        st.session_state.story_last_response = response
        if not safety and "Curious Choice" not in st.session_state.achievements:
            st.session_state.achievements.append("Curious Choice")
        st.rerun()
def render_chat() -> None:
    st.title("Your companion")
    st.caption("Share a little, share a lot, or simply ask for a story. You are in charge.")
    for message_index, item in enumerate(st.session_state.messages):
        with st.chat_message(item["role"]):
            st.write(item["content"])
            if item["role"] == "assistant":
                audio_key = hashlib.sha256(
                    f"{LANGUAGES[st.session_state.language]}:{item['content']}".encode("utf-8")
                ).hexdigest()
                if st.button(
                    "🔊 Read Aloud",
                    key=f"read_aloud_{message_index}_{audio_key}",
                ):
                    try:
                        with st.spinner("Preparing audio…"):
                            st.session_state.audio_replies[audio_key] = text_to_speech(
                                get_client(),
                                item["content"],
                                LANGUAGES[st.session_state.language],
                            )
                    except SarvamServiceError as exc:
                        st.warning(f"Read-aloud is unavailable right now: {exc}")
                    except Exception:
                        st.info("Audio playback is unavailable in this browser. You can still read the reply.")
                if audio_key in st.session_state.audio_replies:
                    try:
                        st.audio(st.session_state.audio_replies[audio_key], format="audio/mpeg")
                    except Exception:
                        st.info("Audio playback is unavailable in this browser. You can still read the reply.")
    transcript = st.session_state.get("voice_transcript")
    if transcript:
        st.info(f"Voice transcript: {transcript}")
        if st.button("Send this transcript"):
            st.session_state.voice_transcript = None
            send_message(transcript)
            st.rerun()

    with st.form(f"chat_form_{len(st.session_state.messages)}", clear_on_submit=True):
        message = st.text_area("Your message", height=90, placeholder="You can type in your selected language…")
        submitted = st.form_submit_button("Send", type="primary")
    if submitted and message.strip():
        send_message(message)
        st.rerun()

    if hasattr(st, "audio_input"):
        try:
            recording = st.audio_input(
                "Or record a voice message",
                sample_rate=16000,
                key="companion_audio_input",
                help="Your recording is sent to Sarvam to transcribe, then submitted as your chat message.",
            )
        except Exception:
            recording = None
            st.info("Voice recording is unavailable in this browser. You can type your message instead.")

        if recording is not None:
            recording_bytes = recording.getvalue()
            recording_key = hashlib.sha256(recording_bytes).hexdigest()
            if recording_key != st.session_state.processed_voice_recording:
                st.session_state.processed_voice_recording = recording_key
                st.session_state.voice_recording_error = None
                try:
                    transcript = speech_to_text(
                        get_client(),
                        recording_bytes,
                        LANGUAGES[st.session_state.language],
                        filename=getattr(recording, "name", None) or "recording.wav",
                    )
                    send_message(transcript)
                    st.rerun()
                except SarvamServiceError as exc:
                    st.session_state.voice_recording_error = str(exc)
            if st.session_state.voice_recording_error:
                st.warning(
                    "I couldn't use that recording. You can record again or type your message. "
                    + st.session_state.voice_recording_error
                )
    else:
        st.info("Voice recording isn't supported by this Streamlit version. You can type your message instead.")


def render_wins() -> None:
    st.title("My little wins")
    st.write("A few gentle reminders of things you chose to do here. These stay only in this browser session.")
    st.caption("This is not a score, personality label, or competition.")
    badges = list(dict.fromkeys(st.session_state.achievements))
    if badges:
        for badge in badges:
            description = (
                "You chose to explore a story."
                if badge == "Story Explorer"
                else "You tried a choice in an interactive story."
            )
            st.markdown(f'<div class="story-card">🌱 <b>{badge}</b><br>{description}</div>', unsafe_allow_html=True)
    else:
        st.info("No badges yet. There is nothing to earn or keep up with.")
    st.button(
        "Mark a thoughtful moment",
        help="This adds a playful reminder that you chose to pause and reflect. It is not a score.",
        on_click=lambda: st.session_state.achievements.append("Thoughtful Pause"),
    )


def render_settings() -> None:
    st.title("Settings and privacy")
    st.write(
        "Choose the language that feels comfortable and an age band for simpler or more detailed "
        "words. You do not need to share your name, school, address, or other identifying details."
    )
    st.caption(
        "Conversation, story position, and little wins are kept in Streamlit's current session only. "
        "Messages are sent to Sarvam AI to generate replies; this app does not save them to a child profile."
    )
    if st.button("Start a new conversation"):
        reset_conversation()
        st.success("A fresh conversation is ready.")


initialize_state()
try:
    stories = load_stories(STORIES_PATH)
except (OSError, ValueError, json.JSONDecodeError) as exc:
    st.error(f"The local story library could not be loaded ({type(exc).__name__}). Check data/panchatantra_stories.json.")
    st.stop()

with st.sidebar:
    st.title("📚 Katha Saathi")
    st.selectbox("Language", list(LANGUAGES), key="language", index=0)
    st.selectbox("Age band (optional)", ["5–7 years", "8–10 years", "11–13 years"], key="age_band", index=1)
    st.radio(
        "Explore",
        ["Welcome", "Companion", "Story library", "Interactive story", "My little wins", "Settings"],
        key="page",
    )
    st.caption("🌿 A gentle space. You can skip any question or story.")
    st.button(
        "New conversation",
        use_container_width=True,
        on_click=start_new_conversation,
    )

page = st.session_state.page
if page == "Welcome":
    render_welcome(stories)
elif page == "Companion":
    render_chat()
elif page == "Story library":
    render_library(stories)
elif page == "Interactive story":
    render_story_mode(stories)
elif page == "My little wins":
    render_wins()
else:
    render_settings()
