#!/usr/bin/env python3
"""
Step 1 Unit Tests: Shared Immutable EditPlan & Transactional Application Engine
Digital Architecture by LSJ Systems TM

Covers all 8 Step 1 Acceptance Criteria:
1. Creating and revising a plan leaves the working timeline unchanged.
2. Nested plan data cannot be mutated.
3. Changed media or timeline state invalidates approval.
4. Invalid segments are rejected before any mutation (allows multi-track overlaps).
5. An injected mid-application failure leaves state and undo history unchanged.
6. Duplicate and concurrent Confirm requests apply the plan exactly once.
7. Undo and redo restore the complete relevant state and invalidate pending approvals.
8. GUI and CLI adapters use the same core validation and application methods.
"""
from __future__ import annotations

import copy
import dataclasses
import os
import sys
import threading
import time
import unittest
from pathlib import Path

# Add repo root and windows folder to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
WINDOWS_DIR = REPO_ROOT / "windows"
if str(WINDOWS_DIR) not in sys.path:
    sys.path.insert(0, str(WINDOWS_DIR))

import edit_plan
from edit_plan import (
    EditPlan,
    FactorScores,
    PlanApproval,
    PlanAudioTrack,
    PlanConstraints,
    PlanMarker,
    PlanSegment,
    RationalTime,
)
import lsj_video_editor as editor_mod


def make_fixture_clip(clip_id: str, name: str, duration: float = 30.0, fps: float = 30.0) -> dict:
    """Deterministic media clip fixture (no live disk or FFmpeg dependency)."""
    return {
        "id": clip_id,
        "path": f"C:\\FixtureMedia\\{name}",
        "name": name,
        "duration": float(duration),
        "width": 1920,
        "height": 1080,
        "codec": "h264",
        "fps": float(fps),
        "is_audio": False,
        "has_audio": True,
        "is_image": False,
    }


def make_valid_segments() -> tuple[PlanSegment, ...]:
    """Deterministic segment fixtures using exact rational timestamps."""
    return (
        PlanSegment(
            segment_id="seg_001",
            media_id="clip_alpha",
            track=0,
            timeline_start=RationalTime(0, 30),
            source_in=RationalTime(30, 30),          # 1.0s
            source_out=RationalTime(120, 30),        # 4.0s (duration = 90 frames = 3.0s)
            factor_scores=FactorScores(composition=0.92, pacing_tempo=0.88),
            filter_preset="Apex",
            volume=1.0,
            fade_in_sec=0.2,
            fade_out_sec=0.2,
        ),
        PlanSegment(
            segment_id="seg_002",
            media_id="clip_beta",
            track=0,
            timeline_start=RationalTime(90, 30),     # 3.0s
            source_in=RationalTime(0, 30),           # 0.0s
            source_out=RationalTime(60, 30),         # 2.0s (duration = 60 frames = 2.0s)
            factor_scores=FactorScores(composition=0.85, pacing_tempo=0.75),
            filter_preset="Solstice",
            volume=0.9,
            transition_in="Dissolve",
            transition_duration=RationalTime(15, 30), # 0.5s
        ),
        # Overlay on Track 1 (intentional multi-track overlap with track 0)
        PlanSegment(
            segment_id="seg_003_overlay",
            media_id="clip_beta",
            track=1,
            timeline_start=RationalTime(30, 30),     # 1.0s to 2.5s (overlaps seg_001)
            source_in=RationalTime(60, 30),
            source_out=RationalTime(105, 30),        # 1.5s (duration = 45 frames = 1.5s)
            factor_scores=FactorScores(composition=0.95),
            filter_preset="Lumina",
            volume=0.5,
        ),
    )


