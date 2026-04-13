from unittest import TestCase, mock

from se_api.services.classifier_cache import ClassifierCache


class TestClassifierCache(TestCase):

    @mock.patch("se_api.services.classifier_cache.ClassifierCache.__init__", return_value=None)
    def setUp(self, _):
        self.instance = ClassifierCache()
        self.instance.cache_directory = "/path"
        self.instance.cache_file = "/path/file.json"

    @mock.patch("se_api.services.classifier_cache.ClassifierCache._write_memory", return_value=None)
    def test_add_classification(self, _):
        self.instance.cache = {}
        self.instance.add_classification("pointer_1", "class")
        self.instance.add_classification("pointer_2", "class")
        assert self.instance.cache == {"pointer_1": "class", "pointer_2": "class"}

    @mock.patch("se_api.services.classifier_cache.ClassifierCache._write_memory", return_value=None)
    def test_remove_classification(self, _):
        self.instance.cache = {"pointer_1": "class", "pointer_2": "class"}
        self.instance.remove_classification("pointer_1")
        self.instance.remove_classification("pointer_2")
        assert self.instance.cache == {}

    @mock.patch("se_api.services.classifier_cache.ClassifierCache._write_memory", return_value=None)
    def test_remove_classifications(self, _):
        self.instance.cache = {"pointer_1": "class", "pointer_2": "class"}
        self.instance.remove_classifications([{"unique_pointer": "pointer_1"}, {"unique_pointer": "pointer_2"}])
        assert self.instance.cache == {}

    def test_fetch_classification(self):
        self.instance.cache = {"pointer_1": "class1", "pointer_2": "class2"}
        classification: str | None = self.instance.fetch_classification("pointer_1")
        assert classification == "class1"
        classification: str | None = self.instance.fetch_classification("pointer_3")
        assert classification == None

    @mock.patch("se_api.services.classifier_cache.ClassifierCache._write_memory", return_value=None)
    def test_reset(self, _):
        self.instance.cache = {"pointer_1": "class1", "pointer_2": "class2"}
        self.instance.reset()
        assert self.instance.cache == {}
