# Stage 2 Revisions

This document explains the revisions made to our Stage 2 submission based on the feedback received.

## Comment 1: FKs should not appear in the ER/UML diagram

### Revision:
We updated the UML diagram so that entities only show their attributes and relationships show the connections and cardinalities. We removed explicit foreign-key notations from the diagram.

## Comment 2: Comparison should be relationship not entity

### Revision:
We remodeled Comparison as a weak entity rather than a relationship because it allows storing multiple records for the same pair of programs, each with different user notes. If modeled as a relationship, this flexibility would be lost, as the same program pair could not appear multiple times. This design better supports user experience and data management.

## Comment 3: Bookmark, Comparison and UserJobPreference table missing primary key specification

### Revision:
We added primary key specifications in the relational schema.

## Comment 4: Incomplete normalization analysis.  You need to list all FDs and verify that each table is in 3NF/BCNF.

### Revision:
We added a complete normalization analysis. We listed all the FDs for each entity and relationship and verified each table in 3NF.
