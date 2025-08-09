"""
Test file for KiroLinter GitHub integration.
This file contains intentional code quality issues for testing.
"""

import os
import sys  # Unused import - should be detected
import json  # Unused import - should be detected
import subprocess  # Unused import - should be detected

# Security issues for testing
API_KEY = "sk-1234567890abcdef1234567890abcdef"  # Hardcoded API key
DATABASE_PASSWORD = "super_secret_password_123"  # Hardcoded password
SECRET_TOKEN = "jwt_secret_token_abcdef123456"   # Hardcoded token

def unsafe_database_query(user_id):
    """Function with SQL injection vulnerability."""
    # SQL injection vulnerability - should be detected
    query = f"SELECT * FROM users WHERE id = {user_id}"
    
    # Another SQL injection pattern
    query2 = "SELECT * FROM posts WHERE author = '%s'" % user_id
    
    return query, query2

def unsafe_eval_function(user_input):
    """Function with unsafe eval usage."""
    # Critical security issue - should be detected
    result = eval(user_input)
    
    # Another unsafe operation
    exec(user_input)
    
    return result

def complex_function_with_issues(a, b, c, d, e, f, g, h):
    """Function with high cyclomatic complexity and code smells."""
    # Unused variables - should be detected
    unused_variable_1 = "this is not used"
    unused_variable_2 = 42
    temp_data = {"key": "value"}
    
    # High complexity nested conditions
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        if f > 0:
                            if g > 0:
                                if h > 0:
                                    return a + b + c + d + e + f + g + h
                                else:
                                    return 0
                            else:
                                return -1
                        else:
                            return -2
                    else:
                        return -3
                else:
                    return -4
            else:
                return -5
        else:
            return -6
    else:
        return -7
    
    # Dead code after return - should be detected
    print("This code is unreachable")
    dead_variable = "never executed"
    return dead_variable

def inefficient_loop_example():
    """Function with performance issues."""
    result = ""
    items = ["a", "b", "c", "d", "e"] * 100
    
    # Inefficient string concatenation in loop
    for item in items:
        result += item  # Should suggest using join()
    
    # Redundant len() calls in loop
    for i in range(len(items)):
        if i < len(items) - 1:  # len() called repeatedly
            print(f"Item {i}: {items[i]}")
    
    return result

class TestClass:
    """Class with various issues for testing."""
    
    def __init__(self):
        self.api_key = "hardcoded_api_key_in_class"  # Security issue
    
    def _private_method_not_used(self):
        """Private method that's never called."""
        return "unused private method"
    
    def method_with_issues(self, user_data):
        """Method with multiple issues."""
        # Unsafe operations
        processed_data = eval(f"process({user_data})")
        
        # SQL injection in method
        query = f"UPDATE users SET data = '{user_data}' WHERE id = 1"
        
        return processed_data, query

# Global variables with issues
GLOBAL_UNUSED = "this global is never used"
another_unused_global = 123

def main():
    """Main function that uses some but not all of the above."""
    # Only use a few functions to leave others unused
    result = complex_function_with_issues(1, 2, 3, 4, 5, 6, 7, 8)
    performance_result = inefficient_loop_example()
    
    # Use os but not the other imports
    current_dir = os.getcwd()
    
    return result, performance_result, current_dir

if __name__ == "__main__":
    main()
