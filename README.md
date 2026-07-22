# MCU Capability Analyzer

A command-line tool that analyses official STM32 documentation and the
STM32Cube firmware SDK to produce a structured capability report for a
given development board.  The tool inspects vendor PDFs (datasheets,
user manuals, reference manuals) and the SDK example tree, then
classifies each peripheral (UART, ADC, Ethernet) as supported,
unsupported, or requiring further information.  Every extracted value
and every classification decision is traced back to its source.
Physical hardware is not required — the analysis is entirely
documentation-driven.

## Project Overview

Firmware teams evaluating a new MCU platform must manually cross-reference
datasheets, reference manuals, and SDK examples to determine which
peripherals are usable on a given board.  This process is repetitive,
error-prone, and produces unstructured results.

The MCU Capability Analyzer automates this evaluation:

    Official Documentation          Official SDK
    (datasheets, manuals)    +      (STM32Cube firmware package)
                         ↓                    ↓
                    Collectors          SDK Collector
                         ↓                    ↓
                      Capability Engine
                         ↓
                 Analysis Result
                         ↓
           ┌─────────────┼─────────────┐
           ↓             ↓             ↓
      board_capabilities.json
                     sdk_recommendations.txt
                               capability_validation.txt

The current implementation targets the STM32 NUCLEO-U083RC platform using
the STM32CubeU0 firmware package.  Vendor-specific extraction logic is
intentionally isolated within the collector layer, allowing the remaining
architecture — including the analyzer, capability engine, data models,
and report writers — to be reused with limited changes for additional
MCU families.

## Quick Start

```sh
git clone <repository-url>
cd mcu-analyzer
pip install -r requirements.txt

# Place official PDFs in docs/ and SDK in sdk/, then run:
python -m src.main --board NUCLEO-U083RC --sdk sdk --docs docs
```

Generated reports appear in `output/`.  The full walkthrough with
expected inputs and output descriptions follows below.

## Features

- Command-line interface (`analyze --board <name> --docs <dir> --sdk <dir>`)
- Board documentation analysis (LED, debug UART, ADC pin mapping)
- MCU datasheet analysis (CPU core, flash and SRAM sizes, peripheral list)
- STM32Cube SDK auto-discovery (root detection, metadata parsing, example
  enumeration)
- Deterministic SDK example ranking (5-level priority scoring with
  tie-breaking)
- Peripheral capability classification (5-tier classification model)
- Full source traceability — every extracted value and every decision is
  linked to the originating document; documentation-based evidence also
  records the page number where the information was found
- Three report formats: JSON (machine-readable), validation report
  (assignment-answer format), SDK recommendation (ranked example pick)

## Assignment Coverage

| Requirement | Implementation | Status |
|---|---|---|
| Capability report | `board_capabilities.json` — vendor, board, MCU, CPU, flash, RAM, SDK, board resources, peripherals with classification and evidence | ✓ |
| SDK example search | SDK collector enumerates `Projects/<board>/Examples/<category>/<example>/` matching UART, ADC, GPIO, TIM | ✓ |
| Ranked recommendation | Deterministic scoring algorithm (+100 exact board, +60 MCU family, +40 U0 series, +20 category folder, +10 name match) with tie-breaking | ✓ |
| Validation / Q&A | `capability_validation.txt` with human-readable answers for UART logging, ADC sampling, Native Ethernet | ✓ |
| Traceability | Every evidence record carries `source_type`, `document`, `notes`, and — for documentation-based evidence — the originating page number | ✓ |
| Unknown handling | `Classification.NOT_ENOUGH_VERIFIED_INFORMATION` when evidence is absent; no fabricated default | ✓ |
| CLI with `--board`, `--sdk`, `--docs`, `--output` | `argparse`-based entry point in `src/main.py` | ✓ |
| JSON output | `board_capabilities.json` with complete schema | ✓ |
| README | This document | ✓ |

## Architecture

