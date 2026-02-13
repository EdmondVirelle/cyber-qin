"""Tests for automation lanes — parameter curves with linear interpolation."""

from cyber_qin.core.automation import AutomationLane, AutomationManager, AutomationPoint


class TestAutomationPoint:
    """Tests for AutomationPoint dataclass."""

    def test_create_point(self):
        """Basic creation with time and value."""
        point = AutomationPoint(time_beats=2.0, value=0.75)
        assert point.time_beats == 2.0
        assert point.value == 0.75

    def test_create_point_with_zero_values(self):
        """Create point at time=0 with value=0."""
        point = AutomationPoint(time_beats=0.0, value=0.0)
        assert point.time_beats == 0.0
        assert point.value == 0.0

    def test_create_point_with_max_values(self):
        """Create point with value=1.0."""
        point = AutomationPoint(time_beats=100.0, value=1.0)
        assert point.time_beats == 100.0
        assert point.value == 1.0

    def test_fields_are_mutable(self):
        """Dataclass fields are mutable (not frozen)."""
        point = AutomationPoint(time_beats=2.0, value=0.5)
        point.time_beats = 4.0
        point.value = 0.8
        assert point.time_beats == 4.0
        assert point.value == 0.8

    def test_equality(self):
        """Two points with same values are equal."""
        p1 = AutomationPoint(time_beats=2.0, value=0.5)
        p2 = AutomationPoint(time_beats=2.0, value=0.5)
        assert p1 == p2


