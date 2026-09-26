# Build the book in each language. Sources live in <lang>/main.tex + <lang>/chapters/;
# figures/ (TikZ data, icons) and models/ (Python simulations) are shared by all languages.
DOCKER = docker run --rm -v "$(CURDIR)":/w -e TEXINPUTS=/w/$(1):/w: -w /w/$(1) texlive/texlive \
         pdflatex -interaction=nonstopmode -jobname=20-watt-computer-$(1) main.tex

.PHONY: all ru en ru-paperback models clean
all: ru

ru en:
	$(call DOCKER,$@) >/dev/null
	$(call DOCKER,$@) >/dev/null
	@grep -a 'Output written' $@/20-watt-computer-$@.log
	@grep -a -c -i '^! \|Overfull\|undefined\|multiply' $@/20-watt-computer-$@.log || true

# Popular «paperback» edition: <lang>/paperback/main.tex, one file per chapter, same numbering as the full edition.
PAPERBACK = docker run --rm -v "$(CURDIR)":/w -e TEXINPUTS=/w/ru:/w: -w /w/ru texlive/texlive \
            pdflatex -interaction=nonstopmode -jobname=20-watt-computer-ru-paperback paperback/main.tex

ru-paperback:
	$(PAPERBACK) >/dev/null
	$(PAPERBACK) >/dev/null
	@grep -a 'Output written' ru/20-watt-computer-ru-paperback.log
	@grep -a -c -i '^! \|Overfull\|undefined\|multiply' ru/20-watt-computer-ru-paperback.log || true

# Regenerate the simulation data in figures/ (run from the repository root).
models:
	for f in models/*.py; do python3 $$f; done

clean:
	rm -f */*.aux */*.log */*.out */*.toc
