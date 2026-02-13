"""Benchmark NoteRoll rendering performance with varying MIDI file sizes."""

import time
from dataclasses import dataclass


@dataclass
class BeatNote:
    """Mock BeatNote for testing."""
    time_beats: float
    note: int
    duration_beats: float


def simulate_paint_event_current(notes: list[BeatNote], viewport_start: float, viewport_end: float, zoom: float) -> int:
    """Simulate current O(n) rendering logic."""
    rendered_count = 0
    viewport_width = 1920  # pixels

    for note in notes:
        x = (note.time_beats * zoom)
        nw = max(4.0, note.duration_beats * zoom)

        # Viewport culling (but after iterating!)
        if x + nw < 0 or x > viewport_width:
            continue

        rendered_count += 1

    return rendered_count


def simulate_paint_event_optimized(notes: list[BeatNote], viewport_start: float, viewport_end: float, zoom: float) -> int:
    """Simulate O(log n + k) rendering with binary search."""
    import bisect

    # Binary search for first visible note
    times = [n.time_beats for n in notes]
    start_idx = bisect.bisect_left(times, viewport_start - 1.0)  # -1.0 for note width buffer
    end_idx = bisect.bisect_right(times, viewport_end + 1.0)

    rendered_count = 0
    viewport_width = 1920

    for note in notes[start_idx:end_idx]:
        x = (note.time_beats * zoom)
        nw = max(4.0, note.duration_beats * zoom)

        if x + nw < 0 or x > viewport_width:
            continue

        rendered_count += 1

    return rendered_count


def generate_test_midi(num_notes: int) -> list[BeatNote]:
    """Generate a synthetic MIDI file with evenly distributed notes."""
    notes = []
    for i in range(num_notes):
        time_beats = i * 0.5  # One note every half beat
        note = 60 + (i % 24)  # Pitch range 60-83 (C4-B5)
        duration_beats = 0.25
        notes.append(BeatNote(time_beats, note, duration_beats))
    return notes


def benchmark():
    """Run performance comparison."""
    test_sizes = [100, 500, 1000, 5000, 10000, 20000]
    zoom = 80.0  # pixels per beat
    viewport_start = 50.0  # beats (scrolled to middle)
    viewport_end = 74.0    # viewport shows ~24 beats (1920px / 80px)

    print("=" * 80)
    print("NoteRoll Rendering Performance Benchmark")
    print("=" * 80)
    print(f"Viewport: {viewport_start:.1f} - {viewport_end:.1f} beats ({viewport_end - viewport_start:.1f} beats visible)")
    print(f"Zoom: {zoom} pixels/beat\n")

    results = []

    for size in test_sizes:
        notes = generate_test_midi(size)

        # Current implementation (O(n))
        start = time.perf_counter()
        for _ in range(100):  # Run 100 times to get stable measurement
            simulate_paint_event_current(notes, viewport_start, viewport_end, zoom)
        current_time = (time.perf_counter() - start) / 100 * 1000  # ms per call

        # Optimized implementation (O(log n + k))
        start = time.perf_counter()
        for _ in range(100):
            simulate_paint_event_optimized(notes, viewport_start, viewport_end, zoom)
        optimized_time = (time.perf_counter() - start) / 100 * 1000  # ms per call

        speedup = current_time / optimized_time if optimized_time > 0 else float('inf')

        results.append({
            'size': size,
            'current_ms': current_time,
            'optimized_ms': optimized_time,
            'speedup': speedup
        })

        print(f"{'Notes':<10} {'Current':<15} {'Optimized':<15} {'Speedup':<10}")
        print(f"{size:<10} {current_time:>10.3f} ms   {optimized_time:>10.3f} ms   {speedup:>8.1f}x")

    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)

    # Frame time analysis (60 FPS = 16.67ms budget)
    fps_budget = 16.67  # ms

    print(f"\nFrame budget for 60 FPS: {fps_budget:.2f} ms\n")
    print(f"{'Notes':<10} {'Current FPS':<15} {'Optimized FPS':<15} {'Status':<20}")
    print("-" * 80)

    for r in results:
        current_fps = 1000 / r['current_ms'] if r['current_ms'] > 0 else float('inf')
        optimized_fps = 1000 / r['optimized_ms'] if r['optimized_ms'] > 0 else float('inf')

        if r['current_ms'] > fps_budget:
            status = "[!] DROPS FRAMES"
        else:
            status = "[OK] Smooth"

        print(f"{r['size']:<10} {current_fps:>10.0f} fps   {optimized_fps:>10.0f} fps   {status:<20}")

    print("\n" + "=" * 80)
    print("Recommendations")
    print("=" * 80)

    critical_size = None
    for r in results:
        if r['current_ms'] > fps_budget:
            critical_size = r['size']
            break

    if critical_size:
        print(f"\n[!] Current implementation drops below 60 FPS at {critical_size} notes")
        print(f"    -> Optimization RECOMMENDED for MIDI files with >{critical_size // 2} notes")
    else:
        print(f"\n[OK] Current implementation maintains 60 FPS up to {test_sizes[-1]} notes")
        print("     -> Optimization optional (future-proofing)")

    print("\nExpected improvement with binary search optimization:")
    avg_speedup = sum(r['speedup'] for r in results[-3:]) / 3  # Average of largest 3 sizes
    print(f"  -> {avg_speedup:.1f}x faster for large MIDI files (>5000 notes)")
    print("  -> Enables smooth playback of complex orchestral scores\n")


if __name__ == "__main__":
    benchmark()
