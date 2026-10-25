import time
import threading
from collections import defaultdict
from contextlib import contextmanager

class PerfProfiler:
    def __init__(self, interval_sec: float = 1.0, bar_length: int = 24, ENABLE_PROFILER = False):
        self.interval_sec = interval_sec
        self.bar_length = bar_length
        self._lock = threading.Lock()
        self._timings = defaultdict(list)
        self._last_print_time = time.monotonic()
        self.ENABLE_PROFILER = ENABLE_PROFILER

    @contextmanager
    def measure(self, tag: str):
        if not self.ENABLE_PROFILER:
            yield
            return
        t0 = time.perf_counter()
        try:
            yield
        finally:
            t1 = time.perf_counter()
            elapsed_ms = (t1 - t0) * 1000.0
            with self._lock:
                self._timings[tag].append(elapsed_ms)
                now = time.monotonic()
                if now - self._last_print_time >= self.interval_sec:
                    self._print_report()
                    self._timings.clear()
                    self._last_print_time = now

    def _print_report(self):
        if not self._timings:
            return
        stats = []
        for tag, values in self._timings.items():
            if not values:
                continue
            avg_ms = sum(values) / len(values)
            max_ms = max(values)
            cnt = len(values)
            stats.append((tag, avg_ms, max_ms, cnt))

        if not stats:
            return
        stats.sort(key=lambda x: x[1], reverse=True)
        max_avg = max(x[1] for x in stats) if stats else 1.0

        C_CYAN, C_GREEN, C_YELLOW, C_RED, C_GRAY, C_BOLD, C_RESET = (
            "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[90m", "\033[1m", "\033[0m"
        )
        lines = [
            f"\n{C_BOLD}{C_CYAN}┌─────────────────────────── [ PERFORMANCE REPORT ] ───────────────────────────┐{C_RESET}",
            f"{C_BOLD}{C_GRAY}│ {'SECTION':<30} │ {'AVG (ms)':>8} │ {'MAX (ms)':>8} │ {'CALLS':>5} │ {'GRAPH':<{self.bar_length}} │{C_RESET}",
            f"{C_GRAY}├────────────────────────────────┼──────────┼──────────┼───────┼──────────────────────────┤{C_RESET}"
        ]
        for tag, avg_ms, max_ms, cnt in stats:
            ratio = (avg_ms / max_avg) if max_avg > 0 else 0
            filled = int(round(ratio * self.bar_length))
            color = C_RED if avg_ms >= 10.0 else (C_YELLOW if avg_ms >= 4.0 else C_GREEN)
            bar = "█" * filled + "░" * (self.bar_length - filled)
            lines.append(f"│ {tag:<30} │ {color}{avg_ms:>8.2f}{C_RESET} │ {max_ms:>8.2f} │ {cnt:>5} │ {color}{bar}{C_RESET} │")

        lines.append(f"{C_CYAN}└────────────────────────────────┴──────────┴──────────┴───────┴──────────────────────────┘{C_RESET}")
        print("\n".join(lines), flush=True)