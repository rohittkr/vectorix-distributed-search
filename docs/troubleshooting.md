# Troubleshooting

## `docker compose up` fails to pull images

Docker Hub / `docker.elastic.co` are unreachable (proxy, firewall,
offline). Check with:

```bash
curl -I https://hub.docker.com
curl -I https://docker.elastic.co
```

If these are blocked in your environment, you'll need a mirror/registry
proxy configured in Docker's daemon settings, or to pull the images on
a machine with access and load them via `docker save`/`docker load`.

## Elasticsearch container exits immediately / `max virtual memory areas` error

Elasticsearch needs `vm.max_map_count >= 262144` on the Docker host.
On Linux:

```bash
sudo sysctl -w vm.max_map_count=262144
```

On Docker Desktop (Mac/Windows), this is usually already set correctly
inside the VM; if not, increase it via `docker run --privileged
alpine sysctl -w vm.max_map_count=262144` against the Docker Desktop VM.

## `docker compose up` succeeds but `/health/ready` reports `degraded`

Check each dependency individually:

```bash
docker compose exec backend python scripts/health_check.py
docker compose logs elasticsearch-node-1 --tail 50
docker compose logs postgres --tail 50
docker compose logs redis --tail 50
```

Common causes:
- Elasticsearch cluster still forming (`status: red` briefly after
  startup is normal for the first 30-60s -- the healthcheck's
  `start_period: 40s` accounts for this, but a slow machine may need
  longer).
- Postgres migrations not yet applied -- run `make migrate` or `docker
  compose exec backend alembic upgrade head`.

## Search returns `503 SEARCH_SERVICE_UNAVAILABLE`

This is the *intended* behavior when Elasticsearch is unreachable (see
`docs/architecture.md`'s failure-handling table), not a bug by itself.
Confirm the cluster is actually healthy:

```bash
curl http://localhost:8000/api/v1/health/elasticsearch
```

If it reports `red` or is unreachable, check `docker compose logs
elasticsearch-node-1 elasticsearch-node-2 elasticsearch-node-3`.

## Indexing jobs stay `pending` forever

The worker container may not be running or may have crashed:

```bash
docker compose ps worker
docker compose logs worker --tail 100
```

A job that was `running` when the worker process crashed (rather than
shut down gracefully) will stay `running` in Postgres indefinitely --
this implementation does not include a job-reaper/lease-timeout
mechanism. To recover manually:

```sql
UPDATE indexing_jobs SET status = 'pending' WHERE status = 'running' AND id = '<job-id>';
```

(A production system would add a `lease_expires_at` column and have
the worker's poll loop reclaim expired leases automatically -- noted
as a known limitation, see the root README.)

## Tests hang instead of failing

This happened twice during development of this project (see git
history / the test files' docstrings for `test_run_indexing_job_*` and
the cache-key tests) -- both times the root cause was an actual bug
(an infinite retry loop, and a cache-version off-by-one), not a test
infrastructure problem. If a test hangs for you, suspect the code
first: add a `timeout` to your test runner (`pytest-timeout`, or run
via `timeout 30 pytest ...`) to convert a hang into a stack trace you
can debug.

## Frontend shows "Search failed" for every query

Check the API base URL the frontend was built with:

```bash
docker compose exec frontend env | grep VITE_API_BASE_URL
```

If you changed the backend's port or host, rebuild the frontend image
with the matching `VITE_API_BASE_URL` build arg (see
`docker-compose.yml`'s `frontend.build.args`).
