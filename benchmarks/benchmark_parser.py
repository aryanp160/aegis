import time
from pathlib import Path

from aegis.parser import SqlParser


def run_benchmark() -> None:
    """Measures the parsing latency and throughput of the SqlParser."""
    parser = SqlParser()
    project_root = Path(__file__).parent.parent

    postgres_file = project_root / "examples" / "postgres" / "0001_init.sql"
    mysql_file = project_root / "examples" / "mysql" / "0001_init.sql"

    if not postgres_file.is_file() or not mysql_file.is_file():
        print("Example migrations not found. Skipping benchmark.")
        return

    iterations = 1000

    print("==================================================")
    # 1. Benchmark Postgres parsing
    start_time = time.perf_counter()
    for _ in range(iterations):
        res = parser.parse(postgres_file)
        if not res.success:
            print(f"Postgres parsing failed during benchmark: {res.errors}")
            return
    duration = time.perf_counter() - start_time
    avg_latency_ms = (duration / iterations) * 1000
    throughput = iterations / duration
    print("Postgres Parser Benchmarks:")
    print(f"  Iterations: {iterations}")
    print(f"  Total Duration: {duration:.4f} seconds")
    print(f"  Average Latency: {avg_latency_ms:.4f} ms")
    print(f"  Throughput: {throughput:.2f} parses/sec")
    print("--------------------------------------------------")

    # 2. Benchmark MySQL parsing
    start_time = time.perf_counter()
    for _ in range(iterations):
        res = parser.parse(mysql_file)
        if not res.success:
            print(f"MySQL parsing failed during benchmark: {res.errors}")
            return
    duration = time.perf_counter() - start_time
    avg_latency_ms = (duration / iterations) * 1000
    throughput = iterations / duration
    print("MySQL Parser Benchmarks:")
    print(f"  Iterations: {iterations}")
    print(f"  Total Duration: {duration:.4f} seconds")
    print(f"  Average Latency: {avg_latency_ms:.4f} ms")
    print(f"  Throughput: {throughput:.2f} parses/sec")
    print("==================================================")


if __name__ == "__main__":
    run_benchmark()