class TestAutomationLane:
    """Tests for AutomationLane interpolation and point management."""

    # ---- Basic behavior ----

    def test_empty_lane_default_value(self):
        """Empty lane returns 0.5 (mid-range) for any time."""
        lane = AutomationLane(parameter="velocity")
        assert lane.value_at(0.0) == 0.5
        assert lane.value_at(10.0) == 0.5
        assert lane.value_at(-5.0) == 0.5

    def test_single_point_constant_value(self):
        """Lane with single point returns that point's value everywhere."""
        lane = AutomationLane(parameter="velocity")
        lane.add_point(5.0, 0.8)
        assert lane.value_at(0.0) == 0.8  # Before point
        assert lane.value_at(5.0) == 0.8  # At point
        assert lane.value_at(10.0) == 0.8  # After point

    def test_two_points_linear_interpolation_midpoint(self):
        """Linear interpolation at exact midpoint between two points."""
        lane = AutomationLane(parameter="velocity")
        lane.add_point(0.0, 0.0)
        lane.add_point(10.0, 1.0)
        # At t=5.0 (midpoint), value should be 0.5
        assert lane.value_at(5.0) == 0.5

    def test_two_points_exact_values_at_endpoints(self):
        """Exact values returned at control points."""
        lane = AutomationLane(parameter="velocity")
        lane.add_point(2.0, 0.2)
        lane.add_point(8.0, 0.9)
        assert lane.value_at(2.0) == 0.2
        assert lane.value_at(8.0) == 0.9

    def test_before_first_point_returns_first_value(self):
        """Values before the first point equal first point's value."""
        lane = AutomationLane(parameter="velocity")
        lane.add_point(5.0, 0.6)
        lane.add_point(10.0, 0.8)
        assert lane.value_at(0.0) == 0.6
        assert lane.value_at(2.5) == 0.6
        assert lane.value_at(4.999) == 0.6

    def test_after_last_point_returns_last_value(self):
        """Values after the last point equal last point's value."""
        lane = AutomationLane(parameter="velocity")
        lane.add_point(5.0, 0.3)
        lane.add_point(10.0, 0.7)
        assert lane.value_at(10.0) == 0.7
        assert lane.value_at(15.0) == 0.7
        assert lane.value_at(100.0) == 0.7

    def test_multiple_points_interpolation(self):
        """Correct interpolation across multiple segments."""
        lane = AutomationLane(parameter="velocity")
        lane.add_point(0.0, 0.0)
        lane.add_point(4.0, 0.4)
        lane.add_point(10.0, 1.0)

        # First segment: 0→4 beats, 0→0.4 value
        assert lane.value_at(2.0) == 0.2  # Midpoint of first segment

        # Second segment: 4→10 beats, 0.4→1.0 value
        assert lane.value_at(7.0) == 0.7  # Midpoint of second segment

    # ---- Point management ----

    def test_add_point_replaces_existing_at_same_time(self):
        """Adding a point at existing time replaces the value."""
        lane = AutomationLane(parameter="velocity")
        lane.add_point(5.0, 0.5)
        assert len(lane.points) == 1
        lane.add_point(5.0, 0.8)
        assert len(lane.points) == 1
        assert lane.points[0].value == 0.8

    def test_add_point_clamps_value_to_zero(self):
        """Values < 0 are clamped to 0."""
        lane = AutomationLane(parameter="velocity")
        lane.add_point(5.0, -0.5)
        assert lane.points[0].value == 0.0

    def test_add_point_clamps_value_to_one(self):
        """Values > 1 are clamped to 1."""
        lane = AutomationLane(parameter="velocity")
        lane.add_point(5.0, 1.5)
        assert lane.points[0].value == 1.0

    def test_remove_point_by_index(self):
        """Remove point at valid index."""
        lane = AutomationLane(parameter="velocity")
        lane.add_point(2.0, 0.2)
        lane.add_point(5.0, 0.5)
        lane.add_point(8.0, 0.8)
        assert len(lane.points) == 3
        lane.remove_point(1)  # Remove middle point
        assert len(lane.points) == 2
        assert lane.points[0].time_beats == 2.0
        assert lane.points[1].time_beats == 8.0

    def test_remove_point_out_of_range_does_nothing(self):
        """Removing invalid index doesn't crash."""
        lane = AutomationLane(parameter="velocity")
        lane.add_point(5.0, 0.5)
        lane.remove_point(10)  # Invalid index
        assert len(lane.points) == 1

    def test_move_point_updates_position_and_value(self):
        """Move point to new time and value."""
        lane = AutomationLane(parameter="velocity")
        lane.add_point(5.0, 0.5)
        lane.move_point(0, 10.0, 0.8)
        assert lane.points[0].time_beats == 10.0
        assert lane.points[0].value == 0.8

    def test_move_point_clamps_value(self):
        """Move point clamps value to 0-1 range."""
        lane = AutomationLane(parameter="velocity")
        lane.add_point(5.0, 0.5)
        lane.move_point(0, 10.0, 1.5)
        assert lane.points[0].value == 1.0
        lane.move_point(0, 10.0, -0.5)
        assert lane.points[0].value == 0.0

    def test_move_point_clamps_time_to_non_negative(self):
        """Move point clamps time to >= 0."""
        lane = AutomationLane(parameter="velocity")
        lane.add_point(5.0, 0.5)
        lane.move_point(0, -3.0, 0.8)
        assert lane.points[0].time_beats == 0.0

    def test_points_auto_sorted_after_add(self):
        """Points are automatically sorted by time after add."""
        lane = AutomationLane(parameter="velocity")
        lane.add_point(10.0, 0.8)
        lane.add_point(2.0, 0.2)
        lane.add_point(6.0, 0.6)
        assert lane.points[0].time_beats == 2.0
        assert lane.points[1].time_beats == 6.0
        assert lane.points[2].time_beats == 10.0

    def test_points_auto_sorted_after_move(self):
        """Points are re-sorted after moving."""
        lane = AutomationLane(parameter="velocity")
        lane.add_point(2.0, 0.2)
        lane.add_point(6.0, 0.6)
        lane.add_point(10.0, 0.8)
        # Move first point to end
        lane.move_point(0, 12.0, 0.9)
        assert lane.points[0].time_beats == 6.0
        assert lane.points[1].time_beats == 10.0
        assert lane.points[2].time_beats == 12.0

    def test_clear_removes_all_points(self):
        """Clear empties the points list."""
        lane = AutomationLane(parameter="velocity")
        lane.add_point(2.0, 0.2)
        lane.add_point(5.0, 0.5)
        lane.clear()
        assert len(lane.points) == 0

    # ---- Real value mapping ----

    def test_real_value_at_maps_zero_to_min(self):
        """Normalized 0 maps to value_min."""
        lane = AutomationLane(parameter="velocity", value_min=20.0, value_max=100.0)
        lane.add_point(5.0, 0.0)
        assert lane.real_value_at(5.0) == 20.0

    def test_real_value_at_maps_one_to_max(self):
        """Normalized 1 maps to value_max."""
        lane = AutomationLane(parameter="velocity", value_min=20.0, value_max=100.0)
        lane.add_point(5.0, 1.0)
        assert lane.real_value_at(5.0) == 100.0

    def test_real_value_at_custom_range_bpm(self):
        """Custom range for BPM (40-300)."""
        lane = AutomationLane(parameter="tempo", value_min=40.0, value_max=300.0)
        lane.add_point(0.0, 0.0)  # 40 BPM
        lane.add_point(10.0, 1.0)  # 300 BPM
        # At t=5.0, normalized value is 0.5, so real = 40 + 0.5 * 260 = 170
        assert lane.real_value_at(5.0) == 170.0

    def test_real_value_at_default_range(self):
        """Default range is 0-127 (MIDI velocity)."""
        lane = AutomationLane(parameter="velocity")
        lane.add_point(5.0, 0.5)
        assert lane.real_value_at(5.0) == 63.5

    # ---- Serialization ----

    def test_to_dict_serialization(self):
        """Serialize lane to dictionary."""
        lane = AutomationLane(parameter="velocity", value_min=10.0, value_max=120.0)
        lane.add_point(2.0, 0.2)
        lane.add_point(5.0, 0.8)
        data = lane.to_dict()
        assert data["parameter"] == "velocity"
        assert data["value_min"] == 10.0
        assert data["value_max"] == 120.0
        assert len(data["points"]) == 2
        assert data["points"][0] == {"time": 2.0, "value": 0.2}
        assert data["points"][1] == {"time": 5.0, "value": 0.8}

    def test_from_dict_deserialization_roundtrip(self):
        """Deserialize lane from dictionary and verify roundtrip."""
        lane = AutomationLane(parameter="tempo", value_min=40.0, value_max=300.0)
        lane.add_point(1.0, 0.1)
        lane.add_point(5.0, 0.9)

        data = lane.to_dict()
        lane2 = AutomationLane.from_dict(data)

        assert lane2.parameter == "tempo"
        assert lane2.value_min == 40.0
        assert lane2.value_max == 300.0
        assert len(lane2.points) == 2
        assert lane2.points[0].time_beats == 1.0
        assert lane2.points[0].value == 0.1
        assert lane2.points[1].time_beats == 5.0
        assert lane2.points[1].value == 0.9

    def test_from_dict_sorts_points(self):
        """from_dict ensures points are sorted even if input is unsorted."""
        data = {
            "parameter": "velocity",
            "value_min": 0.0,
            "value_max": 127.0,
            "points": [
                {"time": 10.0, "value": 0.8},
                {"time": 2.0, "value": 0.2},
                {"time": 6.0, "value": 0.6},
            ],
        }
        lane = AutomationLane.from_dict(data)
        assert lane.points[0].time_beats == 2.0
        assert lane.points[1].time_beats == 6.0
        assert lane.points[2].time_beats == 10.0

    # ---- Binary search correctness ----

    def test_binary_search_many_points(self):
        """Binary search works correctly with many points."""
        lane = AutomationLane(parameter="velocity")
        # Add 100 points
        for i in range(100):
            lane.add_point(float(i), float(i) / 100.0)

        # Test interpolation between points 50 and 51
        # At t=50.5, value should be (0.50 + 0.51) / 2 = 0.505
        assert abs(lane.value_at(50.5) - 0.505) < 1e-9

    def test_binary_search_edge_case_two_points(self):
        """Binary search with exactly two points."""
        lane = AutomationLane(parameter="velocity")
        lane.add_point(0.0, 0.0)
        lane.add_point(100.0, 1.0)
        # At t=25, value should be 0.25
        assert lane.value_at(25.0) == 0.25
        # At t=75, value should be 0.75
        assert lane.value_at(75.0) == 0.75

    def test_interpolation_precision(self):
        """Interpolation maintains high precision."""
        lane = AutomationLane(parameter="velocity")
        lane.add_point(0.0, 0.0)
        lane.add_point(1.0, 1.0)
        # At t=0.333..., value should be very close to 0.333...
        val = lane.value_at(1.0 / 3.0)
        assert abs(val - (1.0 / 3.0)) < 1e-9