The analysis pipeline is organised into four layers:

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI (main.py)                        │
│                 argparse-based entry point                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      Analyzer (analyzer.py)                   │
│                   Pipeline orchestration                      │
└──────────┬──────────────────────────┬────────────────────────┘
           │                          │
           ▼                          ▼
┌──────────────────────┐  ┌──────────────────────────┐
│ DocumentationResolver │  │      Collectors           │
│   (doc_resolver.py)   │  │  ├─ BoardCollector        │
│   Classifies PDFs by  │  │  ├─ MCUCollector          │
│   filename prefix     │  │  └─ SDKCollector          │
└──────────────────────┘  └──────────┬───────────────┘
           │                          │
           ▼                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   CapabilityEngine                           │
│   Runs registered rules (UARTRule, ADCRule, EthernetRule)    │
│   Each rule produces: classification + evidence + examples   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     AnalysisResult                           │
│              board + mcu + sdk + capabilities                │
└──────────┬──────────────────┬──────────────────┬────────────┘
           │                  │                  │
           ▼                  ▼                  ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
│   JsonWriter     │ │SdkReportWriter│ │ ValidationWriter│
│board_capabilities│ │sdk_recommendat│ │capability_validat│
│     .json        │ │  ions.txt    │ │    ion.txt       │
└──────────────────┘ └──────────────┘ └──────────────────┘
```

**Collectors** extract raw information from documents and the SDK.
They do not evaluate or classify — they only gather evidence.

**CapabilityEngine** holds all decision logic.  Each rule implements a
deterministic check order and produces a classification together with
supporting evidence.

**AnalysisResult** is an immutable data container that decouples
collection from report generation.

**Writers** transform the analysis result into output files.  Multiple
writers can produce different views of the same data without repeating
the analysis.

## Repository Structure

```
.
├── src/
│   ├── main.py                   CLI entry point
│   ├── analyzer.py               Pipeline orchestrator
│   ├── collectors/
│   │   ├── base_collector.py     Shared text iteration and resource merging
│   │   ├── board_collector.py    Board-level resource extraction
│   │   ├── mcu_collector.py      MCU metadata and peripheral presence
│   │   └── sdk_collector.py      SDK discovery, example enumeration, scoring
│   ├── reasoning/
│   │   ├── capability_engine.py  Rule runner
│   │   └── rules/
│   │       ├── base_rule.py      Abstract rule with template method
│   │       ├── uart_rule.py      UART capability evaluation
│   │       ├── adc_rule.py       ADC capability evaluation
│   │       └── ethernet_rule.py  Ethernet capability evaluation
│   ├── reports/
│   │   ├── json_writer.py        board_capabilities.json generator
│   │   ├── sdk_report_writer.py  Ranked SDK example recommendation
│   │   └── validation_writer.py  Assignment-answer capability report
│   ├── models/
│   │   ├── evidence.py           Source-attributed data point
│   │   ├── capability.py         Capability + Classification enum
│   │   ├── board_info.py         Board-level information
│   │   ├── mcu_info.py           MCU-level information
│   │   ├── sdk_info.py           SDK metadata and examples
│   │   └── analysis_result.py    Complete analysis container
│   └── utils/
│       ├── documentation.py      Documentation data class
│       ├── doc_resolver.py       PDF classification by filename prefix
│       └── pdf_parser.py         pypdf-based text extraction
├── docs/                         Place official PDF documentation here
├── sdk/                          Place STM32Cube firmware package here
├── output/                       Generated reports (created on first run)
├── tests/                        Test suite (empty — pending implementation)
├── pyproject.toml                Project metadata and entry point
├── requirements.txt              Python dependency (pypdf)
└── README.md                     This file
```

## Workflow

A complete analysis run follows this sequence:

```
  1. ┌─────────────────────────────────────────────────────────┐
     │  DocumentationResolver scans docs/ for PDF files         │
     │  Classifies by filename prefix:                         │
     │    DS_* → datasheet,  UM_* → user_manual,               │
     │    RM_* → reference_manual,  * → documentation          │
     └─────────────────────────────────────────────────────────┘
                                    │
  2. ┌─────────────────────────────────────────────────────────┐
     │  BoardCollector reads each document's text               │
     │  Extracts: vendor (STMicroelectronics), board resources  │
     │  (LED pins, debug UART instance/pins, ADC instance/pins) │
     └─────────────────────────────────────────────────────────┘
                                    │
  3. ┌─────────────────────────────────────────────────────────┐
     │  MCUCollector reads datasheet text                       │
     │  Extracts: CPU core (Arm Cortex-M0+), flash size (256KB),│
     │  SRAM size (40KB), peripheral presence (UART, ADC, TIM,  │
     │  Ethernet — confirmed or not mentioned with negation      │
     │  awareness)                                              │
     └─────────────────────────────────────────────────────────┘
                                    │
  4. ┌─────────────────────────────────────────────────────────┐
     │  SDKCollector locates the SDK root via package.xml       │
     │  (depth 1-2), reads name/version from metadata,          │
     │  enumerates examples under Projects/<board>/Examples/    │
     │  matching target peripherals (UART, ADC, GPIO, TIM)      │
     └─────────────────────────────────────────────────────────┘
                                    │
  5. ┌─────────────────────────────────────────────────────────┐
     │  CapabilityEngine runs every registered rule             │
     │  Each rule:                                              │
     │    1. Checks board resources for the peripheral          │
     │    2. Checks MCU evidence for confirmation               │
     │    3. Checks SDK examples for the peripheral             │
     │    4. Produces a deterministic classification            │
     └─────────────────────────────────────────────────────────┘
                                    │
  6. ┌─────────────────────────────────────────────────────────┐
     │  Three writers produce output files in output/           │
     │  - board_capabilities.json                               │
     │  - sdk_recommendations.txt                               │
     │  - capability_validation.txt                             │
     └─────────────────────────────────────────────────────────┘
