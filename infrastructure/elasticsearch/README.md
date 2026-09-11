# Elasticsearch cluster notes

The `docker-compose.yml` 3-node cluster is intentionally sized for a
developer laptop, not production:

- 512MB JVM heap per node (`ES_JAVA_OPTS=-Xms512m -Xmx512m`), 1GB container
  memory limit per node -> 3GB total for the ES layer. Real deployments
  typically give each node 50% of container memory as heap, up to ~31GB
  (to stay under the compressed-oops limit), with the rest reserved for
  the OS page cache Lucene relies on.
- `xpack.security.enabled=false` for local dev simplicity. Production
  must enable security (TLS + auth) -- see `ELASTICSEARCH_USERNAME`
  / `ELASTICSEARCH_PASSWORD` in `.env.example`, already wired into
  `app/search/es_client.py`.
- 3 shards / 1 replica on the `documents` index (`app/search/mappings.py`)
  -- enough to spread load across all 3 nodes and survive a single node
  loss without data loss, without over-sharding a modest dataset.
- `bootstrap.memory_lock=true` prevents the JVM heap from being swapped
  out; requires the `memlock` ulimit set in compose.

To scale beyond a laptop: add more data nodes, split into dedicated
master/data/ingest node roles (`node.roles` setting), and increase
shard count roughly in proportion to expected index size (target
20-40GB per shard as a rule of thumb).
