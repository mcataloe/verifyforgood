from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

from .models import PolicyDefinition, PolicyEvaluation, PolicyOutcome, PolicyRule

try:
    from .engine import evaluate_policy
except ImportError:
    evaluate_policy = None

__all__ = [
    "PolicyDefinition",
    "PolicyEvaluation",
    "PolicyOutcome",
    "PolicyRule",
]

if evaluate_policy is not None:
    __all__.append("evaluate_policy")
