#!/usr/bin/env python3
"""Shared, stdlib-only installer. Preview -> explicit apply -> recoverable journal.

No project command is executed during installation or migration.
"""
import argparse
import base64
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import uuid

SOURCE = Path(__file__).resolve().parents[1]


def runtime(source=SOURCE):
    candidates = [source / 'bin/plan', source / '.claude/bin/plan', source / '.agents/coldsession/bin/plan']
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        raise ValueError('no runtime for recovery; use the retained release checkout installer')
    loader = importlib.machinery.SourceFileLoader('cs_runtime', str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def sha(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


def read(path):
    return path.read_bytes() if path.exists() else None


def encode(data):
    return base64.b64encode(data).decode('ascii') if data is not None else None


def decode(data):
    return base64.b64decode(data) if data is not None else None


def safe(target, relative):
    if Path(relative).is_absolute() or '..' in Path(relative).parts or ':' in relative:
        raise ValueError(f'invalid managed path: {relative}')
    path = target / relative
    if not path.resolve().is_relative_to(target.resolve()):
        raise ValueError(f'managed path escapes target through a link: {relative}')
    # Avoid replacing through a directory alias even when its destination is inside.
    for parent in [path, *path.parents]:
        if parent == target:
            break
        attributes = getattr(parent.lstat(), 'st_file_attributes', 0) if parent.exists() else 0
        if parent.is_symlink() or attributes & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0):
            raise ValueError(f'managed path contains a link/junction: {relative}')
    return path


def atomic_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name('.cs-install-' + uuid.uuid4().hex)
    try:
        with temp.open('wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            temp.chmod(path.stat().st_mode)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def write_json(path, data):
    atomic_bytes(path, (json.dumps(data, indent=2, sort_keys=True) + '\n').encode())


def get_json(path, default):
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else default


def configured_hooks(windows):
    suffix = 'cmd' if windows else 'sh'
    prefix = '${CLAUDE_PROJECT_DIR}'
    def hook(kind, matcher=None):
        entry = {'hooks': [{'type': 'command', 'command': f'"{prefix}/.claude/hooks/cs-guard-{kind}.{suffix}"'}]}
        if matcher is not None:
            entry['matcher'] = matcher
        return entry
    return {'UserPromptSubmit': [hook('stage')],
            'PreToolUse': [hook('read', 'Read'), hook('write', 'Edit|Write|MultiEdit|apply_patch|Bash|PowerShell|exec_command|shell_command')],
            'PostToolUse': [hook('lint', 'Edit|Write|MultiEdit|apply_patch')]}


def owned_hook(entry):
    hooks = entry.get('hooks', []) if isinstance(entry, dict) else []
    return bool(hooks) and all(isinstance(h, dict) and re.search(
        r'[/\\]cs-guard-(?:read|write|lint|stage)\.(?:cmd|sh)["\s]*$', h.get('command', '')) for h in hooks)


def bundle(source, target, agent, windows):
    files = {}
    def put(relative, path, replace=None):
        data = path.read_bytes()
        if replace:
            data = data.decode('utf-8-sig').replace('.claude/bin/plan', replace).encode()
        files[relative] = data
    if agent in ('claude', 'both'):
        for path in (source / 'commands').glob('cs-*.md'):
            put('.claude/commands/' + path.name, path, '.claude/bin/plan.cmd' if windows else None)
        for path in (source / 'hooks').glob('cs-guard-*'):
            put('.claude/hooks/' + path.name, path)
        for name in ('plan', 'plan.cmd'):
            put('.claude/bin/' + name, source / 'bin' / name)
    if agent in ('codex', 'both'):
        for path in (source / 'commands').glob('cs-*.md'):
            put('.agents/coldsession/commands/' + path.name, path,
                '.agents/coldsession/bin/plan.cmd' if windows else '.agents/coldsession/bin/plan')
        for path in (source / 'skills').rglob('*'):
            if path.is_file():
                put('.agents/skills/' + path.relative_to(source / 'skills').as_posix(), path,
                    '.agents/coldsession/bin/plan.cmd' if windows else '.agents/coldsession/bin/plan')
        for name in ('plan', 'plan.cmd'):
            put('.agents/coldsession/bin/' + name, source / 'bin' / name)
    for path in (source / 'templates').glob('*.md'):
        put('templates/' + path.name, path)
    # Recovery travels with the installed release; no disposable clone required.
    if (source / 'bin' / 'cs_install.py').exists():
        put('.coldsession-state/cs_install.py', source / 'bin' / 'cs_install.py')
    return files


def codex_config(original, enabled):
    """Replace only our delimited TOML block; preserve all other configuration."""
    start, end = '# BEGIN coldsession managed hooks', '# END coldsession managed hooks'
    text = (original or b'').decode('utf-8-sig')
    if (start in text) != (end in text):
        raise ValueError('incomplete managed Codex hooks block; repair config before upgrade')
    text = re.sub(re.escape(start) + r'.*?' + re.escape(end) + r'\n?', '', text, flags=re.S)
    if enabled:
        rows = [start]
        for event, kind, matcher in (('UserPromptSubmit', 'stage', None),
                                      ('PreToolUse', 'read', 'read_file|Read'),
                                      ('PreToolUse', 'write', 'apply_patch|exec_command|shell_command|write_file|Edit|Write'),
                                      ('PostToolUse', 'lint', 'apply_patch|write_file|Edit|Write')):
            rows += [f'[[hooks.{event}]]']
            if matcher:
                rows += ['matcher = ' + json.dumps(matcher)]
            rows += [f'[[hooks.{event}.hooks]]', 'type = "command"',
                     'command = ' + json.dumps(f'python3 .agents/coldsession/bin/plan guard {kind}'),
                     'commandWindows = ' + json.dumps(f'.agents/coldsession/bin/plan.cmd guard {kind}')]
        text = text.rstrip() + '\n\n' + '\n'.join(rows + [end]) + '\n'
    return text.encode()


def codex_hook_hash(data):
    text = (data or b'').decode('utf-8-sig')
    match = re.search(r'# BEGIN coldsession managed hooks.*?# END coldsession managed hooks', text, re.S)
    return sha((match.group(0) if match else '').encode())


def inspect_workflow(target, rt):
    documents, active = {}, []
    if (target / 'PLAN.md').exists():
        rt.read_index()  # Reject traversal and unresolved pointers during preflight.
    for name in ('PLAN.md', 'OBJECTIVE.md'):
        if (target / name).exists():
            fm, _ = rt.split_frontmatter((target / name).read_text(encoding='utf-8-sig'))
            if re.search(r'^active:\s*\S+', fm, re.M):
                raise ValueError(f'{name} has an active workflow stage; finish or explicitly recover it first')
    if (target / '.coldsession-state/transaction.json').exists():
        raise ValueError('workflow transaction is incomplete; run plan recover before upgrading')
    for path in sorted((target / 'docs' / 'plans').glob('*.md')):
        if path.name.endswith('.log.md'):
            continue
        safe(target, path.relative_to(target).as_posix())
        phase = rt.read_phase(str(path))
        if not phase['meta'].get('phase'):
            continue
        if phase['meta'].get('active'):
            active.append(path.name + ': stage ' + phase['meta']['active'])
        for tid, task in phase['tasks'].items():
            if task['status'] == 'in_progress' or task.get('owner'):
                active.append(path.name + ': claim ' + tid)
        assignments = path.with_suffix('.assignments.json')
        if get_json(assignments, {}):
            active.append(path.name + ': assignment group')
        documents[path.relative_to(target).as_posix()] = phase
    if active:
        raise ValueError('active workers/stages/claims: ' + ', '.join(active) +
                         '. Settle them or explicitly recover stale claims; elapsed time is not evidence of abandonment.')
    return documents


def migrate_1_to_2(phase, rt):
    """Legacy files meant readable context. Never silently grant write access."""
    text = phase['text']
    notes = []
    if phase['malformed'] or phase['fmalformed'] or phase['fdupes']:
        raise ValueError('repair malformed tasks/findings before migration: ' + phase['path'])
    for tid, task in phase['tasks'].items():
        reads = list(dict.fromkeys(task['files'] + task.get('reads', [])))
        line = f"  {tid}: {{deps: [{', '.join(task['deps'])}], status: {task['status']}, files: [], reads: [{', '.join(reads)}]}}"
        text = re.sub(r'^  ' + tid + r':.*$', lambda _: line, text, flags=re.M)
        notes.append((tid, 'Legacy readable files do not establish writable scope', 'review exact writable files and update files; retain supporting context in reads'))
        try:
            rt.verification_checks(phase, tid)
        except ValueError:
            notes.append((tid, 'Verification cannot be migrated unambiguously', 'declare exact automated commands or named manual/visual actions'))
    if not rt.block(phase['blocks'], 'Constraints').strip():
        text = rt.append_to_block(text, 'Constraints', 'Unresolved: recover applicable durable product requirements before approval.')
        notes.append(('-', 'Durable constraints are not present', 'recover applicable constraints from existing product documents and review them'))
    number = max([rt.num(fid) for fid in phase['forder']] or [0])
    for tid, description, fix in notes:
        number += 1
        text = rt.append_to_block(text, 'Findings', f'F{number} | High | Migration | {tid} | open | {description} | {fix}')
    completed = [tid for tid, task in phase['tasks'].items() if task['status'] == 'done']
    text = rt.append_to_block(text, 'Migration',
        f"1.x -> 2.0.0: preserved task IDs, dependencies, findings, and completion history ({', '.join(completed) or 'none'}). "
        'No verification evidence was fabricated. Resolve scope and constraint findings, review and obtain human approval; '
        'then run plan verify for historical completions before advancing. The installer did not run project commands.')
    text = rt.set_metas(text, {'workflow-rev': '2.0.0', 'status': 'draft',
                             'rev': rt.intof(phase['meta'].get('rev'), 1) + 1,
                             'reconciliation': 'required'},
                        remove=('ready', 'ready-spec', 'reviewed', 'reviewed-spec', 'active', 'active-rev', 'active-spec'))
    return text.encode(), ['writable scope requires review; readiness revoked',
                           'historical done tasks require plan verify: ' + (', '.join(completed) or 'none')]


MIGRATIONS = {'1.3.0': migrate_1_to_2, '1.4.0': migrate_1_to_2, '1.5.0': migrate_1_to_2}


def snapshot(target, paths):
    return {relative: sha(read(safe(target, relative))) for relative in sorted(paths)}


def preview(args, target, rt):
    state = target / '.coldsession-state'
    journal = get_json(state / 'upgrade.json', {})
    if journal.get('status') not in (None, 'complete', 'rolled-back'):
        raise ValueError('incomplete upgrade; run installer --recover first')
    documents = inspect_workflow(target, rt)
    manifest = get_json(state / 'installed.json', {'files': {}})
    wanted = bundle(SOURCE, target, args.agent, args.windows)
    baseline = bundle(Path(args.baseline).resolve(), target, args.agent, args.windows) if args.baseline else {}
    changes, custom, conflicts = {}, [], []
    for relative in sorted(set(wanted) | set(manifest['files'])):
        current = read(safe(target, relative))
        replacement = wanted.get(relative)
        if current == replacement:
            continue
        known = manifest['files'].get(relative)
        if current is not None and sha(current) != known and current != baseline.get(relative):
            custom.append(relative)
            # Runtime and template conflicts require resolution before installing a
            # mixed contract. User commands stay preserved and are clearly reported.
            if relative.endswith(('/bin/plan', '/bin/plan.cmd')) or relative.startswith('templates/'):
                conflicts.append(relative)
            continue
        changes[relative] = replacement
    settings_path = safe(target, '.claude/settings.json')
    settings = get_json(settings_path, {})
    hooks = settings.get('hooks', {})
    managed_hooks = {event: [entry for entry in entries if owned_hook(entry)] for event, entries in hooks.items()}
    managed_hooks = {event: entries for event, entries in managed_hooks.items() if entries}
    hook_hash = sha(json.dumps(managed_hooks, sort_keys=True).encode())
    previous_hooks = manifest.get('claude_hooks')
    if previous_hooks and previous_hooks != hook_hash:
        conflicts.append('.claude/settings.json: managed hooks were modified; preserve/resolve the changes before preview')
    if not previous_hooks and managed_hooks:
        known_hooks = configured_hooks(args.windows)
        known_legacy = None
        if args.baseline:
            version_text = (Path(args.baseline) / 'bin/plan').read_text(encoding='utf-8-sig')
            if 'TOOL_VERSION = "2.5.0"' in version_text:
                suffix = 'cmd' if args.windows else 'sh'
                known_legacy = {}
                for event, kind, matcher in [('UserPromptSubmit', 'stage', None),
                                              ('PreToolUse', 'read', 'Read|Edit|Write'),
                                              ('PreToolUse', 'write', 'Edit|Write'),
                                              ('PostToolUse', 'lint', 'Edit|Write')]:
                    entry = {'hooks': [{'type': 'command', 'command': f'"$CLAUDE_PROJECT_DIR/.claude/hooks/cs-guard-{kind}.{suffix}"'}]}
                    if matcher:
                        entry['matcher'] = matcher
                    known_legacy.setdefault(event, []).append(entry)
        if managed_hooks not in (known_hooks, known_legacy):
            conflicts.append('.claude/settings.json: legacy hook ownership is uncertain; provide a matching known baseline or reconcile the hook entries')
    for event in list(hooks):
        hooks[event] = [entry for entry in hooks[event] if not owned_hook(entry)]
        if not hooks[event]:
            del hooks[event]
    if args.agent in ('claude', 'both'):
        for event, entries in configured_hooks(args.windows).items():
            hooks.setdefault(event, []).extend(entries)
    if hooks:
        settings['hooks'] = hooks
    else:
        settings.pop('hooks', None)
    if settings or settings_path.exists():
        changed = (json.dumps(settings, indent=2) + '\n').encode()
        if read(settings_path) != changed:
            changes['.claude/settings.json'] = changed
    config_path = safe(target, '.codex/config.toml')
    original_config = read(config_path)
    if manifest.get('codex_hooks') and manifest['codex_hooks'] != codex_hook_hash(original_config):
        conflicts.append('.codex/config.toml: managed hooks were modified; resolve before applying')
    elif not manifest.get('codex_hooks') and codex_hook_hash(original_config) not in (
            codex_hook_hash(None), codex_hook_hash(codex_config(None, True))):
        conflicts.append('.codex/config.toml: existing marked hook block has unknown ownership; reconcile it before applying')
    updated_config = original_config
    if args.agent in ('codex', 'both') or original_config is not None:
        updated_config = codex_config(original_config, args.agent in ('codex', 'both'))
        if updated_config != original_config:
            changes['.codex/config.toml'] = updated_config
    migrations = {}
    for relative, phase in documents.items():
        if phase['meta'].get('status') == 'closed':
            continue
        fmt = phase['meta'].get('workflow-rev')
        if fmt == rt.FORMAT_VERSION:
            continue  # semantic identity; preserve approval and fingerprints
        if fmt not in MIGRATIONS:
            conflicts.append(relative + ': unsupported/unknown format ' + str(fmt))
            continue
        changes[relative], migrations[relative] = MIGRATIONS[fmt](phase, rt)
    # Include all preflight inputs, including unchanged workflow and ownership.
    watched = set(wanted) | set(manifest['files']) | set(documents) | set(changes)
    watched.update(('PLAN.md', 'OBJECTIVE.md', '.claude/settings.json', '.codex/config.toml', '.coldsession-state/installed.json'))
    watched.update(path.relative_to(target).as_posix() for path in (target / 'docs' / 'plans').glob('*.assignments.json'))
    identifier = uuid.uuid4().hex
    record = {'id': identifier, 'release': rt.TOOL_VERSION, 'agent': args.agent, 'windows': args.windows,
              'inputs': snapshot(target, watched), 'documents': sorted(documents),
              'changes': {p: encode(data) for p, data in changes.items()},
              'desired': {p: sha(data) for p, data in wanted.items()},
              'claude_hooks': sha(json.dumps({event: [entry for entry in entries if owned_hook(entry)]
                                              for event, entries in hooks.items() if any(owned_hook(e) for e in entries)}, sort_keys=True).encode()),
              'codex_hooks': codex_hook_hash(updated_config),
              'customizations': custom, 'conflicts': conflicts, 'migrations': migrations}
    write_json(state / 'previews' / (identifier + '.json'), record)
    print(json.dumps({'preview': identifier, 'release': rt.TOOL_VERSION,
                      'changes': sorted(changes), 'preserved_customizations': custom,
                      'conflicts': conflicts, 'migrations': migrations,
                      'next': f'installer --apply {identifier}' if not conflicts else 'resolve conflicts or supply a known --baseline release, then preview again'}, indent=2))


def rollback(target, journal):
    # The backups and all metadata are retained after both success and rollback.
    for relative, original in journal['originals'].items():
        path = safe(target, relative)
        current = sha(read(path))
        if current not in (original['sha'], journal['after'].get(relative)):
            raise ValueError(f'rollback conflict at {relative}; preserve intervening changes and restore backup {journal["backup"]}')
    for relative, original in journal['originals'].items():
        path = safe(target, relative)
        if original['sha'] is None:
            if path.exists():
                path.unlink()
        else:
            backup = safe(target, journal['backup'] + '/' + relative)
            data = backup.read_bytes()
            if sha(data) != original['sha']:
                raise ValueError(f'backup checksum mismatch: {backup}')
            atomic_bytes(path, data)
            path.chmod(original['mode'])
    journal['status'] = 'rolled-back'
    write_json(target / '.coldsession-state' / 'upgrade.json', journal)


def apply(args, target, rt):
    state = target / '.coldsession-state'
    existing = get_json(state / 'upgrade.json', {})
    if existing.get('status') == 'complete' and existing.get('id') == args.apply:
        print('installation upgrade already succeeded; start a fresh session and run plan doctor')
        return
    if existing.get('status') not in (None, 'complete', 'rolled-back'):
        raise ValueError('upgrade incomplete; run installer --recover')
    if not re.fullmatch('[a-f0-9]{32}', args.apply):
        raise ValueError('--apply requires the ID from a saved preview')
    plan = get_json(state / 'previews' / (args.apply + '.json'), None)
    if not plan:
        raise ValueError('preview does not exist; run installer --preview first')
    if plan['conflicts']:
        raise ValueError('preview contains conflicts; resolve them and create a fresh preview')
    documents = inspect_workflow(target, rt)
    if sorted(documents) != plan['documents'] or snapshot(target, plan['inputs']) != plan['inputs']:
        raise ValueError('preflight inputs changed; create a fresh preview')
    backup = '.coldsession-state/backups/' + plan['id']
    changes = {p: decode(data) for p, data in plan['changes'].items()}
    # Ownership records track only actual bundled bytes, never user customizations.
    manifest = {'release': plan['release'], 'claude_hooks': plan['claude_hooks'], 'codex_hooks': plan['codex_hooks'],
                'files': {p: h for p, h in plan['desired'].items()
                if sha(changes.get(p, read(safe(target, p)))) == h}}
    changes['.coldsession-state/installed.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    originals = {}
    for relative, data in changes.items():
        path = safe(target, relative)
        original = read(path)
        originals[relative] = {'sha': sha(original), 'mode': path.stat().st_mode if path.exists() else None}
        if original is not None:
            atomic_bytes(safe(target, backup + '/' + relative), original)
        if data is not None:
            atomic_bytes(safe(target, backup + '/staged/' + relative), data)
    if sorted(inspect_workflow(target, rt)) != plan['documents'] or snapshot(target, plan['inputs']) != plan['inputs']:
        raise ValueError('preflight inputs changed while staging; no installation files replaced; create a fresh preview')
    journal = {'id': plan['id'], 'status': 'applying', 'backup': backup, 'originals': originals,
               'after': {p: sha(data) for p, data in changes.items()}}
    write_json(state / 'upgrade.json', journal)
    try:
        for relative, data in changes.items():
            path = safe(target, relative)
            if sha(read(path)) != originals[relative]['sha']:
                raise ValueError('file changed during application: ' + relative)
            if data is None:
                if path.exists():
                    path.unlink()
            else:
                atomic_bytes(path, data)
                if path.name == 'plan' or path.suffix == '.sh':
                    path.chmod(path.stat().st_mode | 0o111)
        if snapshot(target, journal['after']) != journal['after']:
            raise ValueError('installed file checksum validation failed')
        for relative in ('.claude/bin/plan', '.agents/coldsession/bin/plan'):
            path = target / relative
            if path.exists():
                compile(path.read_text(encoding='utf-8-sig'), str(path), 'exec')
        for relative in plan['migrations']:
            phase = rt.read_phase(str(safe(target, relative)))
            if phase['malformed'] or phase['fmalformed'] or phase['fdupes'] or phase['meta'].get('workflow-rev') != rt.FORMAT_VERSION:
                raise ValueError('migrated document structure invalid: ' + relative)
        if (target / '.codex/config.toml').exists():
            try:
                import tomllib
            except ImportError:
                pass  # Python 3.9/3.10: doctor reports parser availability as a gap.
            else:
                tomllib.loads((target / '.codex/config.toml').read_text(encoding='utf-8-sig'))
        journal['status'] = 'complete'
        write_json(state / 'upgrade.json', journal)
    except BaseException:
        try:
            rollback(target, journal)
        except (OSError, ValueError) as exc:
            print(f'rollback incomplete: {exc}; run installer --recover; backups: {backup}', file=sys.stderr)
        raise
    print(json.dumps({'installation': 'succeeded', 'release': plan['release'], 'backup': backup,
                      'preserved_customizations': plan['customizations'], 'migrations': plan['migrations'],
                      'active_phase_ready': False if plan['migrations'] else 'run plan doctor to determine',
                      'next': 'Start a fresh agent session, run plan doctor, resolve migration findings through review and human approval, then plan verify historical completed tasks.'}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', nargs='?', default='.')
    parser.add_argument('--agent', choices=('claude', 'codex', 'both'), default='both')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--preview', action='store_true')
    group.add_argument('--apply')
    group.add_argument('--recover', action='store_true')
    parser.add_argument('--baseline', help='known release checkout for legacy ownership comparison')
    parser.add_argument('--windows', action='store_true', default=os.name == 'nt')
    parser.add_argument('--keep', action='store_true', help='accepted for compatibility; source checkout is always retained')
    args = parser.parse_args()
    if sys.version_info < (3, 9):
        raise ValueError('Python 3.9 or newer is required')
    target = Path(args.target).resolve()
    if target == SOURCE and not args.recover:
        raise ValueError('refusing to install into the workflow repository itself')
    if not target.is_dir():
        raise ValueError('target directory does not exist')
    if args.recover:
        journal = get_json(target / '.coldsession-state' / 'upgrade.json', {})
        if journal.get('status') in (None, 'complete', 'rolled-back'):
            print('no incomplete installation to recover')
            return
        # Recovery is also available from the backed-up installed helper.
        rt = runtime()
    else:
        rt = runtime()
    rt.ROOT = str(target)
    rt.INDEX = str(target / 'PLAN.md')
    rt.AGENTS_PATH = str(target / 'AGENTS.md')
    lock = rt._lock_acquire(rt.INDEX)
    try:
        if args.recover:
            rollback(target, journal)
            print('installation restored; backups retained; create a fresh preview')
        elif args.apply:
            apply(args, target, rt)
        else:
            preview(args, target, rt)
    finally:
        rt._lock_release(lock)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as exc:
        print('error: ' + str(exc), file=sys.stderr)
        sys.exit(1)