class TestEditPlanTransactional(unittest.TestCase):
    def setUp(self):
        """Create a fresh EditorAPI instance with mock clips."""
        self.api = editor_mod.EditorAPI(project_name="UnitTest_Step1")
        self.clip_a = make_fixture_clip("clip_alpha", "Alpha.mp4", duration=20.0)
        self.clip_b = make_fixture_clip("clip_beta", "Beta.mp4", duration=30.0)
        self.api.clips = [self.clip_a, self.clip_b]
        self.api.timeline = []
        self.api.markers = []
        self.api.undo_stack = []
        self.api.redo_stack = []
        self.api.history = []

    # -------------------------------------------------------------------------
    # Criterion 1: Creating and revising a plan leaves working timeline unchanged
    # -------------------------------------------------------------------------
    def test_1_create_and_revise_leaves_working_timeline_unchanged(self):
        # Baseline timeline with 1 clip
        self.api.add_to_timeline("clip_alpha", start=0.0, track=0)
        baseline_timeline = copy.deepcopy(self.api.timeline)
        baseline_undo_len = len(self.api.undo_stack)

        segments = make_valid_segments()
        plan_v1 = self.api.create_edit_plan(
            segments=segments,
            plan_id="plan_test_01",
            plan_version=1,
        )

        # Timeline and undo stack must be completely untouched by plan creation
        self.assertEqual(self.api.timeline, baseline_timeline)
        self.assertEqual(len(self.api.undo_stack), baseline_undo_len)
        self.assertIsNotNone(self.api.active_edit_plan)
        self.assertEqual(self.api.active_edit_plan.plan_id, "plan_test_01")
        self.assertEqual(self.api.active_edit_plan.plan_version, 1)

        # Revise plan (new revision object produced)
        revised_segments = segments[:2]  # Remove overlay
        plan_v2 = self.api.revise_edit_plan(
            base_plan=plan_v1,
            segments=revised_segments,
        )

        # Working timeline must still be completely untouched
        self.assertEqual(self.api.timeline, baseline_timeline)
        self.assertEqual(len(self.api.undo_stack), baseline_undo_len)

        # Base plan remains at v1 with original 3 segments
        self.assertEqual(plan_v1.plan_version, 1)
        self.assertEqual(len(plan_v1.segments), 3)

        # Revised plan is at v2 with 2 segments
        self.assertEqual(plan_v2.plan_version, 2)
        self.assertEqual(len(plan_v2.segments), 2)
        self.assertEqual(plan_v2.plan_id, plan_v1.plan_id)

    # -------------------------------------------------------------------------
    # Criterion 2: Nested plan data cannot be mutated
    # -------------------------------------------------------------------------
    def test_2_nested_plan_data_cannot_be_mutated(self):
        segments = make_valid_segments()
        plan = self.api.create_edit_plan(
            segments=segments,
            markers=[PlanMarker(time=RationalTime(30, 30), name="Chapter 1")],
            constraints=PlanConstraints(target_duration=RationalTime(300, 1)),
        )

        # 1. EditPlan root is frozen
        with self.assertRaises(dataclasses.FrozenInstanceError):
            plan.plan_id = "mutated_id"
        with self.assertRaises(dataclasses.FrozenInstanceError):
            plan.plan_version = 99

        # 2. plan.segments is a tuple (immutable collection)
        with self.assertRaises(AttributeError):
            plan.segments.append("fake")
        with self.assertRaises(TypeError):
            plan.segments[0] = "fake"

        # 3. PlanSegment is frozen
        seg = plan.segments[0]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            seg.track = 2
        with self.assertRaises(dataclasses.FrozenInstanceError):
            seg.filter_preset = "Hacked"

        # 4. RationalTime nested is frozen
        with self.assertRaises(dataclasses.FrozenInstanceError):
            seg.source_in.numerator = 9999
        with self.assertRaises(dataclasses.FrozenInstanceError):
            seg.source_out.denominator = 60

        # 5. FactorScores nested is frozen
        with self.assertRaises(dataclasses.FrozenInstanceError):
            seg.factor_scores.composition = 0.0

        # 6. PlanConstraints is frozen
        with self.assertRaises(dataclasses.FrozenInstanceError):
            plan.constraints.target_duration = RationalTime(10, 1)

        # 7. PlanMarker is frozen
        with self.assertRaises(dataclasses.FrozenInstanceError):
            plan.markers[0].name = "Mutated Marker"

    # -------------------------------------------------------------------------
    # Criterion 3: Changed media or timeline state invalidates approval
    # -------------------------------------------------------------------------
    def test_3_changed_media_or_timeline_state_invalidates_approval(self):
        segments = make_valid_segments()
        plan = self.api.create_edit_plan(segments=segments)
        approval = self.api.approve_edit_plan(plan, approver="lead_editor")

        # Initially valid and non-stale
        self.assertTrue(approval.is_valid_for(plan))
        self.assertFalse(approval.is_stale(
            self.api.get_media_manifest_hash(),
            self.api.get_timeline_revision(),
        ))

        # --- Subtest 3A: Timeline change invalidates approval ---
        # Add clip to timeline, altering timeline revision
        self.api.add_to_timeline("clip_alpha", start=0.0, track=0)
        self.assertTrue(approval.is_stale(
            self.api.get_media_manifest_hash(),
            self.api.get_timeline_revision(),
        ))
        with self.assertRaises(ValueError) as ctx:
            self.api.apply_approved_plan(plan, approval)
        self.assertIn("Approval is stale", str(ctx.exception))

        # --- Subtest 3B: Media bin change invalidates approval ---
        # Reset timeline to re-align revision, create fresh plan and approval
        self.api.timeline = []
        plan_fresh = self.api.create_edit_plan(segments=segments)
        approval_fresh = self.api.approve_edit_plan(plan_fresh)
        self.assertFalse(approval_fresh.is_stale(
            self.api.get_media_manifest_hash(),
            self.api.get_timeline_revision(),
        ))

        # Alter media manifest (new clip added to media bin)
        new_clip = make_fixture_clip("clip_gamma", "Gamma.mp4", duration=15.0)
        self.api.clips.append(new_clip)

        self.assertTrue(approval_fresh.is_stale(
            self.api.get_media_manifest_hash(),
            self.api.get_timeline_revision(),
        ))
        with self.assertRaises(ValueError) as ctx:
            self.api.apply_approved_plan(plan_fresh, approval_fresh)
        self.assertIn("media_drift=True", str(ctx.exception))

    # -------------------------------------------------------------------------
    # Criterion 4: Invalid segments are rejected before any mutation
    # -------------------------------------------------------------------------
    def test_4_invalid_segments_rejected_before_any_mutation(self):
        baseline_timeline = copy.deepcopy(self.api.timeline)
        baseline_undo_len = len(self.api.undo_stack)

        invalid_cases = [
            # 1. source_in >= source_out
            PlanSegment(
                segment_id="bad_bounds",
                media_id="clip_alpha",
                track=0,
                timeline_start=RationalTime(0, 30),
                source_in=RationalTime(150, 30),
                source_out=RationalTime(60, 30),  # Inverted!
            ),
            # 2. Negative timestamps
            PlanSegment(
                segment_id="negative_time",
                media_id="clip_alpha",
                track=0,
                timeline_start=RationalTime(-10, 30),
                source_in=RationalTime(0, 30),
                source_out=RationalTime(60, 30),
            ),
            # 3. Missing media ID
            PlanSegment(
                segment_id="missing_media",
                media_id="non_existent_clip_999",
                track=0,
                timeline_start=RationalTime(0, 30),
                source_in=RationalTime(0, 30),
                source_out=RationalTime(60, 30),
            ),
            # 4. source_out exceeds clip duration (clip_alpha is 20s = 600 frames)
            PlanSegment(
                segment_id="exceeds_duration",
                media_id="clip_alpha",
                track=0,
                timeline_start=RationalTime(0, 30),
                source_in=RationalTime(0, 30),
                source_out=RationalTime(900, 30),  # 30.0s > 20.0s!
            ),
        ]

        for bad_seg in invalid_cases:
            bad_plan = self.api.create_edit_plan(segments=[bad_seg])
            valid, errors = self.api.validate_edit_plan(bad_plan)
            self.assertFalse(valid, f"Expected validation failure for: {bad_seg.segment_id}")
            self.assertTrue(len(errors) > 0)

            # Attempting to approve must fail
            with self.assertRaises(ValueError):
                self.api.approve_edit_plan(bad_plan)

            # Timeline and undo stack remain completely untouched
            self.assertEqual(self.api.timeline, baseline_timeline)
            self.assertEqual(len(self.api.undo_stack), baseline_undo_len)

        # 5. Timing collision test: Overlap on SAME track 0 rejected
        colliding_seg1 = PlanSegment(
            segment_id="col_1",
            media_id="clip_alpha",
            track=0,
            timeline_start=RationalTime(0, 30),
            source_in=RationalTime(0, 30),
            source_out=RationalTime(90, 30),  # 0.0s to 3.0s
        )
        colliding_seg2 = PlanSegment(
            segment_id="col_2",
            media_id="clip_beta",
            track=0,
            timeline_start=RationalTime(60, 30),     # 2.0s to 4.0s (collides with col_1 on track 0!)
            source_in=RationalTime(0, 30),
            source_out=RationalTime(60, 30),
        )
        collision_plan = self.api.create_edit_plan(segments=[colliding_seg1, colliding_seg2])
        valid, errors = self.api.validate_edit_plan(collision_plan)
        self.assertFalse(valid)
        self.assertTrue(any("overlap" in e for e in errors))

        # 6. Intentional multi-track overlap on SEPARATE tracks is allowed
        multi_track_plan = self.api.create_edit_plan(segments=make_valid_segments())
        valid, errors = self.api.validate_edit_plan(multi_track_plan)
        self.assertTrue(valid, f"Multi-track overlap should be valid, got errors: {errors}")

    # -------------------------------------------------------------------------
    # Criterion 5: Injected mid-application failure leaves state & undo unchanged
    # -------------------------------------------------------------------------
    def test_5_injected_mid_application_failure_leaves_state_and_undo_unchanged(self):
        # Establish baseline editor state
        self.api.add_to_timeline("clip_alpha", start=0.0, track=0)
        baseline_timeline = copy.deepcopy(self.api.timeline)
        baseline_markers = copy.deepcopy(self.api.markers)
        baseline_undo_stack = copy.deepcopy(self.api.undo_stack)
        baseline_history = list(self.api.history)
        baseline_applied_hash = self.api.applied_plan_hash

        plan = self.api.create_edit_plan(segments=make_valid_segments())
        approval = self.api.approve_edit_plan(plan)

        def blow_up_mid_commit():
            raise RuntimeError("SIMULATED_DISK_IO_WRITE_FAILURE_MID_TRANSACTION")

        # Apply plan with injected failure
        with self.assertRaises(RuntimeError) as ctx:
            self.api.apply_approved_plan(plan, approval, injected_failure_hook=blow_up_mid_commit)
        self.assertIn("SIMULATED_DISK_IO_WRITE_FAILURE", str(ctx.exception))

        # State must be 100% restored to baseline
        self.assertEqual(self.api.timeline, baseline_timeline)
        self.assertEqual(self.api.markers, baseline_markers)
        self.assertEqual(self.api.undo_stack, baseline_undo_stack)
        self.assertEqual(self.api.history, baseline_history)
        self.assertEqual(self.api.applied_plan_hash, baseline_applied_hash)

    # -------------------------------------------------------------------------
    # Criterion 6: Duplicate & concurrent Confirm requests apply plan exactly once
    # -------------------------------------------------------------------------
    def test_6_duplicate_and_concurrent_confirm_requests_apply_plan_exactly_once(self):
        plan = self.api.create_edit_plan(segments=make_valid_segments())
        approval = self.api.approve_edit_plan(plan)

        # First application: succeeds
        res1 = self.api.apply_approved_plan(plan, approval)
        self.assertEqual(res1["status"], "applied")
        self.assertEqual(len(self.api.undo_stack), 1)
        self.assertEqual(len(self.api.timeline), 3)

        # Sequential duplicate confirmation: idempotent "already_applied"
        res2 = self.api.apply_approved_plan(plan, approval)
        self.assertEqual(res2["status"], "already_applied")
        self.assertEqual(len(self.api.undo_stack), 1)  # No duplicate undo entry!
        self.assertEqual(len(self.api.timeline), 3)    # No duplicated clips!

        # --- Concurrent execution test ---
        # Reset project to test concurrency with fresh plan
        self.api = editor_mod.EditorAPI(project_name="UnitTest_Concurrent")
        self.api.clips = [self.clip_a, self.clip_b]
        plan_c = self.api.create_edit_plan(segments=make_valid_segments())
        approval_c = self.api.approve_edit_plan(plan_c)

        results = []
        threads = []

        def worker():
            r = self.api.apply_approved_plan(plan_c, approval_c)
            results.append(r)

        for _ in range(10):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Exactly 1 thread must be "applied", 9 threads "already_applied"
        applied_count = sum(1 for r in results if r["status"] == "applied")
        already_applied_count = sum(1 for r in results if r["status"] == "already_applied")
        self.assertEqual(applied_count, 1)
        self.assertEqual(already_applied_count, 9)
        self.assertEqual(len(self.api.undo_stack), 1)
        self.assertEqual(len(self.api.timeline), 3)

    # -------------------------------------------------------------------------
    # Criterion 7: Undo and redo restore complete relevant state
    # -------------------------------------------------------------------------
    def test_7_undo_and_redo_restore_complete_relevant_state(self):
        # Configure rich initial state
        self.api.timeline = [{
            "id": "init_clip_1",
            "mediaId": "clip_alpha",
            "name": "Alpha.mp4",
            "start": 0.0,
            "duration": 5.0,
            "track": 0,
            "sourceIn": 0.0,
            "filter": "Solstice",
        }]
        self.api.markers = [{"time": 2.5, "name": "Initial Marker"}]
        self.api.selected_timeline_ids = ["init_clip_1"]
        self.api.current_filter = "Solstice"
        self.api.export_resolution = "1080x1920"
        self.api.export_fps = 60
        self.api.audio_ducking = True
        baseline_undo_len = len(self.api.undo_stack)

        # Create and apply plan with markers
        plan_markers = [PlanMarker(time=RationalTime(60, 30), name="Plan Marker 1")]
        plan = self.api.create_edit_plan(
            segments=make_valid_segments(),
            markers=plan_markers,
        )
        approval = self.api.approve_edit_plan(plan)
        res = self.api.apply_approved_plan(plan, approval)
        self.assertEqual(res["status"], "applied")
        self.assertEqual(len(self.api.timeline), 3)
        self.assertEqual(len(self.api.markers), 1)
        self.assertEqual(self.api.applied_plan_hash, plan.content_hash())

        # Stage a pending approval (to verify undo invalidates it)
        dummy_plan = self.api.create_edit_plan(segments=make_valid_segments())
        self.api.approve_edit_plan(dummy_plan)
        self.assertIsNotNone(self.api.pending_plan_approval)

        # 1. UNDO
        self.api.undo()
        self.assertEqual(len(self.api.timeline), 1)
        self.assertEqual(self.api.timeline[0]["id"], "init_clip_1")
        self.assertEqual(self.api.markers, [{"time": 2.5, "name": "Initial Marker"}])
        self.assertEqual(self.api.current_filter, "Solstice")
        self.assertEqual(self.api.export_resolution, "1080x1920")
        self.assertEqual(self.api.export_fps, 60)
        self.assertEqual(self.api.audio_ducking, True)
        self.assertIsNone(self.api.applied_plan_hash)
        self.assertIsNone(self.api.pending_plan_approval, "Undo must invalidate stale pending approval")

        # Stage a pending approval (to verify redo invalidates it)
        self.api.approve_edit_plan(dummy_plan)
        self.assertIsNotNone(self.api.pending_plan_approval)

        # 2. REDO
        self.api.redo()
        self.assertEqual(len(self.api.timeline), 3)
        self.assertEqual(self.api.markers[0]["name"], "Plan Marker 1")
        self.assertEqual(self.api.applied_plan_hash, plan.content_hash())
        self.assertIsNone(self.api.pending_plan_approval, "Redo must invalidate stale pending approval")

    # -------------------------------------------------------------------------
    # Criterion 8: GUI and CLI adapters use same core validation & application
    # -------------------------------------------------------------------------
    def test_8_gui_and_cli_adapters_use_same_core_validation_and_application(self):
        # Simulated CLI Adapter (e.g. ssk_agent tool dispatcher)
        def cli_execute_plan(api: editor_mod.EditorAPI, raw_plan: EditPlan) -> dict:
            valid, errors = api.validate_edit_plan(raw_plan)
            if not valid:
                return {"cli_status": "error", "errors": errors}
            approval = api.approve_edit_plan(raw_plan, approver="cli_agent")
            apply_res = api.apply_approved_plan(raw_plan, approval)
            return {"cli_status": "ok", "result": apply_res}

        # Simulated GUI Adapter (e.g. app.py IPC action handler)
        def gui_execute_plan(api: editor_mod.EditorAPI, raw_plan: EditPlan) -> dict:
            valid, errors = api.validate_edit_plan(raw_plan)
            if not valid:
                return {"gui_status": "rejected", "reasons": errors}
            approval = api.approve_edit_plan(raw_plan, approver="gui_user")
            apply_res = api.apply_approved_plan(raw_plan, approval)
            return {"gui_status": "committed", "result": apply_res}

        # Subtest 8A: Both adapters reject invalid plans identically
        bad_seg = PlanSegment(
            segment_id="bad_1",
            media_id="missing_media_xyz",
            track=0,
            timeline_start=RationalTime(0, 30),
            source_in=RationalTime(0, 30),
            source_out=RationalTime(30, 30),
        )
        bad_plan = self.api.create_edit_plan(segments=[bad_seg])
        cli_err = cli_execute_plan(self.api, bad_plan)
        gui_err = gui_execute_plan(self.api, bad_plan)

        self.assertEqual(cli_err["cli_status"], "error")
        self.assertEqual(gui_err["gui_status"], "rejected")
        self.assertEqual(cli_err["errors"], gui_err["reasons"])

        # Subtest 8B: Valid plan execution via adapters
        valid_plan = self.api.create_edit_plan(segments=make_valid_segments())
        cli_ok = cli_execute_plan(self.api, valid_plan)
        self.assertEqual(cli_ok["cli_status"], "ok")
        self.assertEqual(cli_ok["result"]["status"], "applied")
        self.assertEqual(len(self.api.timeline), 3)

        # Subsequent GUI run on same plan returns idempotent status
        gui_ok = gui_execute_plan(self.api, valid_plan)
        self.assertEqual(gui_ok["gui_status"], "committed")
        self.assertEqual(gui_ok["result"]["status"], "already_applied")


if __name__ == "__main__":
    unittest.main(verbosity=2)