```

## Prerequisites

- **Python 3.10 or later**
- **Official STM32 documentation** — MCU datasheet and board user manual
  in PDF format (see [Expected Project Inputs](#expected-project-inputs))
- **STM32CubeU0 firmware package** — the STM32Cube MCU package containing
  SDK examples and metadata, available from [STM32CubeU0](https://github.com/STMicroelectronics/STM32CubeU0)

## Installation

Requires Python 3.10 or later.

```sh
git clone <repository-url>
cd mcu-analyzer
pip install -r requirements.txt
```

## Expected Project Inputs

Before running the analyzer, prepare the following directory structure:

```
project/
├── docs/
│   ├── DS_STM32U083RC.pdf       # MCU datasheet
│   └── UM_NUCLEO-U083RC.pdf     # Board user manual
├── sdk/
│   └── STM32CubeU0-main/        # STM32Cube firmware package
└── output/                      # Created automatically on first run
```

### Documentation (`docs/`)

Place official STM32 PDF documents in this directory.  The resolver
classifies files by their filename prefix:

| Prefix | Document type |
|---|---|
| `DS_` | Datasheet (MCU specifications) |
| `UM_` | User manual (board description) |
| `RM_` | Reference manual (register description) |
| (other) | Generic documentation |

For the NUCLEO-U083RC, expected documents include the datasheet
(`DS_STM32U083RC.pdf`) and the board user manual (`UM_NUCLEO-U083RC.pdf`).

### SDK (`sdk/`)

Place the STM32Cube firmware package (e.g. `STM32CubeU0-main/`) in this
directory.  The collector automatically discovers the root by searching
for `package.xml` at the supplied path and up to two directory levels
deep.

## Usage

```sh
python -m src.main \
    --board NUCLEO-U083RC \
    --sdk sdk/STM32CubeU0-main \
    --docs docs \
    --output output
