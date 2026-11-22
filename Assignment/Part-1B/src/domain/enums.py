from enum import Enum


class StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class Category(StringEnum):
    PAYMENT = "PAYMENT"
    DELIVERY = "DELIVERY"
    ACCOUNT = "ACCOUNT"
    TECHNICAL = "TECHNICAL"
    GENERAL = "GENERAL"


class Priority(StringEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Sentiment(StringEnum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"


class Department(StringEnum):
    PAYMENT_SUPPORT = "PAYMENT_SUPPORT"
    DELIVERY_SUPPORT = "DELIVERY_SUPPORT"
    ACCOUNT_SUPPORT = "ACCOUNT_SUPPORT"
    TECHNICAL_SUPPORT = "TECHNICAL_SUPPORT"
    GENERAL_SUPPORT = "GENERAL_SUPPORT"


CATEGORY_TO_DEPARTMENT = {
    Category.PAYMENT: Department.PAYMENT_SUPPORT,
    Category.DELIVERY: Department.DELIVERY_SUPPORT,
    Category.ACCOUNT: Department.ACCOUNT_SUPPORT,
    Category.TECHNICAL: Department.TECHNICAL_SUPPORT,
    Category.GENERAL: Department.GENERAL_SUPPORT,
}
