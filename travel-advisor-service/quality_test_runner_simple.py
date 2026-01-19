"""
Quality Test Runner - Simplified version for manual evaluation
"""

import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class QualityEvaluation:
    """Quality evaluation for a test"""

    case_id: str
    category: str
    intent: str
    user_message: str

    # Manual evaluation fields (to be filled in)
    relevance_score: int = -1  # 0-5 (-1 = not evaluated)
    entity_extraction_score: int = -1  # 0-1
    context_awareness_score: int = -1  # 0-2
    error_handling_score: int = -1  # 0-2
    latency_score: int = -1  # 0-2

    # Evaluator notes
    evaluator_notes: str = ""

    # Computed
    overall_score: float = 0.0

    def compute_score(self):
        """Compute overall quality score"""
        scores = []
        if self.relevance_score >= 0:
            scores.append(self.relevance_score / 5)
        if self.entity_extraction_score >= 0:
            scores.append(self.entity_extraction_score / 1)
        if self.context_awareness_score >= 0:
            scores.append(self.context_awareness_score / 2)
        if self.error_handling_score >= 0:
            scores.append(self.error_handling_score / 2)
        if self.latency_score >= 0:
            scores.append(self.latency_score / 2)

        if scores:
            self.overall_score = sum(scores) / len(scores) * 5
        return self.overall_score


class QualityTestEvaluator:
    def __init__(self):
        self.evaluations = []

    def load_test_cases(self, filename: str) -> list:
        """Load test cases"""
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("quality_tests", [])

    def create_evaluation_template(self, test_cases: list, output_file: str):
        """Create evaluation template"""
        template = {
            "timestamp": datetime.now().isoformat(),
            "instructions": {
                "relevance_score": "How well does response answer the user question? 0=completely irrelevant, 5=perfect answer",
                "entity_extraction": "Did system correctly identify key entities? 0=no, 1=yes",
                "context_awareness": "Does response show understanding of context? 0=ignores context, 1=partial, 2=perfect",
                "error_handling": "How gracefully handled errors/missing info? 0=crashes, 1=returns error, 2=suggests clarification",
                "latency": "Response speed? 0=>5s, 1=2-5s, 2=<2s",
            },
            "evaluations": [],
        }

        for case in test_cases:
            eval_item = {
                "id": case["id"],
                "category": case["category"],
                "intent": case["intent"],
                "user_message": case["user_message"],
                "quality_criteria": case["quality_criteria"],
                "expected_entities": case["expected_entities"],
                "relevance_score": None,
                "entity_extraction_score": None,
                "context_awareness_score": None,
                "error_handling_score": None,
                "latency_score": None,
                "evaluator_notes": "",
            }
            template["evaluations"].append(eval_item)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=2)

        return output_file

    def calculate_statistics(self, evaluations: list) -> dict:
        """Calculate statistics from evaluations"""
        # Filter only evaluated ones
        evaluated = [e for e in evaluations if e.get("relevance_score") is not None]

        if not evaluated:
            return {"note": "No evaluations completed yet"}

        count = len(evaluated)

        # Calculate average scores
        avg_relevance = sum(e.get("relevance_score", 0) for e in evaluated) / count
        avg_entity = sum(e.get("entity_extraction_score", 0) for e in evaluated) / count
        avg_context = (
            sum(e.get("context_awareness_score", 0) for e in evaluated) / count
        )
        avg_error = sum(e.get("error_handling_score", 0) for e in evaluated) / count
        avg_latency = sum(e.get("latency_score", 0) for e in evaluated) / count

        # Normalize to 0-5 scale
        overall_avg = (
            avg_relevance
            + (avg_entity * 5)
            + (avg_context * 2.5)
            + (avg_error * 2.5)
            + (avg_latency * 2.5)
        ) / 5

        # Distribution
        excellent = sum(1 for e in evaluated if e.get("relevance_score", 0) >= 4)
        good = sum(1 for e in evaluated if 3 <= e.get("relevance_score", 0) < 4)
        fair = sum(1 for e in evaluated if 2 <= e.get("relevance_score", 0) < 3)
        poor = sum(1 for e in evaluated if e.get("relevance_score", 0) < 2)

        # Category breakdown
        category_stats = {}
        for e in evaluated:
            cat = e.get("category", "Unknown")
            if cat not in category_stats:
                category_stats[cat] = []

            score = (
                e.get("relevance_score", 0)
                + (e.get("entity_extraction_score", 0) * 5)
                + (e.get("context_awareness_score", 0) * 2.5)
                + (e.get("error_handling_score", 0) * 2.5)
                + (e.get("latency_score", 0) * 2.5)
            ) / 5
            category_stats[cat].append(score)

        category_summary = {
            cat: {"avg_score": sum(scores) / len(scores), "count": len(scores)}
            for cat, scores in category_stats.items()
        }

        return {
            "total_evaluated": count,
            "total_pending": len(evaluations) - count,
            "overall_score": round(overall_avg, 2),
            "metric_averages": {
                "relevance_0_5": round(avg_relevance, 2),
                "entity_extraction_0_1": round(avg_entity, 2),
                "context_awareness_0_2": round(avg_context, 2),
                "error_handling_0_2": round(avg_error, 2),
                "latency_0_2": round(avg_latency, 2),
            },
            "quality_distribution": {
                "excellent_4_5": excellent,
                "good_3_4": good,
                "fair_2_3": fair,
                "poor_0_2": poor,
            },
            "category_breakdown": category_summary,
        }


