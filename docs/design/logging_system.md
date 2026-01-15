# NNRT Logging System — Channel-Aware Architecture

## Overview

This document describes the channel-aware logging system for NNRT. The system provides:

1. **Channel-based categorization** — Log messages are tagged with semantic channels
2. **Level-based filtering** — Fine-grained control over verbosity
3. **Infrastructure integration** — CLI flags, SSE streaming, GUI visualization

---

## Architecture

```
CLI (--log-level, --log-channel)
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    nnrt/core/logging.py                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Channel-aware Logger                                  │   │
│  │  - PIPELINE: pass start/end, timing                  │   │
│  │  - TRANSFORM: individual transformations             │   │
│  │  - EXTRACT: entity/identifier extraction             │   │
│  │  - POLICY: rule matching                             │   │
│  │  - RENDER: template/LLM rendering                    │   │
│  │  - SYSTEM: errors, warnings, status                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  Log Levels: SILENT(0) | INFO(1) | VERBOSE(2) | DEBUG(3)   │
└─────────────────────────────────────────────────────────────┘
                              ↓
              Server captures via LogCapture
                              ↓
         SSE stream with {channel, level, message}
                              ↓
         GUI Logs panel with channel badges & colors
```

---

## Log Channels

| Channel | Description | Example Messages |
|---------|-------------|------------------|
| `PIPELINE` | Pass orchestration | "p20_tag_spans started", "pass completed in 45ms" |
| `TRANSFORM` | Individual transformations | "removed 'deliberately'", "reframed to first-person" |
| `EXTRACT` | Entity/identifier extraction | "found badge #1234", "extracted 3 entities" |
| `POLICY` | Rule matching | "matched rule R001", "applied legal_hygiene action" |
| `RENDER` | Template/LLM rendering | "rendering 5 segments", "LLM candidate generated" |
| `SYSTEM` | Errors, warnings, status | "pipeline complete", "warning: empty input" |

---

## Log Levels

| Level | Value | Description |
|-------|-------|-------------|
| `SILENT` | 0 | No logging |
| `INFO` | 1 | Key milestones only (default) |
| `VERBOSE` | 2 | Detailed operations |
| `DEBUG` | 3 | Everything, including internal state |

---

## Configuration

### Environment Variables

```bash
NNRT_LOG_LEVEL=verbose           # Global log level
NNRT_LOG_FORMAT=console          # console or json
NNRT_LOG_CHANNELS=pipeline,policy  # Comma-separated channel filter
```

### CLI Flags

```bash
nnrt transform "text" --log-level debug --log-channel pipeline,extract
```

### Programmatic

```python
from nnrt.core.logging import configure_logging, LogLevel, LogChannel

configure_logging(
    level=LogLevel.VERBOSE,
    channels=[LogChannel.PIPELINE, LogChannel.POLICY],
)
```

---

## Implementation

### Core Logger API

```python
from nnrt.core.logging import get_logger, LogChannel

# Get a channel-specific logger
log = get_logger(LogChannel.EXTRACT)

# Log at different levels
log.info("found 3 identifiers", count=3)
log.verbose("processing segment", segment_id="seg_001")
log.debug("token analysis", token="Officer", dep="nsubj")
```

### Pass Integration

Each pass gets a pre-configured logger:

```python
# In p32_extract_entities.py
from nnrt.core.logging import get_pass_logger

PASS_NAME = "p32_extract_entities"
log = get_pass_logger(PASS_NAME, LogChannel.EXTRACT)

def extract_entities(ctx: TransformContext) -> TransformContext:
    log.info("starting entity extraction", segments=len(ctx.segments))
    
    for entity in found_entities:
        log.verbose("extracted entity", 
            label=entity.label, 
            role=entity.role.value,
        )
    
    log.info("completed", entities=len(found_entities))
    return ctx
```

---

## SSE Integration

The server captures logs and streams them via SSE:

```python
# Log entry structure
{
    "type": "log",
    "channel": "EXTRACT",
    "level": "info",
    "message": "found 3 identifiers",
    "data": {"count": 3},
    "timestamp": "2026-01-14T18:45:00Z",
    "pass": "p32_extract_entities"
}
```

---

## GUI Integration

The logs panel displays:

1. **Channel badges** — Color-coded tags (PIPELINE=blue, EXTRACT=green, etc.)
2. **Level indicators** — Icons for info/verbose/debug
3. **Filtering** — Toggle channels on/off
4. **Collapsible groups** — Group by pass or channel

### Channel Colors

| Channel | Badge Color | Hex |
|---------|-------------|-----|
| PIPELINE | Blue | #3B82F6 |
| TRANSFORM | Purple | #8B5CF6 |
| EXTRACT | Green | #10B981 |
| POLICY | Orange | #F59E0B |
| RENDER | Pink | #EC4899 |
| SYSTEM | Gray | #6B7280 |

---

## Migration Path

1. **Phase 1**: Implement core logging module with channels
2. **Phase 2**: Add CLI flags
3. **Phase 3**: Integrate with passes
4. **Phase 4**: Update server SSE streaming
5. **Phase 5**: Update GUI logs panel

---

## File Changes

| File | Changes |
|------|---------|
| `nnrt/core/logging.py` | Complete rewrite with channels |
| `nnrt/cli/main.py` | Add `--log-level`, `--log-channel` flags |
| `nnrt/passes/*.py` | Add logging calls |
| `web/server.py` | Update LogCapture for channels |
| `web/app.js` | Update logs panel rendering |
| `web/styles.css` | Add channel badge styles |

---

*Document created: 2026-01-14*
*Status: In Progress*
