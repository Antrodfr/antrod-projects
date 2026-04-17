# PM Skills for Claude Code

A collection of [Claude Code Skills](https://docs.anthropic.com/en/docs/claude-code/skills) designed for **Product Managers**.

These skills follow the [Agent Skills](https://agentskills.io) open standard and work with Claude Code (and other compatible AI tools).

## Available Skills

| Skill | Description |
|-------|-------------|
| **[ideation-assistant](./ideation-assistant/)** | Go from a raw idea or vague problem to a structured one-pager, step by step. Covers problem exploration, brainstorming, prioritization, and structuring. |

## Installation

### Option 1 — For a specific project

Copy the skill folder into your project's `.claude/skills/` directory:

```bash
# Clone this repo
git clone https://github.com/<your-username>/pm-skills.git

# Copy the skill into your project
cp -r pm-skills/ideation-assistant your-project/.claude/skills/
```

### Option 2 — For all your projects (personal skill)

Copy the skill folder into your personal Claude skills directory:

```bash
# Clone this repo
git clone https://github.com/<your-username>/pm-skills.git

# Copy to personal skills (available in all projects)
cp -r pm-skills/ideation-assistant ~/.claude/skills/
```

### Option 3 — Git submodule (easy updates)

Add this repo as a submodule inside your project:

```bash
cd your-project
git submodule add https://github.com/<your-username>/pm-skills.git .claude/skills/pm-skills
```

To update later:

```bash
git submodule update --remote
```

## Usage

Once installed, the skill is available in Claude Code:

- **Automatic** — Claude detects when you're brainstorming and loads it
- **Manual** — Type `/ideation-assistant` followed by your idea or problem

### Example

```
/ideation-assistant I want to build a collaborative travel itinerary planner
```

Claude will walk you through 6 iterative steps:

1. **Clarify** — Asks a few essential questions
2. **Explore** — Digs into the root problem `[5 Whys]`
3. **Reframe** — Turns the problem into opportunities `[HMW, JTBD]`
4. **Brainstorm** — Generates solutions with comparables `[Comparables]`
5. **Prioritize** — Scores and ranks ideas `[RICE]`
6. **Structure** — Produces a one-pager ready for specs `[Lean Canvas]`

At any step you can go back, skip ahead, or challenge the work with **"What if" mode**.

## Frameworks Used

| Framework | Used In | Purpose |
|-----------|---------|---------|
| **5 Whys** | Explore | Find the root cause of a problem |
| **How Might We** | Reframe | Turn problems into opportunity questions |
| **JTBD** | Reframe + One-pager | Describe the real user need |
| **Comparables** | Brainstorm + One-pager | Reference existing products for inspiration |
| **RICE** | Prioritize | Score ideas on Reach, Impact, Confidence, Effort |
| **Lean Canvas** | Structure | Format the final one-pager |

## Contributing

PRs welcome! If you have ideas for new PM skills or improvements to existing ones, feel free to open an issue or submit a pull request.

## License

MIT
