"""Keep internal character assets and unused entries out of the public catalogue."""

EXCLUDED_SECTIONS = {'Bodies', 'Eyes', 'Faces', 'Coats', 'Manes & tails', 'Test objects', 'Services'}


def exclusion_reason(entry):
    if entry['category'] == 'Game Records' or entry['section'] in EXCLUDED_SECTIONS:
        return 'Internal assets'
    if 'ambassador' in (str(entry['title']) + ' ' + str(entry['internalName'])).lower():
        return 'Ambassador items'
    if entry.get('unlisted'):
        return 'Unlisted entries'
    if entry['section'] == 'Hairstyles' and (str(entry['internalName']) == 'Hair_23' or str(entry['internalName']).startswith('Hair_23_')):
        return 'Excluded hairstyle'
    return None
