from unittest import TestCase, mock

from se_api.services.search_engine import SearchEngine


class TestSearchEngine(TestCase):
    @mock.patch("se_api.services.connector.Connector.__init__", return_value=None)
    def setUp(self, _):
        self.instance = SearchEngine()
        self.instance.categories = ["category1", "category2", "category3"]

    # ==== HAVE_NEW_CATEGORY ====

    def test_have_new_category_one_layer_false(self):
        result = self.instance.have_new_category({"category1": "", "category2": "", "category3": ""})
        assert result == False

    def test_have_new_category_several_layers_false(self):
        result = self.instance.have_new_category(
            {"category1": "", "metadata": {"category2": ""}, "subcategory": {"subsubcategory": {"category3": ""}}}
        )
        assert result == False

    def test_have_new_category_one_layer_true(self):
        result = self.instance.have_new_category({"category1": "", "category2": "", "category3": "", "category4": ""})
        assert result == True

    def test_have_new_category_several_layers_true(self):
        result = self.instance.have_new_category(
            {"category1": "", "metadata": {"category2": ""}, "subcategory": {"subsubcategory": {"category3": "", "category4": ""}}}
        )
        assert result == True

    # ==== _FLATTEN_DICT ====

    def test_flatten_dict_flat(self):
        result = self.instance._flatten_dict({"category1": "", "category2": "", "category3": "", "category4": ""})
        assert result == {"category1": "", "category2": "", "category3": "", "category4": ""}

    def test_flatten_dict_layers(self):
        result = self.instance._flatten_dict(
            {"category1": "", "metadata": {"category2": ""}, "subcategory": {"subsubcategory": {"category3": "", "category4": ""}}}
        )
        assert result == {"category1": "", "category2": "", "category3": "", "category4": ""}
