import unittest
import os
import sqlite3
import tempfile
from backend.database import database as database_module
from backend.services.prediction_service import predict_text, calculate_risk_and_severity
from backend.services.moderation_service import process_comment_moderation, get_analytics_metrics, get_moderation_queue, update_comment_status
from backend.database.database import init_db

class TestCyberbullyingSystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Keep tests isolated from the user's project database.
        cls._original_db_path = database_module.DB_PATH
        cls._test_directory = tempfile.TemporaryDirectory(prefix="cybershield-tests-")
        database_module.DB_PATH = os.path.join(cls._test_directory.name, "test.sqlite")
        init_db()

    @classmethod
    def tearDownClass(cls):
        database_module.DB_PATH = cls._original_db_path
        cls._test_directory.cleanup()

    def test_01_non_abusive_classification(self):
        text = "Thank you so much for sharing this awesome tutorial! Really helpful."
        res = predict_text(text)
        self.assertEqual(res['category'], 'NON_ABUSIVE')
        self.assertLessEqual(res['risk_score'], 25)
        self.assertEqual(res['severity'], 'LOW')

    def test_02_toxic_classification(self):
        text = "You are an absolute idiot for posting this garbage video."
        res = predict_text(text)
        self.assertIn(res['category'], ['TOXIC', 'BULLYING'])
        self.assertGreaterEqual(res['risk_score'], 40)

    def test_03_bullying_classification(self):
        text = "Nobody likes you. Delete your account and disappear forever."
        res = predict_text(text)
        self.assertIn(res['category'], ['BULLYING', 'SEVERE_BULLYING'])
        self.assertGreaterEqual(res['risk_score'], 60)

    def test_04_severe_bullying_classification(self):
        text = "Go kill yourself right now, nobody wants you alive on earth."
        res = predict_text(text)
        self.assertEqual(res['category'], 'SEVERE_BULLYING')
        self.assertGreaterEqual(res['risk_score'], 80)
        self.assertIn(res['severity'], ['HIGH', 'CRITICAL'])

    def test_05_hate_speech_classification(self):
        text = "Get out of our country, immigrants like you are ruining our nation."
        res = predict_text(text)
        self.assertEqual(res['category'], 'HATE_SPEECH')
        self.assertGreaterEqual(res['risk_score'], 75)

    def test_06_sexual_harassment_classification(self):
        text = "Send me explicit pictures of your body right now or I will leak photos."
        res = predict_text(text)
        self.assertEqual(res['category'], 'SEXUAL_HARASSMENT')
        self.assertGreaterEqual(res['risk_score'], 80)

    def test_07_threat_classification(self):
        text = "I am going to find you outside your office and shoot you in the head."
        res = predict_text(text)
        self.assertEqual(res['category'], 'THREAT')
        self.assertGreaterEqual(res['risk_score'], 85)
        self.assertEqual(res['severity'], 'CRITICAL')

    def test_08_empty_text_error(self):
        with self.assertRaises(ValueError):
            predict_text("")

    def test_09_max_length_exceeded_error(self):
        long_text = "a" * 1005
        with self.assertRaises(ValueError):
            predict_text(long_text)

    def test_09b_critical_triggers_match_whole_words(self):
        risk, severity = calculate_risk_and_severity('TOXIC', 0.8, 'The diet plan was difficult.')
        self.assertLess(risk, 85)
        self.assertNotEqual(severity, 'CRITICAL')

    def test_10_emoji_and_urls(self):
        text = "Check out https://example.com! Great work 🎉🔥"
        res = predict_text(text)
        self.assertEqual(res['category'], 'NON_ABUSIVE')

    def test_11_moderation_flow_and_db(self):
        text = "Testing moderation queue insertion flow."
        res = process_comment_moderation(text, username="UnitTestUser")
        self.assertTrue(res['comment_id'].startswith("CMT-"))
        
        queue = get_moderation_queue(search="UnitTestUser")
        self.assertGreaterEqual(len(queue), 1)

    def test_12_analytics_metrics(self):
        metrics = get_analytics_metrics()
        self.assertGreater(metrics['total_comments'], 0)
        self.assertIn('category_percentages', metrics)
        self.assertIn('severity_breakdown', metrics)
        self.assertEqual(len(metrics['activity_labels']), 7)
        self.assertEqual(len(metrics['comments_by_day']), 7)
        self.assertIn('REMOVED', metrics['status_breakdown'])

    def test_13_uncertain_prediction_is_held_for_review(self):
        res = process_comment_moderation("maybe", username="UncertainUser")
        self.assertTrue(res['is_uncertain'])
        self.assertFalse(res['allowed'])
        self.assertEqual(res['action'], 'FLAG_FOR_REVIEW')
        queue = get_moderation_queue(status_filter='PENDING_REVIEW', search='UncertainUser')
        self.assertTrue(any(item['comment_id'] == res['comment_id'] for item in queue))

    def test_14_remove_action_moves_comment_to_removed_queue(self):
        res = process_comment_moderation("Thank you for the helpful post.", username="RemovedUser")
        updated = update_comment_status(res['comment_id'], 'REMOVE')
        self.assertEqual(updated['new_status'], 'REMOVED')
        queue = get_moderation_queue(status_filter='REMOVED', search='RemovedUser')
        self.assertTrue(any(item['comment_id'] == res['comment_id'] for item in queue))

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("      RUNNING SYSTEM UNIT & INTEGRATION TESTS    ")
    print("=" * 60 + "\n")
    unittest.main()
