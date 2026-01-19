"""
Quality Test Runner - Evaluates response quality (manual + automated)
"""

import json
import asyncio
import time
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import system
from app.services.master_controller import MasterController


@dataclass
class QualityMetrics:
    """Quality metrics for a single test"""

    case_id: str
    category: str
    intent: str
    user_message: str
    response_text: str = ""
    response_time_ms: float = 0.0

    # Automated metrics
    latency_score: int = 0  # 0-2
    entity_extraction_score: int = 0  # 0-1
    error_handling_score: int = 0  # 0-2

    # Manual evaluation scores
    relevance_score: int = -1  # 0-5 (-1 = not evaluated)
    context_awareness_score: int = -1  # 0-2 (-1 = not evaluated)

    # Computed
    automated_score: float = 0.0
    manual_score: float = 0.0
    overall_score: float = 0.0

    # Status
    passed: bool = False
    notes: str = ""

    def compute_scores(self):
        """Compute overall scores"""
        # Automated score (out of 5)
        self.automated_score = (
            self.latency_score
            + self.entity_extraction_score
            + self.error_handling_score
        ) / 5.0

        # Manual score (out of 5)
        if self.relevance_score >= 0 and self.context_awareness_score >= 0:
            self.manual_score = (
                self.relevance_score + self.context_awareness_score
            ) / 2.0

        # Overall (weighted)
        if self.manual_score > 0:
            self.overall_score = (self.automated_score * 0.5) + (
                self.manual_score * 0.5
            )
        else:
            self.overall_score = self.automated_score


