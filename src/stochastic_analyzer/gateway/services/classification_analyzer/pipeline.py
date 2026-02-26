"""Qwen3 generative classification pipeline."""

import json
from typing import List, Optional

import torch
from pydantic import ValidationError
from transformers import AutoModelForCausalLM, AutoTokenizer

from schemas import ClassificationResult, InputItem

_SYSTEM_PROMPT = """You are a document security classifier.
Classify the document into exactly one of these security levels:
  Public       (no restrictions, safe for anyone)
  Internal     (for internal use only, not for public release)
  Sensitive    (restricted, limited distribution)
  Confidential (strictly restricted, serious risk if disclosed)

You must respond with ONLY valid JSON in this exact format:
{"Security-class": "<Public|Internal|Sensitive|Confidential>"}

Do not include any explanation, markdown, or extra text."""

_USER_PROMPT_TEMPLATE = """Document metadata:
  Name:    {name}
  Author:  {author}
  Version: {version}

Document content:
{content}

Classify this document."""


class QwenClassificationPipeline:
    """Loads a Qwen3 generative model and classifies documents into security levels."""

    def __init__(self, model_path: str = "Qwen/Qwen3-0.6B", device: str = "cuda") -> None:
        """Initialise the tokenizer and model, moving to the appropriate device."""
        self.device = device if torch.cuda.is_available() else "cpu"
        print(f"Loading pipeline on {self.device}...")

        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
        )
        self.model.to(self.device)
        self.model.eval()
        print("Pipeline ready.")

    def _build_prompt(self, item: InputItem) -> str:
        """Format the classification prompt for a single validated item."""
        return _USER_PROMPT_TEMPLATE.format(
            name=item.metadata.name or "Unknown",
            author=item.metadata.author or "Unknown",
            version=item.metadata.version or "Unknown",
            content=item.content,
        )

    def _generate(self, prompt: str) -> Optional[str]:
        """Run a single prompt through the model and return the raw text output."""
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        input_ids = self.tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
        ).to(self.device)

        with torch.no_grad():
            output_ids = self.model.generate(
                input_ids,
                max_new_tokens=32,
                do_sample=False,
                temperature=None,
                top_p=None,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        new_tokens = output_ids[0][input_ids.shape[-1] :]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    def _parse_response(self, raw: str, name: Optional[str]) -> Optional[ClassificationResult]:
        """Parse the model's JSON response into a ClassificationResult, or None if malformed."""
        try:
            clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(clean)
            security_class = str(data["Security-class"]).strip()
            return ClassificationResult(
                name=name,
                **{"Security-class": security_class},
            )
        except (json.JSONDecodeError, KeyError, ValueError, ValidationError) as e:
            print(f"Failed to parse model response: '{raw}' — {e}")
            return None

    def process(self, raw_data: List[dict]) -> List[Optional[ClassificationResult]]:
        """Validate, classify, and return results for a batch of raw input dicts."""
        print(f"\n--- Validating {len(raw_data)} inputs ---")

        results: list[Optional[ClassificationResult]] = []

        for i, item in enumerate(raw_data):
            try:
                validated = InputItem(**item)
            except ValidationError as e:
                print(f"REJECTED item #{i}: {e.errors()[0]['msg']}")
                results.append(None)
                continue

            print(f"Classifying item #{i}: '{validated.metadata.name}'...")
            prompt = self._build_prompt(validated)
            raw_response = self._generate(prompt)

            if raw_response is None:
                print(f"  → No response generated for item #{i}.")
                results.append(None)
                continue

            result = self._parse_response(raw_response, validated.metadata.name)
            if result:
                print(f"  → {result.model_dump(by_alias=True)}")
            results.append(result)

        return results
