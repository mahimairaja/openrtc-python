# GitHub Pages deployment

This repository deploys documentation with VitePress and GitHub Actions.

## Why GitHub Actions instead of a `gh-pages` branch?

VitePress works well with the native GitHub Pages deployment flow:

- build the site in CI
- upload the static output as an artifact
- deploy with `actions/deploy-pages`

This keeps deployment configuration inside GitHub Actions and avoids managing a
separate published branch.

## One-time repository settings

In GitHub:

1. Go to **Settings → Pages**.
2. Under **Build and deployment**, choose **GitHub Actions** as the source.
3. Confirm the published site URL matches the repository path.

For this repository, the expected project-site URL is:

```text
https://<owner>.github.io/openrtc-python/
```

## VitePress base path

Because this is a project site, the VitePress config must set:

```ts
base: '/openrtc-python/'
```

If the repository name changes, update the base path in
`docs/.vitepress/config.ts` and redeploy.

## Local docs commands

```bash
npm install
npm run docs:dev
npm run docs:build
npm run docs:preview
```
