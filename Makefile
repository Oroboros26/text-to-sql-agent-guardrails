ENV = set -a; [ -f .env ] && . ./.env; set +a
.PHONY: seed run test eval
seed:
	python -m sql_agent.db
run: seed
	@$(ENV); python -m sql_agent "$(Q)"
test:
	pytest -q
eval:
	@$(ENV); python -m eval.run
