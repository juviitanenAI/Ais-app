import re
from typing import Union

def validate_imo(imo: Union[str, int]) -> bool:
    """
    Validates an IMO ship identification number.
    An IMO number is a 7-digit number where the 7th digit is a checksum.
    
    Calculation: multiply each of the first six digits by their position (from 2 to 7) 
    counting from right to left. The last digit of the sum must be the check digit.
    """
    imo_str = str(imo).strip()
    
    # Must be exactly 7 digits
    if not re.match(r"^[0-9]{7}$", imo_str):
        return False
    
    digits = [int(d) for d in imo_str]
    check_digit = digits[6]
    
    # Factors from 7 down to 2
    sum_val = 0
    for i in range(6):
        factor = 7 - i
        sum_val += digits[i] * factor
        
    calc_check_digit = sum_val % 10
    
    return calc_check_digit == check_digit
