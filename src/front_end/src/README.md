# Frontend Source code Structure

This folder (`./front_end/src/`) contains the frotend code for the application. 

## Folder layout

- `main.js`: Entry point that creates and mounts the Vue app.
- `App.vue`: Root application component wrapper.
- `style.css`: Global styles that are shared across views/components.
- `assets/`: Static frontend assets used in the UI, eg. the company logo and DMS pic.
- `components/`: Reusable building blocks and feature components. (e.g., `Header.vue`, `Footer.vue`, `Sidebar.vue`, search widgets).
- `composables/`: Reusable stateful logic (for example metadata, AI summary, rerank).
- `layouts/`: Page shell composition (top-level layout wrapper that assemble common components). Currently this only contain one file (`MainLayout.vue`) which combines the `Header.vue`, `Footer.vue`, `Sidebar.vue`.
- `router/`: Route configuration and navigation guards. This is the code that help us to redirect to new pages.
- `utils/`: Shared utility functions (for example API and auth helpers).
- `views/`: Route-level pages (e.g., `SearchView.vue`, `SourcesView.vue`, `ComplianceView.vue`, `SettingsView.vue`).


## Architecture guideline

- Keep **reusable UI** in `components/`.
- Keep **URL-mapped pages** in `views/`.
- Put cross-component logic in `composables/`.
- Put pure helpers in `utils/`.
- Keep route declarations and guards in `router/`.


## Naming conventions

- Use `PascalCase` for Vue Single File Components (e.g., `MainLayout.vue`, `SearchFiltersCard.vue`).
- Use descriptive names that reflect intent and scope (e.g. `MainLayout`, `SettingsView`, `SearchBar` ).
- Keep composable and utils names in camelCase (e.g. `useFilters.js` etc.).


## When adding new code

- New reusable element -> `components/`
- New route page -> `views/`
- New app-wide frame/layout -> `layouts/`
- New route mapping -> update `router/index.js`

## Testing

### Setup

Tests use **Vitest** + **Vue Test Utils** with `jsdom` as the DOM environment.

Install dependencies:
``` npm install -D vitest @vue/test-utils jsdom ```

Run all tests:
``` npm run test ```

Run tests in watch mode:
``` npm run test:watch ```

### Test file locations

Test files live in `__tests__/` folders next to the code they test:

### Writing new tests

- Place test files in the `__tests__/` folder next to the source file.
- Name test files `ComponentName.test.js` (matching the source file name).
- Mock `window.__ENV__` values in `test-setup.js` — they apply to all tests automatically.
- Mock composables and child components using `vi.mock()` to isolate the unit under test.
- Use `flushPromises()` from `@vue/test-utils` for async operations.
- Use `vi.hoisted()` when a mock variable is referenced inside a `vi.mock()` factory.

### Current coverage

|     Area    |           File                | Tests |
|-------------|-------------------------------|-------|
| Utils       | `auth.test.js`                |   18  |
| Utils       |  `api.test.js`                |   13  |
| Utils       |  `authSync.test.js`           |   15  |
| Utils       |  `config.test.js`             |   12  |
| Composables | `useSearchMetadata.test.js`   |   51  |
| Composables | `useFilters.test.js`          |   14  |
| Composables | `useAIRerank.test.js`         |   11  |
| Composables | `useAISummary.test.js`        |   12  |
| Composables | `useAuthSession.test.js`      |   12  |
| Composables | `useReload.test.js`           |   10  |
| Components  | `SearchBar.test.js`           |   16  |
| Components  | `SearchMatches.test.js`       |   23  |
| Components  | `ClassificationEditor.test.js`|   19  |
| Components  | `SearchPreviewDrawer.test.js` |   20  |
| Views       | `SearchView.test.js`          |   23  |
| Views       | `MergeFilesView.test.js`      |   14  |
| **Total**   | |         **260**                     |

### If questions
## Contribution Checklist

1. Keep changes small and feature-focused.
2. Reuse existing composables and utility helpers when possible.
3. Run lint before committing.
4. Update this structure document when introducing new top-level source folders.


### If questions 

- Ask frontend team :D

