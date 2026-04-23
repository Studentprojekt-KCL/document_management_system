from se_api.handlers import Handler
from unittest import TestCase, mock


class TestHandler(TestCase):
    @mock.patch("se_api.handlers.Handler.__init__", return_value=None)
    def setUp(self, _):
        self.instance = Handler()

    def test_flatten_dict_flat(self):
        result = self.instance._flatten_dict({"category1": "", "category2": "", "category3": "", "category4": ""})
        assert result == {"category1": "", "category2": "", "category3": "", "category4": ""}

    def test_flatten_dict_layers(self):
        result = self.instance._flatten_dict(
            {"category1": "", "metadata": {"category2": ""}, "subcategory": {"subsubcategory": {"category3": "", "category4": ""}}}
        )
        assert result == {"category1": "", "category2": "", "category3": "", "category4": ""}
