# econ-eval results

Tracks included: quantitative, coding.

## Overall

| model | score | 95% CI | total cost (USD) | cost/correct (USD) |
|---|---|---|---|---|
| claude-opus-4-8 | 1.000 | [1.000, 1.000] | 2.85 | 0.0570 |
| deepseek/deepseek-v4-flash-0731 | 1.000 | [1.000, 1.000] | 0.01 | 0.0002 |
| google/gemini-3.6-flash | 1.000 | [1.000, 1.000] | 0.34 | 0.0069 |
| moonshotai/kimi-k3 | 1.000 | [1.000, 1.000] | 0.35 | 0.0070 |
| openai/gpt-5.6-luna | 1.000 | [1.000, 1.000] | 0.01 | 0.0001 |
| x-ai/grok-4.5 | 1.000 | [1.000, 1.000] | 0.13 | 0.0025 |
| nvidia/nemotron-3-ultra-550b-a55b | 0.980 | [0.920, 1.000] | 0.11 | 0.0022 |
| meta-llama/llama-4-maverick | 0.960 | [0.860, 1.000] | 0.01 | 0.0001 |
| minimax/minimax-m3 | 0.960 | [0.880, 1.000] | 0.06 | 0.0012 |
| glm-5.2 | 0.900 | [0.700, 1.000] | 0.01 | 0.0001 |

## quantitative

| model | score | 95% CI |
|---|---|---|
| x-ai/grok-4.5 | 1.000 | [1.000, 1.000] |
| openai/gpt-5.6-luna | 1.000 | [1.000, 1.000] |
| moonshotai/kimi-k3 | 1.000 | [1.000, 1.000] |
| google/gemini-3.6-flash | 1.000 | [1.000, 1.000] |
| deepseek/deepseek-v4-flash-0731 | 1.000 | [1.000, 1.000] |
| claude-opus-4-8 | 1.000 | [1.000, 1.000] |
| nvidia/nemotron-3-ultra-550b-a55b | 0.960 | [0.840, 1.000] |
| minimax/minimax-m3 | 0.960 | [0.840, 1.000] |
| meta-llama/llama-4-maverick | 0.920 | [0.720, 1.000] |
| glm-5.2 | 0.800 | [0.400, 1.000] |

## coding

| model | score | 95% CI |
|---|---|---|
| x-ai/grok-4.5 | 1.000 | [1.000, 1.000] |
| openai/gpt-5.6-luna | 1.000 | [1.000, 1.000] |
| nvidia/nemotron-3-ultra-550b-a55b | 1.000 | [1.000, 1.000] |
| moonshotai/kimi-k3 | 1.000 | [1.000, 1.000] |
| meta-llama/llama-4-maverick | 1.000 | [1.000, 1.000] |
| google/gemini-3.6-flash | 1.000 | [1.000, 1.000] |
| glm-5.2 | 1.000 | [1.000, 1.000] |
| deepseek/deepseek-v4-flash-0731 | 1.000 | [1.000, 1.000] |
| claude-opus-4-8 | 1.000 | [1.000, 1.000] |
| minimax/minimax-m3 | 0.960 | [0.840, 1.000] |

## Paired vs opus

| model | win-rate vs opus | tasks | sign-test p | verdict |
|---|---|---|---|---|
| deepseek/deepseek-v4-flash-0731 | 0.50 | 10 | 1.0000 | no significant difference |
| google/gemini-3.6-flash | 0.50 | 10 | 1.0000 | no significant difference |
| moonshotai/kimi-k3 | 0.50 | 10 | 1.0000 | no significant difference |
| openai/gpt-5.6-luna | 0.50 | 10 | 1.0000 | no significant difference |
| x-ai/grok-4.5 | 0.50 | 10 | 1.0000 | no significant difference |
| nvidia/nemotron-3-ultra-550b-a55b | 0.00 | 10 | 1.0000 | no significant difference |
| meta-llama/llama-4-maverick | 0.00 | 10 | 1.0000 | no significant difference |
| minimax/minimax-m3 | 0.00 | 10 | 0.5000 | no significant difference |
| glm-5.2 | 0.00 | 10 | 1.0000 | no significant difference |
