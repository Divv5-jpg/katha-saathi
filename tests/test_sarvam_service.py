import json
import unittest
from types import SimpleNamespace

from app_logic import load_stories
from services.sarvam_client import (
    chat_completion,
    speech_to_text,
    text_to_speech,
    translate_story_beat,
)


class FakeChat:
    def __init__(self, content):
        self.content = content
        self.request = None

    def completions(self, **request):
        self.request = request
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


class SarvamServiceTests(unittest.TestCase):
    def test_chat_uses_supported_model_and_separated_story_data(self):
        fake_chat = FakeChat("A kind reply.")
        client = SimpleNamespace(chat=fake_chat)
        reply = chat_completion(
            client,
            "System prompt",
            [{"role": "user", "content": "Earlier message"}],
            "Current message",
            story_context={"title": "Local story"},
        )
        self.assertEqual(reply, "A kind reply.")
        self.assertEqual(fake_chat.request["model"], "sarvam-105b-conversations")
        self.assertEqual(fake_chat.request["messages"][0]["role"], "system")
        self.assertEqual(fake_chat.request["messages"][1]["role"], "developer")
        self.assertEqual(fake_chat.request["messages"][-1]["content"], "Current message")

    def test_story_translation_preserves_choice_ids_and_shape(self):
        beat = load_stories()[0]["interactive_story_beats"][0]
        output = {
            "story_beat": {
                "passage": "స్థానిక కథా భాగం",
                "decision_point": "ఏం చేయాలి?",
                "choices": [
                    {"id": choice["id"], "label": "ఎంపిక", "consequence": "ఫలితం"}
                    for choice in beat["choices"]
                ],
                "open_ended_option": "మీ ఆలోచన చెప్పండి",
            }
        }
        fake_chat = FakeChat(json.dumps(output, ensure_ascii=False))
        result = translate_story_beat(
            SimpleNamespace(chat=fake_chat),
            "The Monkey and the Crocodile",
            beat,
            "Telugu",
        )
        self.assertEqual(result["choices"][0]["id"], beat["choices"][0]["id"])
        self.assertEqual(fake_chat.request["response_format"], {"type": "json_object"})

    def test_speech_to_text_uses_sarvam_transcription_endpoint(self):
        stt = SimpleNamespace(
            transcribe=lambda **kwargs: (
                self.assertEqual(kwargs["model"], "saaras:v4"),
                self.assertEqual(kwargs["language_code"], "te-IN"),
                self.assertEqual(kwargs["file"][0], "recording.wav"),
                SimpleNamespace(transcript="నమస్కారం"),
            )[-1]
        )
        result = speech_to_text(
            SimpleNamespace(speech_to_text=stt),
            b"wav audio",
            "te-IN",
        )
        self.assertEqual(result, "నమస్కారం")

    def test_speech_to_text_accepts_streamlit_uploaded_audio(self):
        request = {}

        def transcribe(**kwargs):
            request.update(kwargs)
            return SimpleNamespace(transcript="Hello there")

        recording = SimpleNamespace(
            getvalue=lambda: b"recorded audio",
            name="recording.wav",
            type="audio/wav",
        )
        result = speech_to_text(
            SimpleNamespace(speech_to_text=SimpleNamespace(transcribe=transcribe)),
            recording,
            "en-IN",
        )
        self.assertEqual(result, "Hello there")
        self.assertEqual(request["file"], ("recording.wav", b"recorded audio", "audio/wav"))

    def test_text_to_speech_decodes_sarvam_audio(self):
        import base64

        tts = SimpleNamespace(
            convert=lambda **kwargs: (
                self.assertEqual(kwargs["model"], "bulbul:v3"),
                self.assertEqual(kwargs["language_code"], "en-IN"),
                SimpleNamespace(audios=[base64.b64encode(b"mp3 audio").decode("ascii")]),
            )[-1]
        )
        result = text_to_speech(
            SimpleNamespace(text_to_speech=tts),
            "Hello there.",
            "en-IN",
        )
        self.assertEqual(result, b"mp3 audio")


if __name__ == "__main__":
    unittest.main()