class TestAutomationManager:
    """Tests for AutomationManager multi-lane management."""

    # ---- Basic operations ----

    def test_empty_manager_has_no_lanes(self):
        """Newly created manager has no lanes."""
        mgr = AutomationManager()
        assert len(mgr.lanes) == 0

    def test_ensure_lane_creates_new_lane(self):
        """ensure_lane creates a lane if it doesn't exist."""
        mgr = AutomationManager()
        lane = mgr.ensure_lane("velocity")
        assert lane.parameter == "velocity"
        assert "velocity" in mgr.lanes

    def test_ensure_lane_returns_existing(self):
        """ensure_lane returns existing lane without creating duplicate."""
        mgr = AutomationManager()
        lane1 = mgr.ensure_lane("velocity")
        lane1.add_point(5.0, 0.5)
        lane2 = mgr.ensure_lane("velocity")
        assert lane1 is lane2
        assert len(mgr.lanes) == 1

    def test_ensure_lane_with_custom_range(self):
        """ensure_lane creates lane with custom value range."""
        mgr = AutomationManager()
        lane = mgr.ensure_lane("tempo", value_min=40.0, value_max=300.0)
        assert lane.value_min == 40.0
        assert lane.value_max == 300.0

    def test_get_lane_returns_none_for_missing(self):
        """get_lane returns None if lane doesn't exist."""
        mgr = AutomationManager()
        assert mgr.get_lane("velocity") is None

    def test_get_lane_returns_existing_lane(self):
        """get_lane returns existing lane."""
        mgr = AutomationManager()
        mgr.ensure_lane("velocity")
        lane = mgr.get_lane("velocity")
        assert lane is not None
        assert lane.parameter == "velocity"

    def test_remove_lane_removes_existing(self):
        """remove_lane removes an existing lane."""
        mgr = AutomationManager()
        mgr.ensure_lane("velocity")
        assert "velocity" in mgr.lanes
        mgr.remove_lane("velocity")
        assert "velocity" not in mgr.lanes

    def test_remove_lane_missing_does_nothing(self):
        """remove_lane on non-existent lane doesn't crash."""
        mgr = AutomationManager()
        mgr.remove_lane("nonexistent")  # Should not raise

    # ---- Value queries ----

    def test_value_at_returns_none_for_missing_lane(self):
        """value_at returns None if lane doesn't exist."""
        mgr = AutomationManager()
        assert mgr.value_at("velocity", 5.0) is None

    def test_value_at_returns_interpolated_real_value(self):
        """value_at returns interpolated real value from lane."""
        mgr = AutomationManager()
        lane = mgr.ensure_lane("velocity", value_min=0.0, value_max=127.0)
        lane.add_point(0.0, 0.0)
        lane.add_point(10.0, 1.0)
        # At t=5.0, normalized value is 0.5, real value is 63.5
        assert mgr.value_at("velocity", 5.0) == 63.5

    def test_value_at_multiple_lanes(self):
        """value_at works correctly with multiple lanes."""
        mgr = AutomationManager()

        vel_lane = mgr.ensure_lane("velocity", value_min=0.0, value_max=127.0)
        vel_lane.add_point(5.0, 0.5)

        tempo_lane = mgr.ensure_lane("tempo", value_min=60.0, value_max=180.0)
        tempo_lane.add_point(5.0, 0.5)

        assert mgr.value_at("velocity", 5.0) == 63.5
        assert mgr.value_at("tempo", 5.0) == 120.0

    # ---- Clear and reset ----

    def test_clear_removes_all_lanes(self):
        """clear removes all lanes."""
        mgr = AutomationManager()
        mgr.ensure_lane("velocity")
        mgr.ensure_lane("tempo")
        mgr.ensure_lane("pan")
        assert len(mgr.lanes) == 3
        mgr.clear()
        assert len(mgr.lanes) == 0

    # ---- Deep copy ----

    def test_deep_copy_creates_independent_copy(self):
        """deep_copy creates a new manager with copied lanes."""
        mgr = AutomationManager()
        lane = mgr.ensure_lane("velocity")
        lane.add_point(5.0, 0.5)
        lane.add_point(10.0, 0.8)

        mgr2 = mgr.deep_copy()
        assert len(mgr2.lanes) == 1
        lane2 = mgr2.get_lane("velocity")
        assert lane2 is not None
        assert len(lane2.points) == 2

    def test_modifying_copy_does_not_affect_original(self):
        """Modifying deep_copy doesn't affect original."""
        mgr = AutomationManager()
        lane = mgr.ensure_lane("velocity")
        lane.add_point(5.0, 0.5)

        mgr2 = mgr.deep_copy()
        lane2 = mgr2.get_lane("velocity")
        lane2.add_point(10.0, 0.8)

        # Original should still have only 1 point
        lane_orig = mgr.get_lane("velocity")
        assert len(lane_orig.points) == 1
        assert len(lane2.points) == 2

    def test_deep_copy_copies_points_not_references(self):
        """deep_copy creates new point objects, not references."""
        mgr = AutomationManager()
        lane = mgr.ensure_lane("velocity")
        lane.add_point(5.0, 0.5)

        mgr2 = mgr.deep_copy()
        lane2 = mgr2.get_lane("velocity")

        # Modify point in copy
        lane2.points[0].value = 0.9

        # Original should be unchanged
        assert mgr.get_lane("velocity").points[0].value == 0.5

    # ---- Serialization ----

    def test_to_dict_serialization_with_multiple_lanes(self):
        """Serialize manager with multiple lanes."""
        mgr = AutomationManager()

        vel = mgr.ensure_lane("velocity", value_min=0.0, value_max=127.0)
        vel.add_point(2.0, 0.2)
        vel.add_point(8.0, 0.8)

        tempo = mgr.ensure_lane("tempo", value_min=60.0, value_max=180.0)
        tempo.add_point(5.0, 0.5)

        data = mgr.to_dict()
        assert "velocity" in data
        assert "tempo" in data
        assert len(data["velocity"]["points"]) == 2
        assert len(data["tempo"]["points"]) == 1

    def test_from_dict_deserialization_roundtrip(self):
        """Deserialize manager from dict and verify roundtrip."""
        mgr = AutomationManager()

        vel = mgr.ensure_lane("velocity", value_min=10.0, value_max=120.0)
        vel.add_point(1.0, 0.1)
        vel.add_point(9.0, 0.9)

        tempo = mgr.ensure_lane("tempo", value_min=40.0, value_max=300.0)
        tempo.add_point(5.0, 0.5)

        data = mgr.to_dict()
        mgr2 = AutomationManager.from_dict(data)

        # Verify velocity lane
        vel2 = mgr2.get_lane("velocity")
        assert vel2 is not None
        assert vel2.value_min == 10.0
        assert vel2.value_max == 120.0
        assert len(vel2.points) == 2

        # Verify tempo lane
        tempo2 = mgr2.get_lane("tempo")
        assert tempo2 is not None
        assert tempo2.value_min == 40.0
        assert tempo2.value_max == 300.0
        assert len(tempo2.points) == 1

    def test_from_dict_empty_manager(self):
        """Deserialize empty manager."""
        data = {}
        mgr = AutomationManager.from_dict(data)
        assert len(mgr.lanes) == 0

    # ---- Lanes property ----

    def test_lanes_property_returns_dict_copy(self):
        """lanes property returns a copy, not the internal dict."""
        mgr = AutomationManager()
        mgr.ensure_lane("velocity")

        lanes_copy = mgr.lanes
        lanes_copy["tempo"] = AutomationLane(parameter="tempo")

        # Internal dict should be unchanged
        assert "tempo" not in mgr.lanes
        assert len(mgr.lanes) == 1

    def test_multiple_lanes_for_different_parameters(self):
        """Manager can store multiple lanes with different parameters."""
        mgr = AutomationManager()

        mgr.ensure_lane("velocity")
        mgr.ensure_lane("tempo")
        mgr.ensure_lane("pan")
        mgr.ensure_lane("modulation")

        assert len(mgr.lanes) == 4
        assert "velocity" in mgr.lanes
        assert "tempo" in mgr.lanes
        assert "pan" in mgr.lanes
        assert "modulation" in mgr.lanes
