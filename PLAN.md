# Plan: mapart-bedrock-gui
**Created:** 2026-06-09
**Based on:** vault:/01_Projects/mapart-bedrock-gui
**Source:** C:\Users\aeina\OneDrive\Desktop\mapart-bedrock-gui

## Goal
Desktop GUI that converts images into Minecraft Bedrock map art (128x128). Supports RGB and CIE Lab color matching with dithering, palette filtering, staircasing modes, and WebSocket-based in-game block placement.

## Current State

### What Exists
- 7 Python source files in `mapart_bedrock_gui/` (~3,100 lines total)
- `app.py` (1251 lines) - Monolithic GUI with customtkinter, all UI logic, config, theme system
- `colour_data.py` (1012 lines) - 64 Minecraft colour sets with RGB tones + block mappings
- `processor.py` (224 lines) - Image-to-block conversion with RGB and CIE Lab Delta-E matching
- `builder.py` (356 lines) - WebSocket server using bedrockpy/adorkable, in-game build/coords/help/testblock commands
- `dither.py` (143 lines) - 7 algorithms: Floyd-Steinberg, Bayer 4x4/2x2, Burkes, Sierra-Lite, Stucki, Atkinson
- `presets.py` (71 lines) - Palette mode filtering (all, wool, carpets, concrete, terracotta, greyscale)
- `coordinates.py` (45 lines) - Save/load/list/clear build coordinates
- `pyproject.toml` - Poetry-based build with entry point `mapart-gui`
- `README.md` - Good user-facing docs
- `AGENTS.md` - Basic usage instructions
- `CONTEXT.md` - Partial, lacks architecture section
- `launch.bat` - Double-click launcher for Windows
- `charcoal.json` - Auto-generated theme template (can remove from tracking)

### What Works
- Full MVP: image selection, crop/stretch dialog, 128x128 conversion, preview with pixelated block view
- 6 palette modes, 7 dither algorithms, 3 staircasing modes
- RGB and CIE Lab Delta-E color distance
- WebSocket server binds on configurable address:port
- In-game `#build`, `#coords saveat/list/clear`, `#testblock`, `#help` commands
- Give Materials auto-gift mode
- `/give @s` clipboard copy
- Preset save/load (JSON), config persistence, custom theme system
- Dimension selector (overworld/end/nether)
- Gravity block support placement

### What's Missing or Broken
- **Duplicate entries** in `colour_data.py:258-260`: `orange_concrete_powder` and `orange_glazed_terracotta` appear twice under Orange Wool colour set 14
- **No tests** - zero test coverage anywhere
- **No linting config** - no ruff, flake8, or black config
- **No type checking** - no pyright/mypy config, many untyped signatures
- **CONTEXT.md incomplete** - no architecture section, no file mapping, no known-issues
- **AGENTS.md is thin** - duplicates README, no build/dev commands
- **Project location** on C: drive OneDrive (should migrate to D:\Cobalt\Projects\)
- **Version-specific block filtering** not implemented (vault-listed improvement)
- **PyInstaller bundling** not done (vault-listed improvement)
- **Duplicate color-swatch entries** in `app.py:394-401` (both `#ff8888` and `#88aaff` appear twice)
- **app.py is monolithic** - all 1251 lines in one file, hard to test/modify

## Architecture Approach
- **Stack:** Python 3.11+, customtkinter (GUI), Pillow/numpy (image processing), bedrockpy/adorkable (WebSocket server)
- **Patterns:** Monolithic GUI class delegates to pure functions for image processing. Builder class wraps WebSocket event handlers. Config via JSON files in `~/.mapart/`.
- **Data flow:** `colour_data.py` (block definitions) -> `presets.py` (palette filtering) -> `processor.py` (color matching) <- `dither.py` (optional) -> GUI preview + `builder.py` (in-game placement)
- **Design decisions:**
  - Keep GUI as single file for now (not complex enough to split)
  - Extract image-processing logic from `app.py` into processor if any GUI-less functionality is needed
  - No external services - purely local tool
  - Config versioning (`CONFIG_VERSION = 2`) is a good pattern, keep it

## Implementation Phases

### Phase 0: Project Migration & Dev Tooling (BUILDER READY)
**Scope:** Move project off OneDrive, add dev infrastructure
**Files affected:** All (new path), plus per-file changes for imports, config paths
**Estimated scope:** medium

#### Tasks
1. Move project from `C:\Users\aeina\OneDrive\Desktop\mapart-bedrock-gui` to `D:\Cobalt\Projects\mapart-bedrock-gui`
2. Update all internal path references (config paths, imports, `__init__.py`)
3. Verify `pip install -e .` works at new location
4. Add `ruff` config to `pyproject.toml`
5. Add `pyright` config to `pyproject.toml`
6. Run `ruff check --fix` across entire project
7. Create initial test infrastructure with `pytest`

**User input needed:** None

---

### Phase 1: Minor Safe Bug Fixes (BUILDER READY)
**Scope:** Fix duplicate colour entries -- cosmetic, no functional risk
**Dependencies:** Phase 0 complete
**Files affected:** `colour_data.py`, `app.py`
**Estimated scope:** tiny

#### Tasks
1. Remove duplicate entries `orange_concrete_powder` and `orange_glazed_terracotta` at `colour_data.py:258-260`
2. Remove duplicate color-swatch entries at `app.py:394-401` (both `#ff8888` and `#88aaff`)

**User input needed:** None

---

