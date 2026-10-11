# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= ../.venv/bin/sphinx-build
SOURCEDIR     = src
BUILDDIR      = _build
GITDEST   	  = origin

# Colors for output
BOLD := \033[1m
BLUE := \033[34m
GREEN := \033[32m
RESET := \033[0m

# Put it first so that "make" without argument is like "make help".
help: ## Show documentation targets
	@printf "$(BOLD)Documentation Commands:$(RESET)\n"
	@printf "$(BOLD)=====================$(RESET)\n"
	@printf "  $(BLUE)%-15s$(RESET) %s\n" "install" "Install documentation"
	@printf "  $(BLUE)%-15s$(RESET) %s\n" "doc" "Build documentation (clean rebuild)"
	@printf "\n"
	@printf "  $(BLUE)%-15s$(RESET) %s\n" "clean" "Clean build artifacts and prepare gh-pages worktree"
	@printf "  $(BLUE)%-15s$(RESET) %s\n" "commit" "Commit documentation changes"
	@printf "  $(BLUE)%-15s$(RESET) %s\n" "push" "Push documentation to remote"
	@printf "  $(BLUE)%-15s$(RESET) %s\n" "all" "Clean, commit, and push documentation"
	@printf "\n$(BOLD)Sphinx targets:$(RESET)\n"
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile doc clean install commit push all

install:
	@printf "$(BOLD)Setting up Doc...$(RESET)\n"
		source ../.venv/bin/activate && \
		pip install -r requirements.txt

doc: clean html
	@printf "$(GREEN)✓ Documentation built at $(BUILDDIR)/html$(RESET)\n"

clean:
	@$(SPHINXBUILD) -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O);
	cd _build; git worktree add -f html gh-pages

commit:
	cd "$(BUILDDIR)"/html; git add .; git commit -m "Update documentation"

push:
	cd "$(BUILDDIR)"/html; git push "$(GITDEST)" gh-pages

all: clean commit push

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
