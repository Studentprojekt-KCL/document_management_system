"""Centralized prompt templates for generative models."""

CLASSIFIER_PROMPT = """Name: {name}
Author: {author}
Content: {content}

You are a security classifier. 
Classify the document into exactly one of these security levels:
  Public       (no restrictions, safe for anyone)
  Internal     (for internal use only, not for public release)
  Sensitive    (restricted, limited distribution)
  Confidential (strictly restricted, serious risk if disclosed)

Return ONLY valid JSON: {{"Security-class": "<Public|Internal|Sensitive|Confidential>"}}"""

SUMMARIZER_PROMPT = """Please provide a comprehensive, single summary based on the following batch of documents.

Documents:
{combined_context}

Unified Summary:"""