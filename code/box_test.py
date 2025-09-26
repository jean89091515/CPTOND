#!/usr/bin/env python3
"""
Testing and Logging Utilities

This module provides decorators and utilities for testing function execution,
logging outputs, and debugging during development. Includes thread-safe
logging mechanisms for concurrent processing.

Dependencies:
    - threading (standard library)
    - traceback (standard library)
    - functools (standard library)

Features:
    - Function execution testing with automatic error handling
    - Thread-safe logging with hierarchical output formatting
    - Execution status tracking and error reporting

Author: Development Testing Team
License: MIT
"""

import threading
import traceback
from functools import wraps

# Global configuration variables
PREFIX = ""  # Output prefix for hierarchical reading
PRINT_LOG = True  # Control whether to print logs
LOG = ""  # Global log storage
lock = threading.Lock()  # Thread lock for concurrent access


def log(*args, **kwargs):
    """
    Thread-safe logging function with hierarchical formatting
    
    Provides formatted output with automatic prefixing for better readability
    in nested function calls. Supports standard print() parameters.
    
    Args:
        *args: Variable arguments to log (similar to print())
        **kwargs: Keyword arguments (sep, end, encoding)
    
    Global Variables:
        PREFIX (str): Current indentation prefix
        PRINT_LOG (bool): Whether to print to console
        LOG (str): Accumulated log string
    """
    lock.acquire()  # Acquire thread lock for safe logging
    
    # Parse keyword arguments with defaults
    sep = kwargs.get("sep", " ")  # Default separator
    end = kwargs.get("end", "\n")  # Default line ending
    encoding = kwargs.get("encoding", "utf-8")  # Default encoding
    
    # Build log message
    new_log = PREFIX  # Start with current prefix
    
    # Add all arguments with separator
    for i, arg in enumerate(args):
        if i > 0:  # Add separator before all but first argument
            new_log += sep
        new_log += str(arg)
    
    new_log += end
    
    # Replace newlines with newline + prefix for hierarchical formatting
    new_log = new_log.replace("\n", "\n" + PREFIX)
    
    # Output to console if enabled
    if PRINT_LOG:
        print(new_log, end="")
    
    # Accumulate in global log
    global LOG
    LOG += new_log
    
    lock.release()  # Release thread lock


def test(name=""):
    """
    Function execution testing decorator
    
    Decorates functions to provide automatic testing, error handling,
    and hierarchical logging of execution status. Useful for debugging
    and monitoring function execution in complex pipelines.
    
    Args:
        name (str): Descriptive name for the operation being tested
        
    Returns:
        function: Decorated function with testing capabilities
    
    Features:
        - Automatic execution status logging
        - Exception handling with detailed error reporting
        - Hierarchical output formatting
        - Function parameter logging on failure
    
    Usage:
        @test("Data Processing")
        def process_data(data):
            # Function implementation
            return processed_data
    """
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            global PREFIX
            
            try:
                # Log function execution start
                log(f"--- Starting: {name}")
                
                # Increase indentation for nested operations
                PREFIX += "    "
                
                # Execute the original function
                return func(*args, **kwargs)
                
            except Exception as e:
                # Log detailed error information
                error_msg = (
                    f"!!! FAILED: {name}\n"
                    f"Function: {func.__name__}\n"
                    f"Error: {e}\n"
                    f"Arguments: {args}\n"
                    f"Keyword Arguments: {kwargs}\n"
                    f"Traceback:\n{traceback.format_exc()}"
                )
                log(error_msg)
                
                # Re-raise the exception for upstream handling
                raise
                
            finally:
                # Decrease indentation level
                PREFIX = PREFIX[:-4] if len(PREFIX) >= 4 else ""
        
        return wrapper
    
    return decorator


def clear_log():
    """
    Clear the global log storage
    
    Resets the global LOG variable and PREFIX for fresh logging session.
    Thread-safe operation.
    """
    global LOG, PREFIX
    lock.acquire()
    LOG = ""
    PREFIX = ""
    lock.release()


def get_log():
    """
    Retrieve the current global log content
    
    Returns:
        str: Complete accumulated log content
    """
    global LOG
    lock.acquire()
    log_content = LOG
    lock.release()
    return log_content


def set_print_mode(enabled):
    """
    Enable or disable console output for logging
    
    Args:
        enabled (bool): True to enable console output, False to disable
    """
    global PRINT_LOG
    lock.acquire()
    PRINT_LOG = enabled
    lock.release()


def save_log_to_file(filepath):
    """
    Save accumulated log content to file
    
    Args:
        filepath (str): Path to output log file
        
    Returns:
        bool: True if successful, False if failed
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(get_log())
        return True
    except Exception as e:
        log(f"Failed to save log to {filepath}: {e}")
        return False


# Example usage and testing
if __name__ == "__main__":
    """
    Example usage of testing and logging utilities
    """
    
    @test("Example Function Test")
    def example_function(x, y):
        """Example function for demonstrating testing decorator"""
        log(f"Processing values: x={x}, y={y}")
        
        if x < 0:
            raise ValueError("x must be non-negative")
        
        result = x + y
        log(f"Calculation result: {result}")
        return result
    
    @test("Nested Function Test")
    def nested_example():
        """Example of nested function calls with hierarchical logging"""
        log("Starting nested operations")
        
        result1 = example_function(5, 3)
        result2 = example_function(2, 4)
        
        total = result1 + result2
        log(f"Total result: {total}")
        return total
    
    # Demonstrate successful execution
    print("=== Testing Successful Execution ===")
    try:
        result = nested_example()
        print(f"Final result: {result}")
    except Exception as e:
        print(f"Execution failed: {e}")
    
    print("\n=== Testing Error Handling ===")
    # Demonstrate error handling
    try:
        result = example_function(-1, 5)  # This will cause an error
    except ValueError as e:
        print(f"Caught expected error: {e}")
    
    print("\n=== Log Content ===")
    print("Complete log:")
    print(get_log())
    
    # Demonstrate log file saving
    print("\n=== Saving Log ===")
    if save_log_to_file("test_log.txt"):
        print("Log saved successfully to test_log.txt")
    else:
        print("Failed to save log")