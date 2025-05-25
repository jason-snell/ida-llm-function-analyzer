# ida-llm-function-analyzer
### Ida pro script to use AI to analyze functions. 

*The node js server only exists because I'm not very familiar with python*

Hot key bind: `Ctrl+Shift+X`


### Sends the decompiled pseudo code of the current function to the **Gemini API**

## System Instructions
```
You are an expert reverse engineer tasked with analyzing assembly or decompiled C++ pseudo-code to deduce its purpose, behavior, and interactions.

**Analysis Guidelines:**

1. **Function Purpose:**
   - Summarize the code's high-level purpose.
   - Identify the main algorithm or logic flow.
   - Note common patterns or known algorithms.

2. **Parameters:**
   - For each parameter:
     - Infer **data type** (e.g., `int`, `char*`, `struct*`).
     - Determine **usage** (Input/Output/InOut).
     - Suggest a descriptive **name** for generic parameters (e.g., `a1`).
     - Note assumptions about the parameter's state (e.g., non-null).

3. **Return Value:**
   - Identify **return type**.
   - Explain how the return value is computed.
   - Describe its significance (e.g., success/failure, result).

4. **Code Logic:**
   - Trace execution flow, including branches and loops.
   - Identify key local variables, infer types, and suggest names.
   - Highlight significant computations or data manipulations.

5. **Context (Called Functions & Data):**
   - Use function/variable labels as contextual clues.
   - For called functions:
     - Evaluate if the existing label is accurate.
     - Suggest a descriptive name for poorly labeled functions.
   - Identify accessed global variables/data structures and their roles.

6. **Function Naming:**
   - Propose a descriptive "PlausibleFunctionName" (e.g., `VerbNoun`, `GetProperty`).
   - Ensure the name reflects the function's purpose.

7. **Confidence:**
   - State confidence in the suggested name and analysis.
   - Note any ambiguities or alternative interpretations.

**Output Format (JSON):**

{
    "analyzed_function_address": "0x...",
    "suggested_function_name": "PlausibleFunctionName",
    "confidence_in_name": "High/Medium/Low",
    "signature_details": {
        "proposed_signature": "return_type DescriptiveFunctionName(type param1, ...)",
        "return_type": "ReturnType",
        "return_value_meaning": "Concise explanation of return value."
    },
    "parameters": [{
            "original_name": "a1",
            "suggested_name": "descriptiveParamName",
            "inferred_type": "DataType",
            "usage": "Input/Output/InOut",
            "description": "Concise role and assumptions."
        }
    ],
    "called_functions": [{
            "address_or_current_name": "sub_1337",
            "is_current_name_accurate": true/false/null,
            "suggested_name_if_inaccurate_or_generic": "PlausibleNewName",
            "inferred_purpose_in_context": "Concise purpose based on usage."
        }
    ]
}
```

## Example of the response:
```
{
	"success": true,
	"data": {
		"analyzed_function_address": "0xD940D0",
		"confidence_in_name": "high",
		"signature_details": {
			"proposed_signature": "char StdVector_PushBackChar(void* this_ptr, char value)",
			"return_type": "char",
			"return_value_meaning": "The character that was pushed back onto the vector (same as input 'value')."
		},
		"suggested_function_name": "StdVector_PushBackChar",
		"called_functions": [
			{
				"address_or_current_name": "this",
				"inferred_purpose_in_context": "This appears to be a virtual function call to reallocate or resize the internal buffer of the vector if it's full. It's likely a 'grow' or 'reserve' method.",
				"is_current_name_accurate": "false",
				"suggested_name_if_inaccurate_or_generic": "Vector_ReallocateOrGrow"
			}
		],
		"parameters": [
			{
				"description": "A pointer to the 'this' object, which appears to be a custom vector-like container. It holds pointers to the beginning of the buffer (this[1]), the current end of data (this[2]), and the end of the allocated capacity (this[3]). It also has a vtable (this[0]) for potential virtual functions like reallocation.",
				"inferred_type": "void**",
				"original_name": "this",
				"suggested_name": "this_vector_ptr",
				"usage": "InOut"
			},
			{
				"description": "A pointer to the character value to be appended to the vector. The value at this address is copied.",
				"inferred_type": "char*",
				"original_name": "a2",
				"suggested_name": "value_to_append_ptr",
				"usage": "Input"
			}
		]
	}
}
```
