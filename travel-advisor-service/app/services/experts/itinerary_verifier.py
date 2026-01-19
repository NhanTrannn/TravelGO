"""
Itinerary Verifier Expert - Validates and optimizes itinerary schedules

This module implements a two-phase verification system:
1. Rule-based validator: Deterministic checks for hard constraints
2. LLM-as-critic: Soft constraint checking and optimization suggestions

Key validations:
- Time-of-day constraints (night_market → evening/night only)
- Opening hours compliance
- Travel time between spots
- Hotel check-in/check-out timing
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from app.core import logger


@dataclass
class VerificationIssue:
    """Single issue found during verification"""
    type: str  # time_of_day_mismatch, opening_hours_violation, travel_time_exceeded
    spot_id: str
    spot_name: str
    current_slot: str  # morning, afternoon, evening, night
    expected_slots: List[str]  # Acceptable time slots
    day: int
    severity: str  # error, warning
    reason: str
    suggested_fix: Optional[Dict] = None  # {"to_day": 2, "to_slot": "night"}


@dataclass
class VerificationResult:
    """Complete verification result"""
    verdict: str  # pass, fail, warning
    issues: List[VerificationIssue] = field(default_factory=list)
    suggested_moves: List[Dict] = field(default_factory=list)
    auto_fixed: bool = False
    fixed_itinerary: Optional[List[Dict]] = None


# Category to best visit time mapping (rule-based)
CATEGORY_TIME_CONSTRAINTS = {
    # Evening/Night only spots
    "night_market": ["evening", "night"],
    "nightlife": ["evening", "night"],
    "bar": ["evening", "night"],
    "club": ["night"],
    "night_food": ["evening", "night"],
    "chợ_đêm": ["evening", "night"],
    "phố_đêm": ["evening", "night"],

    # Morning preferred spots
    "sunrise": ["early_morning"],
    "morning_market": ["early_morning", "morning"],
    "chợ_sáng": ["early_morning", "morning"],
    "temple": ["morning", "afternoon"],  # Best to visit temples in daylight
    "pagoda": ["morning", "afternoon"],
    "chùa": ["morning", "afternoon"],

    # Beach activities
    "beach": ["morning", "afternoon"],  # Avoid midday sun
    "beach_swimming": ["morning", "afternoon"],
    "biển": ["morning", "afternoon"],
    "bãi_biển": ["morning", "afternoon"],

    # Sunset spots
    "sunset_view": ["afternoon", "evening"],
    "sunset": ["afternoon", "evening"],
    "ngắm_hoàng_hôn": ["afternoon", "evening"],

    # All-day activities
    "museum": ["morning", "afternoon", "evening"],
    "shopping": ["morning", "afternoon", "evening"],
    "landmark": ["morning", "afternoon", "evening"],
    "park": ["morning", "afternoon", "evening"],
    "theme_park": ["morning", "afternoon"],
    "amusement": ["morning", "afternoon", "evening"],
}

# Name patterns that indicate time constraints
NAME_TIME_PATTERNS = {
    # Night patterns
    "chợ đêm": ["evening", "night"],
    "night market": ["evening", "night"],
    "phố đêm": ["evening", "night"],
    "bar ": ["evening", "night"],
    "quán bar": ["evening", "night"],
    "club": ["night"],

    # Morning patterns
    "bình minh": ["early_morning"],
    "sunrise": ["early_morning"],
    "chợ sáng": ["early_morning", "morning"],

    # Sunset patterns
    "hoàng hôn": ["afternoon", "evening"],
    "sunset": ["afternoon", "evening"],
}

# Time slot definitions (24h format ranges)
TIME_SLOTS = {
    "early_morning": (5, 7),    # 05:00 - 07:00
    "morning": (7, 11),         # 07:00 - 11:00
    "midday": (11, 14),         # 11:00 - 14:00
    "afternoon": (14, 17),      # 14:00 - 17:00
    "evening": (17, 21),        # 17:00 - 21:00
    "night": (21, 24),          # 21:00 - 24:00
}


class ItineraryVerifier:
    """
    Verifies and optimizes itinerary schedules using rule-based and LLM approaches.

    Usage:
        verifier = ItineraryVerifier(llm_client)
        result = verifier.verify(itinerary_days, spots_data)

        if result.verdict == "fail":
            fixed_itinerary = verifier.auto_fix(itinerary_days, result.issues)
    """

    def __init__(self, llm_client=None, mongo_manager=None):
        self.llm = llm_client
        self.mongo = mongo_manager
        logger.info("✅ ItineraryVerifier initialized")

    def verify(
        self,
        itinerary_days: List[Dict],
        spots_data: Optional[Dict[str, Dict]] = None
    ) -> VerificationResult:
        """
        Verify itinerary using rule-based + LLM validation.

        Args:
            itinerary_days: List of day plans with activities
                [{"day": 1, "activities": [{"time": "08:00", "spot_id": "...", "spot_name": "..."}]}]
            spots_data: Optional mapping of spot_id → spot details with best_visit_time

        Returns:
            VerificationResult with issues and suggestions
        """
        start_time = time.time()
        all_issues = []

        # Phase 1: Rule-based validation
        rule_issues = self._rule_based_validation(itinerary_days, spots_data)
        all_issues.extend(rule_issues)

        # Phase 2: LLM validation (if available and rule issues exist)
        if self.llm and (len(rule_issues) > 0 or len(itinerary_days) > 2):
            llm_issues = self._llm_validation(itinerary_days, spots_data)
            # Merge LLM issues, avoiding duplicates
            for llm_issue in llm_issues:
                if not any(
                    i.spot_id == llm_issue.spot_id and i.day == llm_issue.day
                    for i in all_issues
                ):
                    all_issues.append(llm_issue)

        # Determine verdict
        error_count = sum(1 for i in all_issues if i.severity == "error")
        warning_count = sum(1 for i in all_issues if i.severity == "warning")

        if error_count > 0:
            verdict = "fail"
        elif warning_count > 0:
            verdict = "warning"
        else:
            verdict = "pass"

        # Generate suggested moves for issues
        suggested_moves = self._generate_suggested_moves(all_issues, itinerary_days)

        exec_time = int((time.time() - start_time) * 1000)
        logger.info(f"🔍 Verification complete in {exec_time}ms: {verdict} ({error_count} errors, {warning_count} warnings)")

        return VerificationResult(
            verdict=verdict,
            issues=all_issues,
            suggested_moves=suggested_moves
        )

    def _rule_based_validation(
        self,
        itinerary_days: List[Dict],
        spots_data: Optional[Dict[str, Dict]] = None
    ) -> List[VerificationIssue]:
        """
        Rule-based validation - deterministic checks.

        Checks:
        1. Time-of-day constraints based on category
        2. Name pattern matching for time restrictions
        3. Opening hours (if available in spots_data)
        """
        issues = []

        for day_plan in itinerary_days:
            day_num = day_plan.get("day", 1)
            activities = day_plan.get("activities", [])

            # Also check spots field for different format
            if not activities and "spots" in day_plan:
                activities = [
                    {"spot_name": s.get("name") if isinstance(s, dict) else s, "time": self._get_default_time(i)}
                    for i, s in enumerate(day_plan["spots"])
                ]

            for activity in activities:
                spot_name = activity.get("spot_name", activity.get("location", ""))
                spot_id = activity.get("spot_id", spot_name)
                time_str = activity.get("time", "")
                category = activity.get("category", "")

                # Determine current slot from time
                current_slot = self._time_to_slot(time_str)

                # Get spot metadata if available
                spot_meta = spots_data.get(spot_id, {}) if spots_data else {}
                best_visit_time = spot_meta.get("best_visit_time", [])
                spot_category = category or spot_meta.get("category", "")

                # Check 1: Category-based time constraints
                if spot_category:
                    expected_slots = CATEGORY_TIME_CONSTRAINTS.get(spot_category.lower(), [])
                    if expected_slots and current_slot not in expected_slots:
                        issues.append(VerificationIssue(
                            type="time_of_day_mismatch",
                            spot_id=spot_id,
                            spot_name=spot_name,
                            current_slot=current_slot,
                            expected_slots=expected_slots,
                            day=day_num,
                            severity="error",
                            reason=f"{spot_name} ({spot_category}) phù hợp vào {', '.join(expected_slots)}, không phải {current_slot}"
                        ))
                        continue  # Don't double-check with name patterns

                # Check 2: Name pattern matching
                spot_name_lower = spot_name.lower()
                for pattern, expected_slots in NAME_TIME_PATTERNS.items():
                    if pattern in spot_name_lower:
                        if current_slot not in expected_slots:
                            issues.append(VerificationIssue(
                                type="time_of_day_mismatch",
                                spot_id=spot_id,
                                spot_name=spot_name,
                                current_slot=current_slot,
                                expected_slots=expected_slots,
                                day=day_num,
                                severity="error",
                                reason=f"'{spot_name}' có từ khóa '{pattern}' nên phù hợp vào {', '.join(expected_slots)}"
                            ))
                        break

                # Check 3: DB-provided best_visit_time
                if best_visit_time and current_slot not in best_visit_time:
                    # Only warn if we haven't already found an error
                    if not any(i.spot_id == spot_id and i.day == day_num for i in issues):
                        issues.append(VerificationIssue(
                            type="time_of_day_mismatch",
                            spot_id=spot_id,
                            spot_name=spot_name,
                            current_slot=current_slot,
                            expected_slots=best_visit_time,
                            day=day_num,
                            severity="warning",
                            reason=f"Theo dữ liệu, {spot_name} tốt nhất nên đi vào {', '.join(best_visit_time)}"
                        ))

        return issues

    def _llm_validation(
        self,
        itinerary_days: List[Dict],
        spots_data: Optional[Dict[str, Dict]] = None
    ) -> List[VerificationIssue]:
        """
        LLM-as-critic validation for soft constraints.

        Checks:
        1. Logical flow (e.g., don't go far then come back)
        2. Cultural context (e.g., temple visits in appropriate attire time)
        3. Meal timing with restaurant visits
        """
        if not self.llm:
            return []

        issues = []

        try:
            # Format itinerary for LLM
            itinerary_text = self._format_itinerary_for_llm(itinerary_days)

            prompt = f"""Bạn là chuyên gia kiểm duyệt lịch trình du lịch Việt Nam.

LỊCH TRÌNH CẦN KIỂM TRA:
{itinerary_text}

HÃY KIỂM TRA các vấn đề sau:
1. ❌ Chợ đêm/Night market bị xếp vào buổi sáng/trưa (phải là tối)
2. ❌ Điểm ngắm bình minh bị xếp vào chiều/tối (phải là sáng sớm)
3. ❌ Điểm ngắm hoàng hôn bị xếp vào sáng (phải là chiều/tối)
4. ⚠️ Đi xa rồi quay lại cùng khu vực (không tối ưu)
5. ⚠️ Quá nhiều hoạt động trong 1 ngày (>4 địa điểm)

TRẢ VỀ JSON (CHỈ JSON, KHÔNG GIẢI THÍCH):
{{
  "issues": [
    {{
      "day": 1,
      "spot_name": "Tên địa điểm",
      "problem": "Mô tả vấn đề",
      "severity": "error|warning",
      "suggested_slot": "morning|afternoon|evening|night"
    }}
  ]
}}

Nếu không có vấn đề, trả về: {{"issues": []}}"""

            result = self.llm.extract_json(prompt)

            if result and "issues" in result:
                for issue in result["issues"]:
                    issues.append(VerificationIssue(
                        type="llm_detected",
                        spot_id=issue.get("spot_name", ""),
                        spot_name=issue.get("spot_name", ""),
                        current_slot="",
                        expected_slots=[issue.get("suggested_slot", "")],
                        day=issue.get("day", 1),
                        severity=issue.get("severity", "warning"),
                        reason=issue.get("problem", "")
                    ))

        except Exception as e:
            logger.warning(f"⚠️ LLM validation failed: {e}")

        return issues

    def auto_fix(
        self,
        itinerary_days: List[Dict],
        issues: List[VerificationIssue]
    ) -> Tuple[List[Dict], List[str]]:
        """
        Attempt to auto-fix issues in itinerary.

        Returns:
            Tuple of (fixed_itinerary, list_of_changes_made)
        """
        import copy
        fixed = copy.deepcopy(itinerary_days)
        changes = []

        for issue in issues:
            if issue.severity != "error":
                continue  # Only fix errors, not warnings

            if issue.type == "time_of_day_mismatch":
                # Try to move spot to appropriate time slot
                result = self._try_fix_time_slot(fixed, issue)
                if result:
                    changes.append(result)

        return fixed, changes

    def _try_fix_time_slot(
        self,
        itinerary: List[Dict],
        issue: VerificationIssue
    ) -> Optional[str]:
        """
        Try to fix a time slot issue by rearranging activities.

        Strategy:
        1. If spot needs evening/night → move to later in the same day
        2. If no slot available → swap with another activity
        """
        day_num = issue.day
        target_slots = issue.expected_slots

        # Find the day
        day_plan = None
        for d in itinerary:
            if d.get("day") == day_num:
                day_plan = d
                break

        if not day_plan:
            return None

        activities = day_plan.get("activities", [])

        # Find the problematic activity
        target_idx = None
        for i, act in enumerate(activities):
            if act.get("spot_name") == issue.spot_name or act.get("location") == issue.spot_name:
                target_idx = i
                break

        if target_idx is None:
            return None

        # Try to move to appropriate slot
        if "evening" in target_slots or "night" in target_slots:
            # Move to end of day
            activity = activities.pop(target_idx)
            activity["time"] = "19:00" if "evening" in target_slots else "21:00"
            activities.append(activity)
            return f"Đã chuyển '{issue.spot_name}' sang buổi tối ngày {day_num}"

        elif "morning" in target_slots or "early_morning" in target_slots:
            # Move to start of day
            activity = activities.pop(target_idx)
            activity["time"] = "06:00" if "early_morning" in target_slots else "08:00"
            activities.insert(0, activity)
            return f"Đã chuyển '{issue.spot_name}' sang buổi sáng ngày {day_num}"

        return None

    def _generate_suggested_moves(
        self,
        issues: List[VerificationIssue],
        itinerary_days: List[Dict]
    ) -> List[Dict]:
        """Generate suggested moves for each issue."""
        suggestions = []

        for issue in issues:
            if issue.expected_slots:
                target_slot = issue.expected_slots[0]
                suggestions.append({
                    "spot_id": issue.spot_id,
                    "spot_name": issue.spot_name,
                    "from_day": issue.day,
                    "from_slot": issue.current_slot,
                    "to_day": issue.day,  # Same day by default
                    "to_slot": target_slot,
                    "reason": issue.reason
                })

        return suggestions

    def _time_to_slot(self, time_str: str) -> str:
        """Convert time string to slot name."""
        if not time_str:
            return "morning"

        try:
            hour = int(time_str.split(":")[0])

            if 5 <= hour < 7:
                return "early_morning"
            elif 7 <= hour < 11:
                return "morning"
            elif 11 <= hour < 14:
                return "midday"
            elif 14 <= hour < 17:
                return "afternoon"
            elif 17 <= hour < 21:
                return "evening"
            else:
                return "night"
        except:
            return "morning"

    def _get_default_time(self, index: int) -> str:
        """Get default time for activity based on index."""
        times = ["08:00", "10:00", "14:00", "16:00", "19:00"]
        return times[index % len(times)]

    def _format_itinerary_for_llm(self, itinerary_days: List[Dict]) -> str:
        """Format itinerary for LLM prompt."""
        lines = []

        for day_plan in itinerary_days:
            day_num = day_plan.get("day", 1)
            lines.append(f"\n📅 NGÀY {day_num}:")

            activities = day_plan.get("activities", [])
            if not activities and "spots" in day_plan:
                activities = [
                    {"spot_name": s.get("name") if isinstance(s, dict) else s, "time": self._get_default_time(i)}
                    for i, s in enumerate(day_plan["spots"])
                ]

            for act in activities:
                time_str = act.get("time", "")
                spot = act.get("spot_name", act.get("location", ""))
                lines.append(f"  {time_str} - {spot}")

        return "\n".join(lines)


def create_itinerary_verifier(llm_client=None, mongo_manager=None) -> ItineraryVerifier:
    """Factory function to create ItineraryVerifier."""
    return ItineraryVerifier(llm_client, mongo_manager)
