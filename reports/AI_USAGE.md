# AI Usage Statement

I used AI tools as engineering assistants during the development of the
MCU Capability Analyzer.  The AI helped accelerate implementation and
documentation, but all technical claims, architectural decisions, and
output verifications remained my responsibility.  Every specification
extracted or inferred by the tool was checked against official
STMicroelectronics documentation before acceptance.

## AI Tools Used

Two AI tools were used during this project, one acted like MASTER and other as SLAVE:

**MASTER**:
**ChatGPT** was used for architecture discussion, implementation plan
review, code critique, and documentation refinement.  I described the
project requirements and the proposed collector/reasoning/writer
separation, and ChatGPT helped identify potential issues and alternative
approaches before code was written.

**SLAVE**:
**OpenCode** was used as a code-editing assistant within the development
environment.  It implemented reviewed designs, performed iterative code
modifications, refactored existing code, and helped debug extraction
failures.  OpenCode also assisted with drafting the project README and
this AI usage statement.

Neither tool operated autonomously.  Every code change was reviewed
before being committed.

## How AI Was Used

AI assisted with the following activities:

- **Architecture discussion.**  I outlined the required pipeline stages
  (collection, reasoning, report generation) and the AI helped refine
  the separation of concerns and identify missing interfaces.

- **Implementation plan review.**  Before writing each module, I
  described the intended behaviour and the AI highlighted edge cases,
  error paths, and potential design issues.

- **Boilerplate code generation.**  Standard structures such as data
  classes, argument parsers, ASCII diagrams, and the project metadata
  file were generated quickly so I could focus on the project-specific
  logic.

- **Debugging assistance.**  When the MCU collector returned empty
  values for CPU core and flash size, I used the AI to systematically
  isolate the cause — traced from document classification through PDF
  text extraction to regex pattern matching — until the root cause
  (non-breaking hyphen characters) was identified and corrected.

- **Code quality improvements.**  The AI suggested more robust regex
  patterns, better error handling, and consistent naming conventions
  across the codebase.

- **Documentation drafting.**  The README and this AI usage statement
  were drafted with AI assistance, then reviewed and edited for accuracy
  and tone.

AI suggestions were evaluated, accepted, modified, or rejected based on
their suitability for the project.  No AI-generated code was committed
without understanding what it does.

## Verification Process

Every technical claim that appears in the analysis output was verified
before acceptance.  The verification process followed these rules:

- **MCU specifications** (CPU core, flash size, RAM size) were confirmed
  against the official STM32U083RC product page and the corresponding
  datasheet (DS14213).  When the AI suggested extraction patterns, I
  tested them against the actual PDF text extracted by pypdf and
  adjusted the patterns until they matched the real document wording.

- **Board resources** (LED pins, UART instance and pins, ADC pins) were
  verified against the NUCLEO-U083RC user manual (UM3256).  Pin
  assignments extracted by regular expressions were cross-checked
  against the board schematic descriptions in the manual.

- **SDK example paths** and **example names** were verified against the
  actual directory structure of the STM32CubeU0 firmware package
  (version 1.3.0).  The AI never generated SDK paths — it only operated
  on paths discovered by the SDK collector during the analysis run.

- **Capability classifications** (SUPPORTED, UNSUPPORTED,
  NOT_ENOUGH_VERIFIED_INFORMATION) were determined by the capability
  engine's deterministic rules, not by AI.  I reviewed each rule's logic
  to ensure that no classification could be produced without supporting
  evidence.

When AI suggestions conflicted with official documentation, the official
documentation was treated as authoritative.  Values that could not be
found in any official document were intentionally left unknown (returned
as zero or empty) rather than guessed.  The tool never produces a
SUPPORTED classification for a capability without positive evidence from
a trusted source.

## Human Decisions

The following decisions remained entirely under my control and were not
delegated to AI:

- **Platform selection.**  The STM32 NUCLEO-U083RC and STM32CubeU0 SDK
  were chosen based on the assignment requirements, not by AI.

- **Project architecture.**  The three-phase pipeline (collect, reason,
  produce) and the separation of collectors, rules, and writers were
  designed before any AI interaction.  AI helped refine the design but
  did not originate it.

- **Collector responsibilities.**  I decided which resources each
  collector should extract, which documents it should read, and how it
  should handle missing values.

- **Classification model.**  The five-tier classification enum and the
  deterministic evaluation order were defined by me.

- **Code acceptance.**  Every AI-generated code change was reviewed
  before being integrated.  Code that did not meet the project's quality
  or correctness standards was rejected or modified.

- **Output validation.**  Generated reports were inspected manually to
  confirm they matched the official documentation and SDK contents.

## Lessons Learned

AI accelerates implementation, but it does not replace verification.
The most significant time savings came from using AI to quickly generate
and iterate on code that I could then test against real documents.
However, every regex pattern, every extraction rule, and every
classification condition required testing against actual PDF output to
confirm it worked correctly.

I found that the debugging process benefited most from AI assistance:
when extraction failed, the AI helped isolate the cause by examining
document flow, extraction output, and pattern behaviour systematically.

The project reinforced that in firmware engineering, official
documentation is the only reliable source of truth.  AI can suggest
patterns and structures, but only testing against real documents
confirms that a tool produces correct results.

## Summary

AI was used as an engineering productivity tool during the development of
the MCU Capability Analyzer.  It assisted with architecture discussion,
code generation, debugging, and documentation drafting.  All technical
claims, extraction patterns, classification rules, and output formats
were verified against official STMicroelectronics documentation and the
STM32Cube firmware SDK before acceptance.  Final responsibility for
correctness, architecture, and engineering decisions remained with me.
