"""
RAG (Retrieval-Augmented Generation) Test Runner
Evaluates: Document retrieval relevance, accuracy, context usage, source citations
"""

import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass


@dataclass
class RAGEvaluation:
    """RAG evaluation for a single test"""

    case_id: str
    category: str
    intent: str
    query: str

    # Retrieval Quality (0-1)
    retrieval_relevance: int = -1  # 0-1: Did system retrieve relevant documents?

    # Information Quality (0-1)
    information_accuracy: int = -1  # 0-1: Are retrieved facts accurate?

    # Context Usage (0-2)
    context_utilization: int = -1  # 0-2: Did system use context correctly?

    # Source Quality (0-1)
    source_verification: int = -1  # 0-1: Are sources verified/cited?

    # Completeness (0-1)
    coverage_completeness: int = -1  # 0-1: Does response cover all criteria?

    # Notes
    evaluator_notes: str = ""
    actual_response: str = ""

    def compute_overall_rag_score(self) -> float:
        """Compute overall RAG score (0-5)"""
        scores = []
        if self.retrieval_relevance >= 0:
            scores.append(self.retrieval_relevance * 5)  # 0-1 -> 0-5
        if self.information_accuracy >= 0:
            scores.append(self.information_accuracy * 5)  # 0-1 -> 0-5
        if self.context_utilization >= 0:
            scores.append(self.context_utilization * 2.5)  # 0-2 -> 0-5
        if self.source_verification >= 0:
            scores.append(self.source_verification * 5)  # 0-1 -> 0-5
        if self.coverage_completeness >= 0:
            scores.append(self.coverage_completeness * 5)  # 0-1 -> 0-5

        if scores:
            return sum(scores) / len(scores)
        return 0.0


class RAGTestRunner:
    def __init__(self):
        self.test_cases = []
        self.evaluations = []

    def load_test_cases(self, filename: str) -> list:
        """Load RAG test cases"""
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("rag_tests", [])

    def create_evaluation_template(self, test_cases: list, output_file: str):
        """Create evaluation template for manual scoring"""
        template = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(test_cases),
            "instructions": {
                "retrieval_relevance": "Did system retrieve relevant and appropriate sources? 0=irrelevant, 1=highly relevant",
                "information_accuracy": "Are the facts in response accurate? 0=inaccurate, 1=accurate",
                "context_utilization": "Did system correctly use retrieved context? 0=ignored, 1=partial, 2=perfect",
                "source_verification": "Are sources cited and verifiable? 0=no verification, 1=verified",
                "coverage_completeness": "Does response cover all criteria? 0=incomplete, 1=complete",
            },
            "evaluations": [],
        }

        for case in test_cases:
            eval_item = {
                "id": case["id"],
                "category": case["category"],
                "intent": case["intent"],
                "query": case["query"],
                "rag_criteria": case["rag_criteria"],
                "expected_retrieved_fields": case["expected_retrieved_fields"],
                "information_accuracy_checks": case["information_accuracy_checks"],
                "retrieval_relevance": None,  # 0-1
                "information_accuracy": None,  # 0-1
                "context_utilization": None,  # 0-2
                "source_verification": None,  # 0-1
                "coverage_completeness": None,  # 0-1
                "actual_response": "",  # Fill in actual system response
                "evaluator_notes": "",  # Add evaluation notes
            }
            template["evaluations"].append(eval_item)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=2)

        return output_file


