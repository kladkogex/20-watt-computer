# Build the book in each language. Sources live in <lang>/main.tex + <lang>/chapters/;
# figures/ (TikZ data, icons) and models/ (Python simulations) are shared by all languages.
DOCKER = docker run --rm -v "$(CURDIR)":/w -e TEXINPUTS=/w/$(1):/w: -w /w/$(1) texlive/texlive \
         pdflatex -interaction=nonstopmode -jobname=20-watt-computer-$(1) main.tex

.PHONY: all ru en models clean
all: ru

ru en:
	$(call DOCKER,$@) >/dev/null
	$(call DOCKER,$@) >/dev/null
	@grep -a 'Output written' $@/20-watt-computer-$@.log
	@grep -a -c -i '^! \|Overfull\|undefined\|multiply' $@/20-watt-computer-$@.log || true

# Regenerate the simulation data in figures/ (run from the repository root).
models:
	for f in models/*.py; do python3 $$f; done

clean:
	rm -f */*.aux */*.log */*.out */*.toc
