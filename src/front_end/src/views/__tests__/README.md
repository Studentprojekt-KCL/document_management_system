# Search Tests

## SearchView.test

- Renders all four child components
- Initial state (loading false, empty matches, drawer closed)
- Search flow: fetch call, query encoding, results passing
- Handles empty query, whitespace query, API errors, network errors
- Handles different response formats (array, {results}, {matches})
- Resets state between searches
- Match selection opens drawer with correct props
- Ignores null selection
- Drawer close event
- Filter logic: type filtering (PDF, Word, multiple), security filtering (Public, Confidential), combined filters, empty results, clear filters restores all