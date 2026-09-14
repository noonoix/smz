# Delivery quality gate

For every requested fix, upgrade, refactor, or new build, Classroom Studio must be reviewed in two dimensions before delivery:

1. **Behavioral/structural review:** data flow, runtime logic, protocol/firmware compatibility, cancellation and error paths, generated and portable outputs, tests, and release contents.
2. **Visual review:** labels, discoverability, layout, sizing, scrolling, alignment, grouping, copy actions, and the actual packaged UI.

A build is not considered delivered until both reviews are completed, regressions are addressed, tests are green, and the final release artifact is checked against the changed source.
