from .uart_rule import UARTRule
from .adc_rule import ADCRule
from .ethernet_rule import EthernetRule

ALL_RULES = [
    UARTRule(),
    ADCRule(),
    EthernetRule(),
]
