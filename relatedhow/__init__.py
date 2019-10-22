from collections import defaultdict
from datetime import datetime
from itertools import groupby
from time import sleep
from urllib.parse import urlencode

import os
import requests
from os.path import exists
from tqdm import tqdm

from subprocess import check_output

from tri.struct import Struct

biota_pk = 2382443


class FooException(Exception):
    pass


def line_count(filename):
    return int(check_output(["/usr/bin/wc", "-l", filename]).split()[0])


def wikidata_id_as_int(s):
    prefix = '<http://www.wikidata.org/entity/Q'
    suffix = '>'
    if s.startswith(prefix):
        assert s.endswith(suffix), repr(s)
        return int(s[len(prefix):-len(suffix)])
    elif s.startswith('Q'):
        return int(s[1:])
    else:
        assert False, f'Unsupported format for wikidata_as_int: "{s}"'


def fix_text(s):
    return s.encode('ascii', errors='ignore').decode('ascii')


def read_csv(filename):
    # I know the format here, so I don't need to use the csv module. This gives me a bit higher performance
    print('load %s' % filename)
    num_lines = line_count(filename)
    with open(filename, newline='') as csvfile:
        csvfile.readline()  # skip header line
        for row in tqdm(csvfile.readlines(), total=num_lines):
            row = row.split('\t')
            yield wikidata_id_as_int(row[0]), row[1].strip()


class FakeTaxon(Struct):
    def __hash__(self):
        return hash(self.pk)


class TaxonsDict(defaultdict):
    def __missing__(self, key):
        from relatedhow.viewer.models import Taxon
        # t = Taxon(pk=key)
        t = FakeTaxon(pk=key, name=None, parent=None, rank=None)
        t._children = set()
        t._parents = set()
        self[key] = t
        return t


def create_taxon_from_struct(x):
    from relatedhow.viewer.models import Taxon
    kw = {k: v for k, v in x.items() if not k.startswith('_')}
    p = kw.pop('parent')
    if p:
        kw['parent_id'] = p.pk
    return Taxon(**kw)


