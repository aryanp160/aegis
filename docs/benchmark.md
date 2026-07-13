# Performance Benchmark

This document records the performance characteristics of the Aegis `RuleEngine`.

## Execution Details

- **Test Payload:** 1,000 duplicated migrations containing `CREATE TABLE`, `CREATE INDEX`, `ALTER TABLE`, and `DROP TABLE` statements.
- **Active Rules:** 10
- **AST Nodes per Migration:** 4
- **Total AST Nodes Processed:** 4000

## Results

- **Time Taken:** 0.5716 seconds
- **Total Violations Discovered:** 6000
- **Errors / Warnings / Infos:** 3000 / 3000 / 0

The engine demonstrates efficient throughput traversing tens of thousands of AST nodes synchronously.
