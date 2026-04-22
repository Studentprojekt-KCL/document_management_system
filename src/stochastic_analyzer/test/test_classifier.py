"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

Unit tests for the stochastic_analyzer NLI document classifier.
"""

# Tests intentionally call private helpers on Classifier for focused checks.
# pylint: disable=protected-access

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from gateway.schemas import ClassificationResult, InputItem, MetadataTemplate
from gateway.services.classifier import LABELS, Classifier

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_item(
    content: str = "Some document content.",
    name: str | None = "doc.pdf",
    author: str | None = "Alice",
    pointer: str | None = "ptr-001",
) -> InputItem:
    """Return a minimal valid InputItem."""
    return InputItem(
        content=content,
        metadata=MetadataTemplate(name=name, author=author, unique_pointer=pointer),
    )


def _make_classifier(url: str = "http://tei", threshold: float = 0.05) -> Classifier:
    """Return a Classifier with sensible test defaults."""
    return Classifier(url=url, escalation_threshold=threshold)


def _entailment_response(score: float) -> list[dict]:
    """Fake single NLI prediction response with one entailment score."""
    return [
        {"label": "entailment", "score": score},
        {"label": "contradiction", "score": 1.0 - score},
    ]


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestClassifierInit(unittest.TestCase):
    """Tests for Classifier.__init__ and class-level defaults."""

    def test_url_is_stored(self) -> None:
        """Constructor stores the url attribute."""
        c = _make_classifier(url="http://example.com")
        self.assertEqual(c.url, "http://example.com")

    def test_escalation_threshold_is_stored(self) -> None:
        """Constructor stores the escalation_threshold attribute."""
        c = _make_classifier(threshold=0.12)
        self.assertEqual(c.escalation_threshold, 0.12)

    def test_class_level_defaults(self) -> None:
        """Class-level constants have expected default values."""
        self.assertEqual(Classifier.max_chars, 2000)
        self.assertEqual(Classifier.batch_size, 32)
        self.assertEqual(Classifier.timeout, 15.0)


# ---------------------------------------------------------------------------
# _build_inputs
# ---------------------------------------------------------------------------


class TestBuildInputs(unittest.TestCase):
    """Tests for Classifier._build_inputs."""

    def setUp(self) -> None:
        self.classifier = _make_classifier()

    def test_returns_one_pair_per_label_per_document(self) -> None:
        """_build_inputs produces len(LABELS) pairs for each input document."""
        items = [_make_item(), _make_item()]
        result = self.classifier._build_inputs(items)
        self.assertEqual(len(result), len(items) * len(LABELS))

    def test_each_pair_has_two_elements(self) -> None:
        """Every NLI pair contains exactly a premise and a hypothesis."""
        result = self.classifier._build_inputs([_make_item()])
        for pair in result:
            self.assertEqual(len(pair), 2)

    def test_hypothesis_matches_label_trigger(self) -> None:
        """Hypothesis strings in pairs correspond to LABEL_TRIGGERS entries."""
        from gateway.services.classifier import LABEL_TRIGGERS

        result = self.classifier._build_inputs([_make_item()])
        hypotheses = [pair[1] for pair in result]
        self.assertEqual(hypotheses, LABEL_TRIGGERS)

    def test_premise_contains_document_name(self) -> None:
        """Premise includes the document name from metadata."""
        item = _make_item(name="report.pdf")
        result = self.classifier._build_inputs([item])
        self.assertIn("report.pdf", result[0][0])

    def test_premise_contains_author(self) -> None:
        """Premise includes the author from metadata."""
        item = _make_item(author="Bob")
        result = self.classifier._build_inputs([item])
        self.assertIn("Bob", result[0][0])

    def test_premise_contains_content(self) -> None:
        """Premise includes the document content."""
        item = _make_item(content="Top secret data.")
        result = self.classifier._build_inputs([item])
        self.assertIn("Top secret data.", result[0][0])

    def test_premise_truncates_content_at_max_chars(self) -> None:
        """Premise truncates content to max_chars characters."""
        long_content = "A" * 5000
        item = _make_item(content=long_content)
        result = self.classifier._build_inputs([item])
        self.assertNotIn("A" * (self.classifier.max_chars + 1), result[0][0])

    def test_missing_name_falls_back_to_unknown(self) -> None:
        """None metadata.name is replaced with 'Unknown Document' in the premise."""
        item = _make_item(name=None)
        result = self.classifier._build_inputs([item])
        self.assertIn("Unknown Document", result[0][0])

    def test_missing_author_falls_back_to_unknown(self) -> None:
        """None metadata.author is replaced with 'Unknown Author' in the premise."""
        item = _make_item(author=None)
        result = self.classifier._build_inputs([item])
        self.assertIn("Unknown Author", result[0][0])


# ---------------------------------------------------------------------------
# _escalate
# ---------------------------------------------------------------------------


class TestEscalate(unittest.TestCase):
    """Tests for Classifier._escalate."""

    def test_no_escalation_when_gap_exceeds_threshold(self) -> None:
        """Best index is unchanged when higher-ranked scores are far below."""
        # Public=0.9, Internal=0.1, Sensitive=0.05, Confidential=0.02
        scores = [0.9, 0.1, 0.05, 0.02]
        result = Classifier._escalate(scores, best_index=0, escalation_threshold=0.05)
        self.assertEqual(result, 0)

    def test_escalates_when_higher_label_within_threshold(self) -> None:
        """Index is bumped to a higher-ranked label when score gap is below threshold."""
        # Public=0.5, Internal=0.48 → gap 0.02 < threshold 0.05 → escalate to Internal
        scores = [0.5, 0.48, 0.1, 0.05]
        result = Classifier._escalate(scores, best_index=0, escalation_threshold=0.05)
        self.assertGreater(result, 0)

    def test_escalates_to_highest_within_threshold(self) -> None:
        """When multiple higher-ranked labels are within threshold, picks the highest rank."""
        # Public=0.5, Internal=0.48, Sensitive=0.47, Confidential=0.46
        scores = [0.5, 0.48, 0.47, 0.46]
        result = Classifier._escalate(scores, best_index=0, escalation_threshold=0.1)
        self.assertEqual(result, 3)  # Confidential has highest rank

    def test_already_highest_rank_no_escalation(self) -> None:
        """Confidential (rank 3) is never escalated further."""
        scores = [0.1, 0.1, 0.1, 0.9]
        result = Classifier._escalate(scores, best_index=3, escalation_threshold=1.0)
        self.assertEqual(result, 3)

    def test_zero_threshold_never_escalates(self) -> None:
        """A threshold of 0.0 means any positive gap prevents escalation."""
        scores = [0.5, 0.49, 0.1, 0.05]
        result = Classifier._escalate(scores, best_index=0, escalation_threshold=0.0)
        self.assertEqual(result, 0)


# ---------------------------------------------------------------------------
# _resolve_labels
# ---------------------------------------------------------------------------


class TestResolveLabels(unittest.TestCase):
    """Tests for Classifier._resolve_labels."""

    def setUp(self) -> None:
        self.classifier = _make_classifier(threshold=0.0)  # no escalation

    def test_returns_one_result_per_item(self) -> None:
        """_resolve_labels returns exactly one ClassificationResult per InputItem."""
        items = [_make_item(), _make_item()]
        # 2 docs × 4 labels = 8 scores
        all_scores = [0.1, 0.9, 0.2, 0.3, 0.3, 0.2, 0.1, 0.8]  # doc0 → Internal  # doc1 → Confidential
        results = self.classifier._resolve_labels(items, all_scores)
        self.assertEqual(len(results), 2)

    def test_picks_label_with_highest_score(self) -> None:
        """_resolve_labels assigns the label whose score is highest."""
        items = [_make_item(pointer="p1")]
        # Sensitive has highest score at index 2
        all_scores = [0.1, 0.2, 0.9, 0.3]
        results = self.classifier._resolve_labels(items, all_scores)
        self.assertEqual(results[0].security_class, "Sensitive")

    def test_result_contains_correct_pointer(self) -> None:
        """ClassificationResult carries the unique_pointer from item metadata."""
        items = [_make_item(pointer="my-pointer")]
        all_scores = [0.1, 0.2, 0.3, 0.9]
        results = self.classifier._resolve_labels(items, all_scores)
        self.assertEqual(results[0].unique_pointer, "my-pointer")

    def test_missing_pointer_falls_back_to_unknown(self) -> None:
        """None unique_pointer is replaced with 'Unknown Document'."""
        items = [_make_item(pointer=None)]
        all_scores = [0.9, 0.1, 0.1, 0.1]
        results = self.classifier._resolve_labels(items, all_scores)
        self.assertEqual(results[0].unique_pointer, "Unknown Document")

    def test_returns_classification_result_instances(self) -> None:
        """Every element returned is a ClassificationResult instance."""
        items = [_make_item()]
        all_scores = [0.9, 0.1, 0.1, 0.1]
        results = self.classifier._resolve_labels(items, all_scores)
        self.assertIsInstance(results[0], ClassificationResult)


# ---------------------------------------------------------------------------
# classify (async, HTTP mocked)
# ---------------------------------------------------------------------------


class TestClassify(unittest.IsolatedAsyncioTestCase):
    """Tests for Classifier.classify — HTTP layer is fully mocked."""

    def _make_mock_response(self, scores_per_pair: list[float]) -> MagicMock:
        """Build a mock httpx.Response whose .json() returns entailment predictions."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = [_entailment_response(s) for s in scores_per_pair]
        return mock_resp

    @patch("gateway.services.classifier.httpx.AsyncClient")
    async def test_returns_list_of_classification_results(self, mock_client_cls: MagicMock) -> None:
        """classify() returns a list of ClassificationResult for a valid response."""
        scores = [0.1, 0.2, 0.3, 0.9]  # one doc × 4 labels → Confidential wins
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = self._make_mock_response(scores)

        classifier = _make_classifier(threshold=0.0)
        results = await classifier.classify([_make_item()])

        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], ClassificationResult)

    @patch("gateway.services.classifier.httpx.AsyncClient")
    async def test_correct_label_assigned(self, mock_client_cls: MagicMock) -> None:
        """classify() assigns the label corresponding to the highest entailment score."""
        # Index 1 (Internal) has the highest score
        scores = [0.1, 0.9, 0.2, 0.1]
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = self._make_mock_response(scores)

        classifier = _make_classifier(threshold=0.0)
        results = await classifier.classify([_make_item(pointer="doc-1")])

        self.assertEqual(results[0].security_class, "Internal")

    @patch("gateway.services.classifier.httpx.AsyncClient")
    async def test_empty_input_returns_empty_list(self, mock_client_cls: MagicMock) -> None:
        """classify() returns an empty list when given no items."""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        classifier = _make_classifier()
        results = await classifier.classify([])

        self.assertEqual(results, [])

    @patch("gateway.services.classifier.dms_warning")
    @patch("gateway.services.classifier.httpx.AsyncClient")
    async def test_http_status_error_returns_empty_list(self, mock_client_cls: MagicMock, mock_warning: MagicMock) -> None:
        """classify() returns [] and logs a warning on HTTPStatusError."""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.side_effect = httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())

        classifier = _make_classifier()
        results = await classifier.classify([_make_item()])

        self.assertEqual(results, [])
        mock_warning.assert_called_once()

    @patch("gateway.services.classifier.dms_warning")
    @patch("gateway.services.classifier.httpx.AsyncClient")
    async def test_timeout_returns_empty_list(self, mock_client_cls: MagicMock, mock_warning: MagicMock) -> None:
        """classify() returns [] and logs a warning on TimeoutException."""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.side_effect = httpx.TimeoutException("timed out")

        classifier = _make_classifier()
        results = await classifier.classify([_make_item()])

        self.assertEqual(results, [])
        mock_warning.assert_called_once()

    @patch("gateway.services.classifier.dms_warning")
    @patch("gateway.services.classifier.httpx.AsyncClient")
    async def test_json_decode_error_returns_empty_list(self, mock_client_cls: MagicMock, mock_warning: MagicMock) -> None:
        """classify() returns [] and logs a warning on JSONDecodeError."""
        from json.decoder import JSONDecodeError

        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.side_effect = JSONDecodeError("bad json", "", 0)
        mock_client.post.return_value = mock_resp

        classifier = _make_classifier()
        results = await classifier.classify([_make_item()])

        self.assertEqual(results, [])
        mock_warning.assert_called_once()

    @patch("gateway.services.classifier.httpx.AsyncClient")
    async def test_post_called_with_correct_url(self, mock_client_cls: MagicMock) -> None:
        """classify() posts to <url>/predict."""
        scores = [0.1, 0.2, 0.3, 0.9]
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = self._make_mock_response(scores)

        classifier = _make_classifier(url="http://tei-host")
        await classifier.classify([_make_item()])

        called_url = mock_client.post.call_args[0][0]
        self.assertEqual(called_url, "http://tei-host/predict")

    @patch("gateway.services.classifier.httpx.AsyncClient")
    async def test_multiple_documents_return_correct_count(self, mock_client_cls: MagicMock) -> None:
        """classify() returns one result per input document."""
        num_docs = 3
        scores = [0.1, 0.2, 0.3, 0.9] * num_docs
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = self._make_mock_response(scores)

        classifier = _make_classifier(threshold=0.0)
        items = [_make_item(pointer=f"ptr-{i}") for i in range(num_docs)]
        results = await classifier.classify(items)

        self.assertEqual(len(results), num_docs)


if __name__ == "__main__":
    unittest.main()
