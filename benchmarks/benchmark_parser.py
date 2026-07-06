import tempfile
import time
import tracemalloc
from pathlib import Path

from aegis.parser import SqlParser


def measure_runs(
    parser: SqlParser, file_path: Path, label: str, iterations: int = 1000
) -> None:
    """Measures latency, throughput, and memory growth for a configuration."""
    tracemalloc.start()
    start_mem, _ = tracemalloc.get_traced_memory()

    start_time = time.perf_counter()
    for _ in range(iterations):
        res = parser.parse(file_path)
        if not res.success:
            print(f"[{label}] Parsing failed during benchmark: {res.errors}")
            tracemalloc.stop()
            return
    duration = time.perf_counter() - start_time
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    avg_latency_ms = (duration / iterations) * 1000
    throughput = iterations / duration
    peak_mem_kb = peak_mem / 1024

    print(f"{label}:")
    print(f"  Iterations: {iterations}")
    print(f"  Total Duration: {duration:.4f} seconds")
    print(f"  Average Latency: {avg_latency_ms:.4f} ms")
    print(f"  Throughput: {throughput:.2f} parses/sec")
    print(f"  Peak Memory Growth: {peak_mem_kb:.2f} KiB")
    print("--------------------------------------------------")


def run_benchmark() -> None:
    """Measures the parsing latency and throughput of the SqlParser."""
    project_root = Path(__file__).parent.parent
    postgres_file = project_root / "examples" / "postgres" / "0001_init.sql"
    mysql_file = project_root / "examples" / "mysql" / "0001_init.sql"

    if not postgres_file.is_file() or not mysql_file.is_file():
        print("Example migrations not found. Skipping benchmark.")
        return

    print("==================================================")
    print(" Aegis SQL Parser Benchmarks")
    print("==================================================")

    # 1. Uncached Benchmarks
    parser_uncached = SqlParser(use_cache=False)
    measure_runs(parser_uncached, postgres_file, "Postgres Parser (Uncached)")
    measure_runs(parser_uncached, mysql_file, "MySQL Parser (Uncached)")

    # 2. Cached Benchmarks
    parser_cached = SqlParser(use_cache=True)
    # Warm up cache
    parser_cached.parse(postgres_file)
    parser_cached.parse(mysql_file)
    measure_runs(parser_cached, postgres_file, "Postgres Parser (Cached)")
    measure_runs(parser_cached, mysql_file, "MySQL Parser (Cached)")

    # 3. Large Directory Scale Benchmark (100 Files)
    print("Large Directory Scale Benchmark (100 mock SQL files):")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        # Create 100 mock migration files
        for i in range(100):
            sql_file = tmp_path / f"0{i:03d}_migration.sql"
            sql_file.write_text(
                f"CREATE TABLE mock_table_{i} (\n"
                f"    id SERIAL PRIMARY KEY,\n"
                f"    name VARCHAR(100) NOT NULL,\n"
                f"    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP\n"
                f");\n",
                encoding="utf-8",
            )

        parser_scale = SqlParser(use_cache=True)

        tracemalloc.start()
        start_time = time.perf_counter()
        results = parser_scale.parse_directory(tmp_path)
        duration = time.perf_counter() - start_time
        _, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        failed = sum(1 for r in results if not r.success)
        throughput = len(results) / duration
        peak_mem_kb = peak_mem / 1024

        print(f"  Parsed {len(results)} files ({failed} failed)")
        print(f"  Total Duration: {duration:.4f} seconds")
        print(f"  Average Latency/file: {(duration / len(results)) * 1000:.4f} ms")
        print(f"  Throughput: {throughput:.2f} files/sec")
        print(f"  Peak Memory Growth: {peak_mem_kb:.2f} KiB")
    print("==================================================")


if __name__ == "__main__":
    run_benchmark()
