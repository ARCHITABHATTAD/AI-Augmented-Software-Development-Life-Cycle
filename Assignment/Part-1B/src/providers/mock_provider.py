from __future__ import annotations

import json
import re

from src.domain.enums import CATEGORY_TO_DEPARTMENT, Category


class MockProvider:
    def __init__(self, raw_response: str | None = None):
        self.raw_response = raw_response
        self.last_response: str | None = None

    def triage(self, message: str) -> str:
        if self.raw_response is not None:
            self.last_response = self.raw_response
            return self.raw_response

        result = build_mock_result(message)
        self.last_response = json.dumps(result, ensure_ascii=False)
        return self.last_response


def build_mock_result(message: str) -> dict[str, object]:
    lowered = message.lower()
    category, multiple_ambiguous = _dominant_category(lowered)
    security_sensitive = _security_sensitive(lowered)
    prohibited_request = _prohibited_request(lowered)

    if security_sensitive:
        priority = "CRITICAL"
    elif any(word in lowered for word in ("urgent", "emergency", "essential", "locked out")):
        priority = "HIGH"
    elif category in (Category.PAYMENT, Category.DELIVERY, Category.TECHNICAL):
        priority = "MEDIUM"
    else:
        priority = "LOW"

    if any(word in lowered for word in ("thank you", "thanks", "great", "appreciate")):
        sentiment = "POSITIVE"
    elif any(
        word in lowered
        for word in (
            "angry",
            "upset",
            "frustrated",
            "not working",
            "hasn't arrived",
            "has not arrived",
            "not arrived",
            "charged twice",
            "charged me",
            "declined",
            "cannot",
            "can't",
            "locked out",
            "blocked",
            "frustrating",
            "frustrated",
            "unauthorized",
            "fraud",
            "issue",
            "problem",
            "wrong",
            "missing",
        )
    ):
        sentiment = "NEGATIVE"
    else:
        sentiment = "NEUTRAL"

    needs_clarification = (
        _underspecified(lowered)
        or multiple_ambiguous
        or (
            category == Category.DELIVERY
            and any(word in lowered for word in ("late", "missing", "hasn't arrived", "not arrived"))
            and not re.search(r"\b(?:order|tracking)\s*(?:number|#)\s*[\w-]+", lowered)
        )
    )
    clarification_question = (
        "Could you share the order or tracking number so support can check the delivery?"
        if needs_clarification and category == Category.DELIVERY
        else (
            "Could you describe what happened and which service or transaction is affected?"
            if needs_clarification
            else None
        )
    )

    human_review = security_sensitive or prohibited_request
    if security_sensitive:
        response = (
            "Please do not share passwords or verification codes. A support specialist should "
            "review this message."
        )
    elif prohibited_request:
        response = (
            "I cannot perform financial transactions or account changes. A support specialist "
            "can review your request."
        )
    elif needs_clarification:
        response = clarification_question or "Could you provide a little more detail?"
    else:
        response = (
            f"A support agent can review the details of this {category.value.lower()} issue "
            "and advise on next steps."
        )

    rationale = _rationale(category, priority, security_sensitive)
    return {
        "category": category.value,
        "priority": priority,
        "sentiment": sentiment,
        "department": CATEGORY_TO_DEPARTMENT[category].value,
        "suggested_response": response,
        "rationale": rationale,
        "clarification_required": needs_clarification,
        "clarification_question": clarification_question,
        "human_review_required": human_review,
    }


def _dominant_category(message: str) -> tuple[Category, bool]:
    terms = {
        Category.PAYMENT: {
            "payment": 2,
            "charged": 2,
            "charge": 2,
            "refund": 2,
            "billing": 2,
            "invoice": 1,
            "card": 1,
            "transaction": 2,
            "subscription": 1,
        },
        Category.DELIVERY: {
            "delivery": 2,
            "package": 2,
            "shipment": 2,
            "tracking": 2,
            "arrived": 2,
            "late": 1,
            "order": 1,
            "missing": 1,
        },
        Category.ACCOUNT: {
            "account": 2,
            "login": 2,
            "password": 3,
            "passcode": 3,
            "verification code": 3,
            "email": 1,
            "profile": 1,
            "locked out": 3,
            "unauthorized": 3,
        },
        Category.TECHNICAL: {
            "technical": 2,
            "app": 1,
            "website": 2,
            "error": 2,
            "crash": 2,
            "bug": 2,
            "loading": 2,
            "not working": 2,
            "service outage": 3,
        },
    }
    scores = {
        category: sum(weight for term, weight in phrases.items() if term in message)
        for category, phrases in terms.items()
    }
    if "charged twice" in message or "unknown charge" in message or "fraud" in message:
        scores[Category.PAYMENT] += 5
    if any(term in message for term in ("account compromise", "unauthorized login", "stolen")):
        scores[Category.ACCOUNT] += 5
    ranked = sorted(scores.items(), key=lambda item: (-item[1], list(terms).index(item[0])))
    if not ranked or ranked[0][1] == 0:
        return Category.GENERAL, False
    tie = ranked[1][1] == ranked[0][1] and ranked[0][1] > 0
    return ranked[0][0], tie


def _security_sensitive(message: str) -> bool:
    return any(
        term in message
        for term in (
            "password",
            "passcode",
            "verification code",
            "one-time code",
            "api key",
            "access token",
            "card number",
            "cvv",
            "security code",
            "account compromise",
            "unauthorized login",
            "unknown login",
            "fraud",
            "stolen",
        )
    )


def _prohibited_request(message: str) -> bool:
    return any(
        term in message
        for term in (
            "refund me",
            "send money",
            "transfer money",
            "pay this",
            "change my email",
            "change my password",
            "modify my account",
            "update my account",
            "cancel my account",
            "make a payment",
        )
    )


def _underspecified(message: str) -> bool:
    normalized = re.sub(r"[^\w\s]", "", message.lower()).strip()
    return normalized in {
        "help",
        "please help",
        "i need help",
        "there is a problem",
        "i have an issue",
        "something is wrong",
    }


def _rationale(category: Category, priority: str, sensitive: bool) -> str:
    if sensitive:
        return (
            "The message contains a security-sensitive signal, so human review is required and "
            "the priority is critical."
        )
    if priority == "HIGH":
        return (
            f"The message describes a {category.value.lower()} issue with time-sensitive or "
            "essential impact."
        )
    if priority == "MEDIUM":
        return (
            f"The message describes a material {category.value.lower()} issue without evidence "
            "of immediate critical harm."
        )
    return f"The message supports a routine {category.value.lower()} classification."
