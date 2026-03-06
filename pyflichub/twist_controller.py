import asyncio
import time
from typing import Optional, Callable, Dict, Any


def clamp(x: float, min_val: float, max_val: float) -> float:
    return min_val if x < min_val else (max_val if x > max_val else x)


def sign(x: float) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)


class RateDetentController:
    """
    Controller for Flic Twist rotation.
    Handles converting raw positional values to smooth, variable-speed detent increments
    with features like sticky neutral, debounce, and speed tiers.
    """
    def __init__(
        self,
        cfg: Optional[Dict[str, Any]] = None,
        on_change_callback: Optional[Callable[[Optional[int]], None]] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None
    ):
        if cfg is None:
            cfg = {}

        self.cfg = cfg
        self.on_change_callback = on_change_callback
        self._loop = loop

        self.tick_ms = self.cfg.get("tickMs", 333)

        # Neutral hysteresis
        self.deadband_enter = self.cfg.get("deadbandEnter", 5)
        self.deadband_exit = self.cfg.get("deadbandExit", 9)

        # Speed tiers
        self.tier1_max_off = self.cfg.get("tier1MaxOff", 25)
        self.tier2_max_off = self.cfg.get("tier2MaxOff", 50)
        self.tier_hys = self.cfg.get("tierHys", 3)

        # Output clamp
        self.min_out_pct = self.cfg.get("minOutPct", 0)
        self.max_out_pct = self.cfg.get("maxOutPct", 100)

        # --- soft recenter tuning ---
        self.neutral_recenter_alpha = self.cfg.get("neutralRecenterAlpha", 0.08)

        # --- debounce for easing into fine mode ---
        self.ease_confirm_ms = self.cfg.get("easeConfirmMs", 200)

        # State
        self.center_in_pct = None
        self.actual_out_pct = self.cfg.get("initialOutPct", None)

        self.fine_mode = False

        self.last_dir = 0
        self.last_speed = 0

        self.current_dir = 0
        self.current_speed = 0

        self.neutral_latched = False
        self.speed_latched = 0

        # For debouncing easing
        self._ease_candidate_since = None
        self._ease_candidate_dir = 0

        self._last_intent_key = None

        self._running = True
        self._timer_task = None

    def _desired_speed(self, abs_off: float) -> int:
        if abs_off <= self.tier1_max_off:
            return 1
        if abs_off <= self.tier2_max_off:
            return 2
        return 3

    def _update_latched_speed(self, desired: int, abs_off: float) -> None:
        if self.speed_latched == 0:
            self.speed_latched = desired
            return

        if self.speed_latched == 1:
            if desired >= 2 and abs_off >= (self.tier1_max_off + self.tier_hys):
                self.speed_latched = 2
            if desired == 3 and abs_off >= (self.tier2_max_off + self.tier_hys):
                self.speed_latched = 3
            return

        if self.speed_latched == 2:
            if abs_off <= (self.tier1_max_off - self.tier_hys):
                self.speed_latched = 1
                return
            if desired == 3 and abs_off >= (self.tier2_max_off + self.tier_hys):
                self.speed_latched = 3
                return
            return

        if self.speed_latched == 3:
            if abs_off <= (self.tier2_max_off - self.tier_hys):
                self.speed_latched = 2

    def _base_intent(self, raw_in_pct: float) -> dict:
        if self.center_in_pct is None:
            self.center_in_pct = raw_in_pct
            self.neutral_latched = True
            self.speed_latched = 0
            return {"dir": 0, "speed": 0, "desiredSpeed": 0, "reason": "center set"}

        off = raw_in_pct - self.center_in_pct
        abs_off = abs(off)

        # --- Sticky neutral with SOFT RECENTER ---
        if self.neutral_latched:
            if abs_off <= self.deadband_exit:
                # soft recenter while resting
                self.center_in_pct = self.center_in_pct + self.neutral_recenter_alpha * (raw_in_pct - self.center_in_pct)
                self.speed_latched = 0
                return {"dir": 0, "speed": 0, "desiredSpeed": 0, "reason": "deadband (latched)"}
            self.neutral_latched = False
        else:
            if abs_off <= self.deadband_enter:
                self.neutral_latched = True
                self.speed_latched = 0
                return {"dir": 0, "speed": 0, "desiredSpeed": 0, "reason": "deadband (enter)"}

        dir_val = sign(off)
        desired_speed = self._desired_speed(abs_off)
        self._update_latched_speed(desired_speed, abs_off)

        speed = 1 if self.speed_latched == 0 else self.speed_latched
        return {"dir": dir_val, "speed": speed, "desiredSpeed": desired_speed, "reason": "detent"}

    def _apply_fine_mode(self, base: dict) -> dict:
        dir_val = base["dir"]
        speed = base["speed"]
        desired_speed = base["desiredSpeed"]
        now = time.time() * 1000  # ms

        direction_changed = (self.last_dir != 0 and dir_val != 0 and dir_val != self.last_dir)
        hit_neutral_from_intent = (self.last_speed > 0 and speed == 0)

        # --- Debounced easing detection ---
        eased_confirmed = False

        easing_candidate = (
            self.last_speed >= 2 and
            desired_speed > 0 and
            desired_speed < self.last_speed and
            dir_val == self.last_dir
        )

        if easing_candidate:
            if self._ease_candidate_since is None:
                self._ease_candidate_since = now
                self._ease_candidate_dir = dir_val
            elif (self._ease_candidate_dir == dir_val and
                  (now - self._ease_candidate_since) >= self.ease_confirm_ms):
                eased_confirmed = True
        else:
            self._ease_candidate_since = None
            self._ease_candidate_dir = 0

        if not self.fine_mode and (direction_changed or hit_neutral_from_intent or eased_confirmed):
            self.fine_mode = True
            self._ease_candidate_since = None

            if speed == 0:
                self.fine_mode = False
                return {"dir": 0, "speed": 0, "note": "enter fine (neutral)"}
            if direction_changed:
                return {"dir": dir_val, "speed": 1, "note": "enter fine (turn)"}
            if eased_confirmed:
                return {"dir": dir_val, "speed": 1, "note": "enter fine (ease)"}
            return {"dir": dir_val, "speed": 1, "note": "enter fine"}

        if self.fine_mode:
            if speed == 0:
                self.fine_mode = False
                return {"dir": 0, "speed": 0, "note": "fine mode (exit)"}
            return {"dir": dir_val, "speed": 1, "note": "fine mode"}

        return {"dir": dir_val, "speed": speed, "note": None}

    def update_raw(self, raw_in_pct: float) -> Optional[dict]:
        if not isinstance(raw_in_pct, (int, float)):
            return None

        if self._timer_task is None and self._running:
            try:
                loop = asyncio.get_running_loop()
                self._timer_task = loop.create_task(self._tick_loop())
            except RuntimeError:
                if self._loop is not None:
                    self._timer_task = asyncio.run_coroutine_threadsafe(self._tick_loop(), self._loop)
                else:
                    self._timer_task = asyncio.get_event_loop().create_task(self._tick_loop())

        if self.actual_out_pct is None:
            self.actual_out_pct = self.min_out_pct
        if self.center_in_pct is None:
            self.center_in_pct = raw_in_pct

        base = self._base_intent(raw_in_pct)
        applied = self._apply_fine_mode(base)

        self.current_dir = applied["dir"]
        self.current_speed = applied["speed"]

        note = applied["note"] or base.get("reason") or None

        key = f"{self.current_dir}|{self.current_speed}|{'F' if self.fine_mode else '-'}|{'N' if self.neutral_latched else '-'}|{note or ''}"

        intent_changed = (key != self._last_intent_key)
        self._last_intent_key = key

        self.last_dir = self.current_dir
        self.last_speed = self.current_speed

        return {
            "intentChanged": intent_changed,
            "rawInPct": raw_in_pct,
            "dir": self.current_dir,
            "speed": self.current_speed,
            "fineMode": self.fine_mode,
            "note": note
        }

    async def _tick_loop(self):
        while self._running:
            await asyncio.sleep(self.tick_ms / 1000.0)
            self._tick()

    def _tick(self):
        if self.actual_out_pct is None:
            return
        if self.current_dir == 0 or self.current_speed == 0:
            return

        old_out = self.get_actual_out_pct()
        self.actual_out_pct = clamp(
            self.actual_out_pct + (self.current_dir * self.current_speed),
            self.min_out_pct,
            self.max_out_pct
        )
        new_out = self.get_actual_out_pct()

        if old_out != new_out and self.on_change_callback:
            self.on_change_callback(new_out)

    def get_actual_out_pct(self) -> Optional[int]:
        return int(round(self.actual_out_pct)) if self.actual_out_pct is not None else None

    def stop(self) -> Optional[int]:
        self._running = False
        if self._timer_task:
            self._timer_task.cancel()
            self._timer_task = None
        return self.get_actual_out_pct()
