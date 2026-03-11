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


### If questions 

- Ask frontend team :D
