## ADDED Requirements

### Requirement: Persistent State Storage
The system SHALL maintain all autopilot session data (roadmap, task status, handover capsules) in a persistent `.autopilot_state.json` file.

#### Scenario: Atomic state update
- **WHEN** a task status changes or a handover is generated
- **THEN** the system SHALL immediately persist the updated state to the `.autopilot_state.json` file.

### Requirement: Session Resume and Recovery
The system SHALL be able to resume an interrupted autopilot session by reading the existing state from disk.

#### Scenario: Resuming after a crash
- **WHEN** the user restarts Meto in autopilot mode and a state file exists
- **THEN** the system SHALL offer to resume from the last pending task in the roadmap.

### Requirement: State Visualization
The system SHALL provide a clear visual representation of the autopilot progress, showing completed, active, and pending tasks.

#### Scenario: Viewing progress in the CLI
- **WHEN** an autopilot session is running
- **THEN** the system SHALL display a rich UI element (e.g., a progress bar or checklist) showing the overall completion percentage.
