# Views Tests

## SearchView - 23 tests

- Rendering
  - Instantiates child components: SearchBar, SearchFiltersCard, SearchMatches, SearchPreviewDrawer
  - Validates initial state: loading disabled, empty match array, drawer closed

- Search Flow
  - Executes fetch payload containing input query
  - Rejects empty or whitespace-only queries
  - Maps standard array or nested object response structures (results, matches) to component state
  - Traps API and network errors, defaulting to empty match arrays
  - Purges component state prior to sequential search execution

- Match Selection
  - Toggles drawer visibility upon match selection
  - Injects target match data into drawer props
  - Executes drawer termination on close event

- Filtering Logic
  - Evaluates and filters dataset by file extension
  - Evaluates and filters dataset by security classification
  - Executes composite evaluations combining extension and classification metrics
  - Yields empty state if no matches pass filter logic
  - Restores complete dataset upon filter clearance

## MergeFilesView - 14 tests

- Rendering
  - Validates populated state: renders title, target filename header, and SearchMatches component parameters (selectable=true, badgeMode="score")
  - Pre-selects primary source pointer in active array
  - Suppresses file list and action button rendering if rerank results array is empty

- Selection Tracking
  - Computes array length to display selected file count
  - Applies singular or plural string formatting correlating to selection delta

- Execution Logic (Merge & Summarize)
  - Triggers generateAISummary utilizing selected pointer arrays
  - Disables execution button during active generation state
  - Disables execution button if selection array reaches zero
  - Overrides button text to display "Generating summary..." during active generation

- Output Presentation
  - Suppresses summary container if HTML generation is empty
  - Binds generated HTML directly to markdown output block
  - Renders specific error string if summaryError state populates
