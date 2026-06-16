# Views Tests

## SearchView - 25 tests

- Rendering
  - Renders all child components: SearchBar, SearchFiltersCard, SearchMatches, SearchPreviewDrawer
  - Validates initial state: loading disabled, empty match array, drawer closed
- Search Flow
  - Fetches results and sends query in request body on search event
  - Passes results and query to SearchMatches
  - Rejects empty or whitespace-only queries
  - Handles API error and network error responses
  - Handles nested response structures (results, matches properties)
  - Resets preview state before each new search
- Match Selection
  - Opens drawer and passes selected match data on select event
- Drawer Close
  - Closes drawer on close event
- Filtering
  - Shows all results when no filters active
  - Filters by file type extension, security classification, and combined criteria
  - Returns empty when no matches pass filters
  - Restores all results when filters cleared

## MergeFilesView - 25 tests

- Rendering (with results)
  - Displays page title and rerank filename
  - Passes rerank results, selectable=true, badgeMode="score" to SearchMatches
  - Pre-selects the rerank pointer
- Rendering (no results)
  - Hides matches and actions when results are empty
- Selection Counter
  - Shows selected file count with singular/plural formatting
- Merge + Generate PDF Button
  - Triggers generatePDF with pointers on click
  - Disabled during generation or when nothing selected
  - Shows "Generating PDF..." during generation
  - Shows download/preview links after generation
  - Shows error message on failure
- Summarize Button
  - Triggers generateAISummary with pointers on click
  - Disabled during generation
  - Shows "Generating summary..." during generation
  - Shows error message on failure
- Summary Result Display
  - Shows/hides summary section based on aiSummaryHtml
  - Renders HTML content in summary-markdown block
- Merged Result Display
  - Shows/hides merged section based on mergedHtmlRaw
  - Renders HTML content when available

## AuthCallbackView - 8 tests

- Shows "Signing you in…" heading
- Displays OAuth error from query params (error + error_description)
- Shows error when no authorization code in query
- Shows error on state mismatch (OIDC CSRF check)
- Shows error when PKCE verifier is missing from localStorage
- Calls exchangeAuthorizationCode with code + verifier, then redirects to /search on success
- Shows login failure message when exchange fails
- Calls logout via setTimeout after 3s when post-login auth check fails

## LoginView - 6 tests

- Renders page title and sign-in button
- Disables button and shows "Signing in..." while loading
- Stores PKCE verifier in localStorage via SESSION_KEY_PKCE_VERIFIER
- Stores OIDC state in localStorage via SESSION_KEY_OIDC_STATE
- Calls createPkcePair and generateState from pkce utils
- Redirects to correct Keycloak authorization URL with all OIDC params (client_id, redirect_uri, response_type, scope, state, code_challenge, code_challenge_method=S256)

## ErrorStatusView - 6 tests

- Renders error code, title, and description from props
- Shows "Go to login" button for 401 errors
- Shows "Go back to previous page" for non-401 errors (403, 500, etc.)
- Calls router.push('/') on 401 button click
- Calls router.back() on non-401 button click
- Works with string error codes

## SessionCallbackView - 6 tests

- Shows "Signing in..." text
- Redirects to /login when code or state is missing from query
- Calls apiFetch with POST and form-encoded code/state
- Redirects to /connections on successful response
- Does not redirect when response is not ok (400)
- Does not redirect on network error
