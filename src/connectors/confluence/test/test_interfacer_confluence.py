"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

Unit tests for ConfluenceInterfacer static helpers — no Live HTTP.
The connector uses Atlassian's ``api.atlassian.com`` gateway; URL shaping is internal to that stack.
"""

import json
import unittest

from confluence_service.interfacer_confluence import ConfluenceInterfacer


class TestConfluenceSubdataRoundTrip(unittest.TestCase):
    """``_generate_subdata`` / ``_parse_subdata`` must stay symmetrical for indexer checkpoints."""

    def test_roundtrip_dict(self) -> None:
        original = {"last_sync": "2024-01-01T12:00:00+00:00"}
        blob = ConfluenceInterfacer._generate_subdata(original)
        self.assertEqual(ConfluenceInterfacer._parse_subdata(blob), original)

    def test_parse_bad_base64_returns_empty(self) -> None:
        self.assertEqual(ConfluenceInterfacer._parse_subdata("not-valid-base64!!!"), {})

    def test_parse_none_returns_empty(self) -> None:
        self.assertEqual(ConfluenceInterfacer._parse_subdata(None), {})

    def test_custom_dict_survives_urlsafe_transport(self) -> None:
        data = {"k": "v", "nested": {"x": 1}}
        b64 = ConfluenceInterfacer._generate_subdata(data)
        out = ConfluenceInterfacer._parse_subdata(b64)
        round_json = json.dumps(out, sort_keys=True)
        self.assertEqual(round_json, json.dumps(data, sort_keys=True))


class TestConfluenceCreateDateObject(unittest.TestCase):
    def test_none_is_min_utc(self) -> None:
        from datetime import datetime, timezone

        got = ConfluenceInterfacer._create_date_object(None)
        self.assertEqual(got, datetime.min.replace(tzinfo=timezone.utc))

    def test_z_suffix_parsed(self) -> None:
        from datetime import datetime, timezone

        got = ConfluenceInterfacer._create_date_object("2019-06-01T12:00:00Z")
        self.assertEqual(got.year, 2019)
        self.assertEqual(got.tzinfo, timezone.utc)


class TestExtractText(unittest.TestCase):
    def test_strips_tags_and_collapses_space(self) -> None:
        html = "<p>Hello  <b>world</b> &amp; more</p>"
        plain = ConfluenceInterfacer._extract_text(html)
        self.assertEqual(plain, "Hello world & more")
