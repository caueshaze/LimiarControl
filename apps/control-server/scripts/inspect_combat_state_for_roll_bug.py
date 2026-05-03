"""Inspection script to capture combat state at the moment of a bug.

Usage:
    .venv/bin/python scripts/inspect_combat_state_for_roll_bug.py <session_id>

Output:
    Prints CombatState participants with active_effects,
    plus last roll_requested and roll_resolved activities.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to path so imports work when run from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlmodel import Session, create_engine, select

from app.models.combat_state import CombatState
from app.models.session_activity import SessionActivity


def main(session_id: str) -> None:
    engine = create_engine("postgresql+psycopg2://control:control@localhost:5432/control")
    with Session(engine) as db:
        state = db.exec(select(CombatState).where(CombatState.session_id == session_id)).first()
        if state is None:
            print(f"No CombatState found for session_id={session_id}")
            return

        print("=" * 60)
        print(f"CombatState for session_id={session_id}")
        print(f"  phase={state.phase}")
        print(f"  round={state.round}")
        print(f"  current_turn_index={state.current_turn_index}")
        print(f"  participants_count={len(state.participants or [])}")
        print("=" * 60)

        for p in state.participants or []:
            effects = p.get("active_effects") or []
            print(f"\nParticipant id={p.get('id')} ref_id={p.get('ref_id')} kind={p.get('kind')} name={p.get('display_name')}")
            print(f"  active_effects_count={len(effects)}")
            for eff in effects:
                print(f"    - kind={eff.get('kind')} display_label={eff.get('display_label')} metadata={eff.get('metadata')}")

        print("\n" + "=" * 60)
        print("Last 5 roll_requested activities:")
        activities = db.exec(
            select(SessionActivity)
            .where(SessionActivity.session_id == session_id)
            .where(SessionActivity.activity_type.in_(["roll_requested", "roll_resolved"]))
            .order_by(SessionActivity.created_at.desc())
            .limit(10)
        ).all()
        for act in activities:
            print(f"\n  [{act.activity_type}] at {act.created_at.isoformat()}")
            print(f"    actor_name={act.actor_name}")
            payload = act.payload or {}
            print(f"    payload keys={list(payload.keys())}")
            if "expression" in payload:
                print(f"    expression={payload.get('expression')} rollType={payload.get('rollType')} ability={payload.get('ability')} skill={payload.get('skill')}")
            if "check_modifier_sources" in payload:
                print(f"    check_modifier_sources={json.dumps(payload.get('check_modifier_sources'), indent=6)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <session_id>")
        sys.exit(1)
    main(sys.argv[1])
