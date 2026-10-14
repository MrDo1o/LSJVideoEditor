#!/usr/bin/env python3
"""
Step 1 Minimal Example: Approved EditPlan Transactional Transition to Timeline
Digital Architecture by LSJ Systems TM

Demonstrates:
1. Constructing an immutable EditPlan with exact RationalTime boundaries and factor scores.
2. Independent pre-validation against the working media bin.
3. Cryptographic approval binding (media manifest hash, timeline revision, content hash).
4. Atomic application under lock.
5. Idempotent re-application protection ("already_applied").
6. Full state restoration via transactional undo.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add repo root and windows folder to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
WINDOWS_DIR = REPO_ROOT / "windows"
if str(WINDOWS_DIR) not in sys.path:
    sys.path.insert(0, str(WINDOWS_DIR))

import edit_plan
from edit_plan import EditPlan, FactorScores, PlanMarker, PlanSegment, RationalTime
import lsj_video_editor as editor_mod


def run_minimal_example():
    print("=" * 72)
    print("LSJ Systems TM — Step 1: Transactional EditPlan Application Engine")
    print("=" * 72)

    # 1. Initialize native EditorAPI instance
    api = editor_mod.EditorAPI(project_name="Step1_Minimal_Example")
    print(f"\n[1] Initialized EditorAPI (Project: {api.project_name})")
    print(f"    Timeline Clips: {len(api.timeline)} | Undo Stack Depth: {len(api.undo_stack)}")

    # 2. Populate media bin with deterministic fixtures
    api.clips = [
        {
            "id": "clip_drone_01",
            "name": "Bae - 3.MP4",
            "path": "C:\\Media\\Bae - 3.MP4",
            "duration": 45.0,
            "fps": 30.0,
            "width": 1920,
            "height": 1080,
            "codec": "h264",
            "is_audio": False,
            "has_audio": True,
        },
        {
            "id": "clip_action_02",
            "name": "Bae - 4.MP4",
            "path": "C:\\Media\\Bae - 4.MP4",
            "duration": 60.0,
            "fps": 30.0,
            "width": 1920,
            "height": 1080,
            "codec": "h264",
            "is_audio": False,
            "has_audio": True,
        },
    ]
    print(f"[2] Media Bin Populated: {len(api.clips)} clips loaded")
    print(f"    Media Manifest Hash: {api.get_media_manifest_hash()}")
    print(f"    Timeline Revision:   {api.get_timeline_revision()}")

    # 3. Create an immutable EditPlan (frozen dataclass)
    # Shot 1: Drone Establishing shot (0.0s -> 3.0s on Track 0)
    seg1 = PlanSegment(
        segment_id="shot_001_establishing",
        media_id="clip_drone_01",
        track=0,
        timeline_start=RationalTime(0, 30),      # 0.0s
        source_in=RationalTime(30, 30),           # 1.0s
        source_out=RationalTime(120, 30),         # 4.0s (3.0s duration)
        narrative_role="establishing",
        factor_scores=FactorScores(aesthetics=0.95, composition=0.90, lighting=0.88),
        filter_preset="Apex",
        fade_in_sec=0.5,
    )

    # Shot 2: Action sequence cut (3.0s -> 5.5s on Track 0)
    seg2 = PlanSegment(
        segment_id="shot_002_action",
        media_id="clip_action_02",
        track=0,
        timeline_start=RationalTime(90, 30),     # 3.0s
        source_in=RationalTime(15, 30),           # 0.5s
        source_out=RationalTime(90, 30),          # 3.0s (2.5s duration)
        narrative_role="action",
        factor_scores=FactorScores(energy=0.96, camera_stability=0.82),
        filter_preset="Solstice",
        transition_in="Dissolve",
        transition_duration=RationalTime(15, 30), # 0.5s dissolve
    )

    # Shot 3: PIP Overlay on Track 1 (1.5s -> 3.5s - multi-track overlap allowed)
    seg3 = PlanSegment(
        segment_id="shot_003_overlay",
        media_id="clip_action_02",
        track=1,
        timeline_start=RationalTime(45, 30),     # 1.5s
        source_in=RationalTime(150, 30),          # 5.0s
        source_out=RationalTime(210, 30),         # 7.0s (2.0s duration)
        narrative_role="detail",
        scale=0.35,
        x=640,
        y=360,
    )

    plan = api.create_edit_plan(
        segments=[seg1, seg2, seg3],
        markers=[PlanMarker(time=RationalTime(90, 30), name="Scene Transition")],
        plan_id="plan_sovereign_director_alpha",
        plan_version=1,
    )
    print(f"\n[3] Synthesized Immutable EditPlan:")
    print(f"    Plan ID:       {plan.plan_id} (v{plan.plan_version})")
    print(f"    Content Hash:  {plan.content_hash()[:16]}...")
    print(f"    Segments:      {len(plan.segments)} candidate cuts")
    print(f"    Working Timeline Unmodified: len(api.timeline) = {len(api.timeline)}")

    # 4. Validate the EditPlan without mutating state
    is_valid, errors = api.validate_edit_plan(plan)
    print(f"\n[4] Plan Pre-Validation: is_valid = {is_valid} (Errors: {errors})")
    assert is_valid, f"Validation failed: {errors}"

    # 5. Authorize explicit plan approval token
    approval = api.approve_edit_plan(plan, approver="sovereign_lead_director")
    print(f"\n[5] Generated Cryptographic Approval Token:")
    print(f"    Approved Plan Hash:      {approval.plan_content_hash[:16]}...")
    print(f"    Bound Media Manifest:    {approval.media_manifest_hash}")
    print(f"    Bound Timeline Revision: {approval.timeline_revision}")
    print(f"    Is Stale:                {approval.is_stale(api.get_media_manifest_hash(), api.get_timeline_revision())}")
    print(f"    Working Timeline Unmodified: len(api.timeline) = {len(api.timeline)}")

    # 6. Atomic Transaction Application
    print(f"\n[6] Committing Approved Plan to Working Timeline under Lock...")
    result = api.apply_approved_plan(plan, approval)
    print(f"    Application Status: {result['status']}")
    print(f"    Applied Plan Hash:  {result['applied_plan_hash'][:16]}...")
    print(f"    Timeline Clips:     {len(api.timeline)}")
    print(f"    Undo Stack Depth:   {len(api.undo_stack)}")

    print("\n    Resulting Timeline Structure:")
    for idx, clip in enumerate(api.timeline):
        print(f"      [{idx+1}] Track {clip['track']} | {clip['name']} | "
              f"start={clip['start']:.2f}s | dur={clip['duration']:.2f}s | "
              f"sourceIn={clip['sourceIn']:.2f}s | filter={clip.get('filter')} | "
              f"transition={clip.get('transition')}")

    print("\n    Resulting Markers:")
    for idx, marker in enumerate(api.markers):
        print(f"      Marker [{idx+1}]: {marker['name']} at {marker['time']:.2f}s")

    # 7. Demonstrate Idempotency
    print(f"\n[7] Testing Application Idempotency:")
    idempotent_result = api.apply_approved_plan(plan, approval)
    print(f"    Duplicate Call Status: {idempotent_result['status']}")
    print(f"    Undo Stack Depth:      {len(api.undo_stack)} (Unchanged, no duplicate undo entry)")
    assert idempotent_result["status"] == "already_applied"

    # 8. Demonstrate Transactional Undo & Redo
    print(f"\n[8] Testing Transactional Undo & Redo:")
    api.undo()
    print(f"    After Undo: Timeline Clips = {len(api.timeline)} | Applied Plan Hash = {api.applied_plan_hash}")
    assert len(api.timeline) == 0, "Timeline should be empty after undo"

    api.redo()
    print(f"    After Redo: Timeline Clips = {len(api.timeline)} | Applied Plan Hash = {api.applied_plan_hash[:16]}...")
    assert len(api.timeline) == 3, "Timeline should have 3 clips restored after redo"

    print("\n" + "=" * 72)
    print("STEP 1 MINIMAL EXAMPLE VERIFIED SUCCESSFULLY")
    print("=" * 72)


if __name__ == "__main__":
    run_minimal_example()
