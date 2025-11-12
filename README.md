# FRED Simulation Project

A platform for running epidemiological simulations in the cloud built on the FRED (Framework for Reconstructing Epidemiological Dynamics) framework and epx client for FRED jobs.

## Overview

This project combines:

- **FRED Framework**: C++ epidemiological simulation engine
- **Epistemix Platform**: Flask-based API server with clean architecture and AWS infrastructure
- **Simulation Runner**: Python CLI for orchestrating FRED simulation workflows
- **Simulations**: Agent-based simulation configurations and job scripts
- **TCR**: Test && Commit || Revert development tool

Built with **Pants** for dependency management, PEX binaries, and Docker images.

## Inspiration

This project was inspired by a job posting I saw for a company called Epistemix which provides a managed service for running epidemiological simulations built using the FRED framework. An older, open source version of FRED is published on GitHub associated with the University of Pittsburgh, where the framework originated. Epistemix also has a python SDK for submitting FRED jobs to their platform called epx. This project implements the job orchestration required for a local epx job submission request to initiate a FRED simulation remotely and for fetching results with epx when the remote job is done.

## Project Components

- **[fred-framework/](fred-framework/)** - C++ epidemiological simulation engine
- **[epistemix_platform/](epistemix_platform/)** - Flask API server with clean architecture
  - **[infrastructure/](epistemix_platform/infrastructure/)** - AWS CloudFormation/Sceptre templates
- **[simulation_runner/](simulation_runner/)** - FRED workflow orchestration with Python CLI
- **[simulations/](simulations/)** - Simulation configurations and job scripts
- **[tcr/](tcr/)** - Test && Commit || Revert development tool

## Documentation

- **[Getting Started](docs/getting-started.md)** - Installation, dependencies, and quick start
- **[Architecture](docs/architecture.md)** - Project structure and technology stack
- **[FRED Simulations](docs/fred-simulations.md)** - Running and configuring FRED simulations
- **[CLI Tools](docs/cli-tools.md)** - Simulation Runner and Epistemix Platform CLIs
- **[Docker Containers](docs/docker.md)** - Building and running Docker images
- **[AWS Infrastructure](docs/aws-infrastructure.md)** - Deploying to AWS with CloudFormation/Sceptre

## Technology Stack

Below is a comparison of the tech stack mentioned in the job posting and what I used for this project. In general, the difference in technologies was really just a matter of familiarity. I did not take time to analyze which would have been better because I wasn't working from a specification that dictated why these choices were made. The technology choices I did made were more or less equivalent, though.

| Technology | Job Description | Project |
|----------|--------|--------|
| Language | Python | Python |
| Web Framework | FastAPI | Flask |
| Cloud | AWS | AWS |
| Compute | EC2 | EC2 |
| Job Management | EKS (Kubernetes) | AWS Batch (ECS) |
| Object Storage | S3 | S3 |
| Application Database | RDS | RDS |
| Queue Management | SQS | AWS Batch |
| Permissions / Auth | IAM | IAM |
| Logging | CloudWatch | CloudWatch |
| IaC | Terraform | CloudFormation |

### Additional Tools

**Pants**: A build tool similar to Bazel but specifically designed for Python projects. Pants supports PEX for building Python executables, Docker for building container images, Ruff for linting and formatting code, and pytest for unit testing. The key strength of Pants is its dependency mapping and file level caching. The caching is leveraged to only rebuild source code that has changed allowing for faster rebuilds. Testing also benefits from the caching and dependency mapping because Pants knows which tests are associated with which source code files.

**Sceptre**: A deployment tool that makes configuration management easier when using CloudFormation for infrastructure as code. Sceptre also allows the creation of custom defined hooks, so you can run template validation and other tests pre-deployment or even setup post-deployment automated regression tests against cloud resources.

**Ona (fka Gitpod)**: A platform for managing developer environments. Historically, Gitpod hosted these environments themselves but has since moved to a self-hosting model in which they provide you with the IaC for you to use in your cloud provider. What is in this project is just the .gitpod folder which contains an automations.yaml with common setup tasks for this project and a .devcontainer for specifying the container environment.

**Pact**: A tool for contract testing between APIs and their consumers. I needed to map out the HTTP API interface expected by the epx client for this project. Historically, when I created clients for third-party APIs, I would mock the API in unit tests with the Mock library. I decided to use Pact because when you use their Mock HTTP server in tests to generate mock responses, you have the option to generate a JSON specification which is referred to as a pact. For much more complex architectures where you have a many to many relationship between APIs and consumers, a pact broker server can be run which can host pacts and allow contracts to be validated as part of a CI/CD pipeline. Given this project has one API, I didn't waste time setting up the broker.

## Common Commands

### Build System

```bash
# Generate lockfiles
pants generate-lockfiles

# Export virtual environment
pants export --resolve=epistemix_platform_env

# Build PEX binaries
pants package epistemix_platform:epistemix-cli
pants package simulation_runner:simulation-runner-cli

# Build Docker images
pants package //:simulation-runner
pants package //:epistemix-api

# Run tests
pants test ::
```

