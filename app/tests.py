from django.test import TestCase
from unittest.mock import patch

from app.models import Staff


class StaffSignalTests(TestCase):
    @patch("app.signals.BOT_USERNAME", "test_bot")
    @patch("app.signals.generate_random_string", return_value="abc123")
    def test_create_sets_invite_link_once(self, _generate_random_string):
        staff = Staff.objects.create(name="Ali", tg_id="1001")

        staff.refresh_from_db()

        self.assertEqual(staff.invite_link, "https://t.me/test_bot?start=abc123")

    @patch("app.signals.BOT_USERNAME", "test_bot")
    @patch("app.signals.generate_random_string", return_value="abc123")
    def test_update_does_not_regenerate_invite_link(self, generate_random_string):
        staff = Staff.objects.create(name="Ali", tg_id="1002")
        staff.refresh_from_db()

        original_invite_link = staff.invite_link

        staff.name = "Vali"
        staff.save()
        staff.refresh_from_db()

        self.assertEqual(staff.invite_link, original_invite_link)
        self.assertEqual(generate_random_string.call_count, 1)

    @patch("app.signals.BOT_USERNAME", None)
    def test_create_skips_invite_link_when_bot_username_is_missing(self):
        with self.assertLogs("app.signals", level="WARNING") as logs:
            staff = Staff.objects.create(name="Hasan", tg_id="1003")

        staff.refresh_from_db()

        self.assertIsNone(staff.invite_link)
        self.assertIn("Skipping invite link generation", logs.output[0])
