import os

import django


def set_parents(queryset):
    from relatedhow.viewer.models import Taxon
    count = 0
    taxons = {t.wikidata_id: t for t in Taxon.objects.all()}
    for t in queryset:
        try:
            if count % 1000 == 0:
                print(count)
            count += 1

            parents = t.parents_string.split('\t')

            if not t.parents_string:
                print('WARNING: orphan taxon', t)
                continue

            if parents[0] == '':
                print('ERROR', t)
            assert parents[0] != ''
            try:
                t.parent = taxons[parents[0]]
            except KeyError:
                print('WARNING: references unknown name', parents[0])
            t.save()
            # print(t, parents)
        except Taxon.DoesNotExist:
            pass


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relatedhow.settings")
    django.setup()

    from relatedhow.viewer.models import Taxon, setup
    setup()

    taxons = Taxon.objects.filter(parent=None).exclude(name='Biota')
    set_parents(taxons.exclude(name__contains=' '))  # take the more important taxons first
    set_parents(taxons)


if __name__ == '__main__':
    main()
