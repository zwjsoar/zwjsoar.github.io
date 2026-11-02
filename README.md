# Wenjun Zhu — academic website

Public website: https://zwjsoar.github.io/

Built with Quarto 1.10.18 and Python 3, deployed through a manually triggered GitHub Pages workflow. No external runtime or font service is required.

## Update content

- English biography, roles and address: `data/academic_profile.json`.
- Chinese biography and Person details: `data/person.json`.
- News: `data/news.json` (latest first when rendered).
- Paper titles, ordered authors, years, resources and abstracts: `data/papers.json`.
- Short paper descriptions: `data/paper_summaries.json`.
- Shared categories: `data/publication_topics.json`.
- Layout: `styles/`.

Edit structured data and render; generated QMD pages do not require manual HTML editing. Stable paper slugs preserve URLs when titles change.

## Preview and validate

```sh
quarto render
python3 scripts/validate.py
```

The ordinary preview excludes indexing. Local review notes are never deployed.

## Publish an update

```sh
python3 scripts/build_production.py --release
```

After reviewing the result and pushing the changes, open Actions → Academic website — manual build and optional release → Run workflow, select Publish, then run. Pushes alone do not publish. The workflow validates HTML, metadata, internal links and selected asset hashes before deployment.

The repository contains only website sources and selected public asset copies. Original materials, backups, audit records and authentication details stay outside this repository. Existing manuscript versions were approved for launch on 2 November 2026 and can be replaced later by updating the selected PDF and its SHA-256 in `data/assets.json`.

## Change hosting or domain

Update `data/deployment.json` → `site_url` and the corresponding hosting settings, then rebuild and deploy. Canonical URLs, sitemap, robots and scholarly metadata follow that URL. No custom domain is currently configured.

## Restore a release

Revert the relevant commit, then run the manual publishing workflow. Existing repository history is preserved; no force push is required.