### Phase 2: UI Overhaul (1-ON-1 WITH COBALT)
**Scope:** Full UI redesign using UI/UX Pro Max + Refero skills. Re-evaluate customtkinter vs modern alternatives.
**Dependencies:** Phase 0 complete
**Files affected:** Major changes to `app.py`, potentially new frontend framework
**Estimated scope:** large

#### Tasks
1. Schedule 1-on-1 design session with Cobalt
2. Conduct Refero design research (competitor amp sim UIs, modern DAW aesthetics)
3. Present 3 style options (clean dark, skeuomorphic amp, minimal) 
4. Implement chosen design
5. Replace theme/accent system with unified style

**User input needed:** Style preference, design direction (1-on-1 session)

---

### Phase 3: Code Quality & Type Safety
**Scope:** Add type annotations, logging, deeper bug fixes
**Dependencies:** Phase 0-1 complete
**Files affected:** All source files
**Estimated scope:** small

#### Tasks
1. Add type annotations to all function signatures in non-GUI modules
2. Fix real type errors surfaced by `pyright`
3. Add logging to unlogged error paths
4. Fix any non-critical edge-case bugs discovered during migration

**User input needed:** None

---

### Phase 4: Version-Specific Block Filtering (DEFERRED)
**Scope:** Add Minecraft version dropdown for block version filtering
**Dependencies:** Phase 3 complete
**Files affected:** `colour_data.py`, `presets.py`, `app.py`, `processor.py`, `builder.py`
**Estimated scope:** medium

#### Tasks
1. Add `"min_version"`/`"max_version"` fields to each colour set in `colour_data.py`
2. Add version filter parameter to `get_palette_by_mode()` in `presets.py`
3. Add "Minecraft Version" dropdown to UI
4. Thread version param through processing pipeline
5. Update config save/load for version setting

**User input needed:** Research into Bedrock version history per block (can use wiki defaults, user refines later)

---

### Phase 5: Testing
**Scope:** Add test coverage for core modules
**Dependencies:** Phase 3 complete
**Files affected:** New `tests/` directory
**Estimated scope:** medium

#### Tasks
1. Write tests for `processor.py` (color matching, RGB vs Lab, staircasing)
2. Write tests for `dither.py` (all 7 algorithms)
3. Write tests for `presets.py` (palette mode filtering)
4. Write tests for `coordinates.py` (save/load/clear round-trips)
5. Write smoke test for GUI mounting

---

### Phase 6: PyInstaller Bundling
**Scope:** Package as standalone .exe
**Dependencies:** Phase 2 (UI overhaul) complete -- avoid building .exe before UI is final
**Files affected:** New `.spec` file, `pyproject.toml`
**Estimated scope:** small

#### Tasks
1. Create `pyinstaller.spec` with correct library paths
2. Add build script (`scripts/build-exe.ps1`)
3. Test .exe on clean machine

**User input needed:** Icon file (.ico)

---

### Phase 7: Documentation & Polish
**Scope:** Final CONTEXT.md, AGENTS.md updates
**Dependencies:** Phase 3+ complete
**Files affected:** `CONTEXT.md`, `AGENTS.md`, `README.md`
**Estimated scope:** small

#### Tasks
1. Rewrite `CONTEXT.md` with full architecture + data flow
2. Update `AGENTS.md` with build/lint/test commands
3. Clean up temp files, finalize `.gitignore`

---

## User Dependencies
| Dependency | Where to Get It | Workaround Possible? | Notes |
|------------|----------------|---------------------|-------|
| Minecraft Bedrock version history (for version filtering) | wiki.bedrock.dev / Minecraft wiki | Yes - use common-knowledge defaults, refine later | Need user to confirm/research version ranges for blocks |
| App icon for PyInstaller (.ico) | User provides or use generated one | Yes - can use a generic icon | Low priority, can skip initially |
| PyInstaller compatibility | `pip install pyinstaller` | N/A | Standard tool, no auth needed |

## Subagent Build Verdict
**Can a background-builder execute this?** partially

- **Phase 0** (Migration + tooling): **Yes** - mechanical work, clear steps. **DISPATCH READY**
- **Phase 1** (Minor bug fixes): **Yes** - simple duplicate removal, no functional risk. **DISPATCH READY**
- **Phase 2** (UI Overhaul): **No** - needs 1-on-1 design session with Cobalt + UI/UX Pro Max skill
- **Phase 3** (Code quality): **Yes** - type annotations, linting, logging
- **Phase 4** (Version filtering): **No** - needs research into Bedrock version history per block
- **Phase 5** (Testing): **Partially** - can write test files, GUI smoke test needs manual verify
- **Phase 6** (PyInstaller): **Partially** - can write spec, .exe testing needs manual run
- **Phase 7** (Docs): **Yes** - mechanical documentation work

## Assumptions
- User wants to keep `pyproject.toml` as the build config (not migrating to hatch/poetry/etc.)
- Version-specific block filtering should use Bedrock version numbers (e.g., "1.21.0"), not Java edition
- GUI remains monolithic - app.py is not being split into sub-modules (debatable, but current size is manageable)
- `customtkinter` 5.2+ API is stable and won't break with the theme generation approach
- The project will continue to use `bedrockpy` and `adorkable` libraries for WebSocket server (no migration to alternative)

## Next Action
Phase 0 - Migrate to D:\ + add tooling. Then Phase 1 - fix duplicate colour entries.
After those, schedule 1-on-1 for Phase 2 (UI Overhaul).
