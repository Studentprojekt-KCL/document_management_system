# Frontend Source code Structure

Describtion of the frotend code (`./front_end/src/`) structure 

## Folder layout

- `main.js` — App entry point; mounts Vue app and wires router/global styles.
- `App.vue` — Root component wrapper.
- `style.css` — Global styles that are shared across views/components.
- `assets/` — Static frontend assets used by Vue components, currently just the company logo and DMS pic.
- `components/` — Reusable UI building blocks (e.g., `Header.vue`, `Footer.vue`, `Sidebar.vue`, search widgets). This will contain more as we continue to deveolp
- `layouts/` — Page shell composition (top-level layout wrapper that assemble common components). Currently this only contain one file (`MainLayout.vue`) which combines the `Header.vue`, `Footer.vue`, `Sidebar.vue`.
- `router/` — Route definitions and navigation setup. This is the code that help su to redirect to new pages.
- `views/` — Route-level pages (e.g., `SearchView.vue`, `SourcesView.vue`, `ComplianceView.vue`, `SettingsView.vue`).

## Architecture guideline

- Keep **reusable UI** in `components/`.
- Keep **page scaffolding** in `layouts/`.
- Keep **URL-mapped pages** in `views/`.
- Keep routing logic centralized in `router/index.js`.

## Naming conventions

- Please use `PascalCase` for Vue SFC files (e.g., `MainLayout.vue`, `SearchFiltersCard.vue`).
- Use descriptive names that reflect role (`MainLayout`, `SettingsView`, `SearchBar`, etc).

## When adding new code

- New reusable element -> `components/`
- New route page -> `views/`
- New app-wide frame/layout -> `layouts/`
- New route mapping -> update `router/index.js`

## Testing

### Setup

Tests use **Vitest** + **Vue Test Utils** with `jsdom` as the DOM environment.

Install dependencies:
```bash
npm install -D vitest @vue/test-utils jsdom
```

Run all tests:
```bash
npm run test
```

Run tests in watch mode:
```bash
npm run test:watch
```

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
| Composables | `useSearchMetadata.test.js`   |   51  |
| Composables | `useFilters.test.js`          |   14  |
| Components  | `SearchBar.test.js`           |   16  |
| Components  | `SearchMatches.test.js`       |   18  |
| Components  | `ClassificationEditor.test.js`|   19  |
| Components  | `SearchPreviewDrawer.test.js` |   27  |
| Views       | `SearchView.test.js`          |   29  |
| **Total**   | |         **192**                     |

### If questions

- Ask frontend team :D
### If questions 

- Ask frontend team :D
