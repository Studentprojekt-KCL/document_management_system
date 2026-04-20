# Component Test

## ClassificationEditor.test.js — 16 tests

- Renders/hides modal based on visible prop
- Renders all four security levels
- Pre-selects current level on open
- Click to select/deselect levels
- Correct color classes per level
- Save emits with selected level
- Save blocked when nothing selected
- Save button shows "Saving..." state
- Cancel via button and backdrop click
- resetSaving() exposed method works
- Re-syncs to new level when re-opened

## SearchPreviewDrawer.test.js — 22 tests

- Drawer open/close rendering and backdrop
- Title, type tag, header text
- Metadata cells (created, size, format, security)
- Edit button visible for admin, hidden for non-admin
- Opens ClassificationEditor on edit click
- Close via button and backdrop
- Open file link with correct href
- AI summary button present
- Save flow: correct API call, success toast, error toast, network error toast
- Editor closes after successful save
- State resets on document change and drawer close

## SearchBar.test.js — 16 tests

- Renders input, button, icon
- Placeholder changes when loading
- Input disabled when loading
- Button disabled when empty, whitespace, or loading
- Button enabled when text entered
- Emits search with trimmed query on submit
- Emits on Enter key
- Does not emit on empty/whitespace
- Clears input after successful search
- Can emit multiple searches in sequence

## SearchMatches.test.js — 18 tests

- Loading state shows "Searching…"
- No results message with query text
- Empty state when no query
- Renders correct number of cards
- Results count singular/plural
- Displays title, type, date, source for each match
- Security badges with correct text and color classes
- Click emits select with raw match data
- Highlights selected card with active class
- Handles matches with missing fields
- Shows "Unknown" for missing security class
