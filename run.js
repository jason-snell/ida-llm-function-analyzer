const express = require('express');

(async() => {
    const { default: fetch } = await import('node-fetch');
});

const app = express();

app.use(express.text());

const model = 'gemini-2.5-flash-preview-05-20';
const apiKey = '<your gemini api key>';

const systemInstructions = `You are an expert reverse engineer tasked with analyzing assembly or decompiled C++ pseudo-code to deduce its purpose, behavior, and interactions.

**Analysis Guidelines:**

1. **Function Purpose:**
   - Summarize the code's high-level purpose.
   - Identify the main algorithm or logic flow.
   - Note common patterns or known algorithms.

2. **Parameters:**
   - For each parameter:
     - Infer **data type** (e.g., \`int\`, \`char*\`, \`struct*\`).
     - Determine **usage** (Input/Output/InOut).
     - Suggest a descriptive **name** for generic parameters (e.g., \`a1\`).
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
   - Propose a descriptive "PlausibleFunctionName" (e.g., \`VerbNoun\`, \`GetProperty\`).
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
}`;

app.post('/analyze', async (req, res) => {
    console.log(req.body);

    if(!req.body) {
        res.send({
            success: false,
            error: 'bad post data'
        });

        return;
    }

    const postData = {
        "system_instruction": {
            "parts": [
                {
                    "text": systemInstructions
                }
            ]
        },
        "contents": [
            {
                "parts": [
                    {
                        "text": req.body
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.25,
            "thinkingConfig": {
                "thinkingBudget": 0
            },
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "object",
                "properties": {
                    "analyzed_function_address": {
                        "type": "string"
                    },
                    "suggested_function_name": {
                        "type": "string"
                    },
                    "confidence_in_name": {
                        "type": "string",
                        "enum": [
                            "high",
                            "medium",
                            "low"
                        ]
                    },
                    "signature_details": {
                        "type": "object",
                        "properties": {
                            "proposed_signature": {
                                "type": "string"
                            },
                            "return_type": {
                                "type": "string"
                            },
                            "return_value_meaning": {
                                "type": "string"
                            }
                        },
                        "required": [
                            "proposed_signature",
                            "return_type",
                            "return_value_meaning"
                        ]
                    },
                    "parameters": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "original_name": {
                                    "type": "string"
                                },
                                "suggested_name": {
                                    "type": "string"
                                },
                                "inferred_type": {
                                    "type": "string"
                                },
                                "usage": {
                                    "type": "string"
                                },
                                "description": {
                                    "type": "string"
                                }
                            },
                            "required": [
                                "original_name",
                                "suggested_name",
                                "inferred_type",
                                "usage",
                                "description"
                            ]
                        }
                    },
                    "called_functions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "address_or_current_name": {
                                    "type": "string"
                                },
                                "is_current_name_accurate": {
                                    "type": "string"
                                },
                                "suggested_name_if_inaccurate_or_generic": {
                                    "type": "string"
                                },
                                "inferred_purpose_in_context": {
                                    "type": "string"
                                }
                            },
                            "required": [
                                "address_or_current_name",
                                "is_current_name_accurate",
                                "suggested_name_if_inaccurate_or_generic",
                                "inferred_purpose_in_context"
                            ]
                        }
                    }
                },
                "required": [
                    "analyzed_function_address",
                    "suggested_function_name",
                    "confidence_in_name",
                    "signature_details"
                ]
            }
        }
    };

    try {
        const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`, {
            method: 'POST',
            headers: {
                'content-type': 'application/json'
            },
            body: JSON.stringify(postData),
            timeout: 120
        });
    
        const json = await response.json();
    
        if(!response || !response.ok || !json) {
            console.log(`api returned ${response.status}`);
    
            res.send({
                success: false,
                error: 'bad response from ai api'
            });
        }
    
        if(!json?.candidates || 
            json.candidates.length == 0 || 
            !json.candidates[0]?.content?.parts || 
            json.candidates[0]?.content.parts.length == 0 || 
            !json.candidates[0].content.parts[0]?.text) {
    
            res.send({
                success: false,
                error: 'bad response'
            });
    
            return;
        }
    
        res.send({
            success: true,
            data: JSON.parse(json.candidates[0].content.parts[0]?.text)
        });
    }
    catch (e) {
        console.log(e);
        res.send({
            success: false,
            error: 'unhandled exception'
        });
    }
});

app.listen(13337, '127.0.0.1');