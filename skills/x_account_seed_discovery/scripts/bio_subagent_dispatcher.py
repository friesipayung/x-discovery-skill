#!/usr/bin/env python3
"""
Bio Subagent Dispatcher for X Account Seed Discovery

Dispatches parallel subagents to evaluate X account bios for eligibility.
Each subagent evaluates one account based on bio/profile metadata only.

Usage:
    python bio_subagent_dispatcher.py --input accounts.json --output results.json
    python bio_subagent_dispatcher.py --input accounts.json --output results.json --parallel 10
    python bio_subagent_dispatcher.py --input accounts.json --output results.json --dry-run

Input format (JSON):
    {
        "topic": "politics",
        "region": "Indonesia",
        "constraints": {"min_followers": 1000},
        "news_keywords": ["DPR", "presiden", "pemilu"],
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
                "anti_wave_flags": []
            }
        ]
    }

Output format (JSON):
    {
        "total_accounts": 10,
        "successful_evaluations": 10,
        "failed_evaluations": 0,
        "results": [
            {
                "handle": "example_user",
                "decision": "eligible",
                "score": 82,
                "reason_short": "Individual political analyst with clear topical focus in bio.",
                ...
            }
        ],
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
from dataclasses import dataclass


@dataclass
class BioEvaluationResult:
    """Result of a single bio evaluation."""

    handle: str
    success: bool
    decision: Optional[str] = None
    score: Optional[int] = None
    reason_short: Optional[str] = None
    reason_detailed: Optional[str] = None
    bio_relevance_signals: Optional[List[str]] = None
    account_type_indicators: Optional[List[str]] = None
    risk_flags: Optional[List[str]] = None
    suggested_tags: Optional[List[str]] = None
    error: Optional[str] = None
    raw_response: Optional[str] = None


def load_prompt_template() -> str:
    """Load the bio judge prompt template."""
    script_dir = Path(__file__).parent.parent
    prompt_path = script_dir / "prompts" / "bio_judge.md"

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {prompt_path}")

    return prompt_path.read_text(encoding="utf-8")


def render_prompt(
    template: str,
    account: Dict[str, Any],
    topic: str,
    region: str,
    constraints: Dict[str, Any],
    news_keywords: List[str],
) -> str:
    """Render the prompt template with account data."""
    # Format constraints as string
    constraints_str = json.dumps(constraints, indent=2) if constraints else "{}"

    # Format news keywords as bullet list
    keywords_str = (
        "\n".join([f"- {kw}" for kw in news_keywords]) if news_keywords else "- (none)"
    )

    # Format anti-wave flags
    flags = account.get("anti_wave_flags", [])
    flags_str = "\n".join([f"- {f}" for f in flags]) if flags else "- (none)"

    # Replace template variables
    prompt = template
    prompt = prompt.replace("{{topic}}", topic)
    prompt = prompt.replace("{{region}}", region)
    prompt = prompt.replace("{{constraints}}", constraints_str)
    prompt = prompt.replace("{{news_keywords}}", keywords_str)
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
    prompt = prompt.replace("{{anti_wave_flags}}", flags_str)

    return prompt


def evaluate_bio_with_subagent(
    account: Dict[str, Any],
    topic: str,
    region: str,
    constraints: Dict[str, Any],
    news_keywords: List[str],
    prompt_template: str,
    dry_run: bool = False,
) -> BioEvaluationResult:
    """
    Evaluate a single account's bio using a subagent.

    In a real implementation, this would dispatch to an AI subagent.
    For now, this is a placeholder that simulates the subagent call.
    """
    handle = account.get("handle", "unknown")

    if dry_run:
        # Return mock result for dry run
        return BioEvaluationResult(
            handle=handle,
            success=True,
            decision="eligible",
            score=75,
            reason_short=f"[DRY RUN] Would evaluate bio for @{handle}",
            reason_detailed="[DRY RUN] This is a dry run. In production, a subagent would evaluate this bio.",
            bio_relevance_signals=["dry-run-mode"],
            account_type_indicators=["dry-run-mode"],
            risk_flags=[],
            suggested_tags=["dry-run"],
        )

    try:
        # Render the prompt
        prompt = render_prompt(
            template=prompt_template,
            account=account,
            topic=topic,
            region=region,
            constraints=constraints,
            news_keywords=news_keywords,
        )

        # TODO: In production, this would call the AI subagent
        # For now, we return a placeholder that indicates what would happen
        # The actual implementation would use OpenCode's task tool or similar

        # Placeholder: Return uncertain with note about subagent integration
        return BioEvaluationResult(
            handle=handle,
            success=True,
            decision="uncertain",
            score=50,
            reason_short=f"Subagent evaluation pending for @{handle}",
            reason_detailed=(
                f"Account @{handle} queued for subagent bio evaluation. "
                f"Bio: '{account.get('bio', 'N/A')}'. "
                f"In production, an AI subagent would analyze this bio for {topic} relevance."
            ),
            bio_relevance_signals=["pending-subagent-evaluation"],
            account_type_indicators=["pending-subagent-evaluation"],
            risk_flags=[],
            suggested_tags=["pending-evaluation"],
            raw_response=prompt,  # Include the rendered prompt for debugging
        )

    except Exception as e:
        return BioEvaluationResult(handle=handle, success=False, error=str(e))


def dispatch_parallel_evaluations(
    accounts: List[Dict[str, Any]],
    topic: str,
    region: str,
    constraints: Dict[str, Any],
    news_keywords: List[str],
    prompt_template: str,
    parallel: int = 5,
    dry_run: bool = False,
) -> List[BioEvaluationResult]:
    """
    Dispatch bio evaluations in parallel using thread pool.

    Note: This simulates parallel subagent dispatch. In production,
    this would integrate with OpenCode's task tool or similar system.
    """
    results = []

    def evaluate_single(account: Dict[str, Any]) -> BioEvaluationResult:
        return evaluate_bio_with_subagent(
            account=account,
            topic=topic,
            region=region,
            constraints=constraints,
            news_keywords=news_keywords,
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
                    BioEvaluationResult(
                        handle=account.get("handle", "unknown"),
                        success=False,
                        error=str(e),
                    )
                )

    return results


def format_output_results(results: List[BioEvaluationResult]) -> Dict[str, Any]:
    """Format results for JSON output."""
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    output = {
        "total_accounts": len(results),
        "successful_evaluations": len(successful),
        "failed_evaluations": len(failed),
        "results": [],
        "errors": [],
    }

    # Add successful results
    for result in successful:
        result_dict = {
            "handle": result.handle,
            "decision": result.decision,
            "score": result.score,
            "reason_short": result.reason_short,
            "reason_detailed": result.reason_detailed,
            "bio_relevance_signals": result.bio_relevance_signals or [],
            "account_type_indicators": result.account_type_indicators or [],
            "risk_flags": result.risk_flags or [],
            "suggested_tags": result.suggested_tags or [],
        }
        output["results"].append(result_dict)

    # Add errors
    for result in failed:
        output["errors"].append({"handle": result.handle, "error": result.error})

    return output


def main():
    parser = argparse.ArgumentParser(
        description="Dispatch subagents to evaluate X account bios in parallel"
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
        default=5,
        help="Number of parallel subagents (default: 5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode - return mock results without calling subagents",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    try:
        # Load input data
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: Input file not found: {args.input}", file=sys.stderr)
            sys.exit(1)

        with open(input_path, "r", encoding="utf-8") as f:
            input_data = json.load(f)

        # Extract parameters
        topic = input_data.get("topic", "")
        region = input_data.get("region", "Indonesia")
        constraints = input_data.get("constraints", {})
        news_keywords = input_data.get("news_keywords", [])
        accounts = input_data.get("accounts", [])

        if not accounts:
            print("Error: No accounts provided in input", file=sys.stderr)
            sys.exit(1)

        if not topic:
            print("Error: No topic provided in input", file=sys.stderr)
            sys.exit(1)

        if args.verbose:
            print(
                f"Evaluating {len(accounts)} accounts for topic '{topic}' in {region}"
            )
            print(f"Parallel subagents: {args.parallel}")
            print(f"Dry run: {args.dry_run}")

        # Load prompt template
        prompt_template = load_prompt_template()

        # Dispatch parallel evaluations
        start_time = time.time()
        results = dispatch_parallel_evaluations(
            accounts=accounts,
            topic=topic,
            region=region,
            constraints=constraints,
            news_keywords=news_keywords,
            prompt_template=prompt_template,
            parallel=args.parallel,
            dry_run=args.dry_run,
        )
        elapsed = time.time() - start_time

        # Format output
        output = format_output_results(results)
        output["elapsed_seconds"] = round(elapsed, 2)
        output["parallel_subagents"] = args.parallel
        output["dry_run"] = args.dry_run

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
            print(f"Elapsed: {elapsed:.2f}s")

        # Print summary to stdout
        print(
            json.dumps(
                {
                    "success": True,
                    "total_accounts": output["total_accounts"],
                    "successful": output["successful_evaluations"],
                    "failed": output["failed_evaluations"],
                    "elapsed_seconds": elapsed,
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