```

| Argument | Required | Description |
|---|---|---|
| `--board` | Yes | Board name, for example `NUCLEO-U083RC`.  The MCU part number is derived automatically (`NUCLEO-U083RC` → `STM32U083RC`). |
| `--sdk` | No | Path to the STM32Cube firmware SDK.  When omitted, SDK examples are not available and the capability classification relies solely on board documentation. |
| `--docs` | No | Path to a directory containing official PDF documentation.  When omitted, analysis uses only the SDK and board-name heuristics. |
| `--output` | No | Output directory (default: `output/`).  Created automatically if it does not exist. |

The tool can also be invoked via the installed console script:

```sh
analyze --board NUCLEO-U083RC --sdk sdk/STM32CubeU0-main --docs docs
```

## Build Verification

A successful analysis run produces three files in the output directory:

- `board_capabilities.json`
- `sdk_recommendations.txt`
- `capability_validation.txt`

The tool exits with exit code 0 on success.

## Generated Outputs

Three files are written to the output directory:

| File | Purpose |
|---|---|
| `board_capabilities.json` | Machine-readable JSON with the full analysis result: vendor, board, MCU, CPU core, flash/SRAM sizes, SDK metadata, board resources, peripherals with classification, and a deduplicated data-source list. |
| `sdk_recommendations.txt` | Human-readable ranking of the most relevant SDK example for each capability (LED, UART, ADC, TIM).  Uses a deterministic 5-priority scoring algorithm. |
| `capability_validation.txt` | Assignment-answer report answering which peripherals are supported, unsupported, or unconfirmed, with supporting evidence per peripheral. |

## Example Output

`board_capabilities.json` (abbreviated):

```json
{
  "vendor": "STMicroelectronics",
  "board": "NUCLEO-U083RC",
  "mcu": "STM32U083RC",
  "cpu_core": "Arm Cortex-M0+",
  "flash_kb": 256,
  "ram_kb": 40,
  "sdk": {
    "name": "STM32Cube_FW_U0",
    "version": "1.3.0"
  },
  "board_resources": {
    "led": { "pin": "PA5", "label": "LD4", "color": "green" },
    "debug_uart": { "instance": "USART2", "tx_pin": "PD5", "rx_pin": "PD6" },
    "adc": { "instance": "ADC", "pins": ["PA0", "PA1", ...] }
  },
  "peripherals": [
    {
      "peripheral": "UART",
      "classification": "SUPPORTED",
      "evidence": [
        {
          "source_type": "user_manual",
          "document": "UM_NUCLEO-U083RC",
          "page": "53",
          "notes": "Peripheral confirmed in UM_NUCLEO-U083RC: UART"
        }
      ]
    }
  ],
  "data_sources": [
    { "source_type": "user_manual", "document": "UM_NUCLEO-U083RC", "page": "1", "notes": "..." }
  ]
}
```

## Design Decisions

### Separation of collection and reasoning

Collectors extract raw information from documents and attach evidence.
They never classify or evaluate.  The CapabilityEngine holds all
decision logic.  This separation means that extraction logic can be
updated or corrected without affecting classification rules, and vice
versa.

### Collector → Engineer → Writer pipeline

The pipeline runs in three phases: collect, reason, produce.  Each phase
produces an intermediate data structure (BoardInfo, MCUInfo, SDKInfo;
then AnalysisResult) that is consumed by the next phase.  This makes
each phase independently testable and permits alternative writers
without re-running the analysis.

### Evidence is attached to values, not to decisions

Every extracted value carries an Evidence object that records which
document provided the value, what specific text or metadata was used,
and — for documentation-based evidence — the page number on which the
information was found.  This allows downstream consumers (including the
validation writer) to present a complete trace from raw document to
final classification.

### Collectors never guess

When a datasheet does not mention a value (for example, SRAM size absent
from a board user manual), the collector returns its zero value rather
than applying a heuristic.  The capability engine then produces
NOT_ENOUGH_VERIFIED_INFORMATION, signalling that human review is needed.
This prevents the tool from silently producing plausible but incorrect
specifications.

### Classification uses checks, not probabilities

The capability engine uses a deterministic check order:
NOT_ENOUGH_VERIFIED_INFORMATION → SUPPORTED →
SUPPORTED_MCU_NOT_BOARD → REQUIRES_EXTERNAL_COMPONENT → UNSUPPORTED.
Each classification requires positive evidence — absence of evidence
never produces a SUPPORTED result.

### Only official documentation is used

The analysis considers only official PDF documents (datasheets, user
manuals, reference manuals) and the official SDK directory structure.
Third-party sources, community documentation, and web-scraped data are
not consulted.  This guarantees that every claim in the report can be
independently verified against the same source documents.

### SDK example ranking is deterministic

The scoring algorithm uses only intrinsic properties of the example path
(board directory, MCU family, category folder, example name).  There are
no weights, priors, or learned parameters.  Ties are broken by path
length, exact category folder, then alphabetical order.  Running the
tool twice with the same inputs always produces the same output.

## Reusability

The current implementation targets the STM32 NUCLEO-U083RC board and the
STM32CubeU0 firmware ecosystem.  However, the architecture is organised
around interfaces that support extension:

- **Collectors** are independent classes.  A new MCU family requires a
  new collector (or modified regex patterns in the existing collector),
  but does not require changes to the capability engine or the writers.

- **Rules** are registered in `rules/__init__.py`.  Adding a new
  peripheral capability means creating a new rule class and adding it to
  the `ALL_RULES` list.  No collector or writer changes are needed.

- **Writers** consume `AnalysisResult` and are decoupled from the
  collection and reasoning phases.  Additional output formats (for
  example, HTML or CSV) can be added as new writer classes without
  modifying the pipeline.

- **SDK scoring** uses a configurable keyword dictionary
  (`_P4_FOLDER_KEYWORDS`, `_P5_NAME_KEYWORDS`).  Adapting the ranking
  for a different SDK layout requires updating these dictionaries rather
  than rewriting the algorithm.

Support for non-STM32 platforms (for example, NXP, Nordic, or ESP32)
would require equivalent collectors for their documentation and SDK
formats, but the pipeline and reporting layers would remain unchanged.

## Limitations

- **Extraction patterns are optimised for STM32 documentation.**  CPU
  core patterns recognise Cortex-M variants only.  Vendor detection is
  limited to STMicroelectronics.  Size patterns expect the specific
  wording used in STM32 datasheets ("Kbytes of Flash memory",
  "Kbyte SRAM").

- **Document classification relies on filename prefixes.**  Files that
  do not follow the `DS_` / `UM_` / `RM_` naming convention receive the
  generic `documentation` type.  Renaming files to match the convention
  is the recommended workaround.

- **PDF text extraction uses pypdf.**  Scanned PDFs, image-based pages,
  and PDFs with unusual encodings may produce incomplete or garbled
  text.  The tool reports extraction errors as evidence entries rather
  than crashing.

- **No hardware interaction.**  All analysis is documentation-based.
  Pin availability, electrical characteristics, and board layout
  validation are outside scope.

- **No assumptions are made when evidence is unavailable.**  If the
  required document is not present in `docs/`, the corresponding values
  remain blank or zero, and the capability is reported as
  NOT_ENOUGH_VERIFIED_INFORMATION.  The tool will not invent
  specifications.

- **Only three peripheral rules are implemented.**  UART, ADC, and
  Ethernet are covered.  SPI, I2C, USB, and other peripherals are not
  evaluated.

## AI Usage

AI was used as an implementation assistant during the development of this
project.  All technical claims — pin mappings, SDK example paths,
peripheral presence conclusions, MCU specifications — were verified
against the official STMicroelectronics documentation and the STM32Cube
SDK before inclusion in the analysis output.  The architecture and design
decisions were determined by the project requirements, not by AI
suggestion.

## License

This project is provided under the terms of the repository's license.
See the LICENSE file (if present) for details.
