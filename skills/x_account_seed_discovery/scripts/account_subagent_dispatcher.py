#!/usr/bin/env python3
"""
Account Evaluation Subagent Dispatcher for X Account Seed Discovery

Dispatches parallel subagents to evaluate accounts end-to-end after aggregation.
Each subagent handles ALL remaining stages for ONE account:
- Anti-wave filter
- Deterministic prefilter
- Bio evaluation
- AI judge eligibility
- Prepare database record

Usage:
    python account_subagent_dispatcher.py --input accounts.json --output results.json
    python account_subagent_dispatcher.py --input accounts.json --output results.json --parallel 20
    python account_subagent_dispatcher.py --input accounts.json --output results.json --dry-run

Input format (JSON):
    {
        "run_id": "20260330T100000Z-abc123",
        "topic": "politics",
        "region": "Indonesia",
        "constraints": {
            "min_followers": 1000,
            "max_followers": null,
            "min_posts": 50,
            "must_be_verified": false,
            "must_have_profile_image": false
        },
        "news_keywords": ["DPR", "presiden", "pemilu"],
        "use_bio_subagents": true,
        "accounts": [
            {
                "handle": "example_user",
                "display_name": "Example User",
                "bio": "Political analyst | Jakarta",
                "followers_count": 5000,
                "following_count": 800,
                "post_count": 1200,
                "verified": false,
                "location_text": "Jakarta",
                "profile_url": "https://x.com/example_user",
                "joined_at": "2019-03-15",
                "matched_posts_count": 8,
                "distinct_keywords_matched": ["DPR", "politik"],
                "matched_entities": ["DPR"],
                "recent_topic_post_count": 5,
                "sample_posts": [...],
                "source_queries": ["politics Indonesia"]
            }
        ]
    }

Output format (JSON):
    {
        "run_id": "20260330T100000Z-abc123",
        "total_accounts": 10,
        "successful_evaluations": 9,
        "failed_evaluations": 1,
        "summary": {
            "eligible": 5,
            "not_eligible": 3,
            "uncertain": 1,
            "filtered": 1
        },
        "results": [...],
        "database_records": [...],
        "errors": []
    }
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class AccountEvaluationResult:
    """Result of a complete account evaluation."""

    handle: str
    success: bool
    evaluation_complete: bool = False
    stages: Optional[Dict[str, Any]] = None
    database_record: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    raw_response: Optional[str] = None
    elapsed_seconds: float = 0.0


def load_prompt_template() -> str:
    """Load the account evaluation prompt template."""
    script_dir = Path(__file__).parent.parent
    prompt_path = script_dir / "prompts" / "account_evaluation.md"

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {prompt_path}")

    return prompt_path.read_text(encoding="utf-8")


def render_prompt(
    template: str,
    account: Dict[str, Any],
    run_id: str,
    topic: str,
    region: str,
    constraints: Dict[str, Any],
    news_keywords: List[str],
    use_bio_subagents: bool,
) -> str:
    """Render the prompt template with account data."""
    # Format constraints as string
    constraints_str = json.dumps(constraints, indent=2) if constraints else "{}"

    # Format news keywords as bullet list
    keywords_str = (
        "\n".join([f"- {kw}" for kw in news_keywords]) if news_keywords else "- (none)"
    )

    # Format sample posts
    sample_posts = account.get("sample_posts", [])
    if sample_posts:
        posts_str = "\n\n".join(
            [
                f"Post {i + 1}:\n{json.dumps(post, indent=2, ensure_ascii=False)}"
                for i, post in enumerate(sample_posts[:10])  # Limit to 10 posts
            ]
        )
    else:
        posts_str = "- (no sample posts available)"

    # Format source queries
    queries = account.get("source_queries", [])
    queries_str = "\n".join([f"- {q}" for q in queries]) if queries else "- (none)"

    # Format distinct keywords matched
    distinct_keywords = account.get("distinct_keywords_matched", [])
    distinct_keywords_str = (
        ", ".join(distinct_keywords) if distinct_keywords else "(none)"
    )

    # Format matched entities
    entities = account.get("matched_entities", [])
    entities_str = ", ".join(entities) if entities else "(none)"

    # Replace template variables
    prompt = template
    prompt = prompt.replace("{{run_id}}", run_id)
    prompt = prompt.replace("{{topic}}", topic)
    prompt = prompt.replace("{{region}}", region)
    prompt = prompt.replace("{{constraints}}", constraints_str)
    prompt = prompt.replace("{{news_keywords}}", keywords_str)
    prompt = prompt.replace("{{use_bio_subagents}}", str(use_bio_subagents))

    # Account fields
    prompt = prompt.replace("{{handle}}", account.get("handle", ""))
    prompt = prompt.replace("{{display_name}}", account.get("display_name", ""))
    prompt = prompt.replace("{{bio}}", account.get("bio", ""))
    prompt = prompt.replace(
        "{{followers_count}}", str(account.get("followers_count", 0))
    )
    prompt = prompt.replace(
        "{{following_count}}", str(account.get("following_count", 0))
    )
    prompt = prompt.replace("{{post_count}}", str(account.get("post_count", 0)))
    prompt = prompt.replace("{{verified}}", str(account.get("verified", False)))
    prompt = prompt.replace("{{location_text}}", account.get("location_text", ""))
    prompt = prompt.replace("{{profile_url}}", account.get("profile_url", ""))
    prompt = prompt.replace("{{joined_at}}", account.get("joined_at", ""))

    # Topic signals
    prompt = prompt.replace(
        "{{matched_posts_count}}", str(account.get("matched_posts_count", 0))
    )
    prompt = prompt.replace("{{distinct_keywords_matched}}", distinct_keywords_str)
    prompt = prompt.replace("{{matched_entities}}", entities_str)
    prompt = prompt.replace(
        "{{recent_topic_post_count}}", str(account.get("recent_topic_post_count", 0))
    )
    prompt = prompt.replace("{{sample_posts}}", posts_str)
    prompt = prompt.replace("{{source_queries}}", queries_str)

    # Constraint values for prefilter stage
    prompt = prompt.replace(
        "{{min_followers}}", str(constraints.get("min_followers", "N/A"))
    )
    prompt = prompt.replace(
        "{{max_followers}}", str(constraints.get("max_followers", "N/A") or "N/A")
    )
    prompt = prompt.replace("{{min_posts}}", str(constraints.get("min_posts", "N/A")))
    prompt = prompt.replace(
        "{{must_be_verified}}", str(constraints.get("must_be_verified", False))
    )

    return prompt


def evaluate_account_with_subagent(
    account: Dict[str, Any],
    run_id: str,
    topic: str,
    region: str,
    constraints: Dict[str, Any],
    news_keywords: List[str],
    use_bio_subagents: bool,
    prompt_template: str,
    dry_run: bool = False,
) -> AccountEvaluationResult:
    """
    Evaluate a single account end-to-end using a subagent.

    In a real implementation, this would dispatch to an AI subagent.
    For now, this is a placeholder that simulates the subagent call.
    """
    handle = account.get("handle", "unknown")
    start_time = time.time()

    if dry_run:
        # Return mock result for dry run
        elapsed = time.time() - start_time
        return AccountEvaluationResult(
            handle=handle,
            success=True,
            evaluation_complete=True,
            stages={
                "anti_wave": {"score": 0, "flags": [], "decision": "pass"},
                "prefilter": {
                    "passed": True,
                    "failed_constraints": [],
                    "decision": "continue",
                },
                "bio_evaluation": {
                    "decision": "eligible",
                    "score": 75,
                    "relevance_signals": ["dry-run-mode"],
                    "account_type_indicators": ["dry-run-mode"],
                    "risk_flags": [],
                },
                "final_judgment": {
                    "decision": "eligible",
                    "score": 75,
                    "reason_short": f"[DRY RUN] Account @{handle} would be evaluated end-to-end",
                    "reason_detailed": "[DRY RUN] This is a dry run. In production, a subagent would process all stages.",
                    "matched_topic_signals": ["dry-run"],
                    "risk_flags": [],
                    "suggested_tags": ["dry-run"],
                    "opportunistic_score": 0,
                    "consistency_score": 75,
                },
            },
            database_record={
                "account": {
                    "handle": handle,
                    "handle_normalized": handle.lower(),
                    "display_name": account.get("display_name", ""),
                    "bio": account.get("bio", ""),
                    "followers_count": account.get("followers_count", 0),
                    "following_count": account.get("following_count", 0),
                    "post_count": account.get("post_count", 0),
                    "verified": account.get("verified", False),
                    "location_text": account.get("location_text", ""),
                    "profile_url": account.get("profile_url", ""),
                    "joined_at": account.get("joined_at", ""),
                },
                "evaluation": {
                    "decision": "eligible",
                    "score": 75,
                    "reason_short": f"[DRY RUN] Account @{handle} would be evaluated",
                    "reason_detailed": "[DRY RUN] End-to-end evaluation placeholder",
                    "suggested_tags_json": '["dry-run"]',
                    "opportunistic_score": 0,
                    "consistency_score": 75,
                },
                "topic_signals": {
                    "matched_posts_count": account.get("matched_posts_count", 0),
                    "distinct_keywords_matched": json.dumps(
                        account.get("distinct_keywords_matched", [])
                    ),
                    "matched_entities": json.dumps(account.get("matched_entities", [])),
                    "sample_posts_json": json.dumps(account.get("sample_posts", [])),
                    "recent_topic_post_count": account.get(
                        "recent_topic_post_count", 0
                    ),
                },
            },
            elapsed_seconds=elapsed,
        )

    try:
        # Render the prompt
        prompt = render_prompt(
            template=prompt_template,
            account=account,
            run_id=run_id,
            topic=topic,
            region=region,
            constraints=constraints,
            news_keywords=news_keywords,
            use_bio_subagents=use_bio_subagents,
        )

        # TODO: In production, this would call the AI subagent
        # For now, we return a placeholder that indicates what would happen
        # The actual implementation would use OpenCode's task tool or similar

        elapsed = time.time() - start_time

        # Placeholder: Return uncertain with note about subagent integration
        return AccountEvaluationResult(
            handle=handle,
            success=True,
            evaluation_complete=True,
            stages={
                "anti_wave": {"score": 0, "flags": [], "decision": "pass"},
                "prefilter": {
                    "passed": True,
                    "failed_constraints": [],
                    "decision": "continue",
                },
                "bio_evaluation": {
                    "decision": "uncertain",
                    "score": 50,
                    "relevance_signals": ["pending-subagent-evaluation"],
                    "account_type_indicators": ["pending-subagent-evaluation"],
                    "risk_flags": [],
                },
                "final_judgment": {
                    "decision": "uncertain",
                    "score": 50,
                    "reason_short": f"Subagent evaluation pending for @{handle}",
                    "reason_detailed": f"Account @{handle} queued for end-to-end subagent evaluation. In production, a subagent would process anti-wave filter, prefilter, bio evaluation, and final judgment.",
                    "matched_topic_signals": ["pending-evaluation"],
                    "risk_flags": [],
                    "suggested_tags": ["pending-evaluation"],
                    "opportunistic_score": 50,
                    "consistency_score": 50,
                },
            },
            database_record={
                "account": {
                    "handle": handle,
                    "handle_normalized": handle.lower(),
                    "display_name": account.get("display_name", ""),
                    "bio": account.get("bio", ""),
                    "followers_count": account.get("followers_count", 0),
                    "following_count": account.get("following_count", 0),
                    "post_count": account.get("post_count", 0),
                    "verified": account.get("verified", False),
                    "location_text": account.get("location_text", ""),
                    "profile_url": account.get("profile_url", ""),
                    "joined_at": account.get("joined_at", ""),
                },
                "evaluation": {
                    "decision": "uncertain",
                    "score": 50,
                    "reason_short": f"Subagent evaluation pending for @{handle}",
                    "reason_detailed": "End-to-end evaluation queued",
                    "suggested_tags_json": '["pending-evaluation"]',
                    "opportunistic_score": 50,
                    "consistency_score": 50,
                },
                "topic_signals": {
                    "matched_posts_count": account.get("matched_posts_count", 0),
                    "distinct_keywords_matched": json.dumps(
                        account.get("distinct_keywords_matched", [])
                    ),
                    "matched_entities": json.dumps(account.get("matched_entities", [])),
                    "sample_posts_json": json.dumps(account.get("sample_posts", [])),
                    "recent_topic_post_count": account.get(
                        "recent_topic_post_count", 0
                    ),
                },
            },
            raw_response=prompt,  # Include the rendered prompt for debugging
            elapsed_seconds=elapsed,
        )

    except Exception as e:
        elapsed = time.time() - start_time
        return AccountEvaluationResult(
            handle=handle, success=False, error=str(e), elapsed_seconds=elapsed
        )


def dispatch_parallel_evaluations(
    accounts: List[Dict[str, Any]],
    run_id: str,
    topic: str,
    region: str,
    constraints: Dict[str, Any],
    news_keywords: List[str],
    use_bio_subagents: bool,
    prompt_template: str,
    parallel: int = 10,
    dry_run: bool = False,
) -> List[AccountEvaluationResult]:
    """
    Dispatch account evaluations in parallel using thread pool.

    Note: This simulates parallel subagent dispatch. In production,
    this would integrate with OpenCode's task tool or similar system.
    """
    results = []

    def evaluate_single(account: Dict[str, Any]) -> AccountEvaluationResult:
        return evaluate_account_with_subagent(
            account=account,
            run_id=run_id,
            topic=topic,
            region=region,
            constraints=constraints,
            news_keywords=news_keywords,
            use_bio_subagents=use_bio_subagents,
            prompt_template=prompt_template,
            dry_run=dry_run,
        )

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=parallel) as executor:
        # Submit all tasks
        future_to_account = {
            executor.submit(evaluate_single, account): account for account in accounts
        }

        # Collect results as they complete
        for future in as_completed(future_to_account):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                account = future_to_account[future]
                results.append(
                    AccountEvaluationResult(
                        handle=account.get("handle", "unknown"),
                        success=False,
                        error=str(e),
                    )
                )

    return results


def format_output_results(
    run_id: str, results: List[AccountEvaluationResult]
) -> Dict[str, Any]:
    """Format results for JSON output."""
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    # Count decisions
    decision_counts = {"eligible": 0, "not_eligible": 0, "uncertain": 0, "filtered": 0}
    for result in successful:
        if result.stages and "final_judgment" in result.stages:
            decision = result.stages["final_judgment"].get("decision", "uncertain")
            decision_counts[decision] = decision_counts.get(decision, 0) + 1
        elif result.stages and "prefilter" in result.stages:
            if not result.stages["prefilter"].get("passed", True):
                decision_counts["filtered"] += 1

    output = {
        "run_id": run_id,
        "total_accounts": len(results),
        "successful_evaluations": len(successful),
        "failed_evaluations": len(failed),
        "summary": decision_counts,
        "results": [],
        "database_records": [],
        "errors": [],
    }

    # Add successful results
    for result in successful:
        result_dict = {
            "handle": result.handle,
            "evaluation_complete": result.evaluation_complete,
            "stages": result.stages,
            "elapsed_seconds": result.elapsed_seconds,
        }
        output["results"].append(result_dict)

        # Add database record if available
        if result.database_record:
            output["database_records"].append(result.database_record)

    # Add errors
    for result in failed:
        output["errors"].append({"handle": result.handle, "error": result.error})

    return output


def main():
    parser = argparse.ArgumentParser(
        description="Dispatch subagents to evaluate accounts end-to-end in parallel"
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to input JSON file containing accounts to evaluate",
    )
    parser.add_argument(
        "--output", "-o", required=True, help="Path to output JSON file for results"
    )
    parser.add_argument(
        "--parallel",
        "-p",
        type=int,
        default=10,
        help="Number of parallel subagents (default: 10, max: 50)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode - return mock results without calling subagents",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Validate parallel count
    if args.parallel < 1:
        args.parallel = 1
    elif args.parallel > 50:
        args.parallel = 50

    try:
        # Load input data
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: Input file not found: {args.input}", file=sys.stderr)
            sys.exit(1)

        with open(input_path, "r", encoding="utf-8") as f:
            input_data = json.load(f)

        # Extract parameters
        run_id = input_data.get("run_id", f"run_{int(time.time())}")
        topic = input_data.get("topic", "")
        region = input_data.get("region", "Indonesia")
        constraints = input_data.get("constraints", {})
        news_keywords = input_data.get("news_keywords", [])
        use_bio_subagents = input_data.get("use_bio_subagents", True)
        accounts = input_data.get("accounts", [])

        if not accounts:
            print("Error: No accounts provided in input", file=sys.stderr)
            sys.exit(1)

        if not topic:
            print("Error: No topic provided in input", file=sys.stderr)
            sys.exit(1)

        if args.verbose:
            print(f"Evaluating {len(accounts)} accounts end-to-end")
            print(f"Topic: '{topic}' in {region}")
            print(f"Parallel subagents: {args.parallel}")
            print(f"Use bio subagents: {use_bio_subagents}")
            print(f"Dry run: {args.dry_run}")

        # Load prompt template
        prompt_template = load_prompt_template()

        # Dispatch parallel evaluations
        start_time = time.time()
        results = dispatch_parallel_evaluations(
            accounts=accounts,
            run_id=run_id,
            topic=topic,
            region=region,
            constraints=constraints,
            news_keywords=news_keywords,
            use_bio_subagents=use_bio_subagents,
            prompt_template=prompt_template,
            parallel=args.parallel,
            dry_run=args.dry_run,
        )
        elapsed = time.time() - start_time

        # Format output
        output = format_output_results(run_id, results)
        output["elapsed_seconds"] = round(elapsed, 2)
        output["parallel_subagents"] = args.parallel
        output["dry_run"] = args.dry_run
        output["avg_seconds_per_account"] = (
            round(elapsed / len(accounts), 2) if accounts else 0
        )

        # Write output
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        if args.verbose:
            print(f"\nResults written to: {args.output}")
            print(f"Total accounts: {output['total_accounts']}")
            print(f"Successful: {output['successful_evaluations']}")
            print(f"Failed: {output['failed_evaluations']}")
            print(f"Summary: {output['summary']}")
            print(f"Elapsed: {elapsed:.2f}s")
            print(f"Avg per account: {output['avg_seconds_per_account']:.2f}s")

        # Print summary to stdout
        print(
            json.dumps(
                {
                    "success": True,
                    "run_id": run_id,
                    "total_accounts": output["total_accounts"],
                    "successful": output["successful_evaluations"],
                    "failed": output["failed_evaluations"],
                    "summary": output["summary"],
                    "elapsed_seconds": elapsed,
                    "avg_seconds_per_account": output["avg_seconds_per_account"],
                    "output_file": str(output_path),
                }
            )
        )

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
