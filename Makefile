# Build the book in each language. Sources live in <lang>/main.tex + <lang>/chapters/;
# figures/ (TikZ data, icons) and models/ (Python simulations) are shared by all languages.
# Russian, English, Spanish and Portuguese build with pdflatex; Chinese (ctex), Japanese (xeCJK) and Korean (kotex) with xelatex.
ENGINE = $(if $(filter zh ja ko,$(1)),xelatex,pdflatex)
DOCKER = docker run --rm -v "$(CURDIR)":/w -e TEXINPUTS=/w/$(1):/w: -w /w/$(1) texlive/texlive \
         $(call ENGINE,$(1)) -interaction=nonstopmode -jobname=20-watt-computer-$(1) main.tex

.PHONY: all ru en zh ja ko es pt ru-paperback en-paperback zh-paperback ja-paperback ko-paperback es-paperback pt-paperback models clean
all: ru

ru en zh ja ko es pt:
	$(call DOCKER,$@) >/dev/null
	$(call DOCKER,$@) >/dev/null
	@grep -a 'Output written' $@/20-watt-computer-$@.log
	@grep -a -c -i '^! \|Overfull\|undefined\|multiply' $@/20-watt-computer-$@.log || true

# Popular «paperback» edition: <lang>/paperback/main.tex, one file per chapter, same numbering as the full edition.
PAPERBACK = docker run --rm -v "$(CURDIR)":/w -e TEXINPUTS=/w/$(1):/w: -w /w/$(1) texlive/texlive \
            $(call ENGINE,$(1)) -interaction=nonstopmode -jobname=20-watt-computer-$(1)-paperback paperback/main.tex

ru-paperback en-paperback zh-paperback ja-paperback ko-paperback es-paperback pt-paperback:
	$(call PAPERBACK,$(@:-paperback=)) >/dev/null
	$(call PAPERBACK,$(@:-paperback=)) >/dev/null
	@grep -a 'Output written' $(@:-paperback=)/20-watt-computer-$@.log
	@grep -a -c -i '^! \|Overfull\|undefined\|multiply' $(@:-paperback=)/20-watt-computer-$@.log || true

# Regenerate the simulation data in figures/ (run from the repository root).
models:
	for f in models/*.py; do python3 $$f; done

clean:
	rm -f */*.aux */*.log */*.out */*.toc */*/*.aux
