# Companion qualification

The [local receipt](../compatibility/companion-local-qualification.json) records
21 complete Django/Python pairs, a separate Python 3.15 qualification, the native
oracle, 151 response comparisons per interpreter, strict SDK type checks, installed
CLI/LSP controls and the 7,082-file/2,501-model regression. Source preservation,
negative controls, process-tree memory accounting and cleanup are required.

Local measurements are candidate checks. CI builds one universal wheel and tests
that exact artifact on Linux, macOS and Windows, then repeats the contract matrix
and bounded scalability workload. Published wheel/source hashes and their signed
provenance are checked separately after release.

Django editor qualification uses workspace diagnostics. The controlled legacy and
companion comparison in the receipt shows why: closed model facts are absent in
open-files-only mode. Workspace mode passes both references. This is a required
Django configuration, not a claim that every editor default provides project-wide
plugin facts.

Python 3.15 is checked against Django's official contracts and actual framework
runtime. Its pinned mypy/django-stubs comparison runs on Python 3.13, which that
comparator declares supported; it is separate from the 21 version-matched pairs.
The recorded workloads do not prove behavior for unavailable private applications.
