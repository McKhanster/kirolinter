"""
Sample vulnerable Python code for testing KiroLinter detection capabilities.
This file contains intentional security vulnerabilities, code smells, and performance issues.
"""

import os
import sqlite3
import pickle
import subprocess
import yaml
import xml.etree.ElementTree as ET


# Security Vulnerabilities

def sql_injection_example(user_id):
    """Example of SQL injection vulnerability."""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Vulnerable: Direct string formatting in SQL query
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    
    return cursor.fetchall()


def eval_vulnerability(user_input):
    """Example of eval() vulnerability."""
    # Dangerous: Executing arbitrary user input
    result = eval(user_input)
    return result


def exec_vulnerability(code_string):
    """Example of exec() vulnerability."""
    # Dangerous: Executing arbitrary code
    exec(code_string)


def pickle_deserialization(data):
    """Example of unsafe pickle deserialization."""
    # Vulnerable: Deserializing untrusted data
    obj = pickle.loads(data)
    return obj


def yaml_load_vulnerability(yaml_string):
    """Example of unsafe YAML loading."""
    # Vulnerable: Using unsafe yaml.load
    data = yaml.load(yaml_string)
    return data


def subprocess_shell_injection(filename):
    """Example of shell injection in subprocess."""
    # Vulnerable: Using shell=True with user input
    result = subprocess.run(f"cat {filename}", shell=True, capture_output=True)
    return result.stdout


def os_system_vulnerability(command):
    """Example of os.system vulnerability."""
    # Vulnerable: Direct execution of user input
    os.system(command)


def xml_external_entity(xml_data):
    """Example of XML External Entity vulnerability."""
    # Vulnerable: Parsing XML without protection against XXE
    root = ET.fromstring(xml_data)
    return root


def hardcoded_secrets():
    """Example of hardcoded secrets."""
    # Vulnerable: Hardcoded credentials
    api_key = "sk-1234567890abcdef"
    password = "admin123"
    secret_token = "secret_token_12345"
    
    return api_key, password, secret_token


# Code Smells

def unused_variables_example():
    """Function with unused variables."""
    used_variable = "I am used"
    unused_variable = "I am not used"
    another_unused = 42
    yet_another_unused = [1, 2, 3]
    
    print(used_variable)
    return True


def dead_code_example():
    """Function with dead code after return."""
    value = calculate_something()
    
    if value > 0:
        return "positive"
    
    return "non-positive"
    
    # Dead code below - will never execute
    print("This will never be printed")
    unused_after_return = "dead variable"
    return "unreachable"


def overly_complex_function(a, b, c, d, e, f, g):
    """Function with high cyclomatic complexity."""
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        if f > 0:
                            if g > 0:
                                return a + b + c + d + e + f + g
                            else:
                                return a + b + c + d + e + f
                        else:
                            return a + b + c + d + e
                    else:
                        return a + b + c + d
                else:
                    return a + b + c
            else:
                return a + b
        else:
            return a
    else:
        if b < 0:
            if c < 0:
                return -1
            else:
                return -2
        else:
            return 0


def duplicate_code_block_1():
    """First instance of duplicate code."""
    data = []
    for i in range(10):
        if i % 2 == 0:
            data.append(i * 2)
        else:
            data.append(i * 3)
    return data


def duplicate_code_block_2():
    """Second instance of duplicate code."""
    data = []
    for i in range(10):
        if i % 2 == 0:
            data.append(i * 2)
        else:
            data.append(i * 3)
    return data


# Performance Issues

def inefficient_string_concatenation(items):
    """Example of inefficient string concatenation."""
    result = ""
    # Inefficient: String concatenation in loop
    for item in items:
        result = result + str(item) + ","
    return result


def inefficient_list_concatenation(items):
    """Example of inefficient list concatenation."""
    result = []
    # Inefficient: List concatenation in loop
    for item in items:
        result = result + [item * 2]
    return result


def redundant_len_calls(data_list):
    """Example of redundant len() calls."""
    # Inefficient: Calling len() repeatedly
    for i in range(len(data_list)):
        if len(data_list) > 10:
            print(f"Item {i}: {data_list[i]}")
        if len(data_list) > 100:
            break


