# Server Vault v2 -- Zones and the Developer-to-Server Flow

## Context

We deploy to three kinds of server environments ("zones"):

1. **Local physical servers** (Windows, on the office network)
2. **Django server(s) on a VPS** (Linux; the apps read secrets with the
   Python `seeqret` package)
3. **Vercel** (serverless; configuration arrives as environment variables)

Not every `:prod:*` secret is needed in every zone -- an app that deploys
only to Vercel has no business having its secrets on the VPS, and vice
versa. So we need some form of app-to-zone mapping.

Historically, publishing a new secret meant adding it directly to the vault
on the server, and any developer could pull any secret value back down from
the server. That was convenient, but it had two costs:

- **All** secrets ended up on the server -- dev, staging, and prod alike --
  because the server vault doubled as the team's secret-sharing hub.
- Every developer needed (and used) direct access to the production server.

User-to-user sharing is now handled by the Slack export flow, but Slack is
not available on the servers. What remains unsolved is the
developer-to-server flow:

- **(a)** the server picking up new secrets, and
- **(b)** developers pushing new/updated secrets to the server.

## Design Principle: Deployment Target, Not Distribution Hub

The old model conflated two roles: the server vault was both *where apps
read secrets at runtime* and *the team's secret-sharing hub*. The second
role is why everything accumulated on the server.

With the Slack flow covering user-to-user sharing, the server vault can
shed the hub role entirely and become a **one-way deployment target**:

- Only `*:prod:*` secrets, intersected with the apps that actually run in
  that zone, flow **in**.
- Nothing flows **out** to developers.

This is the single biggest security improvement available, and it requires
no new mechanism -- just the decision not to implement a pull path.

**Caveat**: the old pull-from-server path was popular *because* it was
zero-friction. If asking a colleague over Slack is slower, people will
route around it. The "secret request protocol" on the roadmap (a signed
request file that a colleague reviews and fulfills with an export) is the
right pressure valve -- keep it on the list so the request/fulfill loop
stays cheap.

## Zones

### A zone is a push target with a filter

No new data model is needed. The linked-vault plan's `links` table already
has the right shape: a named target with a transport, an address, a
direction, and a `FilterSpec`. A zone is a **push-only link**. What is
genuinely new is the mapping and the drivers, below.

### The app-to-zone mapping must be authoritative

If every developer configures their own push targets, the mappings drift
and eventually someone pushes `intranet:prod:*` to the wrong zone. The
mapping should live in exactly one place. For a small team, a checked-in
`zones.json` (in an infra repo, or distributed through the vault itself)
is enough:

```json
{
    "vps": {
        "type": "seeqret",
        "address": "deploy@vps:/srv/.seeqret-inbox",
        "apps": ["intranet", "api"]
    },
    "office": {
        "type": "seeqret",
        "address": "\\\\fileserver\\seeqret-inbox",
        "apps": ["backup-agent"]
    },
    "www": {
        "type": "vercel-env",
        "project": "www",
        "apps": ["www"]
    }
}
```

The derived filter for a zone is the union of `app:prod:*` for each app in
the zone. Note: `FilterSpec` must support a union of patterns for this
(or the push command loops over the apps) -- check whether that is already
expressible.

The ergonomic payoff of having the mapping as data: when a developer runs
`update DB_PASSWORD --app intranet --env prod`, the CLI can immediately
say *"this affects zone `vps` -- push now?"*. That inverts the workflow
from "remember to distribute" to "the tool tells you where it goes",
which is what made the old server-as-hub model feel easy.

### Zones are heterogeneous -- Vercel is not a vault

There is no server process on Vercel to run seeqret; its "vault" is
`vercel env`. So the zone `type` is really a **driver**:

- `seeqret` zones receive NaCl-encrypted export files.
- `vercel-env` zones are synced via the Vercel API/CLI.

This also leaves the door open for other env-var-shaped targets later
(e.g. GitHub Actions secrets). Trying to make Vercel look like a seeqret
vault would be fighting the platform.

## Transport: the Inbox Pattern

For the VPS and the physical servers, the **mailbox/inbox pattern**
(already sketched in the linked-vault plan) is recommended over an
SSH-pipe (`export | ssh server import`), because it cleanly separates
requirements (a) and (b):

