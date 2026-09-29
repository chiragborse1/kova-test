"""A workflow that cannot start is not a safety net.

`.github/workflows/ci.yaml` is the orchestrator: it is the only top-level
workflow with a `pull_request` trigger, and it is what calls the 20-odd
`workflow_call` sub-workflows that actually run the tests. It has been broken
since a rebrand commit - `5339ce959c`, "attribution: drop upstream
contributor map" - deleted the `contributor-check` JOB DEFINITION and left
the entry in `all-checks-pass`'s `needs`.

GitHub rejects the whole file on that one dangling name, so the orchestrator
never starts. Every sub-workflow is `workflow_call`-only, so with the caller
gone they never start either. The result: the repository has 51 workflows
and ZERO of them have ever run on a pull request. `gh run list` on this fork
shows 19 runs, all `main`, all from before that commit.

Nothing local can see this. `tsc` passes, eslint passes, vitest passes, and
every script in `scripts/kova/` passes - they all run against a dev server on
this machine. The failure is entirely in whether GitHub would accept the
file.

So this gate does what a local run cannot: parse the workflow, resolve every
`needs` to a real job, reject cycles, and confirm that the workflows which
carry the `pull_request` trigger actually exist and are parseable. A
`workflow_call` sub-workflow with no caller is reported too - 21 of them are
currently orphaned behind the broken orchestrator.

Usage:  py scripts/kova/workflows.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WF = os.path.join(ROOT, ".github", "workflows")

try:
    import yaml
except ImportError:
    print("  PyYAML is not installed; cannot check the workflows.")
    print("  pip install pyyaml")
    return_code = 2
    yaml = None


def needs_of(job):
    raw = job.get("needs") or []
    return [raw] if isinstance(raw, str) else list(raw)


def main():
    if yaml is None:
        return return_code

    files = sorted(f for f in os.listdir(WF) if f.endswith((".yml", ".yaml")))
    parsed, broken = {}, []

    class StrictLoader(yaml.SafeLoader):
        pass

    def _no_duplicates(loader, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in mapping:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping", node.start_mark,
                    "found duplicate key %r" % (key,), key_node.start_mark)
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    StrictLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicates)

    for name in files:
        path = os.path.join(WF, name)
        try:
            with open(path, encoding="utf-8") as handle:
                doc = yaml.load(handle, Loader=StrictLoader)
        except Exception as error:  # noqa: BLE001 - report, do not raise
            broken.append("%s does not parse: %s" % (name, str(error).split("\n")[0]))
            continue
        if not isinstance(doc, dict):
            broken.append("%s is not a workflow mapping" % name)
            continue
        # PyYAML reads a bare `on:` as the boolean True
        doc["on"] = doc.get("on", doc.get(True))
        parsed[name] = doc

    print("  %d workflow files, %d parsed" % (len(files), len(parsed)))

    problems = list(broken)

    for name, doc in parsed.items():
        jobs = doc.get("jobs") or {}
        if not isinstance(jobs, dict):
            problems.append("%s: `jobs` is not a mapping" % name)
            continue
        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            for need in needs_of(job):
                if need not in jobs:
                    problems.append(
                        "%s: job `%s` needs `%s`, which is not defined" % (name, job_name, need)
                    )

        # A cycle makes GitHub reject the file outright, so catch it here.
        colour, stack = {}, []

        def visit(node):
            if colour.get(node) == 1:
                return node            # a back edge: this node is on the stack
            if colour.get(node) == 2:
                return None             # already finished: a diamond, not a cycle
            colour[node] = 1
            stack.append(node)
            for need in needs_of(jobs.get(node) or {}):
                if need not in jobs:
                    continue
                back = visit(need)
                if back is not None:
                    return back
            stack.pop()
            colour[node] = 2
            return None

        for job_name in jobs:
            if colour.get(job_name) is None:
                back = visit(job_name)
                if back is not None:
                    problems.append(
                        "%s: dependency cycle - `%s` needs `%s`, which is already being built"
                        % (name, job_name, back)
                    )
                    break

    # Who carries the pull_request trigger, and does it parse?
    pr_carriers = [n for n, d in parsed.items() if "pull_request" in (d.get("on") or {})]
    print("  pull_request carriers: %s" % (", ".join(sorted(pr_carriers)) or "NONE"))
    if not pr_carriers:
        problems.append("no workflow has a `pull_request` trigger, so a PR is never checked")

    # A workflow_call with no caller never runs.
    callers = set()
    for name, doc in parsed.items():
        body = yaml.safe_dump(doc)
        for other in files:
            if other == name:
                continue
            if "./.github/workflows/%s" % os.path.splitext(other)[0] in body:
                callers.add(other)
    orphans = sorted(
        n for n, d in parsed.items()
        if "workflow_call" in (d.get("on") or {}) and n not in callers
    )
    print("  workflow_call with no caller: %d" % len(orphans))
    if orphans and pr_carriers:
        # Only worth reporting while the orchestrator is broken.
        for n in orphans:
            problems.append("%s: workflow_call but nothing calls it" % n)

    print()
    if problems:
        for p in problems:
            print("  ATTENTION  " + p)
        print()
        print("  A workflow GitHub refuses to parse never runs. Everything it")
        print("  gates is unchecked, and no local command can see that.")
        return 1

    print("  every workflow parses, every needs resolves, and a PR triggers CI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
