"""Validate suggestions, never apply them to the source or a file."""
from persian_protection import overlaps


def validate(text, candidate, spans):
    start, end = candidate['start'], candidate['end']
    if not 0 <= start < end <= len(text) or text[start:end] != candidate['before']:
        return 'invalid_source_span'
    if overlaps(start, end, spans):
        return 'protected_or_ambiguous_span'
    before, after = candidate['before'], candidate['replacement']
    # This phase can only replace ASCII spaces, not letters, punctuation or digits.
    if before.replace(' ', '') != after.replace(' ', '').replace('\u200c', ''):
        return 'non_mechanical_change'
    if candidate['rule_id'] == 'fa-extra-inline-space':
        if before.strip(' ') or after != ' ':
            return 'invalid_space_change'
    elif candidate['rule_id'] == 'fa-limited-zwnj':
        if before.count(' ') != 1 or after != before.replace(' ', '\u200c'):
            return 'invalid_zwnj_change'
    else:
        return 'unknown_rule'
    return None


def mark_conflicts(suggestions):
    for item in suggestions:
        item['conflicts_with'] = [other['id'] for other in suggestions
            if other is not item and item['start'] < other['end'] and item['end'] > other['start']]


def validate_selection(suggestions, selected_ids):
    """Future callers must validate an explicit selection; no application API."""
    if len(set(selected_ids)) != len(selected_ids):
        raise ValueError('duplicate selection')
    by_id = {s['id']: s for s in suggestions}
    if any(key not in by_id for key in selected_ids):
        raise ValueError('unknown suggestion')
    selected = [by_id[key] for key in selected_ids]
    for index, item in enumerate(selected):
        if any(item['start'] < other['end'] and item['end'] > other['start']
               for other in selected[index + 1:]):
            raise ValueError('overlapping suggestions cannot be selected together')
    return True