def import_wikidata():

    # print('Clearing database')
    # from django.db import connection
    # cursor = connection.cursor()
    # cursor.execute('TRUNCATE TABLE `viewer_taxon`')

    initial_taxons = [
        FakeTaxon(rank=None, parent=None, pk=2382443, name='Biota', english_name='Life'),
        FakeTaxon(rank=None, parent=None, pk=23012932, name='Ichnofossils'),
        FakeTaxon(rank=None, parent=None, pk=24150684, name='Agmata'),
        FakeTaxon(rank=None, parent=None, pk=5381701, name='Eohostimella'),
        FakeTaxon(rank=None, parent=None, pk=23832652, name='Anucleobionta'),
        FakeTaxon(rank=None, parent=None, pk=21078601, name='Yelovichnus'),
        FakeTaxon(rank=None, parent=None, pk=35107213, name='Rhizopodea'),
        FakeTaxon(rank=None, parent=None, pk=46987746, name='Pan-Angiospermae'),
        FakeTaxon(rank=None, parent=None, pk=14868864, name='Enoplotrupes'),
        FakeTaxon(rank=None, parent=None, pk=17290456, name='Erythrophyllum'),
        FakeTaxon(rank=None, parent=None, pk=14868878, name='Chelotrupes'),
    ]

    taxon_by_pk = TaxonsDict()
    for t in initial_taxons:
        taxon_by_pk[t.pk] = t
        t._children = set()
        t._parents = set()

    fix_obsolete_pks = {}
    for pk1, v in read_csv('synonyms.csv'):
        pk2 = wikidata_id_as_int(v)
        use_pk, obsolete_pk = sorted([pk1, pk2])
        fix_obsolete_pks[obsolete_pk] = use_pk

    pks_of_taxons_with_ambiguous_parents = set()

    for pk, v in read_csv('names.csv'):
        name = fix_text(v)
        if name:
            taxon_by_pk[pk].english_name = clean_name(name)

    ## getting labels no longer work
    # for pk, v in read_csv('labels.csv'):
    #     name = fix_text(v)
    #     if name:
    #         taxon_by_pk[pk].english_name = clean_name(name)

    for pk, v in read_csv('taxons.csv'):
        name = fix_text(v)
        pk = fix_obsolete_pks.get(pk, pk)
        if name:
            taxon_by_pk[pk].name = name

    for pk, v in read_csv('images.csv'):
        taxon_by_pk[pk].image = v[1:-1]

    def backload_missing_data(filename, query, process_item):
        if exists(filename):
            for pk, v in read_csv(filename):
                process_item(pk, v)
        else:
            with open(filename, 'w') as output:
                output.write('pk\tvalue\n')
                for t in tqdm([x for x in taxon_by_pk.values() if x.name is None]):
                    r = download_contents(f'{t.pk}', query % t.pk)
                    lines = r.strip().split('\n')
                    if len(lines) != 2:
                        continue
                    value = lines[-1]
                    process_item(t.pk, value)
                    output.write(f'Q{t.pk}\t{value}\n')
                    output.flush()

    print('loading missing names')

    def set_name(pk, value):
        taxon_by_pk[pk].name = clean_name(value)

    backload_missing_data(
        filename='missing_names.csv',
        query="""
            SELECT ?itemLabel WHERE {
              VALUES ?item { wd:Q%s }
              ?item p:P171 ?p171stm .
              ?p171stm ps:P171 ?parenttaxon;
                       wikibase:rank ?rank .
              SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
            }
            ORDER BY DESC(?rank)
            """,
        process_item=set_name),

    # def check_loop(pk, visited_pks=None):
    #     if visited_pks is None:
    #         visited_pks = []
    #     if pk in visited_pks:
    #         print('loop!', visited_pks, pk)
    #         exit(1)
    #     for p in taxon_by_pk[pk]._parents:
    #         check_loop(p.pk, visited_pks=visited_pks)

    for pk, v in read_csv('parent_taxons.csv'):
        if '_:' in v:
            continue
        pk = fix_obsolete_pks.get(pk, pk)
        parent_pk = wikidata_id_as_int(v)
        parent_pk = fix_obsolete_pks.get(parent_pk, parent_pk)
        parent_taxon = taxon_by_pk[parent_pk]
        taxon = taxon_by_pk[pk]
        taxon._parents.add(parent_taxon)
        # check_loop(pk)

    print('loading parent data')
    # TODO: load from csv if available
    # with open('missing_parent_taxons.csv', 'w') as output:
    #     output.write('pk\tvalue\n')
    #     for t in tqdm([x for x in taxon_by_pk.values() if x.name is None]):
    #         r = download_contents(f'{t.pk}', """
    #         SELECT ?parenttaxon WHERE {
    #           VALUES ?item { wd:%s }
    #           ?item p:P171 ?p171stm .
    #           ?p171stm ps:P171 ?parenttaxon;
    #                    wikibase:rank ?rank .
    #         }
    #         ORDER BY DESC(?rank)
    #         """ % t.pk)
    #         parent_pk = wikidata_id_as_int(r.strip().split('\n')[-1])
    #         parent_pk = fix_obsolete_pks.get(parent_pk, parent_pk)
    #         parent_taxon = taxon_by_pk[parent_pk]
    #         taxon = taxon_by_pk[pk]
    #         taxon._parents.add(parent_taxon)
    #         output.write(f'{t.pk}\t{parent_pk}\n')
    #         # t.name = clean_name(r.strip().split('\n')[-1])
    #         sleep(0.1)

    def set_parent(pk, value):
        parent_pk = wikidata_id_as_int(value)
        parent_pk = fix_obsolete_pks.get(parent_pk, parent_pk)
        parent_taxon = taxon_by_pk[parent_pk]
        taxon = taxon_by_pk[pk]
        taxon._parents.add(parent_taxon)

    backload_missing_data(
        filename='missing_parent_taxons.csv',
        query="""
            SELECT ?parenttaxon WHERE {
              VALUES ?item { wd:Q%s }
              ?item p:P171 ?p171stm .
              ?p171stm ps:P171 ?parenttaxon;
                       wikibase:rank ?rank .
            }
            ORDER BY DESC(?rank)
            """,
        process_item=set_parent),

    print('Set non-ambiguous parents')
    top_level = set()
    for taxon in tqdm(taxon_by_pk.values()):
        if len(taxon._parents) == 1:
            taxon.parent = list(taxon._parents)[0]
        elif len(taxon._parents) > 1:
            pks_of_taxons_with_ambiguous_parents.add(taxon.pk)
        elif len(taxon._parents) == 0:
            top_level.add(taxon.pk)
        else:
            assert False

    print('fix ambiguous parents, until stable (%s)' % len(pks_of_taxons_with_ambiguous_parents))

    def fix_ambiguous_parents():
        count = 0
        for pk in tqdm(pks_of_taxons_with_ambiguous_parents.copy()):
            taxon = taxon_by_pk[pk]

            def get_all_parents_or_raise(t):
                result = []
                orig = t
                while t._parents:
                    if t.parent:
                        result.append(t.parent)
                    else:
                        raise FooException('Still ambiguous')
                    t = t.parent
                # handle cases where tree is not in biota
                if result and result[-1].pk != biota_pk:
                    print('\t%s is not related to biota' % orig.pk)
                    return []
                return result

            try:
                taxon.parent = sorted(taxon._parents, key=lambda x: len(get_all_parents_or_raise(x)), reverse=True)[0]
                taxon._parents = {taxon.parent}
                pks_of_taxons_with_ambiguous_parents.remove(pk)
                count += 1
            except FooException:
                continue

        print('\t%s fixed, %s left' % (count, len(pks_of_taxons_with_ambiguous_parents)))
        return count

    while fix_ambiguous_parents():
        continue

    print('set children')
    for taxon in tqdm(taxon_by_pk.values()):
        if taxon.parent:
            taxon.parent._children.add(taxon)

    print('set rank, and number of children (direct and indirect)')

    def get_count(t, rank):
        t.rank = rank
        t.number_of_direct_children = len(t._children)
        t.number_of_direct_and_indirect_children = sum(get_count(c, rank=rank + 1) for c in t._children) + t.number_of_direct_children
        return t.number_of_direct_and_indirect_children

    biota = taxon_by_pk[biota_pk]
    get_count(biota, rank=0)

    print('remove non-biota trees')
    # TODO: some trees found here were just incorrect leaves, lots of this should be fixable!
    non_biota_tree_roots = [t for t in taxon_by_pk.values() if t.pk != biota_pk and t.parent is None]

    def remove_tree(t):
        for child in t._children:
            remove_tree(child)
        del taxon_by_pk[t.pk]

    for t in non_biota_tree_roots:
        print('\t', t.name, t.pk)
        remove_tree(t)

    print('...inserting %s clades' % len(taxon_by_pk))
    from relatedhow.viewer.models import Taxon
    for k, group in groupby(sorted(taxon_by_pk.values(), key=lambda x: x.rank or 0), key=lambda x: x.rank or 0):
        group = [create_taxon_from_struct(x) for x in group]
        start = datetime.now()
        print('inserting rank %s (%s items)' % (k, len(group)), end='', flush=True)
        Taxon.objects.bulk_create(group, batch_size=100)
        print(' .. took %s' % (datetime.now() - start))

    # TODO: load images.csv


