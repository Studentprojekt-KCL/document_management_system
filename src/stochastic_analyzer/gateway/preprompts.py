"""Centralized prompt templates for generative models."""

SUMMARIZER_PROMPT = """Please provide a comprehensive, single summary based on the following batch of documents.

Documents:
{combined_context}

Unified Summary:"""