def main():
    """Main execution"""
    runner = RAGTestRunner()

    # Load test cases
    test_file = Path("rag_test_cases_50.json")
    if not test_file.exists():
        print(f"ERROR: Test file not found: {test_file}")
        return

    print(f"Loading RAG test cases from {test_file.name}...")
    test_cases = runner.load_test_cases(str(test_file))
    print(f"[OK] Loaded {len(test_cases)} RAG test cases\n")

    # Create evaluation template
    eval_file = "rag_evaluation_template.json"
    print(f"Creating evaluation template: {eval_file}")
    runner.create_evaluation_template(test_cases, eval_file)
    print(f"[OK] Template created!\n")

    # Print summary
    print("=" * 80)
    print("RAG (Retrieval-Augmented Generation) TEST FRAMEWORK")
    print("=" * 80)
    print(
        f"""
This RAG test suite has {len(test_cases)} test cases evaluating:

**RAG Metrics (5 Dimensions):**

1. **Retrieval Relevance** (0-1 binary)
   - Question: Did system retrieve RELEVANT documents?
   - 0 = Irrelevant sources retrieved
   - 1 = Highly relevant sources retrieved
   - Measures: Document selection quality, source appropriateness

2. **Information Accuracy** (0-1 binary)
   - Question: Are the FACTS in response accurate?
   - 0 = Facts are incorrect or outdated
   - 1 = Facts are accurate and up-to-date
   - Measures: Factual correctness, data freshness

3. **Context Utilization** (0-2 scale)
   - Question: Did system CORRECTLY USE retrieved context?
   - 0 = Ignored retrieved context
   - 1 = Partially used context
   - 2 = Perfectly integrated context into response
   - Measures: Context application quality, logical flow

4. **Source Verification** (0-1 binary)
   - Question: Are sources CITED and VERIFIABLE?
   - 0 = No sources cited or unverifiable
   - 1 = Sources cited and verifiable
   - Measures: Citation accuracy, source credibility

5. **Coverage Completeness** (0-1 binary)
   - Question: Does response COVER ALL CRITERIA?
   - 0 = Missing important information
   - 1 = Covers all specified criteria
   - Measures: Comprehensiveness, criterion satisfaction

**Test Categories (50 tests):**

Hotel Retrieval (RAG-001, RAG-002, RAG-012, RAG-021, RAG-025, RAG-042, RAG-043, RAG-046, RAG-047)
- Budget filtering accuracy
- Star rating filtering
- Landmark proximity
- Special requirements handling
- Accessibility verification
- Pattern matching
- Range queries
- Sorting accuracy
- Boolean AND queries

Attraction/Spot Retrieval (RAG-003, RAG-006, RAG-007, RAG-016, RAG-020, RAG-023, RAG-031, RAG-037, RAG-040, RAG-041, RAG-049)
- Location verification
- Attraction type accuracy
- Operating status detection
- Ranking accuracy
- Seasonal data
- Ticket pricing
- Error handling
- Negative info handling
- Consistency checks
- Hyperlocal specificity
- Fuzzy matching

Food/Restaurant Retrieval (RAG-004, RAG-024, RAG-048)
- Cuisine type filtering
- Rating-based sorting
- Menu accuracy
- OR query handling

Comparative Queries (RAG-019)
- Multi-location comparison
- Fair comparison metrics

Cross-referenced Data (RAG-010)
- Local specialty dishes
- Restaurant-dish accuracy

Temporal/Dynamic Data (RAG-005, RAG-008, RAG-014, RAG-028, RAG-029, RAG-030, RAG-035, RAG-039)
- Distance/time calculations
- Budget estimation
- Weather forecasting
- Visa requirements
- Health/vaccination info
- Exchange rates
- New opening detection
- Seasonal recommendations

Multi-source Aggregation (RAG-013, RAG-045, RAG-050)
- Hotel + Restaurant + Activity combining
- Cost aggregation and multiplication
- Comprehensive travel planning

Error Handling (RAG-031, RAG-032, RAG-033)
- Non-existent location handling
- Ambiguous query clarification
- Weather query detection

Specialized Queries (RAG-022, RAG-026, RAG-027, RAG-034, RAG-036, RAG-038, RAG-044)
- Activity duration estimation
- Sustainable tourism data
- Safety information
- Review citation accuracy
- Duplicate detection
- Category correctness
- Negative filter handling

**Evaluation Steps:**

1. **Run Query:** Send each query to system
2. **Record Response:** Capture actual system response
3. **Score Retrieval Relevance:**
   - Check if retrieved documents are relevant
   - Verify information sources
   - Assess document quality
4. **Score Information Accuracy:**
   - Verify facts against known data
   - Check for outdated information
   - Validate pricing/hours/details
5. **Score Context Utilization:**
   - Check if response uses retrieved data
   - Assess integration quality
   - Verify logical flow
6. **Score Source Verification:**
   - Confirm sources are cited
   - Verify source credibility
   - Check if sources are current
7. **Score Coverage Completeness:**
   - Check all criteria are addressed
   - Verify nothing major is missing
   - Assess comprehensiveness
8. **Add Notes:** Document any issues or observations

**Overall RAG Score Calculation:**

Normalized to 0-5 scale:
- Retrieval Relevance: 0-1 -> 0-5 (weight: 20%)
- Information Accuracy: 0-1 -> 0-5 (weight: 20%)
- Context Utilization: 0-2 -> 0-5 (weight: 20%)
- Source Verification: 0-1 -> 0-5 (weight: 20%)
- Coverage Completeness: 0-1 -> 0-5 (weight: 20%)

Overall RAG Score = Average of 5 normalized metrics (0-5.0)

**Quality Tiers:**
- 4.5-5.0: Excellent RAG performance
- 4.0-4.4: Very Good RAG performance
- 3.0-3.9: Good RAG performance
- 2.0-2.9: Fair RAG performance
- <2.0: Poor RAG performance

**Next Steps:**

1. Run each query through the travel advisor system
2. Fill in 'actual_response' field in {eval_file}
3. Score each metric (0-1, 0-2 as specified)
4. Add evaluator notes explaining scores
5. Run: python rag_evaluation_report.py
6. Review QUALITY_RAG_REPORT.md

**Expected Timeline:**
- Time per test: 3-5 minutes (run query, evaluate, score)
- Total for 50 tests: 2.5-4 hours
- Best done in batches (10 tests per session)

**File Locations:**
- Test cases: {test_file}
- Evaluation template: {eval_file}
- Report script: rag_evaluation_report.py
- Output report: QUALITY_RAG_REPORT.md
"""
    )

    print("=" * 80)
    print(f"\n[OK] Template ready: {eval_file}")
    print(f"[OK] Instructions printed above")
    print(f"\nStart evaluation by:")
    print(f"  1. Running system with queries from {eval_file}")
    print(f"  2. Recording system responses in 'actual_response' field")
    print(f"  3. Scoring each metric (0-1, 0-2 as specified)")
    print(f"  4. Running: python rag_evaluation_report.py")


if __name__ == "__main__":
    main()
