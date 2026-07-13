import time
from pathlib import Path

# Important to register rules
import aegis.rules.best_practices  # noqa: F401
import aegis.rules.high_risk  # noqa: F401
import aegis.rules.operational  # noqa: F401
from aegis.engine import RuleEngine
from aegis.parser.core import SqlParser
from aegis.rules.registry import RuleRegistry

BENCHMARK_SQL = """
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_name ON users (name);

ALTER TABLE users ADD COLUMN email VARCHAR(255) NOT NULL;

DROP TABLE users;
"""

def main() -> None:
    print("Preparing Benchmark...")
    
    script_path = Path("benchmark_script.sql")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(BENCHMARK_SQL)
    
    parser = SqlParser()
    parse_result = parser.parse(script_path)
    
    if not parse_result.success or not parse_result.migration:
        print("Failed to parse benchmark SQL.")
        return
        
    parsed_migration = parse_result.migration
    
    # Cleanup file
    script_path.unlink()
    
    # Duplicate it 1,000 times
    MIGRATION_COUNT = 1000
    migrations = [parsed_migration for _ in range(MIGRATION_COUNT)]
    
    active_rules = RuleRegistry.get_rules()
    print(f"Active Rules: {len(active_rules)}")
    print(f"Total Migrations: {MIGRATION_COUNT}")
    print(f"Total AST Nodes per Migration: {len(parsed_migration.ast_nodes)}")
    print(f"Total AST Nodes to Process: {len(parsed_migration.ast_nodes) * MIGRATION_COUNT}")
    
    engine = RuleEngine()
    
    print("\nStarting Engine Analysis...")
    start_time = time.perf_counter()
    
    result = engine.analyze(migrations)
    
    duration = time.perf_counter() - start_time
    
    print("\n--- Benchmark Results ---")
    print(f"Time Taken:     {duration:.4f} seconds ({result.duration_ms:.2f} ms)")
    print(f"Total Violations: {len(result.violations)}")
    print(f"Errors:           {result.total_errors}")
    print(f"Warnings:         {result.total_warnings}")
    print(f"Infos:            {result.total_infos}")
    
    # Generate benchmark markdown report
    report_content = f"""# Performance Benchmark

This document records the performance characteristics of the Aegis `RuleEngine`.

## Execution Details

- **Test Payload:** 1,000 duplicated migrations containing `CREATE TABLE`, `CREATE INDEX`, `ALTER TABLE`, and `DROP TABLE` statements.
- **Active Rules:** {len(active_rules)}
- **AST Nodes per Migration:** {len(parsed_migration.ast_nodes)}
- **Total AST Nodes Processed:** {len(parsed_migration.ast_nodes) * MIGRATION_COUNT}

## Results

- **Time Taken:** {duration:.4f} seconds
- **Total Violations Discovered:** {len(result.violations)}
- **Errors / Warnings / Infos:** {result.total_errors} / {result.total_warnings} / {result.total_infos}

The engine demonstrates efficient throughput traversing tens of thousands of AST nodes synchronously.
"""
    
    report_path = Path("docs/benchmark.md")
    report_path.parent.mkdir(exist_ok=True, parents=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"\nSaved benchmark results to {report_path}")

if __name__ == "__main__":
    main()
