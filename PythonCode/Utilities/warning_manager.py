import warnings


class CustomWarning(Warning):
    def __init__(self, category: str, message: str, entry_id: str = None):
        self.category = category
        self.message = message
        self.entry_id = entry_id
        super().__init__(self.message)


class WarningManager:
    def __init__(self):
        self.warning_count = 0
        self.warnings = []

    def log_warning(
        self, category: str, warning_message: str, entry_id: str = None
    ) -> CustomWarning:
        warning = CustomWarning(category, warning_message, entry_id)
        warnings.warn(warning)
        self.warning_count += 1
        self.warnings.append(warning)
        return warning

    def display_warning_summary(self):
        if self.warning_count > 0:
            print(f"\nWarning Summary ({self.warning_count} warnings):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"{i}. {warning.category}: {warning.message[:50]}...")

            user_input = input(
                "\nEnter a number to see full warning details, or press Enter to continue: "
            )
            if user_input.isdigit() and 1 <= int(user_input) <= len(self.warnings):
                warning = self.warnings[int(user_input) - 1]
                print(f"\nFull Warning Details:")
                print(f"Category: {warning.category}")
                print(f"Message: {warning.message}")
                print(f"Entry ID: {warning.entry_id}")
                input("Press Enter to continue...")