## Use of AI

Early on in the project I used GitHub Copilot for code generation but found the terminal integration of Claude Code to be a much better experience. One of the goals I had for this project was to explore the benefits and limitations of AI code generation in a non-work environment where the only money on the line is the subscription fee I paid. While "vibecoding" and attempting to "one-shot" solution is in vogue, the approach I took to this project was to use Claude Code for AI-assisted pair programming. Anthropic has told stories of getting Claude to write production-ready features by just letting it run unassisted for 8+ hours. I've only seen it run unaided for 30m max, but more like 5-10min on average for complex tasks. The more broad and open ended the goal, the more assistance Claude needs. This isn't necessarily a problem because good software is usually built iteratively. In my experience, I would write far less code without Claude but it would write nothing useful without me.

The challenges I've run into and the discoveries I've made for what works seem to be shared across the community of developers who are attempting to use LLM-based AI code generators for pair programming.

### Key Takeaways

- Getting Claude to do what you want is all about managing what is in the Context Window when your prompt is being interpreted. The struggle is you only have access to the conversation history and sometimes early information in the thread is forgot, so you don't have a complete picture of why a prompt might have been misinterpreted.
- There's no long-term memory. It's not just between sessions that's a problem, if the Context Window becomes flooded mid-session the conversation is compacted and useful information is lost, so you waste tokens reminding Claude of things you already said. It seems like some local RAG + Knowledge Graph solution served over a MCP server might help with context construction. The question is, what metadata is most useful to store in the graph database to help Claude better understand the semantics of the code base?
- If you are working with Claude Code long enough it will eventually make an unethical decision. For example, when installing sceptre, sceptre shared a dependency with another python package and there was a version conflict. Unable to find a suitable version each python package could agree on, Claude chose to comment out the other depdency in the pyproject.toml, so that sceptre would install. The real solution was to restructure the project, so deployment requirments and app requirements were managed separately.

### Observations

- Claude struggles with greenfield development. It's much easier to add a feature or refactor one in an existing code base.
- The cleaner and more organized the code is the better suggestions you get
- I want Claude to follow the Red-Green-Refactor pattern for TDD. Unless constantly reminded it always writes the tests to the implementation it already wrote.
- It struggles with tool use when the tool is less commonly used or conflicts with embedded tool biases. In particular, it frequently conflates the `pants test` syntax with pytest interface. However, some of the cli options for `pants test` are passthroughs to pytest.
- Claude subagents are good for dictating workflow orchestration and are generally more efficient at implementing solutions than the main thread.
  - Initially I had many subagents until Anthropic released the Skills feature for packaging on-demand context and scripts. After, I converted most of my subagents specifications to skills and only left one general software-architect subagent
- Since Claude struggles writing on a blank canvas, it's best to generate a plan first before implementation.
  - Specification documents like Gherkin-style feature files for behavior-driven development help (I have recently stubbled upon, but have not used, the [spec-kit](https://github.com/github/spec-kit) from GitHub which seems to have been built around this same idea)
  - Asking Claude to write decisions to files in a temporary folder can be useful for debugging and memory
- If you have lot of files that need a very simple change (e.g. removing excessive comments), it's very easy to have Claude use the built-in, general-purpose Task subagent to parallelize the work using multi-agent pattern.

### CodeRabbit

I used CodeRabbit for automated PR review. I initially used GitHub's Copilot for PR review but found CodeRabbit gave better review comments. It's particularly good at linting and formatting issues, when I've forgotten to run ruff (though, a pre-commit hook would work just as well for this purpose). CodeRabbit also seems to be trained on AWS's Well-Architected Framework and generally provides good suggestions for managing infrastructure as code. Although, now and then it would hallucinate, so I generally fact-checked suggestions with a web search or documentation when it was available.

### TCR (Test && Commit || Revert)

This is an extreme pattern for following test-driven development (TDD). Whenever the source code changes, tests are automatically run. If tests pass, the new source code is committed. If tests fail, the new source code is reverted to the last stable commit. The intent is to coerce the developer into writing small testable changes. I did not find a dedicated tool for implementing this behavior, so I built one using the file-watching python package [watchdog](https://python-watchdog.readthedocs.io/en/stable/). The program uses a yaml config to specify what file path to watch and what test command to run and the event loop is designed to run in the background.

The hope was that the aggressive nature of TCR and sufficient context would guide Claude into following TDD. It did not. Very simple requests which took 1min without TCR running took 30min with TCR. Claude spent most of its time complaining that TCR was erasing the code that was just written, despite having been provided context about the tool and a cli interfcace to access docs and monitor background tcr processes. On more than one occasion Claude asked if it could just kill the TCR background process so it could complete the objective of the prompt unimpeded.

While I found the TCR program to be a useful guardrail when I was manually editing code, I was never able to get Claude to work efficiently with it.

## License

See individual component READMEs for license information.
