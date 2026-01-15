# Arcane Package

## Description

No description provided.

## Packaging

Software should be packaged (preferably using Spack or Guix package formats). They should be published in public (community controlled) package repositories (Guix-science, etc.).

* [ ] Packages exist
* [ ] Packages published in easily usable repositories
* [ ] Packages installation tested on supercomputers
* [ ] Packages available in community repositories
  * Spack: URL
  * Guix: URL
  * Docker: URL
  * Apptainer: URL

## Minimal Validation Tests

Software should include minimal validation tests triggered through automated mechanism such as Guix. These tests should be automatic functional tests that do not require specific hardware.

* [x] Unit tests exist
* [x] CI exists
* [ ] CI runs regularly (each new release)
* [x] CI runs regularly (each commit)

## Public Repository

A public repository, must be available for at least the development version of the software, allowing for pull requests to be submitted.

* [x] Publicly available source repository
* [x] Supports contribution via pull requests

Repository: https://github.com/arcaneframework/framework

## Clearly-identified license

Sources should be published under a clearly-identified free software license (preferably with REUSE)

* [x] License clearly stated
* [ ] FLOSS license (FSF/OSI conformant)
* [ ] SPDX is used
* [ ] REUSE is used
  * OSS: apache-2

## Minimal Documentation

Basic documentation should be publicly available to facilitate user understanding and usage of the software.

* [x] Documentation exists
* [ ] Easily browsable online
  * nan

## Open Public Discussion Channel

An open, public discussion channel must be provided that is easily accessible to all potential users. The chosen platform must not require special permissions or memberships that could limit user participation.

* [x] Channel exists
* [x] Freely joinable without invitation
  * nan

## Metadata

Each repository should include metadata easing integration and publicity on a software list.

* [ ] The following metadata is available:
  * Software name: ✅
  * Description: ❌
  * License: ✅
  * Documentation URL: ❌
  * Discussion channel URL: ❌
  * Package repositories URLs: ✅
  * Repository URL: ✅
  * Autoevaluation using the list of criteria stated here: ✅
* [ ] Uses codemeta format

## API Compatibility Information

Each repository should include information enabling downstream users to know which versions they can use

* [ ] API changes documented
* [ ] Semantic Versioning used
* [ ] Clear release policy

## Minimal Performance Tests

Software should include a minimal set of performance tests divided in three categories: single node without specific hardware, single node with specific hardware, multi-nodes. These tests should be automated as much as possible.

* [x] Tests exist
* [ ] Scripts to automate tests on supercomputers
* [ ] Scripts/tools easing portability to new hardware
