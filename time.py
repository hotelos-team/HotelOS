from datetime import datetime, timedelta, timezone
import time

class SimulationClock:

    def __init__(self, start_time=None, speed=60):
        self.simulated_time = (
            start_time or datetime.now(timezone.utc)
        )

        self.speed = speed
        self.real_anchor = time.monotonic()

    def now(self):
        real_elapsed = time.monotonic() - self.real_anchor

        simulated_elapsed = real_elapsed * self.speed
        print(timedelta(seconds=simulated_elapsed))
        return self.simulated_time + timedelta(
            seconds=simulated_elapsed
        )

    def set_speed(self, new_speed):
        # First calculate time at the old speed
        current_time = self.now()

        # Re-anchor the clock
        self.simulated_time = current_time
        self.real_anchor = time.monotonic()

        # Apply new speed
        self.speed = new_speed
