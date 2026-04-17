from unittest import TestCase, mock

from se_api.services.classifier_cache import ClassifierCache


class TestClassifierCache(TestCase):

    @mock.patch("se_api.services.classifier_cache.ClassifierCache.__init__", return_value=None)
    def setUp(self, _):
        self.instance = ClassifierCache()
        self.instance.cache_file = "/path"
        self.instance.cache_file = "/path/file.json"

    def test_add_classification(self):
        self.instance.cache = {}
        self.instance.add_classification("pointer_1", "class")
        self.instance.add_classification("pointer_2", "class")
        assert self.instance.cache == {"pointer_1": "class", "pointer_2": "class"}

    def test_remove_classification(self):
        self.instance.cache = {"pointer_1": "class", "pointer_2": "class"}
        self.instance.remove_classification("pointer_1")
        self.instance.remove_classification("pointer_2")
        assert self.instance.cache == {}

    def test_remove_classifications(self):
        self.instance.cache = {"pointer_1": "class", "pointer_2": "class"}
        self.instance.remove_classifications([{"unique_pointer": "pointer_1"}, {"unique_pointer": "pointer_2"}])
        assert self.instance.cache == {}

    def test_fetch_classification(self):
        self.instance.cache = {"pointer_1": "class1", "pointer_2": "class2"}
        classification: str | None = self.instance.fetch_classification("pointer_1")
        assert classification == "class1"
        classification: str | None = self.instance.fetch_classification("pointer_3")
        assert classification == None
