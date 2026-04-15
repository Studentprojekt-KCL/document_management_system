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

    # ==== ADD_FILE ====

    def test_add_file(self):
        self.instance = SearchEngine()
        self.instance.add_files([
            {
                "unique_pointer": "file/pointer/at/somewhere",
                "content": "dGhpcyBpcyBhIGZpbGU="
            }
        ])
        pointers = self.instance.query_files("this", 10)
        assert pointers == ["file/pointer/at/somewhere"]
        self.instance.add_files([
            {
                "unique_pointer": "file/pointer/at/somewhere",
                "content": "dGhpcyBpcyBhIGZpbGU="
            }
        ])
        pointers = self.instance.query_files("this", 10)
        assert pointers == ["file/pointer/at/somewhere"]
        self.instance.add_files([
            {
                "unique_pointer": "file/pointer/at/somewhere/else",
                "content": "dGhpcyBpcyBhIGZpbGU="
            }
        ])
        pointers = self.instance.query_files("this", 10)
        assert pointers == ["file/pointer/at/somewhere", "file/pointer/at/somewhere/else"]

    def test_remove_file(self):
        self.instance = SearchEngine()
        self.instance.add_files([
            {
                "unique_pointer": "file/pointer/at/somewhere",
                "content": "dGhpcyBpcyBhIGZpbGU="
            }
        ])
        self.instance.remove_file("file/pointer/at/somewhere")
        pointers = self.instance.query_files("this", 10)
        assert pointers == []
