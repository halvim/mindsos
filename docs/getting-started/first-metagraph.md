---
last_confirmed_phase: 05a
---

# Your first metagraph

This walkthrough creates a metagraph with two contained graphs and a
metaedge between them. Assumes Phase 05a Docker setup
(`docker compose up -d`) is running.

## 1. Create the metagraph

```sh
mindsos metagraph create --name people-and-orgs --json
```

Output (abridged):

```json
{
  "name": "people-and-orgs",
  "metagraph_id": "...",
  "properties": {},
  "state_file": ".mindsos/metagraph-people-and-orgs.json"
}
```

## 2. Create two standalone graphs

```sh
mindsos graph create --name people --role ontology
mindsos graph create --name orgs   --role ontology
```

Add a node to each:

```sh
mindsos graph add-node alice --name people --type Person --node-id alice
mindsos graph add-node acme  --name orgs   --type Org    --node-id acme
```

## 3. Add the graphs to the metagraph

```sh
mindsos metagraph add-graph --name people-and-orgs --graph people
mindsos metagraph add-graph --name people-and-orgs --graph orgs
```

Each graph's state file now carries a `metagraph_name: "people-and-orgs"`
back-pointer (B2). Per Q4-B, attempting `mindsos graph add-node` on
either graph now refuses with a stderr suggestion to use
`mindsos metagraph` instead.

## 4. Add a graph-level metaedge

```sh
mindsos metagraph add-metaedge --name people-and-orgs \
  --source-graph people --target-graph orgs \
  --type EMPLOYS --label "people work at orgs" --json
```

P15: same source and target are refused (no self-loops).

## 5. Inspect

```sh
mindsos metagraph inspect --name people-and-orgs --json
```

Returns:

```json
{
  "name": "people-and-orgs",
  "metagraph_id": "...",
  "properties": {},
  "contained_graphs": ["orgs", "people"],
  "counts": {"graphs": 2, "metaedges": 1, "metahyperedges": 0},
  "_state_version": 1,
  "state_file": ".mindsos/metagraph-people-and-orgs.json"
}
```

## 6. Set a metagraph-level property (ADR-0130)

```sh
mindsos metagraph set-prop --name people-and-orgs \
  --on-metagraph --prop kl:active_graph_ids=people --json
```

Mid-life property updates require P17's `--on-metagraph` marker flag.

## 7. Clean up

```sh
mindsos metagraph remove-graph --name people-and-orgs --graph people
mindsos metagraph remove-graph --name people-and-orgs --graph orgs
mindsos metagraph reset --name people-and-orgs
```

OR, if any graph references survive a `reset` attempt and you need to
force:

```sh
mindsos metagraph reset --name people-and-orgs --force --yes
```

P5: `--force` and `--all` require `--yes`.
