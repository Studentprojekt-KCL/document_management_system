"""Token counting using the model's native HuggingFace tokenizer."""

from dataclasses import dataclass

from tokenizers import Tokenizer

from shared_functions.initialisation_tools import read_env_variable, read_int_env_variable


@dataclass
class MergeLimits:
    """Token-count limits for the merge endpoint."""

    max_doc_tokens: int
    max_total_tokens: int

    @classmethod
    def from_env(cls) -> "MergeLimits":
        """Construct from STOCHAN_MERGE_MAX_DOC_TOKENS and STOCHAN_MERGE_MAX_TOTAL_TOKENS."""
        return cls(
            max_doc_tokens=read_int_env_variable("STOCHAN_MERGE_MAX_DOC_TOKENS"),
            max_total_tokens=read_int_env_variable("STOCHAN_MERGE_MAX_TOTAL_TOKENS"),
        )


class TokenCounter:
    """Counts tokens using the model's native tokenizer.

    Loads the tokenizer once at startup and reuses it for all counts.

    Attributes:
        tokenizer: The HuggingFace tokenizer instance.
    """

    def __init__(self, tokenizer_name: str) -> None:
        self.tokenizer = Tokenizer.from_pretrained(tokenizer_name)

    @classmethod
    def from_env(cls) -> "TokenCounter":
        """Construct from STOCHAN_TOKENIZER_NAME env variable."""
        return cls(tokenizer_name=read_env_variable("STOCHAN_TOKENIZER_NAME"))

    def count(self, text: str) -> int:
        """Count tokens in a single string."""
        return len(self.tokenizer.encode(text).ids)