class QualityTestRunner:
    def __init__(self):
        self.controller = MasterController()
        self.metrics: list[QualityMetrics] = []

    async def run_test_case(self, test_case: dict) -> QualityMetrics:
        """Run a single quality test case"""
        case_id = test_case["id"]

        logger.info(f"[RUN] {case_id}: {test_case['category']}")

        metrics = QualityMetrics(
            case_id=case_id,
            category=test_case["category"],
            intent=test_case["intent"],
            user_message=test_case["user_message"],
        )

        try:
            # Measure response time
            start_time = time.time()
            response = self.controller.process_request(
                messages=[{"role": "user", "content": test_case["user_message"]}],
                context=test_case.get("context", {}),
            )
            response_time = (time.time() - start_time) * 1000

            metrics.response_time_ms = response_time
            metrics.response_text = response.get("message", "")[:200]  # First 200 chars

            # AUTOMATED SCORING
            # 1. Latency score
            if response_time < 1000:
                metrics.latency_score = 2
            elif response_time < 3000:
                metrics.latency_score = 1
            else:
                metrics.latency_score = 0

            # 2. Entity Extraction (simple check - response should have location if expected)
            expected_entities = test_case.get("expected_entities", {})
            if expected_entities:
                response_text_lower = metrics.response_text.lower()

                # Check if key entities appear in response
                found_count = 0
                total_count = 0

                for key, value in expected_entities.items():
                    if key in ["location", "dish", "topic"]:
                        if isinstance(value, str):
                            # Normalize Vietnamese names
                            value_normalized = value.lower().replace(" ", "")
                            response_normalized = response_text_lower.replace(" ", "")
                            if value_normalized in response_normalized:
                                found_count += 1
                        total_count += 1

                if total_count > 0:
                    metrics.entity_extraction_score = (
                        1 if (found_count / total_count) >= 0.7 else 0
                    )
                else:
                    metrics.entity_extraction_score = 1  # No entities required
            else:
                metrics.entity_extraction_score = 1

            # 3. Error Handling
            has_apology = any(
                x in metrics.response_text.lower()
                for x in ["xin lỗi", "sorry", "hiện tại", "không thể"]
            )
            has_suggestion = any(
                x in metrics.response_text.lower()
                for x in ["có thể", "đề nghị", "suggest", "gợi ý"]
            )

            if metrics.response_text and len(metrics.response_text) > 50:
                metrics.error_handling_score = 2
            elif metrics.response_text:
                metrics.error_handling_score = 1
            else:
                metrics.error_handling_score = 0

            # Compute automated score
            metrics.compute_scores()

            logger.info(
                f"[RESULT] {case_id}: {metrics.overall_score:.2f}/5.0 (latency: {response_time:.0f}ms)"
            )
            return metrics

        except Exception as e:
            logger.error(f"[ERROR] {case_id}: {str(e)}")
            metrics.notes = f"Error: {str(e)}"
            metrics.compute_scores()
            return metrics

    async def run_all_tests(self, test_cases: list[dict]):
        """Run all quality test cases"""
        logger.info(f"Starting quality test run: {len(test_cases)} tests")

        for test_case in test_cases:
            metrics = await self.run_test_case(test_case)
            self.metrics.append(metrics)

        logger.info(f"Completed all {len(self.metrics)} quality tests")

    def generate_report(self) -> dict:
        """Generate quality test report"""
        if not self.metrics:
            return {}

        # Compute statistics
        total_tests = len(self.metrics)
        avg_overall_score = (
            sum(m.overall_score for m in self.metrics) / total_tests
            if total_tests > 0
            else 0
        )
        avg_latency = (
            sum(m.response_time_ms for m in self.metrics) / total_tests
            if total_tests > 0
            else 0
        )
        avg_automated = (
            sum(m.automated_score for m in self.metrics) / total_tests
            if total_tests > 0
            else 0
        )

        # Score distribution
        excellent = sum(1 for m in self.metrics if m.overall_score >= 4.5)
        very_good = sum(1 for m in self.metrics if 4.0 <= m.overall_score < 4.5)
        good = sum(1 for m in self.metrics if 3.0 <= m.overall_score < 4.0)
        fair = sum(1 for m in self.metrics if 2.0 <= m.overall_score < 3.0)
        poor = sum(1 for m in self.metrics if m.overall_score < 2.0)

        # Category breakdown
        category_stats = {}
        for metric in self.metrics:
            if metric.category not in category_stats:
                category_stats[metric.category] = []
            category_stats[metric.category].append(metric.overall_score)

        category_summary = {
            cat: {"avg_score": sum(scores) / len(scores), "count": len(scores)}
            for cat, scores in category_stats.items()
        }

        report = {
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "total_tests": total_tests,
                "avg_overall_score": round(avg_overall_score, 2),
                "avg_automated_score": round(avg_automated, 2),
                "avg_latency_ms": round(avg_latency, 2),
            },
            "score_distribution": {
                "excellent_5": excellent,
                "very_good_4": very_good,
                "good_3": good,
                "fair_2": fair,
                "poor_0-1": poor,
            },
            "category_summary": category_summary,
            "results": [asdict(m) for m in self.metrics],
        }

        return report

    def save_report(self, report: dict, filename: str = None):
        """Save report to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"quality_results_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"Report saved: {filename}")
        return filename


async def main():
    """Main test execution"""
    # Load test cases
    test_file = Path("quality_test_cases_50.json")
    if not test_file.exists():
        logger.error(f"Test file not found: {test_file}")
        return

    with open(test_file, "r", encoding="utf-8") as f:
        test_data = json.load(f)

    test_cases = test_data.get("quality_tests", [])
    logger.info(f"Loaded {len(test_cases)} quality test cases")

    # Run tests
    runner = QualityTestRunner()
    await runner.run_all_tests(test_cases)

    # Generate and save report
    report = runner.generate_report()
    filename = runner.save_report(report)

    # Print summary
    metrics = report["metrics"]
    distribution = report["score_distribution"]

    print("\n" + "=" * 80)
    print("QUALITY TEST REPORT")
    print("=" * 80)
    print(f"\nTotal Tests: {metrics['total_tests']}")
    print(
        f"Average Overall Score: {metrics['avg_overall_score']}/5.0 ({int(metrics['avg_overall_score']*20)}%)"
    )
    print(f"Average Automated Score: {metrics['avg_automated_score']}/5.0")
    print(f"Average Latency: {metrics['avg_latency_ms']:.0f}ms")

    print(f"\nScore Distribution:")
    print(f"  Excellent (4.5-5.0): {distribution['excellent_5']} tests")
    print(f"  Very Good (4.0-4.4): {distribution['very_good_4']} tests")
    print(f"  Good (3.0-3.9): {distribution['good_3']} tests")
    print(f"  Fair (2.0-2.9): {distribution['fair_2']} tests")
    print(f"  Poor (0-1.9): {distribution['poor_0-1']} tests")

    print(f"\nCategory Breakdown:")
    for cat, stats in report["category_summary"].items():
        print(f"  {cat}: {stats['avg_score']:.2f}/5.0 ({stats['count']} tests)")

    print("\n" + "=" * 80)
    print(f"Full report saved to: {filename}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
