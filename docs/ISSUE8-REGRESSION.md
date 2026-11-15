# Issue 8 resource regression

The [last report](https://github.com/regularkevvv/django-ty/issues/8#issuecomment-6403672557) described a long stall and growing memory on Django-ty 0.5.0 and ty-extended 0.84.5. The same Python 3.13 / Django 6.1.3 fixture now runs against those exact public releases and public Django-ty 0.8.0 / ty-extended 0.90.0.

Both stacks first pass a small positive/error control. The large fixture contains 7,082 Python files and 2,501 linked models; its Python source hash is identical across versions. Each run has a 15-second deadline and a process-tree RSS guard sampled every 200ms at 1 GiB. Scratch output is removed after each run, and generated source trees are archived with every file hash verified before removal.

The old release reaches the memory guard after **5.07 seconds**, with **1050 MiB** observed. It is stopped instead of allowing the original multi-gigabyte growth. This does not measure its eventual completion time or maximum memory.

Current public releases pass three complete positive/error runs with one core. Their means are **2.70 seconds** for the valid project and **2.67 seconds** for the intentional errors. Default parallelism also passes in **2.41/2.79 seconds**. Across these runs, the highest sampled combined RSS is **552 MiB**.

The negative fixture requires both an ordinary assignment error and the Django-specific `django-ty.unknown-lookup` error at exact source locations. Bare official Ty catches only the ordinary error. A plugin crash, skipped validation, misplaced error or extra diagnostic cannot satisfy the regression.

This deliberately standalone chained-model fixture requires the validated second-check path described in the [runtime performance report](https://github.com/regularkevvv/ty-extended/blob/main/docs/performance.md). The separately registered distributed-model workload averages 0.743 seconds with the public runtime. These measurements describe their respective fixtures. The reporter's private project remains unavailable for direct qualification.

See the [summary](../compatibility/issue8-public-regression-0.8.0.json) and [complete compressed receipt](../compatibility/issue8-public-regression-0.8.0.json.gz). Reproduce the current semantic/resource regression with:

```sh
python scripts/check_companion_scalability.py --python /path/to/environment/bin/python --checker /path/to/environment/bin/ty-extended --files 7082 --models 2501 --timeout 15 --max-memory-mib 1024 --output /tmp/new-issue8-check
```

The regression changes tests and documentation; the production Python and declaration payloads are unchanged from published 0.8.0.
