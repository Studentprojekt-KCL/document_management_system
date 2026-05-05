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


## Contribution Checklist

1. Keep changes small and feature-focused.
2. Reuse existing composables and utility helpers when possible.
3. Run lint before committing.
4. Update this structure document when introducing new top-level source folders.


### If questions 

- Ask frontend team :D

