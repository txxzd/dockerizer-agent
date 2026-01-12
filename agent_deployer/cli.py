import argparse
import sys
from pathlib import Path

from agent_deployer.analyzer import ProjectAnalyzer
from agent_deployer.agent import DockerfileAgent
from agent_deployer.builder import DockerBuilder


def cmd_analyze(args: argparse.Namespace) -> int:
    try:
        analyzer = ProjectAnalyzer(args.project_path)
        context = analyzer.analyze()

        print(f"Project: {context.root_path}")
        print(f"Total files: {context.total_files}")
        print("\nFile extensions:")
        for ext, count in sorted(context.extensions.items(), key=lambda x: -x[1])[:10]:
            print(f"  {ext}: {count}")

        print("\nConfiguration files found:")
        for filename in context.config_files.keys():
            print(f"  {filename}")

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_generate(args: argparse.Namespace) -> int:
    try:
        print("Starting Dockerfile agent...")
        agent = DockerfileAgent()
        result = agent.run(args.project_path)
        print(f"\nDockerfile generated: {result}")
        return 0
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_build(args: argparse.Namespace) -> int:
    quiet = getattr(args, "quiet", False)

    def log(msg: str):
        if not quiet:
            print(msg)

    try:
        dockerfile_path = Path(args.project_path) / "Dockerfile"

        if not dockerfile_path.exists() or args.regenerate:
            log("Starting Dockerfile agent...")
            agent = DockerfileAgent()
            result = agent.run(args.project_path, verbose=not quiet)
            log(f"Dockerfile generated: {result}")

        log("\nBuilding Docker image...")
        builder = DockerBuilder(args.project_path)
        result = builder.build(tag=args.tag, stream_output=not quiet)

        if result.success:
            if quiet:
                # Output only the image URI for piping
                print(args.tag if args.tag else result.image_id)
            else:
                print(f"\nBuild successful!")
                if result.image_id:
                    print(f"Image ID: {result.image_id}")
                if args.tag:
                    print(f"Tagged as: {args.tag}")
            return 0
        else:
            print(f"Build failed: {result.error}", file=sys.stderr)
            return 1

    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="agent-deployer",
        description="AI-powered Dockerfile generation and Docker image building",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze a project directory",
    )
    analyze_parser.add_argument(
        "project_path",
        help="Path to the project directory",
    )

    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate a Dockerfile for the project",
    )
    generate_parser.add_argument(
        "project_path",
        help="Path to the project directory",
    )

    build_parser = subparsers.add_parser(
        "build",
        help="Generate Dockerfile and build Docker image",
    )
    build_parser.add_argument(
        "project_path",
        help="Path to the project directory",
    )
    build_parser.add_argument(
        "-t",
        "--tag",
        help="Tag for the built image (e.g., myapp:latest)",
    )
    build_parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerate Dockerfile even if one exists",
    )
    build_parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Output only the image URI (for piping to other commands)",
    )

    args = parser.parse_args()

    if args.command == "analyze":
        return cmd_analyze(args)
    elif args.command == "generate":
        return cmd_generate(args)
    elif args.command == "build":
        return cmd_build(args)

    return 1


if __name__ == "__main__":
    sys.exit(main())
