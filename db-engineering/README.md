# Database query engineering samples

These six tasks are public development and calibration examples for the
database query engineering category. Each task includes a reference solution
for after-the-fact inspection.

In this category an agent authors, repairs, or optimizes the queries a real
application runs against a live PostgreSQL or ClickHouse database: raw SQL,
ORM code, or query-builder code, inside the application's own repository. Correctness is judged on data
the task does not show, and optimization tasks measure the database work the
query performs, not just whether tests pass.

Run a task locally from the `ridges-bench` repository root after configuring
the Ridges miner CLI:

```bash
ridges miner setup
ridges miner run-local \
  --task-path "./db-engineering/pg-netbox-contact-group-counts-001" \
  --agent-path "/path/to/your/agent"
```

Available tasks:

| Task | Kind | Focus |
|---|---|---|
| `pg-netbox-bulk-tag-assignment-001` | optimization | Bounded-query tag assignment |
| `pg-netbox-cached-value-index-001` | optimization | A migration index that must serve an exact-object predicate |
| `pg-netbox-contact-group-counts-001` | repair | Descendant counts across a tree hierarchy |
| `pg-netbox-ipaddress-device-filter-001` | optimization | A filter whose query count must not scale with the selection |
| `pg-netbox-prefix-hierarchy-annotations-001` | authoring | Depth and descendant annotations over network prefixes |
| `pg-netbox-vlangroup-utilization-001` | repair | Percentage arithmetic computed in the database |

What to take from these samples, and what not to:

- The samples come from one repository and one engine, PostgreSQL. The
  competition checks both PostgreSQL and ClickHouse, across several
  repositories, languages, and query layers. Build for the category, not for
  this codebase.
- Some competition tasks name the file or function to change and some do not.
  An agent should be able to trace a symptom to the query that causes it.
- When a task bounds the change to one method, everything else in that file
  must stay exactly as it is, including imports. Use only names the file
  already imports.
- The tests a task names are regression checks that already pass. They tell
  you what must keep working, not what the fix is. Passing them is necessary,
  not sufficient.
- The rule of thumb: the agent you submit should work unchanged on your own
  PostgreSQL or ClickHouse query problems in a repository nobody has seen.
  Specializing on engines, query layers, and kinds of query problems is the
  point. Knowledge of specific tasks, repositories, files, datasets, or
  verifiers is not.

Tasks are samples - real competition will not reuse the same strategy, task/repo family etc.
