from pydwf import DwfLibrary


class Pin:
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


# If exposing other pin functionality, do a different class, this is specifically for DIO
class DIO:
    """Wrapper for pydwf DigitalIO to enable intuitive pin manipulation.
    Specifically for controlling digital IO only.
    Across all pins DIO behaves the same, however there are multiple other
    functions (which differ between pins"""

    def __init__(self, dio):
        self._dio = dio
        self.Pin0 = Pin(self._dio, 0)
        self.Pin1 = Pin(self._dio, 1)
        self.Pin2 = Pin(self._dio, 2)
        self.Pin3 = Pin(self._dio, 3)
        self.Pin4 = Pin(self._dio, 4)
        self.Pin5 = Pin(self._dio, 5)
        self.Pin6 = Pin(self._dio, 6)
        self.Pin7 = Pin(self._dio, 7)
        self.Pin8 = Pin(self._dio, 8)
        self.Pin9 = Pin(self._dio, 9)
        self.Pin10 = Pin(self._dio, 10)
        self.Pin11 = Pin(self._dio, 11)
        self.Pin12 = Pin(self._dio, 12)
        self.Pin13 = Pin(self._dio, 13)
        self.Pin14 = Pin(self._dio, 14)
        self.Pin15 = Pin(self._dio, 15)




# --- Example Usage ---
if __name__ == "__main__":
    dwf = DwfLibrary()

    with dwf.deviceControl.open(-1) as device:
        dio_main = DIO(device.digitalIO)

        # Turn on pin 1
        dio_main.Pin0.on = True
