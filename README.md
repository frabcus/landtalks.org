# landtalks.org

The Land Talks website. It's built by `build.py`, which needs only Python: no
Ruby, Jekyll or anything to install.

## How it works

You edit the files here and push to `main`. A GitHub Action
(`.github/workflows/publish.yml`) then runs `build.py` and publishes the result
to GitHub Pages, usually within a minute or two. **Every push to `main` goes
live.** You can follow each run in the repo's Actions tab, and a failed build
leaves the live site as it was.

GitHub's Settings > Pages > Source must be set to "GitHub Actions".

`build.py` turns the files below into a finished site in `_site/`, which git
ignores:

| Where | What |
|---|---|
| `_talks/<evening>/<name>.md` | One talk: its text and details |
| `slides/<evening>/<name>.pdf` | That talk's slides |
| `_data/evenings.yml` | Each evening's number, month and Luma link |
| `index.html` | The home page |
| `talks/index.html` | The Talks page |
| `_layouts/`, `_includes/` | Templates: shared page parts, talk page, home page card |
| `style.css`, `images/` | Styles and pictures |
| `assets/flip.js` | The slide viewer |
| `assets/pdfjs/` | PDF.js, which the viewer uses to draw PDFs in the browser |

## Test locally

Try changes here before pushing:

```bash
python3 build.py --serve
```

Then open <http://localhost:8000/>. After editing anything, stop it with Ctrl-C
and run it again. If something is wrong with a file, the build says which one.

## Add a talk

1. Create `_talks/<evening>/<name>.md`, for example `_talks/8/beth.md`:

   ```markdown
   ---
   title: "The talk's title"
   speaker: "Beth Example"
   evening: 8
   emoji: 🌱
   hook: "One opening sentence."
   ---

   The rest of the description.
   ```

2. Put the slides at `slides/<evening>/<name>.pdf`, for example
   `slides/8/beth.pdf`. Until the PDF is there, the page shows without the
   slides and download link.

3. For a new evening, also add it to the top of `_data/evenings.yml`.

4. Test it, then push.

That one file feeds the talk's page at `/talks/8/beth/`, the home page's random
cards and the Talks page. The filename sets the web address, so don't rename a
talk once it's live. Talks within an evening are listed alphabetically by
filename.

Optional fields: `bio`, `photo` (a file in `images/speakers/`), `action_text`
and `action_url`.

## Changing templates

Templates use `{{ page.title }}` and `{% if %}`, from the Liquid template
language. `build.py` understands only the parts of Liquid the site uses, and
stops with an error on anything else, so a new template feature may need a few
lines added to it.
