.PHONY: doctor git-status

doctor:
	@./scripts/doctor.sh

git-status:
	@git status --short --branch
