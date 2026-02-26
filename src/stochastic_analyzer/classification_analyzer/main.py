"""Entry point for the Qwen3 document classification pipeline."""

from pipeline import QwenClassificationPipeline

TEST_DATA = [
    {
        "content": "This is our public press release announcing the new product launch.",
        "metadata": {"name": "Press Release", "author": "Marketing", "version": "1.0"},
    },
    {
        "content": "Internal memo: please update your timesheets by end of Friday.",
        "metadata": {"name": "HR Memo", "author": "HR", "version": "1.0"},
    },
    {
        "content": "Q3 financial projections and regional sales targets for leadership review.",
        "metadata": {"name": "Q3 Projections", "author": "Finance", "version": "2.1"},
    },
    {
        "content": "Merger negotiation terms and acquisition target details. Do not distribute.",
        "metadata": {"name": "M&A Brief", "author": "Legal", "version": "1.0"},
    },
    # BAD: missing required metadata key
    {
        "content": "Some document.",
        "metadata": {"name": "Doc X", "author": "Admin"},
    },
]


def main() -> None:
    """Run the classification pipeline against the test data and print results."""
    pipeline = QwenClassificationPipeline()
    results = pipeline.process(TEST_DATA)

    print("\n--- Results ---")
    for result in results:
        if result:
            print(result.model_dump(by_alias=True))
        else:
            print("None")


if __name__ == "__main__":
    main()
