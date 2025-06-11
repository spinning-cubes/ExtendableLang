import re
import os
import argparse
import tkinter

parser = argparse.ArgumentParser(description="An interpreter for the Extendable Language.")
parser.add_argument("file", help="file to run")
parser.add_argument("-d", "--debug", help="show debug prints", action="store_true")
args = parser.parse_args()

home_dir = os.path.expanduser("~")

class ELInterpreter:
    """
    ELInterpreter: An interpreter for the Extendable Language (EL).
    """

    def __init__(self, debug=False):
        """
        Initializes the interpreter's state, including variable scopes,
        labels, program lines, current execution index, and loaded extensions.

        Args:
            debug (bool): If True, enables debug print statements. Defaults to False.
        """
        self.globals = {}          # Global variables
        self.locals = {}           # Local variables
        self.labels = {}           # Maps label names to line indices
        self.program_lines = []    # List of processed program lines
        self.current_line_index = 0 # Current line being executed
        self.extensions = {}       # Stores loaded extension classes/objects
        self.debug = debug         # Debug flag

    def load_program(self, el_code):
        """
        Loads the EL program code, preprocesses it, and maps labels.

        Args:
            el_code (str): The raw EL program code as a string.
        """
        raw_lines = el_code.split('\n')
        processed_lines = []
        for line in raw_lines:
            stripped_line = line.strip()
            # Keep lines that are labels (@name) or non-comment, non-empty lines
            if stripped_line.startswith('@') or (not stripped_line.startswith(';') and stripped_line):
                processed_lines.append(stripped_line)
        self.program_lines = processed_lines
        self._map_labels() # Map labels AFTER processing all lines to get correct indices

        if self.debug:
            print(f"\n--- Debug: Program Lines ---")
            for i, line in enumerate(self.program_lines):
                print(f"{i}: {line}")
            print(f"--- Debug: Mapped Labels ---")
            print(self.labels)
            print(f"----------------------------\n")


    def _map_labels(self):
        """
        Scans the program lines to identify and store label names with their
        corresponding line numbers in the `self.labels` dictionary.
        Labels are stored without the leading '@' symbol.
        """
        for i, line in enumerate(self.program_lines):
            if line.startswith('@'):
                label_name = line[1:] # Store label name WITHOUT the '@'
                self.labels[label_name] = i

    def run(self):
        """
        Executes the loaded EL program line by line.
        Handles program flow, including jumps and complex IF statements.
        """
        self.current_line_index = 0
        while self.current_line_index < len(self.program_lines):
            line = self.program_lines[self.current_line_index].strip()

            # Skip labels during execution; they are just markers for jumps
            if line.startswith('@'):
                self.current_line_index += 1
                continue

            if self.debug:
                print(f"DEBUG: Executing line {self.current_line_index}: '{line}'")

            # Handle multi-line IF statement separately
            if line.startswith("if "):
                next_index_after_if_structure = self._handle_if_statement(self.current_line_index)
                if next_index_after_if_structure is None:
                    print(f"Error: Malformed IF statement at line {self.current_line_index}. Halting program.")
                    break # Halt on error
                
                # _handle_if_statement returns the actual next line index, which could be a jump target
                self.current_line_index = next_index_after_if_structure 
            else:
                # For all other single-line statements
                original_index_before_exec = self.current_line_index # Store to detect jumps
                self._execute_single_statement(line)
                
                # If a jump occurred, _execute_single_statement would have updated self.current_line_index.
                # In that case, we don't increment it further.
                if self.current_line_index == original_index_before_exec:
                    self.current_line_index += 1 # Only increment if no jump happened

    def _execute_single_statement(self, line):
        """
        Parses and executes a single line of EL code.
        This method does NOT manage `self.current_line_index` for general program flow;
        that is handled by the `run()` loop or `_handle_if_statement()`.
        It WILL modify `self.current_line_index` if a `jump` instruction is executed.

        Args:
            line (str): The EL code line to execute.
        """
        # VARIABLE DEFINITION AND SETTING
        if line.startswith("local "):
            parts = re.match(r"local (.+) = (.+)", line)
            if parts:
                var_name = parts.group(1).strip()
                value = self._evaluate_expression(parts.group(2).strip(), scope="local")
                self.locals[var_name] = value
            else:
                print(f"Syntax error defining local variable: {line}")
        elif line.startswith("global "):
            parts = re.match(r"global (.+) = (.+)", line)
            if parts:
                var_name = parts.group(1).strip()
                value = self._evaluate_expression(parts.group(2).strip(), scope="global")
                self.globals[var_name] = value
            else:
                print(f"Syntax error defining global variable: {line}")
        elif line.startswith("set "):
            # Check for 'set var = LIBRARY:FUNCTION(args)' as a specific case first
            match_set_extension_call = re.match(r"set (.+) = ([a-zA-Z_][a-zA-Z0-9_]*):([a-zA-Z_][a-zA-Z0-9_]*)\((.*)\)", line)
            if match_set_extension_call:
                var_name = match_set_extension_call.group(1).strip()
                library_name = match_set_extension_call.group(2)
                function_name = match_set_extension_call.group(3)
                args_str = match_set_extension_call.group(4).strip()

                if self.debug:
                    print(f"DEBUG: SET Extension Call - Looking for '{library_name}'. Extensions: {list(self.extensions.keys())}")
                    if library_name not in self.extensions:
                        print(f"DEBUG: !!! CRITICAL: '{library_name}' is NOT in self.extensions here. This is the source of the error.")


                if library_name in self.extensions:
                    library_obj = self.extensions[library_name]
                    if hasattr(library_obj, function_name):
                        func = getattr(library_obj, function_name)
                        args = []
                        if args_str:
                            raw_args = [arg.strip() for arg in args_str.split(',')]
                            for arg_item in raw_args:
                                args.append(self._evaluate_expression(arg_item))
                        try:
                            result = func(*args)
                            self._assign_variable(var_name, result)
                        except Exception as e:
                            print(f"Error calling extension function {library_name}:{function_name} for assignment: {e}")
                    else:
                        print(f"Error: Function '{function_name}' not found in library '{library_name}' for assignment.")
                else:
                    print(f"Error: Extension library '{library_name}' not found for assignment.")
            else: # General 'set var = value'
                parts = re.match(r"set (.+) = (.+)", line)
                if parts:
                    var_name = parts.group(1).strip()
                    value = self._evaluate_expression(parts.group(2).strip())
                    self._assign_variable(var_name, value)
                else:
                    print(f"Syntax error setting variable: {line}")

        # STANDALONE EXTENSION FUNCTION CALLS (not assigned)
        elif re.match(r"([a-zA-Z_][a-zA-Z0-9_]*):([a-zA-Z_][a-zA-Z0-9_]*)\((.*)\)", line):
            self._evaluate_expression(line.strip())

        # FLOW CONTROL (only jump here; if statements handled in run())
        elif line.startswith("jump "):
            label = line[len("jump "):].strip()
            target_label_name = label[1:]
            if self.debug:
                print(f"DEBUG: jump - Looking for label '{target_label_name}'. self.labels: {self.labels}")
            if target_label_name in self.labels:
                # Set current_line_index directly. The calling context (run or _handle_if_statement)
                # will then pick up from this new index.
                self.current_line_index = self.labels[target_label_name] 
                if self.debug:
                    print(f"DEBUG: Jumped to line {self.current_line_index} (@{target_label_name})")
            else:
                print(f"Error: Label '{label}' not found for jump.")
                self.current_line_index = len(self.program_lines) # Effectively ends the program on error

        # EXTENSIONS
        elif line.startswith(".include "):
            file_to_include = line[len(".include "):].strip().replace('~', f'{home_dir}/lib')
            if (file_to_include.startswith('"') and file_to_include.endswith('"')) or \
               (file_to_include.startswith("'") and file_to_include.endswith("'")):
                file_to_include = file_to_include[1:-1]

            if file_to_include.endswith(".epp"):
                try:
                    # Use file_to_include directly, as the EL program provides the full path (e.g., "lib/stdio.epp")
                    full_path = file_to_include 
                    with open(full_path, 'r') as f:
                        epp_content_from_file = f.read()
                    
                    epp_globals = {}
                    exec(epp_content_from_file, epp_globals)

                    for name, obj in epp_globals.items():
                        if isinstance(obj, type) and name != '__builtins__':
                            self.extensions[name] = obj # Store the class object itself
                    if self.debug:
                        print(f"DEBUG: Included EPP file '{full_path}'. Loaded extensions: {list(self.extensions.keys())}")
                        if 'stdio' in self.extensions:
                            print(f"DEBUG: 'stdio' confirmed in self.extensions after include: {self.extensions['stdio']}")

                except FileNotFoundError:
                    print(f"Error: EPP file '{full_path}' not found. Make sure the path is correct.")
                except Exception as e:
                    print(f"Error executing EPP file '{full_path}': {e}")
            else:
                print(f"Error: Can only include .epp files. Found: {file_to_include}")
        else:
            if not line.startswith("]"): print(f"Unknown command or syntax error: {line}")

    def _handle_if_statement(self, start_line_index):
        """
        Parses the entire multi-line if/or/else statement structure,
        executes the first matching block, and returns the next line index
        for the main run loop to continue, or None on error.
        """
        parsed_branches = [] # List to store (condition_str, block_start_idx, block_end_exclusive_for_range)
        current_line_for_parsing = start_line_index

        # --- Phase 1: Parse all IF, OR, and ELSE branches ---
        while current_line_for_parsing < len(self.program_lines):
            line = self.program_lines[current_line_for_parsing].strip()

            condition_text = None
            
            # The 'if' must start at the beginning of the `if` construct
            if current_line_for_parsing == start_line_index:
                match = re.match(r"if \[(.+?)\] then \[", line)
            else: # 'or' and 'else' can follow
                match = re.match(r"or \[(.+?)\] then \[", line)
            
            if match:
                condition_text = match.group(1).strip()
            elif re.match(r"else \[", line): # 'else' without a condition
                condition_text = "ELSE"
            else:
                # If it's not an IF, OR, or ELSE continuation, we've parsed the entire structure.
                break 
            
            # Find the end of the *current branch's* block
            block_content_start = current_line_for_parsing + 1
            # _find_block_end returns the exclusive end index for the range
            block_end_exclusive, success = self._find_block_end(block_content_start) 
            if not success:
                print(f"Syntax error: Unclosed block for '{line}' starting near line {current_line_for_parsing}")
                return None
            
            # Store the range for block content (exclusive of the closing bracket line itself)
            parsed_branches.append((condition_text, block_content_start, block_end_exclusive))
            
            # Move parsing cursor to the line *after* the current block (its closing ']')
            current_line_for_parsing = block_end_exclusive

            # If it was an 'else' block, it's the end of the entire if-structure's parsing
            if condition_text == "ELSE":
                break
        
        # 'overall_if_end_index' now holds the index of the line immediately after the entire if-structure.
        overall_if_end_index = current_line_for_parsing

        # --- Phase 2: Execute the first matching branch ---
        # Store original index to detect if a jump happened *during* block execution
        original_current_line_index_at_entry = self.current_line_index 

        block_executed = False
        for cond_text, block_start_idx, block_end_exclusive in parsed_branches:
            if cond_text == "ELSE" or self._evaluate_condition(cond_text):
                if self.debug:
                    # Adjusted debug print for clarity
                    print(f"DEBUG: Executing branch (Condition: '{cond_text}') from line {block_start_idx} to {block_end_exclusive - 1}")
                
                # Execute lines within this block (from block_start_idx up to block_end_exclusive - 1)
                block_exec_idx = block_start_idx
                while block_exec_idx < (block_end_exclusive -1): # CORRECTED: Ensure ']' line is not executed
                    nested_line = self.program_lines[block_exec_idx].strip()

                    # Handle nested IF statements recursively
                    if nested_line.startswith("if "):
                        # Set interpreter's global index for nested call (important for label lookups inside nested if)
                        self.current_line_index = block_exec_idx 
                        
                        next_index_after_nested_if = self._handle_if_statement(block_exec_idx)
                        
                        if next_index_after_nested_if is None:
                            return None # Propagate error
                        
                        # Advance past the nested if-structure for the current block execution
                        block_exec_idx = next_index_after_nested_if 
                        
                        # If a jump happened inside the nested IF, it overrides the normal flow
                        # and we must return that new jump target immediately to the top-level `run`.
                        if self.current_line_index != original_current_line_index_at_entry:
                             if self.debug:
                                print(f"DEBUG: Jump detected inside nested IF. Returning new target: {self.current_line_index}")
                             return self.current_line_index
                    else:
                        # Execute other non-IF statements normally
                        self._execute_single_statement(nested_line)
                        
                        # If a jump occurred, it overrides the normal flow
                        if self.current_line_index != original_current_line_index_at_entry:
                            if self.debug:
                                print(f"DEBUG: Jump detected inside block. Returning new target: {self.current_line_index}")
                            return self.current_line_index
                        
                        block_exec_idx += 1 # Move to the next line in the current block

                block_executed = True
                break # Exit after executing the first matching block

        # --- Phase 3: Determine the next line for the main loop ---
        # If no jump occurred within any executed block, we should continue after the entire if-structure.
        return overall_if_end_index

    def _find_block_end(self, start_line_of_block_content):
        """
        Helper to find the matching ']' for a code block, handling nested brackets.
        `start_line_of_block_content` is the index of the first line *within* the block (after 'then [' etc.).
        Returns (exclusive_end_line_index, success_boolean).
        The returned index is the line *after* the line containing the closing bracket.
        """
        # We start with a balance of 1 because the current block started with an implicit '[' (from 'then [' etc.)
        bracket_balance = 1 
        
        for i in range(start_line_of_block_content, len(self.program_lines)):
            line = self.program_lines[i].strip()
            
            bracket_balance += line.count('[')
            bracket_balance -= line.count(']')
            
            if bracket_balance == 0:
                # Found the closing ']' for the block. Return the index of the line *after* it.
                return i + 1, True 
        
        # If loop finishes and balance is not 0, it means block was unclosed
        return -1, False 

    def _evaluate_expression(self, expr_str, scope=None):
        """
        Evaluates an expression string, which can be a literal, a variable,
        a function call from an extension, or a simple mathematical expression.

        Args:
            expr_str (str): The expression string to evaluate.
            scope (str, optional): Hints the current scope ('local' or 'global')
                                   for variable lookup. Defaults to None (checks both).

        Returns:
            The evaluated value (int, float, str, or result of function call).
        """
        # 1. Try to convert to int/float first (for numeric literals)
        try:
            return int(expr_str)
        except ValueError:
            try:
                return float(expr_str)
            except ValueError:
                # 2. Check for string literals (enclosed in quotes)
                if (expr_str.startswith('"') and expr_str.endswith('"')) or \
                   (expr_str.startswith("'") and expr_str.endswith("'")):
                    return expr_str[1:-1]

        # 3. Check for LIBRARY:FUNCTION() or LIBRARY:FUNCTION(args) pattern (Extension calls)
        match_extension_call = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*):([a-zA-Z_][a-zA-Z0-9_]*)\((.*)\)", expr_str)
        if match_extension_call:
            library_name = match_extension_call.group(1)
            function_name = match_extension_call.group(2)
            args_str = match_extension_call.group(3).strip()

            if library_name in self.extensions:
                library_obj = self.extensions[library_name]
                if hasattr(library_obj, function_name):
                    func = getattr(library_obj, function_name)

                    args = []
                    if args_str: # If there are arguments
                        # This split already supports multiple arguments separated by commas.
                        raw_args = [arg.strip() for arg in args_str.split(',')]
                        for arg_item in raw_args:
                            # Recursively evaluate each argument before passing to the function
                            args.append(self._evaluate_expression(arg_item)) 

                    try:
                        result = func(*args) # Call the Python function with unpacked arguments
                        if self.debug:
                            print(f"DEBUG: Extension call '{library_name}:{function_name}({args_str})' returned: {result}")
                        return result
                    except Exception as e:
                        print(f"Error calling extension function {library_name}:{function_name}: {e}")
                        return None # Return None on error, or raise a custom EL error
                else:
                    print(f"Error: Function '{function_name}' not found in library '{library_name}'.")
                    return None
            else:
                print(f"Error: Extension library '{library_name}' not found.")
                return None

        # 4. Finally, try to evaluate as a variable or a general Python expression
        if scope == "local" and expr_str in self.locals:
            return self.locals[expr_str]
        elif scope == "global" and expr_str in self.globals:
            return self.globals[expr_str]
        elif expr_str in self.locals: 
            return self.locals[expr_str]
        elif expr_str in self.globals:
            return self.globals[expr_str]
        else:
            try:
                # Attempt to evaluate as a general Python expression if it's not a variable or literal
                # Provide both globals and locals to eval's namespace
                combined_namespace = {**self.globals, **self.locals}
                return eval(expr_str, {}, combined_namespace)
            except (NameError, SyntaxError, TypeError) as e:
                # If evaluation fails, it might be an unrecognized variable name or invalid expression
                # Or it could be a string literal that wasn't quoted.
                # For now, return the string itself if it can't be evaluated.
                if self.debug:
                    print(f"DEBUG: Could not evaluate '{expr_str}' as number, string, variable or extension. Error: {e}")
                return expr_str

    def _evaluate_condition(self, condition_str):
        """
        Evaluates a conditional expression (e.g., "variable-x = 30").

        Args:
            condition_str (str): The condition string to evaluate.

        Returns:
            bool: True if the condition is met, False otherwise.
        """
        parts = condition_str.split(' ')

        if len(parts) == 3: # Format: operand1 operator operand2 (e.g., 'var = 30')
            var_name = parts[0]
            operator = parts[1]
            right_operand_str = parts[2]
            
            # Evaluate the right-hand side, which can be a literal, variable, or expression
            right_operand_value = self._evaluate_expression(right_operand_str)

            # Get the value of the left-hand side variable
            var_value = None
            if var_name in self.locals:
                var_value = self.locals[var_name]
            elif var_name in self.globals:
                var_value = self.globals[var_name]
            else:
                # If the variable is not defined, attempt to evaluate it as an expression.
                # This helps handle cases like `if ["hello" = "hello"]` or direct numbers.
                var_value = self._evaluate_expression(var_name)
                if var_value == var_name: # Still not found/evaluated as something else, so it's truly undefined as a var
                    print(f"Error: Variable or unrecognized expression '{var_name}' in condition.")
                    return False


            if self.debug:
                print(f"DEBUG: _evaluate_condition - comparing '{var_value}' (type: {type(var_value)}) {operator} '{right_operand_value}' (type: {type(right_operand_value)})")

            # Attempt type coercion for numerical comparisons if types are mixed
            try:
                if isinstance(var_value, (int, float)) and isinstance(right_operand_value, (int, float)):
                    # Both are numbers, direct comparison
                    pass
                elif (isinstance(var_value, str) and var_value.replace('.', '', 1).isdigit()) and isinstance(right_operand_value, (int, float)):
                    # Left is numeric string, right is number -> convert left to number
                    var_value = float(var_value) if '.' in var_value else int(var_value)
                elif isinstance(var_value, (int, float)) and (isinstance(right_operand_value, str) and right_operand_value.replace('.', '', 1).isdigit()):
                    # Left is number, right is numeric string -> convert right to number
                    right_operand_value = float(right_operand_value) if '.' in right_operand_value else int(right_operand_value)
                # If both are strings, or other types, compare directly without conversion attempt
            except ValueError:
                pass # Conversion failed, proceed with original types; comparison might still work or raise TypeError

            if operator == "=":
                return var_value == right_operand_value
            elif operator == "!=":
                return var_value != right_operand_value
            elif operator == ">":
                return var_value > right_operand_value
            elif operator == "<":
                return var_value < right_operand_value
            elif operator == ">=":
                return var_value >= right_operand_value
            elif operator == "<=":
                return var_value <= right_operand_value
            else:
                print(f"Unsupported operator '{operator}' in condition.")
                return False
        elif len(parts) == 1: # Format: single variable or expression (treated as boolean check)
            single_value = self._evaluate_expression(parts[0])
            return bool(single_value)
        else:
            print(f"Invalid condition format: {condition_str}")
            return False

    def _assign_variable(self, var_name, value):
        """
        Assigns a value to a variable, prioritizing local scope, then global.
        If the variable doesn't exist, it prints an error.
        """
        if var_name in self.locals:
            self.locals[var_name] = value
        elif var_name in self.globals:
            self.globals[var_name] = value
        else:
            print(f"Error: Variable '{var_name}' not defined. Cannot assign value: {value}.")

try:
    with open(args.file, 'r') as file:
        interpreter = ELInterpreter(debug=args.debug)
        interpreter.load_program(file.read())
        interpreter.run()
except Exception as e:
    print(f'Error: {e}')
