# The 20-Watt Computer · Компьютер на 20 ваттах

**How the Brain Computes — A Quantitative Approach for Engineers**
**Как вычисляет мозг: количественный подход для инженеров**

A free textbook that treats the brain as an engineer would treat a machine:
circuits, signals, codes, learning rules, energy. Every number in the book
comes from a small, runnable simulation.

| Language | Source | PDF |
|---|---|---|
| Русский | [`ru/`](ru/) | [`ru/20-watt-computer-ru.pdf`](ru/20-watt-computer-ru.pdf) |
| English | [`en/`](en/) | in progress |
| Русский, популярная версия («коротко и просто») | [`ru/paperback/`](ru/paperback/) | `make ru-paperback` → `ru/20-watt-computer-ru-paperback.pdf` |

## Layout

- `ru/`, `en/` — one folder per language: `main.tex` + `chapters/`
- `figures/` — shared TikZ icons and data files used by every edition
- `models/` — Python models behind the book's figures and numbers
- `site/` — the interactive website with a language switcher
- `ru/solutions/` — full instructor solutions: a submodule pointing to a private repository (not needed to build the book; `git submodule update --init` works only with access)

## Build

Requires Docker (uses the `texlive/texlive` image).

    make ru          # build the Russian PDF
    make ru-paperback  # build the popular pocket-size edition (one short chapter per full chapter)
    make models      # regenerate simulation data in figures/ (acet_memory.py needs numpy)

## License

Book text, figures, exercises and PDFs: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) — free to share, teach with and translate for non-commercial use, with credit and under the same license.
Code (models, build scripts, breadboard): MIT. See [LICENSE](LICENSE).
