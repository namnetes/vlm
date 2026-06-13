SHELL       := /bin/bash
.SHELLFLAGS := -euo pipefail -c

PID_FILE := .mkdocs.pid
LOG_FILE := .mkdocs.log
HOST     := 127.0.0.1
PORT     := $(shell \
	for p in $$(seq 8000 8050); do \
		lsof -ti:$$p >/dev/null 2>&1 || { \
			echo $$p; \
			break; \
		}; \
	done \
)
STEPS         ?=
PYTHON_RUN    ?= uv run
QUERY_INPUT   ?= datas/vlm.json
QUERY_OUTPUT  ?= datas/export.csv
QUERY_MODE    ?= -g
QUERY_DATE    ?=
IMAGE_NAME    ?= vlm-pipeline
DOCKER_RUN_OPTS ?= \
	--rm -v "$(CURDIR)/datas:/app/datas"
ARGS          ?=

export DISABLE_MKDOCS_2_WARNING := true

RED    := \033[0;31m
GREEN  := \033[0;32m
YELLOW := \033[0;33m
BOLD   := \033[1m
RESET  := \033[0m

LOG_LEVELS   := DEBUG INFO WARNING ERROR
PIPELINE_LOG := datas/pipeline.log

.DEFAULT_GOAL := help
.PHONY: \
	run \
	query \
	log-level \
	log \
	clean \
	docs \
	docs-start \
	docs-stop \
	docs-build \
	docker-build \
	docker-build-s390x \
	docker-run \
	help

# ── Macros internes ───────────────────────────────────────────────────────────

define require_cmd
	@command -v $(1) >/dev/null 2>&1 || { \
		printf "$(RED)Erreur$(RESET) : '$(1)' est requis mais"; \
		printf " introuvable dans PATH.\n"; \
		exit 1; \
	}
endef

define check_mkdocs_yml
	@[ -f mkdocs.yml ] || { \
		printf "$(RED)Erreur$(RESET) : mkdocs.yml introuvable"; \
		printf " dans le répertoire courant.\n"; \
		exit 1; \
	}
endef

define check_port_available
	@[ -n "$(PORT)" ] || { \
		printf "$(RED)Erreur$(RESET) : aucun port libre"; \
		printf " disponible entre 8000 et 8050.\n"; \
		exit 1; \
	}
endef

define check_copt_folder
	@[ -d ./datas/copt ] || { \
		mkdir -p ./datas/copt; \
		printf "$(YELLOW)Attention$(RESET) : le dossier ./datas/copt "; \
		printf "n'existait pas et a été créé.\n"; \
	}
endef

# ── Pipeline ──────────────────────────────────────────────────────────────────

run:
	$(call check_copt_folder)
	$(PYTHON_RUN) python src/pipeline.py $(STEPS)

# ── Export CSV ────────────────────────────────────────────────────────────────

query:
	$(call require_cmd,jq)
	bash script/export_csv.sh \
		-i $(QUERY_INPUT) \
		-o $(QUERY_OUTPUT) \
		$(QUERY_MODE) \
		$(if $(QUERY_DATE),-d $(QUERY_DATE),)

# ── Configuration ─────────────────────────────────────────────────────────────

log-level:
	@[ -n "$(LOG_LEVEL)" ] || { \
		printf "$(RED)Erreur$(RESET) : LOG_LEVEL est requis "; \
		printf "($(LOG_LEVELS)).\n"; \
		printf "  → Exemple : make log-level LOG_LEVEL=DEBUG\n"; \
		exit 1; \
	}
	@case " $(LOG_LEVELS) " in \
		*" $(LOG_LEVEL) "*) ;; \
		*) printf "$(RED)Erreur$(RESET) : niveau '$(LOG_LEVEL)'"; \
		   printf " invalide ($(LOG_LEVELS)).\n"; \
		   exit 1;; \
	esac
	@sed -i 's/^level = ".*"/level = "$(LOG_LEVEL)"/' config.toml
	@printf "$(GREEN)OK$(RESET) Niveau de log défini sur"; \
	printf " $(LOG_LEVEL) dans config.toml\n"

log:
	$(call require_cmd,less)
	@[ -f $(PIPELINE_LOG) ] || { \
		printf "$(RED)Erreur$(RESET) : $(PIPELINE_LOG) introuvable"; \
		printf " — lancez 'make run' au moins une fois.\n"; \
		exit 1; \
	}
	less +G $(PIPELINE_LOG)

# ── Nettoyage ─────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete 2>/dev/null || true

	rm -f .coverage 2>/dev/null || true

	rm -f datas/clean_vlm.xml \
		  ./datas/clean_vlm_copt.xml \
		  ./datas/copt_ignored.txt \
		  ./datas/vlm.json 2>/dev/null || true

	rm -f ./datas/pipeline.log \
		  ./datas/pipeline.log.* 2>/dev/null || true

	rm -rf ./datas/copt 2>/dev/null || true

# ── Conteneurisation ──────────────────────────────────────────────────────────

docker-build:
	$(call require_cmd,docker)
	docker build -t $(IMAGE_NAME) .

docker-build-s390x:
	$(call require_cmd,docker)
	docker buildx build --platform linux/s390x --load -t $(IMAGE_NAME):s390x .

docker-run:
	$(call require_cmd,docker)
	docker run $(DOCKER_RUN_OPTS) $(IMAGE_NAME) $(ARGS)

# ── Documentation ─────────────────────────────────────────────────────────────

docs:
	$(call require_cmd,uv)
	$(call check_mkdocs_yml)
	$(call check_port_available)
	uv run mkdocs serve --dev-addr $(HOST):$(PORT)

docs-start:
	$(call require_cmd,uv)
	$(call check_mkdocs_yml)
	$(call check_port_available)
	@if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		printf "$(YELLOW)Attention$(RESET) : MkDocs tourne déjà"; \
		printf " (PID $$(cat $(PID_FILE))).\n"; \
		printf "  → Arrêtez-le d'abord : make docs-stop\n"; \
	else \
		rm -f $(PID_FILE); \
		uv run mkdocs serve --dev-addr $(HOST):$(PORT) > $(LOG_FILE) 2>&1 & \
		echo $$! > $(PID_FILE); \
		sleep 1; \
		if kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
			printf "$(GREEN)OK$(RESET) MkDocs démarré"; \
			printf " (PID $$(cat $(PID_FILE)))"; \
			printf " — http://$(HOST):$(PORT)\n"; \
		else \
			printf "$(RED)Erreur$(RESET) : MkDocs a planté au démarrage.\n"; \
			printf "  → Consultez les logs : cat $(LOG_FILE)\n"; \
			rm -f $(PID_FILE); \
			exit 1; \
		fi; \
	fi

docs-stop:
	@if [ ! -f $(PID_FILE) ]; then \
		printf "$(YELLOW)Attention$(RESET) : aucun PID enregistré"; \
		printf " — MkDocs ne tourne pas en background.\n"; \
		exit 0; \
	fi
	@PID=$$(cat $(PID_FILE)); \
	if kill -0 $$PID 2>/dev/null; then \
		kill $$PID && printf "$(GREEN)OK$(RESET) MkDocs arrêté (PID $$PID).\n"; \
	else \
		printf "$(YELLOW)Attention$(RESET) : processus $$PID"; \
		printf " introuvable (déjà arrêté ?).\n"; \
	fi; \
	rm -f $(PID_FILE)

docs-build:
	$(call require_cmd,uv)
	$(call check_mkdocs_yml)
	@uv run mkdocs build || { \
		printf "$(RED)Erreur$(RESET) : la compilation a échoué."; \
		printf " Voir la sortie ci-dessus.\n"; \
		exit 1; \
	}
	@printf "$(GREEN)OK$(RESET) Documentation compilée dans site/\n"

# ── Aide ──────────────────────────────────────────────────────────────────────

help:
	@printf "$(BOLD)VLM pipeline$(RESET) — cibles disponibles\n\n"
	@printf "  $(BOLD)run$(RESET)                 Lance le pipeline VLM complet\n"
	@printf "                      STEPS=2-4 pour n'exécuter que certaines étapes\n"
	@printf "  $(BOLD)query$(RESET)               Exporte le JSON vers CSV via export_csv.sh\n"
	@printf "                      QUERY_MODE=-g (défaut) | -p | -c\n"
	@printf "                      QUERY_OUTPUT=datas/export.csv\n"
	@printf "                      QUERY_DATE=2026/01/01 (filtre optionnel)\n"
	@printf "  $(BOLD)log-level$(RESET)           Modifie le niveau de log dans config.toml\n"
	@printf "                      LOG_LEVEL=DEBUG|INFO|WARNING|ERROR (requis)\n"
	@printf "  $(BOLD)log$(RESET)                 Ouvre $(PIPELINE_LOG) avec less (fin du fichier)\n"
	@printf "  $(BOLD)clean$(RESET)               Supprime caches et fichiers produits par le pipeline\n\n"
	@printf "  $(BOLD)docker-build$(RESET)        Construit l'image Docker ($(IMAGE_NAME))\n"
	@printf "  $(BOLD)docker-build-s390x$(RESET)  Cross-build de l'image pour linux/s390x (IBM Z / zCX)\n"
	@printf "  $(BOLD)docker-run$(RESET)          Lance une cible make dans le conteneur (volume datas/ monté)\n"
	@printf "                      ARGS=\"run STEPS=2-4\" | ARGS=query | ARGS=\"query QUERY_MODE=-p\"\n\n"
	@printf "  $(BOLD)docs$(RESET)                Lance MkDocs en mode développement (foreground)\n"
	@printf "  $(BOLD)docs-start$(RESET)          Lance MkDocs en arrière-plan\n"
	@printf "  $(BOLD)docs-stop$(RESET)           Arrête MkDocs lancé en arrière-plan\n"
	@printf "  $(BOLD)docs-build$(RESET)          Compile la documentation statique\n"
