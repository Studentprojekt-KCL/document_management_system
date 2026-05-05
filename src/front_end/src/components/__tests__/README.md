# Component Test

## ClassificationEditor.test.js — 19 tests

- Renders and hides modal based on visible prop.
- Displays modal title, description, and all four security level options.
- Pre-selects current level upon opening.
- Selects and deselects levels via click; applies corresponding color classes.
- Save function emits selected level; disables and blocks save when no level is selected.
- Save button displays "Saving..." state upon click.
- Cancel function emits via button and backdrop click; ignores modal body clicks.
- Exposes resetSaving() method to revert button state.
- Syncs to new currentLevel upon modal re-opening.

## SearchPreviewDrawer.test.js — 20 tests

- Renders drawer and backdrop; applies open class based on prop.
- Emits close event via backdrop click or X button.
- Displays metadata: preview title, file description tag, created date, file size, and security class.
- Security section: Displays classification badge; conditionally renders edit button based on admin role.
- Opens ClassificationEditor upon edit button click.
- Renders footer link to open file in external source.
- Displays "Generate AI Summary" button when summary is absent.
- Displays "Find Similar Files" button when rerank results are absent.
- State reset: Hides classification editor and notifications upon selectedFile change.

## SearchBar.test.js — 16 tests

- Renders search input, button, and icon.
- Toggles placeholder text based on loading state.
- Disables input and button during loading state.
- Disables button for empty or whitespace-only inputs; enables on valid text.
- Emits search event with trimmed query and documentsOnly: true on form submit or Enter key.
- Blocks search emit on empty or whitespace queries.
- Clears input field upon successful search submission.
- Processes and emits multiple sequential searches.

## SearchMatches.test.js — 23 tests

- Renders list of result items and match titles.
- Conditionally displays "Searching…", result count labels (singular/plural), or "No results" message.
- Hides result count when loading or when query is empty.
- Default mode: Emits select with raw match data on card click; applies active class to selected card.
- Selectable mode: Blocks default select emit; emits update:selectedPointers to add/remove pointers; applies selected class.
- Badge mode (security): Displays security class text and corresponding CSS class; defaults to "Unknown" if missing.
- Badge mode (score): Displays score percentage; defaults to "N/A" if missing.
- Renders external links with target="_blank" and stops click propagation to prevent card selection.
