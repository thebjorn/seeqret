"""Two-phase secret merge (mirrors jseeqret's merge.js).

   Phase 1 (``plan_secret_merge``) classifies incoming secrets
   against the local vault: additions, identical (skipped), and
   conflicts. Phase 2 (``apply_secret_merge``) applies the plan
   under explicit per-secret resolutions -- nothing is overwritten
   without a decision.

   ``updated_at`` timestamps are advisory merge metadata: the
   ``newer`` strategy uses them, but interactive callers should
   surface them to a human rather than auto-applying.
"""
from .models import Secret

RESOLUTION_MINE = 'mine'
RESOLUTION_THEIRS = 'theirs'
STRATEGY_NEWER = 'newer'


def secret_id(secret: Secret) -> str:
    return f'{secret.app}:{secret.env}:{secret.key}'


def plan_secret_merge(storage, incoming: list[Secret]) -> dict:
    """Classify *incoming* secrets against the vault.

       Returns ``{additions: [Secret], identical: [Secret],
       conflicts: [{incoming, local}]}``.
    """
    additions = []
    identical = []
    conflicts = []
    for secret in incoming:
        existing = storage.fetch_secrets(
            app=secret.app, env=secret.env, key=secret.key)
        local = existing[0] if existing else None
        if local is None:
            additions.append(secret)
        elif (str(local.value) == str(secret.value)
              and local.type == secret.type):
            identical.append(secret)
        else:
            conflicts.append(dict(incoming=secret, local=local))
    return dict(additions=additions, identical=identical,
                conflicts=conflicts)


def resolve_conflict(conflict: dict, strategy: str) -> str:
    """Resolve one conflict with a bulk *strategy*.

       ``newer`` compares the advisory ``updated_at`` stamps
       (missing stamps count as 0); ties keep the local value --
       conservative by design.
    """
    if strategy in (RESOLUTION_MINE, RESOLUTION_THEIRS):
        return strategy
    if strategy == STRATEGY_NEWER:
        local_ts = conflict['local'].updated_at or 0
        incoming_ts = conflict['incoming'].updated_at or 0
        return (RESOLUTION_THEIRS if incoming_ts > local_ts
                else RESOLUTION_MINE)
    raise ValueError(f'unknown merge strategy: {strategy}')


def conflict_summary(plan: dict) -> list[dict]:
    """Flatten a plan's conflicts for display / IPC-style transfer.

       Matches jseeqret's phase-1 return shape.
    """
    return [dict(
        app=c['incoming'].app,
        env=c['incoming'].env,
        key=c['incoming'].key,
        id=secret_id(c['incoming']),
        local_value=str(c['local'].value),
        incoming_value=str(c['incoming'].value),
        local_updated_at=c['local'].updated_at,
        incoming_updated_at=c['incoming'].updated_at,
    ) for c in plan['conflicts']]


def apply_secret_merge(storage, plan: dict,
                       resolutions: dict | None = None,
                       strategy: str | None = None) -> dict:
    """Apply a merge plan.

       *resolutions* maps ``app:env:key`` to ``mine``/``theirs``;
       *strategy* is an optional fallback for unresolved conflicts.
       Raises ValueError if any conflict remains unresolved --
       nothing is written in that case.
    """
    resolutions = resolutions or {}

    decided = []
    unresolved = []
    for conflict in plan['conflicts']:
        cid = secret_id(conflict['incoming'])
        decision = resolutions.get(cid)
        if decision is None and strategy:
            decision = resolve_conflict(conflict, strategy)
        if decision not in (RESOLUTION_MINE, RESOLUTION_THEIRS):
            unresolved.append(cid)
        else:
            decided.append((conflict, decision))
    if unresolved:
        raise ValueError(
            'unresolved conflicts: ' + ', '.join(unresolved))

    added = updated = kept = 0
    for secret in plan['additions']:
        # storage stamps updated_at (honoring an import-carried
        # timestamp, else now) -- see SqliteStorage._secret_stamp
        storage.upsert_secret(secret)
        added += 1
    for conflict, decision in decided:
        if decision == RESOLUTION_THEIRS:
            storage.upsert_secret(conflict['incoming'])
            updated += 1
        else:
            kept += 1

    return dict(
        added=added,
        updated=updated,
        kept=kept,
        skipped=len(plan['identical']),
        count=added + updated,
    )
