"""``mindsos brain`` — the resident-brain REPL.

One long-lived process holds a single live :class:`~mindsos_server.boot.Stack`.
The user probes it live and tasks it; state accrues in-process across
commands. The user's Local is persisted to Falkor on ``save`` / ``quit``
(durable mode).

Verb dispatch is a pure ``BrainREPL.dispatch(line) -> str`` so the loop is
testable headless. Verbs take Linux-style flags (see ``_replparse``); every
verb has a man page shown by ``<verb> -h`` (see ``_manpages``). ``loop()`` is
the thin stdin front end.

Slice 1: read/probe surface + single-capacity ``invoke``. Slice 2 adds
``execute`` (a skill's declared entry pipeline); ``task`` (the generic,
modality-less lifecycle) is retained. Installed Skills also contribute their
own verbs via ``[l4.slots]`` (ADR-0183 §am-3): a skill verb builds a
modality-stamped ``InputEnvelope`` and drives ``run_lifecycle`` through the L4
dispatcher — builtins always win a name clash, so a shadowed skill verb is
dropped at construction. Create options (``--new`` / ``--seq`` / ``--sub`` /
``--prototype``) are placeholders pending the skill-acquisition process (SAP).
"""

from __future__ import annotations

import fnmatch
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import typer

from ._manpages import MANPAGES
from ._replparse import SCOPE, parse, scope_of, tokenize, wants_help

log = logging.getLogger(__name__)

brain_app = typer.Typer(
    name="brain",
    help="Resident-brain REPL — probe and task one live instance.",
)

_HELP = """\
verbs (try '<verb> -h' for a manual page):
  ls [-l|-g]                 list everything in the brain
  search <pattern>           find where a string is registered
  ds [<iri>]                 datastates: list / inspect / --code
  caps [<iri>]               capacities: list / inspect / --code
  pl [<from> <to>]           pipelines: list / find / --transitions
  skills [<name>]            installed skills: list / inspect
  episodes [<iri>]           episodic memory: list / inspect
  invoke <cap> [inputs]      run one capacity
  execute <input>            run a skill's declared entry pipeline
  verify [--ds|--caps|--pl]  system report + health
  task <text>                run the six-phase lifecycle
  save                       persist this user's Local to Falkor
  reset                      wipe run-state, keep learned params
  view [path]                build a graph + print an scp line to open on your Mac
  help                       show this
  quit                       save then exit"""

_SAP = "not yet — pending skill-acquisition (SAP)"


