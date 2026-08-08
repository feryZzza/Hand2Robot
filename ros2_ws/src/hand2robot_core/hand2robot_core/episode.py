"""Sequence-based observation/action alignment with explicit missing masks."""

from dataclasses import dataclass

from .retargeting import RobotTargetData
from .validation import EXPECTED_SCHEMA_VERSION, HandObservationData


@dataclass(frozen=True)
class EpisodeRecordData:
    schema_version: str
    episode_id: str
    step_index: int
    record_timestamp_ns: int
    observation: HandObservationData | None
    action: RobotTargetData | None
    observation_timestamp_ns: int
    action_timestamp_ns: int
    observation_missing: bool
    action_missing: bool
    task: str
    episode_complete: bool
    success: bool
    failure_reason: str


class EpisodeAligner:
    """Join by source sequence without rewriting either event timestamp."""

    def __init__(
        self,
        *,
        episode_id: str,
        task: str,
        expected_steps: int = 0,
        maximum_pending: int = 256,
    ) -> None:
        self.episode_id = str(episode_id).strip()
        self.task = str(task).strip()
        self.expected_steps = int(expected_steps)
        self.maximum_pending = int(maximum_pending)
        if not self.episode_id:
            raise ValueError("episode_id must be non-empty")
        if not self.task:
            raise ValueError("task must be non-empty")
        if self.expected_steps < 0:
            raise ValueError("expected_steps must be non-negative")
        if self.maximum_pending <= 0:
            raise ValueError("maximum_pending must be positive")
        self._observations: dict[int, HandObservationData] = {}
        self._actions: dict[int, RobotTargetData] = {}
        self._seen_observations: set[int] = set()
        self._seen_actions: set[int] = set()
        self._step_index = 0
        self.complete = False

    @property
    def pending_count(self) -> int:
        return len(set(self._observations) | set(self._actions))

    def add_observation(
        self,
        observation: HandObservationData,
        *,
        record_timestamp_ns: int,
    ) -> EpisodeRecordData | None:
        if observation.schema_version != EXPECTED_SCHEMA_VERSION:
            raise ValueError("observation schema does not match episode schema")
        sequence = observation.sequence
        if sequence in self._seen_observations:
            raise ValueError(f"duplicate observation sequence {sequence}")
        self._seen_observations.add(sequence)
        self._observations[sequence] = observation
        return self._complete_if_paired(sequence, int(record_timestamp_ns))

    def add_action(
        self,
        action: RobotTargetData,
        *,
        record_timestamp_ns: int,
    ) -> EpisodeRecordData | None:
        if action.schema_version != EXPECTED_SCHEMA_VERSION:
            raise ValueError("action schema does not match episode schema")
        sequence = action.sequence
        if sequence in self._seen_actions:
            raise ValueError(f"duplicate action sequence {sequence}")
        self._seen_actions.add(sequence)
        self._actions[sequence] = action
        return self._complete_if_paired(sequence, int(record_timestamp_ns))

    def flush_missing(
        self,
        *,
        record_timestamp_ns: int,
        failure_reason: str = "unaligned_at_flush",
    ) -> tuple[EpisodeRecordData, ...]:
        records = []
        for sequence in sorted(set(self._observations) | set(self._actions)):
            observation = self._observations.pop(sequence, None)
            action = self._actions.pop(sequence, None)
            records.append(
                self._make_record(
                    observation=observation,
                    action=action,
                    record_timestamp_ns=int(record_timestamp_ns),
                    force_complete=False,
                    success=False,
                    failure_reason=failure_reason,
                )
            )
        return tuple(records)

    def _complete_if_paired(
        self,
        sequence: int,
        record_timestamp_ns: int,
    ) -> EpisodeRecordData | None:
        if self.complete:
            self._observations.pop(sequence, None)
            self._actions.pop(sequence, None)
            return None
        if sequence not in self._observations or sequence not in self._actions:
            if self.pending_count > self.maximum_pending:
                raise ValueError("episode alignment pending buffer exceeded")
            return None
        observation = self._observations.pop(sequence)
        action = self._actions.pop(sequence)
        completing = self.expected_steps > 0 and self._step_index + 1 >= self.expected_steps
        record = self._make_record(
            observation=observation,
            action=action,
            record_timestamp_ns=record_timestamp_ns,
            force_complete=completing,
            success=completing,
            failure_reason="",
        )
        self.complete = completing
        return record

    def _make_record(
        self,
        *,
        observation: HandObservationData | None,
        action: RobotTargetData | None,
        record_timestamp_ns: int,
        force_complete: bool,
        success: bool,
        failure_reason: str,
    ) -> EpisodeRecordData:
        if record_timestamp_ns < 0:
            raise ValueError("record_timestamp_ns must be non-negative")
        record = EpisodeRecordData(
            schema_version=EXPECTED_SCHEMA_VERSION,
            episode_id=self.episode_id,
            step_index=self._step_index,
            record_timestamp_ns=record_timestamp_ns,
            observation=observation,
            action=action,
            observation_timestamp_ns=(
                observation.timestamp_ns if observation is not None else 0
            ),
            action_timestamp_ns=action.timestamp_ns if action is not None else 0,
            observation_missing=observation is None,
            action_missing=action is None,
            task=self.task,
            episode_complete=force_complete,
            success=success if force_complete else False,
            failure_reason=failure_reason,
        )
        self._step_index += 1
        return record


def episode_record_to_dict(record: EpisodeRecordData) -> dict:
    """Create a stable JSON-serializable representation for local artifacts."""

    observation = record.observation
    action = record.action
    return {
        "schema_version": record.schema_version,
        "episode_id": record.episode_id,
        "step_index": record.step_index,
        "record_timestamp_ns": record.record_timestamp_ns,
        "observation_timestamp_ns": record.observation_timestamp_ns,
        "action_timestamp_ns": record.action_timestamp_ns,
        "observation_missing": record.observation_missing,
        "action_missing": record.action_missing,
        "task": record.task,
        "episode_complete": record.episode_complete,
        "success": record.success,
        "failure_reason": record.failure_reason,
        "observation": None
        if observation is None
        else {
            "sequence": observation.sequence,
            "frame_id": observation.frame_id,
            "handedness": observation.handedness,
            "source": observation.source,
            "joints_2d_px": observation.joints_2d_px,
            "joints_3d_m": observation.joints_3d_m,
            "joints_3d_valid": observation.joints_3d_valid,
            "confidence": observation.confidence,
            "valid": observation.valid,
        },
        "action": None
        if action is None
        else {
            "sequence": action.sequence,
            "frame_id": action.frame_id,
            "position_m": action.position_m,
            "quaternion_xyzw": action.quaternion_xyzw,
            "finger_joint_names": action.finger_joint_names,
            "finger_joint_positions_rad": action.finger_joint_positions_rad,
            "max_ee_linear_velocity_m_s": action.max_ee_linear_velocity_m_s,
            "max_ee_angular_velocity_rad_s": action.max_ee_angular_velocity_rad_s,
            "max_finger_velocity_rad_s": action.max_finger_velocity_rad_s,
            "valid": action.valid,
            "status_code": int(action.status_code),
            "status_message": action.status_message,
            "mapping": action.mapping,
            "rate_limited": action.rate_limited,
        },
    }
