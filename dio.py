from pydwf import DwfLibrary


class PinController:
    """Wrapper for an individual Digital IO pin."""

    def __init__(self, dio, pin_index: int):
        self._dio = dio
        self._mask = 1 << pin_index

    @property
    def on(self) -> bool:
        """Read whether the pin output is driven HIGH."""
        return bool(self._dio.outputGet() & self._mask)

    @on.setter
    def on(self, value: bool) -> None:
        """Set the pin HIGH (True) or LOW (False), enabling output if needed."""
        # Ensure direction bit is enabled for output
        current_enable = self._dio.outputEnableGet()
        if not (current_enable & self._mask):
            self._dio.outputEnableSet(current_enable | self._mask)

        # Update output state without altering other pins
        current_output = self._dio.outputGet()
        if value:
            self._dio.outputSet(current_output | self._mask)
        else:
            self._dio.outputSet(current_output & ~self._mask)


class DIOWrapper:
    """Wrapper for pydwf DigitalIO to enable intuitive pin manipulation."""

    def __init__(self, dio):
        self._dio = dio

    def pin(self, index: int) -> PinController:
        """Access a specific DIO pin controller."""
        return PinController(self._dio, index)


# --- Example Usage ---

dwf = DwfLibrary()

with dwf.deviceControl.open(-1) as device:
    dio = DIOWrapper(device.digitalIO)

    # Turn on pin 1
    dio.pin(1).on = True

    # Check state
    print(f"Pin 1 state: {dio.pin(1).on}")  # Output: True

    # Turn off pin 1
    dio.pin(1).on = False