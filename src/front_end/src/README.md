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


### If questions 

- Ask frontend team :D
