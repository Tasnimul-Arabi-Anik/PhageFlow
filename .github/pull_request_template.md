## Summary

- 

## Validation

- [ ] `python3 -m py_compile bin/*.py`
- [ ] `bash -n bin/phageflow bin/run_local_validation.sh bin/container_smoke_test.sh`
- [ ] `bash bin/run_local_validation.sh` when workflow/report behavior changed
- [ ] `bash bin/phageflow container-smoke` when container behavior changed

## Scope Boundary

- [ ] This change preserves local reproducibility.
- [ ] This change does not add network-dependent core behavior.
- [ ] This change does not claim biological interpretation beyond validated software outputs.
