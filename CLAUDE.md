# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

This repository is currently a near-empty scaffold. As of this writing it contains only:

- `README.md` — a placeholder with the project title (`# chi`).
- `無題1.txt` — a scratch file containing the git commands used to create the initial commit. Not part of any application; safe to remove.

There is no source code, build system, dependency manifest, test suite, or CI configuration yet. Consequently there are no build/lint/test commands and no architecture to describe.

## When code is added

Once real code exists, regenerate this file (re-run `/init`) so it documents:

- How to install dependencies, build, run, lint, and test — including how to run a single test.
- The high-level architecture: the major components and how they interact, i.e. the "big picture" that requires reading multiple files to grasp.

Until then, ask the user about the intended language, framework, and structure before scaffolding, rather than assuming.
