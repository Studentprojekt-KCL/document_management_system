"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

Unit tests for the stochastic_analyzer NLI document classifier.
"""

# Tests intentionally call private helpers on Classifier for focused checks.
# pylint: disable=protected-access

import unittest
from json.decoder import JSONDecodeError
from unittest.mock import AsyncMock, MagicMock

import httpx

from gateway.schemas import ClassificationResult, InputItem, MetadataTemplate
from gateway.services.classifier import LABELS, LABEL_TRIGGERS, Classifier

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_item(
    content: str = "Some document content.",
    name: str | None = "doc.pdf",
    author: str | None = "Ali",
    pointer: str | None = "ptr-001",
) -> InputItem:
    """Return a minimal valid InputItem."""
    return InputItem(
        content=content,
        metadata=MetadataTemplate(name=name, author=author, unique_pointer=pointer),
    )


def _make_classifier(url: str = "http://tei-inference-server", threshold: float = 0.05) -> Classifier:
    """Return a Classifier with a mock async HTTP client."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    return Classifier(url=url, escalation_threshold=threshold, client=mock_client)


def _entailment_response(score: float) -> list[dict]:
    """Fake single NLI prediction response with one entailment score."""
    return [
        {"label": "entailment", "score": score},
        {"label": "contradiction", "score": 1.0 - score},
    ]


def _mock_post_response(mock_client: AsyncMock, scores: list[float]) -> None:
    """Configure mock_client.post to return entailment predictions for given scores."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = [_entailment_response(s) for s in scores]
    mock_client.post.return_value = mock_resp


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

    def test_client_is_stored(self) -> None:
        """Constructor stores the injected client."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        c = Classifier(url="http://tei-inference-server", escalation_threshold=0.05, client=mock_client)
        self.assertIs(c.client, mock_client)

    def test_class_level_defaults_are_valid(self) -> None:
        """Class-level constants exist and have sensible values."""
        self.assertGreater(Classifier.max_chars, 0)
        self.assertGreater(Classifier.batch_size, 0)
        self.assertGreater(Classifier.timeout, 0.0)


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
        scores = [0.9, 0.1, 0.05, 0.02]
        result = Classifier._escalate(scores, best_index=0, escalation_threshold=0.05)
        self.assertEqual(result, 0)

    def test_escalates_when_higher_label_within_threshold(self) -> None:
        """Index is bumped to a higher-ranked label when score gap is below threshold."""
        scores = [0.5, 0.48, 0.1, 0.05]
        result = Classifier._escalate(scores, best_index=0, escalation_threshold=0.05)
        self.assertGreater(result, 0)

    def test_escalates_to_highest_within_threshold(self) -> None:
        """When multiple higher-ranked labels are within threshold, picks the highest rank."""
        scores = [0.5, 0.48, 0.47, 0.46]
        result = Classifier._escalate(scores, best_index=0, escalation_threshold=0.1)
        self.assertEqual(result, 3)

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
        all_scores = [0.1, 0.9, 0.2, 0.3, 0.3, 0.2, 0.1, 0.8]
        results = self.classifier._resolve_labels(items, all_scores)
        self.assertEqual(len(results), 2)

    def test_picks_label_with_highest_score(self) -> None:
        """_resolve_labels assigns the label whose score is highest."""
        items = [_make_item(pointer="p1")]
        all_scores = [0.1, 0.2, 0.9, 0.3]  # index 2 → Sensitive
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
# classify (async, client injected and mocked)
# ---------------------------------------------------------------------------