def main():
    """Main execution"""
    evaluator = QualityTestEvaluator()

    # Load test cases
    test_file = Path("quality_test_cases_50.json")
    if not test_file.exists():
        print(f"ERROR: Test file not found: {test_file}")
        return

    print(f"Loading test cases from {test_file.name}...")
    test_cases = evaluator.load_test_cases(str(test_file))
    print(f"✓ Loaded {len(test_cases)} test cases")

    # Create evaluation template
    eval_file = "quality_evaluation_template.json"
    print(f"\nCreating evaluation template: {eval_file}")
    evaluator.create_evaluation_template(test_cases, eval_file)
    print(f"✓ Template created!")

    print("\n" + "=" * 80)
    print("QUALITY TEST EVALUATION - INSTRUCTIONS")
    print("=" * 80)
    print(
        f"""
This quality test suite has {len(test_cases)} test cases covering:
- Plan Trip (8 tests)
- Find Spot (10 tests)
- Find Hotel (5 tests)
- General Q&A (10 tests)
- Entity Extraction (3 tests)
- Error Handling (3 tests)
- Special Scenarios (11 tests)

NEXT STEPS:
1. Run the system with each user_message in quality_evaluation_template.json
2. Record the system's response
3. Score each response based on quality_criteria:
   - relevance_score: 0-5 (does it answer the question?)
   - entity_extraction_score: 0-1 (correct entities?)
   - context_awareness_score: 0-2 (understands context?)
   - error_handling_score: 0-2 (graceful failures?)
   - latency_score: 0-2 (response speed?)
4. Add evaluator_notes for any issues
5. Run: python quality_evaluation_report.py

SCORING GUIDE:
Relevance (0-5):
  0 = Completely off-topic
  2 = Partially relevant
  4 = Very relevant
  5 = Perfect answer

Entity Extraction (0-1):
  0 = Missed key entities
  1 = Correctly identified entities

Context Awareness (0-2):
  0 = Ignores conversation context
  1 = Partial understanding
  2 = Perfect context awareness

Error Handling (0-2):
  0 = Returns error/crashes
  1 = Returns error message
  2 = Suggests clarification or workaround

Latency (0-2):
  0 = >5 seconds
  1 = 2-5 seconds
  2 = <2 seconds
    """
    )
    print("=" * 80)
    print(f"\nTemplate file ready: {eval_file}")
    print("Start evaluating responses and fill in the scores.")


if __name__ == "__main__":
    main()
