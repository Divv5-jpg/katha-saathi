import unittest

from app_logic import (
    classify_safety_concern,
    format_history,
    load_stories,
    prepare_system_prompt,
    select_relevant_story,
)


class StoryDataTests(unittest.TestCase):
    def test_exactly_five_complete_provisional_records(self):
        stories = load_stories()
        self.assertEqual(len(stories), 5)
        self.assertTrue(
            all("PROVISIONAL" in story["content_review_status"] for story in stories)
        )
        self.assertTrue(all(story["interactive_story_beats"] for story in stories))

    def test_story_matching_and_no_forced_match(self):
        self.assertEqual(
            select_relevant_story("I lied to my friend")["story_id"], "blue_jackal"
        )
        self.assertIsNone(select_relevant_story("Can you tell me a joke?"))


class ConversationLogicTests(unittest.TestCase):
    def test_history_is_bounded_and_filters_unknown_roles(self):
        history = [
            {"role": "user", "content": str(index)} for index in range(20)
        ] + [{"role": "system", "content": "not allowed"}]
        result = format_history(history, max_messages=6)
        self.assertEqual(len(result), 6)
        self.assertEqual(result[0]["content"], "14")
        self.assertTrue(all(item["role"] in {"user", "assistant"} for item in result))

    def test_safety_terms_and_prompt_override(self):
        self.assertTrue(classify_safety_concern("Someone is bullying me"))
        self.assertFalse(classify_safety_concern("I enjoyed a story today"))
        prompt = prepare_system_prompt("Hindi", "8–10 years", safety_concern=True)
        self.assertIn("SAFETY OVERRIDE", prompt)
        self.assertIn("Hindi", prompt)


if __name__ == "__main__":
    unittest.main()
