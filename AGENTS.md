# Repository Guidelines

## Project Structure & Module Organization
This repository is intentionally small and currently stores image assets only.

- `assets/`: canonical image set (`books_01.jpeg` through `books_20.jpeg`).
- Repository root: lightweight documentation files such as this guide.

Keep new content organized by type. If scripts are introduced later, place them in a dedicated `scripts/` directory instead of mixing them into `assets/`.

## Build, Test, and Development Commands
There is no build pipeline in this repository. Use lightweight validation commands when updating assets:

- `find assets -type f -name '*.jpeg' | wc -l`  
  Confirms expected image count.
- `file assets/books_01.jpeg`  
  Verifies file type/encoding.
- `sips -g pixelWidth -g pixelHeight assets/books_01.jpeg` (macOS)  
  Checks image dimensions.

Run these checks before opening a PR when adding, replacing, or renaming images.

## Coding Style & Naming Conventions
Use consistent, predictable naming for assets:

- Pattern: `books_XX.jpeg` (two-digit, zero-padded index).
- Use lowercase and underscores only.
- Avoid spaces and mixed extensions (`.jpg` vs `.jpeg`).

For Markdown docs, use clear headings, short sections, and actionable instructions.

## Agent-Specific Instructions
- Shell preference: use `fish` for repository task commands and `just` recipes.
- Avoid `zsh`-specific command syntax in docs, scripts, and examples.
- Execute project tasks through `just` recipes whenever possible, instead of running raw commands directly.
- Never execute Python code as an inline command string (for example, `python -c` or heredoc snippets). If Python is needed, create a script file and run it.

## Testing Guidelines
Testing is file-integrity based rather than unit-test based.

- Ensure every image opens correctly and is a valid JPEG.
- Confirm naming sequence has no gaps or duplicates.
- If replacing an existing image, keep filename stable unless renaming is intentional and documented.

## Commit & Pull Request Guidelines
Git history is not available in this exported folder, so follow a clear, conventional format:

- Commit message style: `<scope>: <imperative summary>`.
- Commit messages must always be written in Spanish.  
  Examples: `assets: agrega books_21.jpeg`, `docs: actualiza la guia de contribucion`.
- PRs should include:
  - What changed and why.
  - A list of added/removed/renamed files.
  - Any quality checks run (type, dimensions, count).
  - Licensing/source notes for newly introduced images.