def nested_loops_with_inefficiency(matrix):
    """Example of nested loops with inefficient operations."""
    result = []
    # Inefficient: Nested loops with repeated operations
    for i in range(len(matrix)):
        for j in range(len(matrix[i])):
            # Inefficient: Creating new list each time
            temp_list = []
            for k in range(10):
                temp_list = temp_list + [matrix[i][j] * k]
            result.append(temp_list)
    return result


def memory_inefficient_operation(large_list):
    """Example of memory-inefficient operation."""
    # Inefficient: Creating multiple copies of large data
    copy1 = large_list[:]
    copy2 = large_list[:]
    copy3 = large_list[:]
    
    # Inefficient: Not using generators for large datasets
    squared = [x * x for x in large_list]
    cubed = [x * x * x for x in large_list]
    
    return copy1, copy2, copy3, squared, cubed


# Mixed Issues

class ProblematicClass:
    """Class with multiple types of issues."""
    
    def __init__(self):
        self.data = []
        self.unused_attribute = "not used"
        self.secret_key = "hardcoded_secret_123"  # Security issue
    
    def vulnerable_method(self, user_input):
        """Method with security vulnerability."""
        # SQL injection
        query = f"SELECT * FROM data WHERE value = '{user_input}'"
        
        # Eval vulnerability
        if user_input.startswith("eval:"):
            result = eval(user_input[5:])
            return result
        
        return query
    
    def inefficient_method(self, items):
        """Method with performance issues."""
        # Inefficient operations
        for i in range(len(items)):
            if len(self.data) > 0:  # Redundant len() call
                self.data = self.data + [items[i]]  # Inefficient concatenation
        
        return len(self.data)
    
    def complex_method(self, a, b, c, d):
        """Method with high complexity."""
        unused_var = "not used"  # Code smell
        
        if a > 0:
            if b > 0:
                if c > 0:
                    if d > 0:
                        return self._helper_method(a, b, c, d)
                    else:
                        return self._helper_method(a, b, c, 0)
                else:
                    if d > 0:
                        return self._helper_method(a, b, 0, d)
                    else:
                        return self._helper_method(a, b, 0, 0)
            else:
                return a
        else:
            return 0
        
        # Dead code
        print("This will never execute")
        return -1
    
    def _helper_method(self, a, b, c, d):
        """Helper method."""
        return a + b + c + d


# Utility functions for testing

def calculate_something():
    """Utility function for testing."""
    return 42


def create_test_data():
    """Create test data with various issues."""
    # Hardcoded sensitive data
    config = {
        'database_password': 'admin123',
        'api_secret': 'sk-abcdef123456',
        'encryption_key': 'my_secret_key'
    }
    
    return config


# Global variables (potential code smell)
GLOBAL_COUNTER = 0
UNUSED_GLOBAL = "not used anywhere"


def modify_global():
    """Function that modifies global state."""
    global GLOBAL_COUNTER
    GLOBAL_COUNTER += 1
    
    # Unused local variable
    temp_var = "temporary"
    
    return GLOBAL_COUNTER


# Function with multiple return statements (code smell)
def multiple_returns(value):
    """Function with multiple return statements."""
    if value < 0:
        return "negative"
    
    if value == 0:
        return "zero"
    
    if value < 10:
        return "small positive"
    
    if value < 100:
        return "medium positive"
    
    return "large positive"


# Long parameter list (code smell)
def too_many_parameters(a, b, c, d, e, f, g, h, i, j, k, l):
    """Function with too many parameters."""
    return a + b + c + d + e + f + g + h + i + j + k + l


if __name__ == "__main__":
    # Code that would trigger various issues when analyzed
    test_data = create_test_data()
    
    # This would trigger security warnings
    user_id = "1 OR 1=1"  # SQL injection payload
    result = sql_injection_example(user_id)
    
    # This would trigger eval warning
    dangerous_input = "__import__('os').system('ls')"
    eval_result = eval_vulnerability(dangerous_input)
    
    # Performance issues
    large_list = list(range(10000))
    inefficient_result = inefficient_list_concatenation(large_list)
    
    print("Test file executed - this contains intentional vulnerabilities for testing!")