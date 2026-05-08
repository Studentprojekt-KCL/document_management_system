"""Unit tests for summarizer"""

from unittest import IsolatedAsyncioTestCase, mock

from gateway.services.summarize import Summarizer
from gateway.schemas import InputItem, MetadataTemplate


class TestSummarizer(IsolatedAsyncioTestCase):
    """Class level test for summarization."""

    @mock.patch("gateway.services.summarize.Summarizer.__init__", return_value=None)
    def setUp(self, _):
        self.instance = Summarizer()