class TestClassify(unittest.IsolatedAsyncioTestCase):
    """Tests for Classifier.classify — injected client is fully mocked."""

    async def test_returns_list_of_classification_results(self) -> None:
        """classify() returns a list of ClassificationResult for a valid response."""
        classifier = _make_classifier(threshold=0.0)
        _mock_post_response(classifier.client, [0.1, 0.2, 0.3, 0.9])

        results = await classifier.classify([_make_item()])

        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], ClassificationResult)

    async def test_correct_label_assigned(self) -> None:
        """classify() assigns the label corresponding to the highest entailment score."""
        classifier = _make_classifier(threshold=0.0)
        _mock_post_response(classifier.client, [0.1, 0.9, 0.2, 0.1])  # index 1 → Internal

        results = await classifier.classify([_make_item(pointer="doc-1")])

        self.assertEqual(results[0].security_class, "Internal")

    async def test_empty_input_returns_empty_list(self) -> None:
        """classify() returns an empty list when given no items."""
        classifier = _make_classifier()

        results = await classifier.classify([])

        self.assertEqual(results, [])
        classifier.client.post.assert_not_called()

    async def test_http_status_error_returns_empty_list(self) -> None:
        """classify() returns [] and logs a warning on HTTPStatusError."""
        classifier = _make_classifier()
        classifier.client.post.side_effect = httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())

        with unittest.mock.patch("gateway.services.classifier.dms_warning") as mock_warning:
            results = await classifier.classify([_make_item()])

        self.assertEqual(results, [])
        mock_warning.assert_called_once()

    async def test_timeout_returns_empty_list(self) -> None:
        """classify() returns [] and logs a warning on TimeoutException."""
        classifier = _make_classifier()
        classifier.client.post.side_effect = httpx.TimeoutException("timed out")

        with unittest.mock.patch("gateway.services.classifier.dms_warning") as mock_warning:
            results = await classifier.classify([_make_item()])

        self.assertEqual(results, [])
        mock_warning.assert_called_once()

    async def test_json_decode_error_returns_empty_list(self) -> None:
        """classify() returns [] and logs a warning on JSONDecodeError."""
        classifier = _make_classifier()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.side_effect = JSONDecodeError("bad json", "", 0)
        classifier.client.post.return_value = mock_resp

        with unittest.mock.patch("gateway.services.classifier.dms_warning") as mock_warning:
            results = await classifier.classify([_make_item()])

        self.assertEqual(results, [])
        mock_warning.assert_called_once()

    async def test_post_called_with_correct_url(self) -> None:
        """classify() posts to <url>/predict."""
        classifier = _make_classifier(url="http://tei-host", threshold=0.0)
        _mock_post_response(classifier.client, [0.1, 0.2, 0.3, 0.9])

        await classifier.classify([_make_item()])

        called_url = classifier.client.post.call_args[0][0]
        self.assertEqual(called_url, "http://tei-host/predict")

    async def test_multiple_documents_return_correct_count(self) -> None:
        """classify() returns one result per input document."""
        num_docs = 3
        classifier = _make_classifier(threshold=0.0)
        _mock_post_response(classifier.client, [0.1, 0.2, 0.3, 0.9] * num_docs)

        items = [_make_item(pointer=f"ptr-{i}") for i in range(num_docs)]
        results = await classifier.classify(items)

        self.assertEqual(len(results), num_docs)

    async def test_post_called_with_inputs_payload(self) -> None:
        """classify() sends the NLI pairs under the 'inputs' key."""
        classifier = _make_classifier(threshold=0.0)
        _mock_post_response(classifier.client, [0.1, 0.2, 0.3, 0.9])

        await classifier.classify([_make_item()])

        call_kwargs = classifier.client.post.call_args[1]
        self.assertIn("inputs", call_kwargs["json"])

    async def test_post_called_with_correct_timeout(self) -> None:
        """classify() forwards the configured timeout to the HTTP call."""
        classifier = _make_classifier(threshold=0.0)
        _mock_post_response(classifier.client, [0.1, 0.2, 0.3, 0.9])

        await classifier.classify([_make_item()])

        call_kwargs = classifier.client.post.call_args[1]
        self.assertEqual(call_kwargs["timeout"], Classifier.timeout)