class BrainREPL:
    """Stateful verb dispatcher over one held :class:`Stack`."""

    def __init__(self, stack: Any, viz_spec: Any = None) -> None:
        self.stack = stack
        self.viz_spec = viz_spec
        # ADR-0183 §am-3 — installed-skill verb table. Builtins WIN: a skill
        # verb colliding with a ``_do_<verb>`` method is unreachable, so it is
        # dropped here (runtime-authoritative; catches builtins added AFTER a
        # skill was installed, which a one-time install preflight cannot).
        self._skill_verbs: Dict[str, Dict[str, Any]] = {}
        self._shadowed: List[str] = []
        for verb, slots in getattr(stack, "skill_verbs", {}).items():
            if getattr(self, f"_do_{verb}", None) is not None:
                self._shadowed.append(verb)
                log.warning(
                    "brain: skill verb %r shadowed by a builtin; unreachable.",
                    verb,
                )
                continue
            self._skill_verbs[verb] = slots

    def _do_view(self, args: List[str]) -> str:
        """view [-l|-g] — build a self-contained interactive graph of this brain
        (DataStates, capacities, finder segments) into a temp file on this host,
        and print a one-line scp command to download + open it on your Mac."""
        import getpass
        import glob
        import json
        import os
        import tempfile
        import time
        from pathlib import Path

        opts, pos, err = parse(args, SCOPE)
        if err:
            return err
        views = self._views(scope_of(opts))
        try:
            import importlib.resources as ir
            template = (ir.files("mindsos_cli.commands")
                        .joinpath("brain_viz_template.html")
                        .read_text(encoding="utf-8"))
        except Exception as e:
            return f"view: cannot load viewer template ({type(e).__name__}: {e})"
        from mindsos_cli.brain_viz import build_data
        data = build_data(views, spec=getattr(self, "viz_spec", None),
                          context=self.stack)
        html = template.replace(
            "const DATA = /*__DATA__*/{};",
            "const DATA = " + json.dumps(data, separators=(",", ":")) + ";")

        serve_dir = Path(tempfile.gettempdir()) / "mindsos_viz"
        serve_dir.mkdir(exist_ok=True)
        for f in sorted(glob.glob(str(serve_dir / f"{self.stack.user}_graph_*.html")))[:-3]:
            try:
                os.remove(f)
            except OSError:
                pass
        out = serve_dir / f"{self.stack.user}_graph_{int(time.time())}.html"
        out.write_text(html, encoding="utf-8")

        ncap = sum(1 for n in data["nodes"] if n["kind"] == "cap")
        nds = sum(1 for n in data["nodes"] if n["kind"] == "ds")
        nseg = len(data["segments"])
        stats = f"({ncap} caps, {nds} datastates, {nseg} segments)"
        if not getattr(self, "viz_spec", None):
            stats += "  (no viz_spec - heuristic groups, no segments)"

        conn = os.environ.get("SSH_CONNECTION", "").split()
        host = conn[2] if len(conn) >= 3 else None
        target = f"{getpass.getuser()}@{host}" if host else "<user>@<linux-host>"
        scp = f"scp {target}:{out} ~/Downloads/ && open ~/Downloads/{out.name}"
        hint = ("\n  (if you ssh via a ~/.ssh/config alias, use it in place of "
                f"{target})") if host else \
               "\n  (not detected as an SSH session - fill in the host you connect with)"
        return f"view: {out}  {stats}\n  run on your Mac:\n    {scp}{hint}"

    def dispatch(self, line: str) -> str:
        """Execute one verb line; return the rendered output."""
        tokens, err = tokenize(line)
        if err:
            return err
        if not tokens:
            return ""
        verb, args = tokens[0], tokens[1:]
        handler = getattr(self, f"_do_{verb}", None)
        if handler is not None:
            if wants_help(args):
                return MANPAGES.get(verb, f"(no manual page for {verb!r})")
            return handler(args)
        slots = self._skill_verbs.get(verb)
        if slots is not None:
            if wants_help(args):
                return self._skill_verb_help(verb, slots)
            return self._run_skill_verb(slots, args)
        return f"unknown verb: {verb!r} (try 'help')"

    # ── helpers ───────────────────────────────────────────────────────

    def _views(self, scope: str) -> List[Any]:
        if scope == "local":
            return [self.stack.local_view()]
        if scope == "global":
            return [self.stack.global_view()]
        return [self.stack.global_view(), self.stack.local_view()]

    @staticmethod
    def _section(title: str, iris: List[str]) -> str:
        iris = list(iris)
        head = f"{title} ({len(iris)}):"
        if not iris:
            return head + " (none)"
        return head + "\n" + "\n".join(f"  {i}" for i in iris)

    # ── probe verbs ───────────────────────────────────────────────────

    def _do_ls(self, args: List[str]) -> str:
        opts, _pos, err = parse(args, SCOPE)
        if err:
            return err
        scope = scope_of(opts)
        views = self._views(scope)
        from mindsos_server.episodes import iter_episodes
        from mindsos_server.pipelines import iter_pipelines
        from mindsos_server.skills.records import iter_skill_records

        cap_iris = sorted({n.node_id for v in views for n in v.iter_capacities()})
        ds_iris = sorted({n.node_id for v in views for n in v.iter_datastates()})
        pls = list(iter_pipelines(self.stack.kl, self.stack.user, scope))
        skills = iter_skill_records(self.stack.kl) if scope in ("both", "global") else []
        eps = (
            list(iter_episodes(self.stack.kl, self.stack.user))
            if scope in ("both", "local")
            else []
        )
        return "\n".join(
            [
                f"brain: {self.stack.user!r} [{scope}]",
                self._section("capacities", cap_iris),
                self._section("datastates", ds_iris),
                self._section("pipelines", [f"{n.node_id} [{src}]" for src, n in pls]),
                self._section("skills", [r.bundle_name for r in skills]),
                self._section("episodes", [n.node_id for n in eps]),
            ]
        )

    def _do_search(self, args: List[str]) -> str:
        spec = {**SCOPE, "ignore": (("-i", "--ignore-case"), False)}
        opts, pos, err = parse(args, spec)
        if err:
            return err
        if not pos:
            return "usage: search [-i] [-l|-g] <pattern>"
        pattern = pos[0]
        scope = scope_of(opts)
        ic = bool(opts.get("ignore"))
        views = self._views(scope)

        cands: List[Tuple[str, str]] = []
        for v in views:
            for n in v.iter_capacities():
                cands.append(("cap", n.node_id))
            for n in v.iter_datastates():
                cands.append(("ds", n.node_id))
        from mindsos_server.pipelines import iter_pipelines

        for src, n in iter_pipelines(self.stack.kl, self.stack.user, scope):
            cands.append((f"pl/{src}", n.node_id))
        if scope in ("both", "global"):
            from mindsos_server.skills.records import iter_skill_records

            for r in iter_skill_records(self.stack.kl):
                cands.append(("skill", r.bundle_name))
        if scope in ("both", "local"):
            from mindsos_server.episodes import iter_episodes

            for n in iter_episodes(self.stack.kl, self.stack.user):
                cands.append(("episode", n.node_id))

        def match(iri: str) -> bool:
            if ic:
                return fnmatch.fnmatchcase(iri.lower(), pattern.lower())
            return fnmatch.fnmatchcase(iri, pattern)

        seen = set()
        hits = []
        for kind, iri in cands:
            if (kind, iri) in seen:
                continue
            seen.add((kind, iri))
            if match(iri):
                hits.append((kind, iri))
        if not hits:
            return f"(no matches for {pattern!r})"
        hits.sort()
        n = len(hits)
        return f"{n} match{'' if n == 1 else 'es'}:\n" + "\n".join(
            f"  [{kind}] {iri}" for kind, iri in hits
        )

    def _do_ds(self, args: List[str]) -> str:
        spec = {**SCOPE, "code": (("--code",), False), "new": (("--new",), False)}
        opts, pos, err = parse(args, spec)
        if err:
            return err
        if opts.get("new"):
            return f"ds --new: {_SAP}"
        if opts.get("code") and not pos:
            return "ds --code requires an <iri>"
        scope = scope_of(opts)
        views = self._views(scope)
        if not pos:
            iris = sorted({n.node_id for v in views for n in v.iter_datastates()})
            return self._section("datastates", iris) if iris else "(no datastates)"
        iri = pos[0]
        node = None
        for v in views:
            node = v.get_datastate(iri)
            if node is not None:
                break
        if node is None:
            return f"no such datastate: {iri!r}"
        if opts.get("code"):
            props = dict(node.properties) if getattr(node, "properties", None) else {}
            lines = [iri, f"  type: {node.type_name}"]
            if props:
                lines += [f"  {k} = {props[k]!r}" for k in sorted(props)]
            else:
                lines.append("  (no schema properties)")
            return "\n".join(lines)
        prod, cons = set(), set()
        for v in views:
            if v.get_datastate(iri) is None:
                continue
            prod |= {n.node_id for n in v.producers_of(iri)}
            cons |= {n.node_id for n in v.consumers_of(iri)}
        return "\n".join(
            [
                iri,
                "  produced by: " + (", ".join(sorted(prod)) if prod else "(none)"),
                "  consumed by: " + (", ".join(sorted(cons)) if cons else "(none)"),
            ]
        )

    def _do_caps(self, args: List[str]) -> str:
        spec = {**SCOPE, "code": (("--code",), False), "new": (("--new",), False)}
        opts, pos, err = parse(args, spec)
        if err:
            return err
        if opts.get("new"):
            return f"caps --new: {_SAP}"
        if opts.get("code") and not pos:
            return "caps --code requires an <iri>"
        scope = scope_of(opts)
        views = self._views(scope)
        if not pos:
            iris = sorted({n.node_id for v in views for n in v.iter_capacities()})
            return self._section("capacities", iris) if iris else "(no capabilities)"
        iri = pos[0]
        if not any(v.get_capacity(iri) is not None for v in views):
            return f"no such capability: {iri!r}"
        if opts.get("code"):
            try:
                decl = self.stack.cl.get_declaration(iri)
            except Exception as e:
                return f"{iri}\n  (no declaration bound: {type(e).__name__})"
            return "\n".join(
                [
                    iri,
                    f"  declaration: {type(decl).__qualname__}",
                    f"  module: {type(decl).__module__}",
                ]
            )
        ins, outs = set(), set()
        for v in views:
            if v.get_capacity(iri) is None:
                continue
            ins |= set(v.inputs_of(iri))
            outs |= set(v.outputs_of(iri))
        return "\n".join(
            [
                iri,
                "  consumes: " + (", ".join(sorted(ins)) if ins else "(none)"),
                "  produces: " + (", ".join(sorted(outs)) if outs else "(none)"),
            ]
        )

    def _do_pl(self, args: List[str]) -> str:
        spec = {
            **SCOPE,
            "transitions": (("--transitions",), False),
            "seq": (("--seq",), False),
            "sub": (("--sub",), False),
            "new": (("--new",), False),
        }
        opts, pos, err = parse(args, spec)
        if err:
            return err
        for ph in ("seq", "sub", "new"):
            if opts.get(ph):
                return f"pl --{ph}: {_SAP}"
        scope = scope_of(opts)
        if not pos:
            from mindsos_server.pipelines import iter_pipelines

            rows = list(iter_pipelines(self.stack.kl, self.stack.user, scope))
            if not rows:
                return "(no pipelines)"
            n = len(rows)
            return f"{n} pipeline{'' if n == 1 else 's'}:\n" + "\n".join(
                f"  [{src}] {node.node_id}" for src, node in rows
            )
        if len(pos) < 2:
            return "usage: pl <from-datastate> <to-datastate>"
        start, target = pos[0], pos[1]
        views = self._views(scope)
        if not any(v.get_datastate(start) is not None for v in views):
            return f"no such datastate: {start!r}"
        if not any(v.get_datastate(target) is not None for v in views):
            return f"no such datastate: {target!r}"
        from mindsos_capacity.exceptions import PipelineNotFoundError
        from mindsos_capacity.pipeline import find_pipeline

        try:
            pipe = find_pipeline(
                self.stack.cl,
                session=None,
                start_datastate=start,
                target_datastate=target,
            )
        except PipelineNotFoundError as e:
            return f"no pipeline: {e}"
        n = len(pipe)
        if n == 0:
            return f"{target} already available at {start} (no-op)"
        show_tr = bool(opts.get("transitions"))
        lines = [f"pipeline: {start} -> {target} ({n} step{'' if n == 1 else 's'})"]
        for i, step in enumerate(pipe, 1):
            lines.append(f"  {i}. {step.capacity_iri}")
            if show_tr:
                lines.append("       in:  " + (", ".join(step.input_datastates) or "(none)"))
                lines.append("       out: " + (", ".join(step.output_datastates) or "(none)"))
        return "\n".join(lines)

    def _do_skills(self, args: List[str]) -> str:
        spec = {**SCOPE, "new": (("--new",), False), "prototype": (("--prototype",), False)}
        opts, pos, err = parse(args, spec)
        if err:
            return err
        for ph in ("new", "prototype"):
            if opts.get(ph):
                return f"skills --{ph}: {_SAP}"
        from mindsos_server.skills.records import iter_skill_records

        recs = iter_skill_records(self.stack.kl)
        if pos:
            name = pos[0]
            hit = [r for r in recs if r.bundle_name == name]
            if not hit:
                return f"no such skill: {name!r}"
            r = hit[-1]
            return "\n".join(
                [
                    r.bundle_name,
                    f"  version: {r.bundle_version}",
                    f"  status: {r.status}",
                    f"  action: {r.action}",
                    f"  seq: {r.seq}",
                    f"  recorded: {r.recorded_at}",
                ]
            )
        if not recs:
            return "(no installed-skills ledger records)"
        n = len(recs)
        return f"{n} record{'' if n == 1 else 's'}:\n" + "\n".join(
            f"  [{r.seq}] {r.bundle_name} {r.bundle_version} — {r.action}/{r.status}"
            for r in recs
        )

    def _do_episodes(self, args: List[str]) -> str:
        opts, pos, err = parse(args, SCOPE)
        if err:
            return err
        if scope_of(opts) == "global":
            return "(episodes are Local; nothing in Global)"
        from mindsos_server.episodes import get_episode, iter_episodes

        if pos:
            node = get_episode(self.stack.kl, self.stack.user, pos[0])
            if node is None:
                return f"no such episode: {pos[0]!r}"
            val = node.value if isinstance(node.value, dict) else {}
            out = [pos[0]]
            out += [f"  {k} = {val[k]!r}" for k in sorted(val)]
            if not val:
                out.append("  (no recorded content)")
            return "\n".join(out)
        eps = list(iter_episodes(self.stack.kl, self.stack.user))
        if not eps:
            return f"(no episodes for {self.stack.user!r})"
        n = len(eps)
        return f"{n} episode{'' if n == 1 else 's'}:\n" + "\n".join(
            f"  {node.node_id}" for node in eps
        )

    def _do_verify(self, args: List[str]) -> str:
        spec = {
            "ds": (("--ds",), False),
            "caps": (("--caps",), False),
            "pl": (("--pl",), False),
        }
        opts, _pos, err = parse(args, spec)
        if err:
            return err
        from mindsos_capacity.catalog_check import catalog_check
        from mindsos_server.episodes import iter_episodes
        from mindsos_server.pipelines import iter_pipelines
        from mindsos_server.skills.records import iter_skill_records

        r = catalog_check(self.stack.global_view())
        npl = sum(1 for _ in iter_pipelines(self.stack.kl, self.stack.user))
        if opts.get("ds"):
            out = [f"datastates: {r.datastates}", f"  orphans: {len(r.orphans)}"]
            if r.orphans:
                out.append("  " + ", ".join(r.orphans))
            return "\n".join(out)
        if opts.get("caps"):
            return f"capabilities: {r.capacities}\n  sources: {len(r.sources)}  sinks: {len(r.sinks)}"
        if opts.get("pl"):
            return f"pipelines: {npl}"
        mode = (
            "ephemeral"
            if type(self.stack.persister).__name__.startswith("InMemory")
            else "durable"
        )
        neps = sum(1 for _ in iter_episodes(self.stack.kl, self.stack.user))
        nskills = len(iter_skill_records(self.stack.kl))
        return "\n".join(
            [
                f"user: {self.stack.user}",
                f"mode: {mode}",
                f"capabilities: {r.capacities}",
                f"datastates: {r.datastates}",
                f"pipelines: {npl}",
                f"episodes: {neps}",
                f"installed skills: {nskills}",
                f"catalog: {'OK' if r.ok else 'ORPHANS'} "
                f"(sources {len(r.sources)}, sinks {len(r.sinks)}, orphans {len(r.orphans)})",
            ]
        )

    # ── invoke (single capacity) ──────────────────────────────────────

    def _resolve_capacity(self, target: str) -> Tuple[Optional[str], Optional[str]]:
        views = [self.stack.global_view(), self.stack.local_view()]
        all_iris = sorted({n.node_id for v in views for n in v.iter_capacities()})
        if target in all_iris:
            return target, None
        cand = sorted({i for i in all_iris if i.endswith(target)})
        if not cand:
            return None, f"no such capability: {target!r}"
        if len(cand) > 1:
            return None, "ambiguous: " + ", ".join(cand)
        return cand[0], None

    def _cap_inputs(self, cap_iri: str) -> List[str]:
        for v in (self.stack.global_view(), self.stack.local_view()):
            if v.get_capacity(cap_iri) is not None:
                return v.inputs_of(cap_iri)
        return []

    @staticmethod
    def _match_input(inputs: List[str], key: str) -> Optional[str]:
        for iri in inputs:
            if iri == key or iri.endswith(key):
                return iri
        return None

    @staticmethod
    def _coerce(val: str) -> Any:
        try:
            return json.loads(val)
        except Exception:
            return val

    def _parse_inputs(
        self, cap_iri: str, rest: List[str]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        inputs = self._cap_inputs(cap_iri)
        if not rest:
            return {}, None
        joined = " ".join(rest).strip()
        if joined.startswith("{"):
            try:
                obj = json.loads(joined)
            except json.JSONDecodeError as e:
                return None, f"bad json inputs: {e}"
            if not isinstance(obj, dict):
                return None, "inputs must be a JSON object (datastate-iri -> value)"
            return obj, None
        if all("=" in t for t in rest):
            mapping: Dict[str, Any] = {}
            for t in rest:
                k, _, val = t.partition("=")
                full = self._match_input(inputs, k)
                if full is None:
                    return None, f"no input datastate matching {k!r} on this capacity"
                mapping[full] = self._coerce(val)
            return mapping, None
        if len(rest) == 1:
            if len(inputs) == 1:
                return {inputs[0]: self._coerce(rest[0])}, None
            if len(inputs) == 0:
                return None, "capacity takes no inputs"
            return None, (
                "capacity takes multiple inputs; use key=value (inputs: "
                + ", ".join(inputs)
                + ")"
            )
        return None, "too many values; use key=value or a JSON object"

    def _resolve_pipeline(self, target):
        from mindsos_capacity.pipeline import Pipeline
        from mindsos_server.pipelines import iter_promoted_pipelines

        nodes = list(iter_promoted_pipelines(self.stack.kl))
        match = [n for n in nodes if n.node_id == target or n.node_id.endswith(target)]
        if not match:
            return None, f"no such capability or pipeline: {target!r}"
        if len(match) > 1:
            return None, "ambiguous pipeline: " + ", ".join(n.node_id for n in match)
        val = match[0].value if isinstance(match[0].value, dict) else {}
        try:
            return Pipeline.from_dict(val), None
        except Exception as e:
            return None, f"pipeline {match[0].node_id} not reconstructable: {type(e).__name__}"

    def _parse_pipeline_inputs(self, pipe, rest):
        starts = list(pipe.start_datastates)
        if not rest:
            return {}, None
        joined = " ".join(rest).strip()
        if joined.startswith("{"):
            try:
                obj = json.loads(joined)
            except json.JSONDecodeError as e:
                return None, f"bad json inputs: {e}"
            if not isinstance(obj, dict):
                return None, "inputs must be a JSON object"
            return obj, None
        if all("=" in t for t in rest):
            mapping = {}
            for t in rest:
                k, _, v = t.partition("=")
                full = self._match_input(starts, k)
                if full is None:
                    return None, f"no start datastate matching {k!r}"
                mapping[full] = self._coerce(v)
            return mapping, None
        if len(rest) == 1 and len(starts) == 1:
            return {starts[0]: self._coerce(rest[0])}, None
        return None, "use key=value or JSON (starts: " + ", ".join(starts) + ")"

    def _do_invoke(self, args: List[str]) -> str:
        opts, pos, err = parse(args, {})
        if err:
            return err
        if not pos:
            return "usage: invoke <cap|pipeline-iri|suffix> [inputs]"
        target = pos[0]
        cap_iri, caperr = self._resolve_capacity(target)
        if cap_iri is not None:
            inputs, ierr = self._parse_inputs(cap_iri, pos[1:])
            if ierr:
                return ierr
            try:
                result = self.stack.dispatcher.dispatch(cap_iri, inputs)
            except Exception as e:
                return f"invoke error: {type(e).__name__}: {e}"
            if not result.success:
                return f"invoke failed: {result.error}"
            if getattr(result, "needs_input", None) is not None:
                return f"needs input: {result.needs_input}"
            outs = dict(result.outputs)
            if not outs:
                return "ok (no outputs / write capability)"
            return "outputs:\n" + "\n".join(f"  {k} = {v!r}" for k, v in outs.items())
        pipe, perr = self._resolve_pipeline(target)
        if pipe is None:
            return caperr if "ambiguous" in caperr else perr
        inputs, ierr = self._parse_pipeline_inputs(pipe, pos[1:])
        if ierr:
            return ierr
        from mindsos_server.pipeline_runner import run_pipeline

        state, rerr = run_pipeline(self.stack.dispatcher, pipe, inputs)
        if rerr:
            return f"invoke pipeline failed: {rerr}"
        out = state.get(pipe.target_datastate)
        return f"pipeline -> {pipe.target_datastate} = {out!r}"

    def _do_execute(self, args: List[str]) -> str:
        from mindsos_capacity.exceptions import PipelineNotFoundError
        from mindsos_capacity.pipeline import ConjunctionFinder
        from mindsos_server.pipeline_runner import run_pipeline
        from mindsos_server.skills.records import skill_entries

        opts, pos, err = parse(args, {})
        if err:
            return err
        entries = skill_entries(self.stack.kl)
        if not entries:
            return "execute: no installed skill declares an entry pipeline"
        if len(entries) > 1:
            return "execute: ambiguous — entries declared by " + ", ".join(
                n for n, _, _ in entries
            )
        name, start, target = entries[0]
        if not pos:
            return f"usage: execute <input>   (runs {name}: {start} -> {target})"
        value = self._coerce(pos[0]) if len(pos) == 1 else " ".join(pos)
        try:
            pipe = ConjunctionFinder().find(
                self.stack.cl,
                session=None,
                start_datastates=(start,),
                target_datastate=target,
            )
        except PipelineNotFoundError as e:
            return f"execute: no pipeline {start} -> {target}: {e}"
        state, rerr = run_pipeline(self.stack.dispatcher, pipe, {start: value})
        if rerr:
            return f"execute failed: {rerr}"
        return f"execute[{name}]: {target} = {state.get(target)!r}"

    # ── skill-declared verbs (ADR-0183 §am-3) ─────────────────────────

    def _run_skill_verb(self, slots: Dict[str, Any], args: List[str]) -> str:
        """Run an installed skill's Phase-1 ingress lifecycle: build a
        modality-stamped :class:`InputEnvelope` and drive ``run_lifecycle``.

        ``run_lifecycle`` PROPAGATES ``InterpretationError`` (unroutable /
        mis-wired modality, unresolved map target) — the orchestrator has no
        try/except around ``phase_1.run``, so it does NOT become a
        ``dont_know``. Mirror the ``_do_invoke`` guard so a mis-registered
        skill cannot crash the REPL.
        """
        if not args:
            return (
                f"usage: {slots.get('verb', '?')} <input>   "
                f"(modality {slots.get('modality')!r})"
            )
        from mindsos_intelligence.ingress import InputEnvelope

        env = InputEnvelope(
            value=" ".join(args),
            modality=slots["modality"],
            source="brain-cli",
        )
        try:
            outcome = self.stack.orch.run_lifecycle(env)
        except Exception as e:  # noqa: BLE001 — REPL guard, _do_invoke precedent
            return f"skill error: {type(e).__name__}: {e}"
        # ADR-0196 — the skill asked the user; surface it, don't swallow it
        # behind a bare status string.
        if outcome.status == "pending_confirmation":
            return f"needs input: {outcome.pending_confirmation}"
        return outcome.status

    @staticmethod
    def _skill_verb_help(verb: str, slots: Dict[str, Any]) -> str:
        return "\n".join(
            [
                f"{verb} <input> — run this skill's Phase-1 ingress lifecycle",
                f"  modality: {slots.get('modality')}",
                f"  process:  {slots.get('process')}",
                f"  map:      {slots.get('map')}",
            ]
        )

    # ── task + persistence verbs ──────────────────────────────────────

    def _do_task(self, args: List[str]) -> str:
        if not args:
            return "usage: task <text>"
        text = " ".join(args)
        outcome = self.stack.orch.run_lifecycle({"text": text})
        return f"task: {outcome.status}"

    def _do_save(self, args: List[str]) -> str:
        if self.stack.persister is None:
            return "save: no persister (ephemeral)"
        self.stack.save()
        return f"saved Local for {self.stack.user!r}"

    def _do_reset(self, args: List[str]) -> str:
        p = self.stack.persister
        if p is None or not hasattr(p, "reset_run_state"):
            return "reset: unsupported (ephemeral)"
        existed = p.reset_run_state(self.stack.user)
        return "run-state wiped" if existed else "(no Local to reset)"

    def _do_help(self, args: List[str]) -> str:
        out = [_HELP]
        if self._skill_verbs:
            out.append("")
            out.append("installed skill verbs:")
            out += [
                f"  {v} <input>    -> {self._skill_verbs[v].get('modality')}"
                for v in sorted(self._skill_verbs)
            ]
        if self._shadowed:
            out.append("")
            out.append(
                "shadowed by builtins (unreachable): "
                + ", ".join(sorted(self._shadowed))
            )
        skipped = getattr(getattr(self.stack, "activation", None), "skipped", ())
        if skipped:
            out.append("")
            out.append(
                "skills not activated (verbs unavailable): "
                + ", ".join(sorted(b for b, _ in skipped))
            )
        return "\n".join(out)

    def _do_quit(self, args: List[str]) -> str:
        return ""


def loop(repl: BrainREPL) -> None:
    """Read-eval-print until EOF or ``quit``."""
    typer.echo("MindsOS resident brain. Type 'help', 'quit' to exit.")
    n_skill = len(getattr(repl, "_skill_verbs", {}))
    n_bad = len(getattr(repl, "_shadowed", []))
    if n_skill or n_bad:
        typer.echo(
            f"  {n_skill} skill verb(s) available"
            + (f", {n_bad} shadowed (see 'help')" if n_bad else "")
        )
    while True:
        try:
            line = input("brain> ").strip()
        except (EOFError, KeyboardInterrupt):
            typer.echo("")
            line = "quit"
        if line in ("quit", "exit"):
            typer.echo(repl._do_save([]))
            typer.echo("bye")
            return
        if not line:
            continue
        typer.echo(repl.dispatch(line))


@brain_app.callback(invoke_without_command=True)
def brain(
    user: str = typer.Option("default", "--user", "-u", help="Local user this brain serves."),
    ephemeral: bool = typer.Option(
        False, "--ephemeral", help="In-memory only (no Falkor, no persistence)."
    ),
) -> None:
    """Boot one resident brain and drop into the REPL."""
    from mindsos_server.boot import boot_brain

    client = None
    if not ephemeral:
        from mindsos_core.config import FalkorConfig
        from mindsos_core.persistence.client import FalkorClient

        client = FalkorClient(FalkorConfig.from_env())
    try:
        stack = boot_brain(client, user=user)
        loop(BrainREPL(stack))
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


def register_brain_app(parent: typer.Typer) -> None:
    """Register the ``brain`` subapp on the root Typer."""
    parent.add_typer(brain_app, name="brain")


__all__ = ["BrainREPL", "loop", "brain_app", "register_brain_app"]