def clean_name(name):
    name = name.strip()
    if name.endswith('@en'):
        if name.startswith('"'):
            assert name.endswith('"@en')
            name = name[1:-len('"@en')]
        else:
            assert name.endswith('@en')
            name = name[:-len('@en')]
    return name.replace('\t', ' ')


def download(select, filename):
    if exists(filename):
        print('Using existing file %s' % filename)
        return

    print('Downloading %s' % filename)
    result = download_contents(filename, select)

    with open(filename, 'w') as f:
        f.write(result)


def download_contents(filename, select):
    result = requests.get('https://query.wikidata.org/sparql?%s' % urlencode([('query', select)]), headers={'Accept': 'text/tab-separated-values', 'User-agent': 'relatedhow/0.0 (https://github.com/boxed/related_how; boxed@killingar.net) data extraction bot'}).text
    if '\tat ' in result:
        print('Error with download of %s (1), got %sMB' % (filename, len(result) / (1024 * 10424)), result[-500:])
        exit(1)
    if '</html>' in result:
        print('Error with download of %s (2), got %sMB' % (filename, len(result) / (1024 * 10424)), result[-500:])
        exit(1)
    sleep(0.1)
    return result


def import_and_process():
    download(
        filename='taxons.csv',
        select="""
            SELECT ?item ?taxonname WHERE {
              ?item wdt:P225 ?taxonname.
              FILTER (!isBLANK(?taxonname)).
            }
            """,
    )

    download(
        filename='synonyms.csv',
        select="""
            SELECT ?item ?synonym WHERE {
                  ?item wdt:P1420 ?synonym.
                }
            """
    )

    download(
        filename='parent_taxons.csv',
        select="""
            SELECT ?item ?parenttaxon WHERE {
              ?item p:P171 ?p171stm .
              ?p171stm ps:P171 ?parenttaxon .
            }
            """
    )

    download(
        filename='names.csv',
        select="""
            SELECT DISTINCT ?item ?label WHERE {
              ?item wdt:P31 wd:Q16521.
              ?item wdt:P1843 ?label. 
              FILTER (langMatches( lang(?label), "EN" ) )
            }
            """,
    )

    # # well this doesn't seem to work anymore :(
    # download(
    #     filename='labels.csv',
    #     select="""
    #         SELECT DISTINCT ?item ?itemLabel WHERE {
    #           ?item wdt:P31 wd:Q16521.
    #           ?item wdt:P225 ?taxonname.
    #           FILTER isBLANK(?taxonname) .
    #           SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE]". }
    #         }
    #         """,
    # )

    download(
        filename='images.csv',
        select="""
            SELECT DISTINCT ?item ?image WHERE {
              ?item wdt:P31 wd:Q16521.
              ?item wdt:P18 ?image.
            }
        """
    )

    import_wikidata()
    # fast exit because we're using a lot of memory and cleaning that is silly
    os._exit(0)
