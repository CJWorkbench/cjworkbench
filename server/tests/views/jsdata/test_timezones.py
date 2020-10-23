import json


from django.test import SimpleTestCase


def _find_index(values, condition):
    for i, value in enumerate(values):
        if condition(value):
            return i
    else:
        raise ValueError("No value matched condition")


class IndexTest(SimpleTestCase):
    def test_sort_by_offset(self):
        response = self.client.get("/jsdata/timezones.json")
        timezones = json.loads(response.content)["timezones"]
        self.assertLess(
            _find_index(
                timezones, lambda tz: tz["name"] == "United States (Los Angeles) Time"
            ),
            _find_index(
                timezones,
                lambda tz: tz["name"] == "Canada (Toronto) Time",
            ),
        )

    def test_sort_alphabetically_within_offset(self):
        response = self.client.get("/jsdata/timezones.json")
        timezones = json.loads(response.content)["timezones"]
        self.assertLess(
            _find_index(timezones, lambda tz: tz["name"] == "Canada (Toronto) Time"),
            _find_index(
                timezones, lambda tz: tz["name"] == "United States (New York) Time"
            ),
        )

    def test_aliases(self):
        response = self.client.get("/jsdata/timezones.json")
        timezones = json.loads(response.content)["timezones"]
        toronto = next(tz for tz in timezones if tz["id"] == "America/Toronto")
        self.assertIn("America/Montreal", toronto["aliases"])

    def test_localize_gmt_offset(self):
        response = self.client.get("/jsdata/timezones.json")
        timezones = json.loads(response.content)["timezones"]
        utc = next(tz for tz in timezones if tz["id"] == "Etc/UTC")
        self.assertEqual(utc["offset"], "GMT+00:00")

    def test_translate_timezone_name(self):
        response = self.client.get("/jsdata/timezones.json?locale=el")
        timezones = json.loads(response.content)["timezones"]
        toronto = next(tz for tz in timezones if tz["id"] == "America/Toronto")
        self.assertEqual(toronto["name"], "Ώρα ([Καναδάς (Τορόντο)])")
