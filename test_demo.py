#!/usr/bin/env python3
# Test file with obvious issues for demo

import os
import sys
import json  # unused import

def bad_function():
    password = "hardcoded_secret_123"  # security issue
    unused_var = "this is unused"      # code quality issue
    
    # SQL injection vulnerability
    query = "SELECT * FROM users WHERE id = " + str(user_id)
    
    # Complex function with high cyclomatic complexity
    if True:
        if True:
            if True:
                if True:
                    if True:
                        print("too complex")
                        
    # Performance issue - inefficient loop
    result = ""
    for i in range(1000):
        result += str(i)  # should use join()
        
    return result

# Unsafe eval usage
eval("print('dangerous')")

# More unused variables
temp1 = 1
temp2 = 2  
temp3 = 3