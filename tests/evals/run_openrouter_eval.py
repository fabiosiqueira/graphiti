"""
Copyright 2024, Zep Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Compares extraction quality of candidate OpenRouter models against the fixed
baseline/judge model (see `eval_e2e_graph_building.default_judge_client`) on a
slice of the longmemeval dataset. Each candidate gets its own Neo4j group_id
suffix and result file so runs don't contaminate each other.

Requires OPENAI_API_KEY / OPENAI_BASE_URL pointed at OpenRouter (see .env) and
the benchmark Neo4j instance (graphiti-memory-neo4j-1, localhost:7687) running.

Usage: uv run python -m tests.evals.run_openrouter_eval
"""

import asyncio
import json
import re

from graphiti_core.llm_client import LLMConfig
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
from tests.evals.eval_e2e_graph_building import build_baseline_graph, eval_graph

MULTI_SESSION_COUNT = 3
SESSION_LENGTH = 5

CANDIDATE_MODELS = [
    'openai/gpt-4.1-nano',
    'google/gemini-2.5-flash-lite',
    'deepseek/deepseek-v4-flash',
]


def _slug_to_suffix(model: str) -> str:
    return 'candidate_' + re.sub(r'[^a-zA-Z0-9]+', '_', model).strip('_')


async def main() -> None:
    print(f'Building baseline graph ({MULTI_SESSION_COUNT} sessions x {SESSION_LENGTH} msgs)...')
    await build_baseline_graph(
        multi_session_count=MULTI_SESSION_COUNT, session_length=SESSION_LENGTH
    )

    scores: dict[str, float] = {}
    for model in CANDIDATE_MODELS:
        print(f'\n=== Evaluating {model} ===')
        # json_object for all candidates (not just DeepSeek): OpenRouter's json_schema
        # pass-through is inconsistent across the underlying providers it aggregates, and
        # using the same mode for every candidate keeps the comparison apples-to-apples.
        llm_client = OpenAIGenericClient(
            config=LLMConfig(model=model, small_model=model),
            structured_output_mode='json_object',
        )
        suffix = _slug_to_suffix(model)
        score = await eval_graph(
            multi_session_count=MULTI_SESSION_COUNT,
            session_length=SESSION_LENGTH,
            llm_client=llm_client,
            group_id_suffix=suffix,
            output_filename=f'{suffix}_graph_results.json',
        )
        scores[model] = score
        print(f'{model}: score={score:.3f}')

    print('\n=== Summary (higher is better, 1.0 = never worse than baseline) ===')
    for model, score in sorted(scores.items(), key=lambda kv: -kv[1]):
        print(f'{score:.3f}  {model}')

    with open('openrouter_eval_summary.json', 'w') as file:
        json.dump(scores, file, indent=2)


if __name__ == '__main__':
    asyncio.run(main())
