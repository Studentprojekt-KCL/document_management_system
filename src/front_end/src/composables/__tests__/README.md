# Composables Tests

## useAIRerank.js — 12 tests

- Returns all expected reactive keys and methods.
- aiRerankResultsComputed filters results to match the current rerankPointer.
- generateAIRerank (Success):
  - Sends POST request to /api/rerank with correct pointer payload.
  - Toggles isReranking state during fetch.
  - Maps API response to include rank and formatted scorePercent.
  - Stores rerankPointer and rerankFilename upon success.
  - Clears rerankError on successful fetch.

- generateAIRerank (Error):
  - Sets rerankError on non-ok HTTP responses.
  - Sets rerankError on network failures.
  - Resets isReranking state after errors.

- generateAIRerank (No Pointer):
  - Resets state and aborts fetch if no uniquePointer is available.

- Edge Cases:
  - Handles missing ranked_results gracefully.
  - Defaults null scores to 0.

## useAISummary.js — 21 tests

- Returns all expected reactive keys and methods.
- aiSummaryHtml computed property returns HTML only when summaryPointer matches uniquePointer.
- generateAISummary (Single/Default):
  - Sends POST request to /api/summarize with the current uniquePointer.
  - Toggles isGeneratingSummary state during fetch.
  - Parses markdown to HTML using globalThis.marked.

- generateAISummary (Multiple Pointers):
  - Merges and deduplicates provided pointers with sourcePointer.
  - Filters out empty or whitespace-only pointers.
  - Falls back to uniquePointer if the provided pointer array is empty.

- generateAISummary (Response Handling):
  - Processes non-JSON (text/plain) responses by reading raw text.

- generateAISummary (Errors):
  - Sets summaryError on non-ok HTTP responses.
  - Sets summaryError on network failures.
  - Resets isGeneratingSummary state after errors.

- generateAISummary (No Pointers):
  - Resets state and aborts fetch if no valid pointers are found.

- Edge Case:
  - Falls back to rendering raw text if globalThis.marked is unavailable.

## useAuthSession.js — 20 tests

- Initialization: Attempts to become leader on mount and sets leader if successful.
- Activity Tracking: Registers window event listeners (mousemove, keydown, click, scroll) on mount and broadcasts activity on user interaction. Registers storage listener for cross-tab logout sync.
- Cleanup: Removes all event listeners on unmount.
- Watchdog: Tries to become leader if the current leader is detected as dead; ignores if leader is alive.
- Leader Loop:
  - Refreshes token if expired and user is active.
  - Triggers logout and broadcasts logout event if user is inactive.
  - Does nothing if not the leader or if no token exists.
  - Logs out if token refresh fails.
  - Proactively refreshes the token before expiration.
- Logout Sync: Redirects to / when a logout event is detected from another tab via storage events.

## useSearchMetadata.js — 25 tests

- Pure Functions:
  - resolveFilename: Returns metadata name, fallback name, or indexed default.
  - resolveDocumentType: Returns metadata or entry-level type description.
  - resolveDocumentExtension: Returns metadata or entry-level file extension.
  - resolveSource: Returns metadata or entry-level source system.
  - resolveDateOnly: Extracts date portion from ISO strings or falls back to metadata.
  - resolveLink: Returns metadata or entry-level clickable URL.
  - resolveSecurityClass: Returns metadata or entry-level security classification.
- Composable Computed Properties:
  - Returns all mapped fields correctly from a provided selectedMatch (e.g., title, size, description, date, source, link, pointer).
  - Returns empty strings or defaults when selectedMatch is null.
- normalizeMatches:
  - Normalizes an array of match objects to extract titles and map missing data.
  - Preserves the original raw match reference.
  - Assigns indexed filenames for missing names.
  - Returns empty arrays for empty or undefined inputs.

## useFilters.js — 16 tests

- useSourceFilters:
  - Initializes with an empty array.
  - Fetches data from /api/connector/connected_source_systems.
  - Populates ref on successful fetch.
  - Retains empty array on non-ok responses or network errors (logs errors).
  - Creates a new, unshared ref on each call.
- useSecurityFilters:
  - Initializes with an empty array.
  - Fetches data from /api/stochastic-analyzer/classifications.
  - Populates ref on successful fetch.
  - Retains empty array on non-ok responses or network errors.
  - Logs specific error messages for failed fetches.
  - Creates a new, unshared ref on each call.
