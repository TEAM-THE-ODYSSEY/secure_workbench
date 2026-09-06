# P&ID Multimodal Agent Architecture

## Goal
Convert P&ID drawings into an uncertainty-aware engineering graph, retrieve plant evidence, and let a local agent answer only from verified evidence.

## Pipeline
P&ID -> preprocessing -> symbol/OCR/line detection -> multimodal fusion -> P&ID graph -> topology + evidence -> local agent -> validation -> output or human verification.

## Design principle
Detection is not understanding. Every downstream relationship should carry provenance and confidence.
