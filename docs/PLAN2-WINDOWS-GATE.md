# PLAN2 Windows gate report

- release pins: success
- migration: success
- split runtime: success
- bridge: success
- app build: success
- TestRunner: success (`0 failed`)
- sensitive guard: success

- validated head: `14fea3fc0718791ea00a10501de8068e02186108`
- app workflow run: `34582391025`
- app workflow job: `103208744984`
- sensitive workflow run: `34582394804`
- result: all required release gates completed successfully

## Version contract

- Classroom Studio app: `0.9.66`
- Pico firmware bundle: `0.9.64f` (intentionally unchanged)
- Pro Micro baseline: `2.5` (intentionally unchanged)
- portable plan runtime: `PLAN|2`, engine `0.9.66`

The release workflow verifies that the version patch is idempotent and that all
version changes are committed on the tested head. Successful CI does not mutate
the branch.
