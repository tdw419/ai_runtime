
class SafetyGuard:
    def __init__(self, max_risk_level="medium"):
        self.risk_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        self.max_risk_level = self.risk_levels.get(max_risk_level, 2)

    def validate(self, action):
        if not action:
            return False

        risk_level = self.risk_levels.get(action.get("risk_level", "high"), 3)

        if risk_level > self.max_risk_level:
            # Log the rejection of the action
            print(f"Action rejected due to high risk level: {action.get('risk_level')}")
            return False

        # Add more sophisticated checks here, for example:
        # - Blacklist/whitelist of commands
        # - Parameter validation (e.g., prevent `rm -rf /`)
        # - Rate limiting of actions

        return True