### (b) Push -- developer side

`push vps` does:

1. Export secrets matching the zone's derived filter.
2. NaCl-encrypt the export to the zone vault's public key.
3. Drop the file into the zone's inbox directory (`scp`/`rsync` for the
   VPS, a UNC copy for office servers).

The developer needs only *write access to one spool directory* -- not
shell access to the vault, not read access to anything on the server.

### (a) Pickup -- server side

A `seeqret import-inbox` command, run by a systemd timer (or cron) every
minute:

1. For each file in the inbox: validate the sender's public key against
   the vault's `users` table (the allowlist of who may push).
2. Import the secrets.
3. Delete the file (never leave ciphertext lying around).
4. Append to an import log: who, when, which keys changed.
5. Run a configurable **post-import hook** -- e.g.
   `systemctl reload gunicorn`, or touching the wsgi file.

A one-minute pickup latency is fine for secret distribution, and a timer
plus an idempotent import is far more robust on a headless server than a
file watcher.

### Why a post-import hook instead of in-process reload

The apps on the VPS are Django processes that read secrets at startup;
"reload" realistically means "reload/restart gunicorn". A post-import
hook covers this with one line of configuration. In-process file watching
and reload-diffing remain useful for long-running Node consumers, but
they are not on the critical path for this flow.

## Division of Work: jseeqret vs seeqret (Python)

The consumer on the VPS runs **Python** seeqret. Earlier drafts of the
server-vault plan put watch/reload machinery in the JS library, but that
does nothing for the Django servers. The split should be:

| Deliverable                                        | Repo     |
| -------------------------------------------------- | -------- |
| `zones.json` format + zone resolution              | both     |
| `push <zone>` command (export + encrypt + deliver) | jseeqret |
| `vercel-env` driver                                | jseeqret |
| `import-inbox` command (validate, import, log)     | seeqret  |
| Post-import hook configuration                     | seeqret  |
| Example systemd timer/service units                | seeqret  |
| `api.watch()` / reload events (Node consumers)     | jseeqret |
| GUI integration (zone status, push button)         | jseeqret |

The NaCl export format already exists and is compatible in both
implementations, so no new wire format is needed. Since the flow is
useless until both ends exist, the Python `import-inbox` command is
arguably the critical path.

## Keys and Trust

- Each zone vault gets its **own keypair**, generated at server init.
  Per-zone keys mean compromising the office file server does not expose
  the VPS.
- The zone is "just another user" in each developer's vault: its public
  key is registered like a colleague's.
- The zone vault's `users` table is the allowlist of who may push. This
  is the existing NaCl trust model applied unchanged.
- Per-developer *scoping* (who may push which apps) is not worth it for a
  small team -- it would be advisory anyway. The import log provides
  accountability, which is what is actually needed.

## Open Questions

1. **Where does `zones.json` live** -- infra repo vs distributed through
   the vault itself? A repo is simpler and diffable; the vault is
   self-contained. Leaning: repo.
2. **Does the Vercel driver push secrets or just verify them?** Pushing
   via the Vercel API is convenient but means developer machines hold
   Vercel tokens with write access. A `diff vercel` command (compare
   vault vs deployed env, names only) might be the safer v1.
3. **Update semantics on import** -- last-write-wins per key is probably
   fine for a push-only target, but decide explicitly what happens when
   two developers push conflicting values for the same key. The import
   log at least makes it visible.
4. **Sequencing** -- how much lands in Python first? The pickup side is
   pure Python work; the push side is jseeqret.

## Relationship to Existing Plans

- Supersedes the push/pull sketch in `documentation/server-vault/plan.md`
  (jseeqret repo): Phase 2 there becomes the zone map + inbox design;
  Phases 1/3 (JS watch/reload) are demoted to Node-consumer conveniences.
- Reuses the mailbox pattern and `links` table shape from
  `documentation/linked-vault/plan.md` (jseeqret repo).
- Consistent with Plan A (incremental extension) of
  `documentation/feature-plans/vault-architecture-roadmap/` -- no
  daemons, no HTTP service; files, CLI commands, and a timer.
