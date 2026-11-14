# Installed package qualification

Django-ty 0.8 uses native Django inference and a reviewed modern declaration layer. Current qualification keeps these checks separate:

- Pinned source-wheel reproduction, exact provider hashes, two tamper controls and an audit of every Django-local declaration import.
- 172 documented assertions,84 independent Django runtime contracts, and nine QueryDict cases. MyPy agreement is reported separately.
- 52 custom relation-key, constructor and default-row cases in each disk/memory mode, with original source/provider preservation.
- Eight modern static API assertions and three intentional errors, with widget, validator, attachment and async pagination runtime controls.
- All 21 supported Django/Python pairs, plus a separate Python 3.15.1 run. The latter uses a MyPy comparator on a separately supported interpreter.
- Installed discovery, module and empty-PATH entry points, actual editor sessions, hover, unsaved errors and restoration.
- Complete raw CPython/Monty parity for 156 regression requests. The historical Rust reference retains its own regression tests and generates diverse requests; its eager index format and former declaration provider are not the expected representation for the current plugin. Django runtime contracts supply the independent semantic reference.
- Ten rotated fresh-process comparisons per checker across all five performance shapes, including exact type assertions, ordinary Python and ORM error controls, source preservation and per-workload cleanup.

The local restored-provider distributed-stress workload averages 0.785 seconds, with a 0.762-second median, against native Ty's 0.228-second mean. It meets the accepted mean-and-median policy while preserving every paired ratio. These are local workload measurements, not worst-case bounds for arbitrary applications.

Hosted CI builds one universal wheel, tests it on Linux, macOS and Windows, repeats the complete contract and version matrices, and runs the bounded 7,082-file/2,501-model regression. Publication and public-wheel/provenance checks remain separate release gates.

Historical 0.7 evidence remains in [its receipt](../compatibility/companion-local-qualification.json) with its original versions and measured scope.
