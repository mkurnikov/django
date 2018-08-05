import inspect
import os
import shutil
from contextlib import contextmanager

from django_stubs_root.generator import monkeytype_config
from monkeytype import typing
from monkeytype.postgres.config import PostgresConfig
from monkeytype.rewriters.transformers import simplify_types, simplify_int_float, FindAcceptableCommonBase, \
    remove_empty_container, DepthFirstTypeTraverser, TwoElementUnionRewriter, SimplifyGenerics, MroSimplifier, SimplifyTuples
from monkeytype.typing import ChainedRewriter, RewriteLargeUnion, TypeRewriter


ACCEPTABLE_MODULES = ['django.']


def get_closest_acceptable_class_from_mro(cls):
    try:
        inspect.getmro(cls)
    except Exception:
        return None

    for base in inspect.getmro(cls):
        if not base.__module__.split('.')[0] not in monkeytype_config.ALL_TEST_APPS_SET:
            return base

    return None


class ClosestBaseClassRewriter(TypeRewriter):
    def generic_rewrite(self, typ: type):
        return get_closest_acceptable_class_from_mro(typ)


class DjangoStubsConfig(PostgresConfig):
    @contextmanager
    def cli_context(self, command: str):
        import os
        import django

        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_sqlite')

        django.setup()
        yield

    def sample_rate(self):
        return 2

    def type_rewriter(self):
        two_element_transformers = [simplify_types,
                                    simplify_int_float,
                                    FindAcceptableCommonBase(allowed_bases_prefixes=['django', 'unittest']),
                                    remove_empty_container]
        traverser = DepthFirstTypeTraverser(
            num_of_passes=3,
            union_rewriter=TwoElementUnionRewriter(
                two_element_transformers=[
                    *two_element_transformers,
                    SimplifyGenerics(two_element_transformers=two_element_transformers),
                    SimplifyTuples(two_element_transformers=[*two_element_transformers,
                                                             SimplifyGenerics(two_element_transformers=two_element_transformers)])
                ]
            ))
        return ChainedRewriter(rewriters=[
            MroSimplifier(filtered_modules=monkeytype_config.ALL_TEST_APPS_SET),
            traverser,
            typing.RewriteConfigDict(),
            RewriteLargeUnion(max_union_len=5)
        ])


CONFIG = DjangoStubsConfig(skip_private_methods=True,
                           skip_private_properties=True,
                           relevant_modules=['django'],
                           connection_data={
                               'user': 'postgres',
                               'password': 'postgres',
                               'dbname': 'traces',
                               'host': '0.0.0.0'
                           }, log_queries=False)

if __name__ == '__main__':
    import django

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_sqlite')
    django.setup()

    standard_apps = [
        'django.contrib.auth',
        'django.contrib.admin',
        'django.contrib.contenttypes',
        'django.contrib.sites',
        'django.contrib.sessions',
        'django.contrib.redirects',
        'django.contrib.flatpages'
    ]

    module_names = CONFIG.trace_store().list_modules(prefix='django')
    # filtered_module_names = []
    # for module_name in module_names:
    #     if module_name.startswith('django'):
    #         filtered_module_names.append(module_name)
    from django.test import override_settings

    for module in module_names:
    # for module in ['django.db.models.sql.compiler']:
        with override_settings(INSTALLED_APPS=standard_apps + monkeytype_config.TEST_APPS_WITH_MODELS):
            path_to_stub_file = monkeytype_config.generate_stub(module, config=CONFIG,
                                                                output_dir=monkeytype_config.STUBS_ROOT.parent,
                                                                suppress_errors=True)
            print('path_to_stub_file', path_to_stub_file)

            from path import Path

            required_stub_path = Path(str(path_to_stub_file).replace('django/', 'django-stubs/'))
            required_stub_path.parent.makedirs_p()

            shutil.copy(path_to_stub_file, required_stub_path)
