from __future__ import annotations

import contextlib
import importlib
import importlib.abc
import importlib.machinery
import json
import sys
import typing

from datamodel_code_generator.parser.base import ParseConfig, Parser, Result


def animal_home_schema():
    return {
        '$schema': 'http://json-schema.org/draft-07/schema#',
        'title': 'AnimalHome',
        'type': 'object',
        'properties': {
            'pets': {
                'type': 'array',
                'items': {'$ref': '#/definitions/Animal'},
            },
        },
        'required': ['pets'],
        'definitions': {
            'Animal': {
                'oneOf': [
                    {'$ref': '#/definitions/Cat'},
                    {'$ref': '#/definitions/Dog'},
                ],
            },
            'Cat': {
                'type': 'object',
                'properties': {'meow': {'type': 'boolean'}},
                'required': ['meow'],
            },
            'Dog': {
                'type': 'object',
                'properties': {'bark': {'type': 'boolean'}},
                'required': ['bark'],
            },
        },
    }


def json_schema_parser_class():
    parser_module = importlib.import_module('datamodel_code_generator.parser.jsonschema')
    parser_classes = [
        value
        for value in vars(parser_module).values()
        if isinstance(value, type) and issubclass(value, Parser) and value is not Parser
    ]
    assert len(parser_classes) == 1
    return parser_classes[0]


def single_module_split_mode():
    hint = typing.get_type_hints(Parser.parse)['module_split_mode']
    for candidate in typing.get_args(hint) or (hint,):
        try:
            return candidate('single')
        except (TypeError, ValueError):
            pass
    raise AssertionError('Parser.parse does not expose a single module split mode')


def generate_split_models():
    parser = json_schema_parser_class()(
        json.dumps(animal_home_schema()),
        collapse_root_models=True,
        use_exact_imports=True,
        formatters=['builtin'],
    )
    assert isinstance(parser, Parser)

    split_mode = single_module_split_mode()
    parse_options = ParseConfig(
        with_import=True,
        use_deferred_annotations=True,
        code_formatter=None,
        module_split_mode=split_mode,
        all_exports_scope=None,
        all_exports_collision_strategy=None,
    )
    assert parse_options.module_split_mode == split_mode

    results = Parser.parse(
        parser,
        with_import=parse_options.with_import,
        format_=True,
        module_split_mode=parse_options.module_split_mode,
    )

    assert isinstance(results, dict)
    assert results
    assert all(isinstance(result, Result) for result in results.values())
    return results


class GeneratedModuleLoader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, sources, packages):
        self.sources = sources
        self.packages = packages

    def find_spec(self, fullname, path=None, target=None):
        if fullname not in self.sources and fullname not in self.packages:
            return None

        is_package = fullname in self.packages
        spec = importlib.machinery.ModuleSpec(fullname, self, is_package=is_package)
        if is_package:
            spec.submodule_search_locations = []
        return spec

    def exec_module(self, module):
        module_name = module.__spec__.name
        if module_name in self.packages:
            module.__path__ = []
        code = self.sources.get(module_name, '')
        exec(compile(code, f'<generated {module_name}>', 'exec'), vars(module))


def module_name_for_key(package_name, key):
    parts = list(key)
    if parts[-1] == '__init__.py':
        module_parts = parts[:-1]
    else:
        leaf = parts[-1]
        if leaf.endswith('.py'):
            leaf = leaf[:-3]
        module_parts = [*parts[:-1], leaf]

    return '.'.join([package_name, *module_parts]) if module_parts else package_name


def sources_and_packages(package_name, results):
    sources = {}
    packages = {package_name}

    for key, result in results.items():
        module_name = module_name_for_key(package_name, key)
        sources[module_name] = result.body
        if key[-1] == '__init__.py':
            packages.add(module_name)

    for module_name in list(sources):
        segments = module_name.split('.')
        for index in range(1, len(segments)):
            packages.add('.'.join(segments[:index]))

    return sources, packages


@contextlib.contextmanager
def installed_generated_modules(results):
    package_name = 'generated_dcg_contract_models'
    for module_name in list(sys.modules):
        if module_name == package_name or module_name.startswith(package_name + '.'):
            sys.modules.pop(module_name)

    sources, packages = sources_and_packages(package_name, results)
    loader = GeneratedModuleLoader(sources, packages)
    sys.meta_path.insert(0, loader)
    try:
        yield package_name
    finally:
        if loader in sys.meta_path:
            sys.meta_path.remove(loader)
        for module_name in list(sys.modules):
            if module_name == package_name or module_name.startswith(package_name + '.'):
                sys.modules.pop(module_name)


def test_collapsed_named_oneof_array_items_import_and_validate_in_split_modules():
    results = generate_split_models()

    with installed_generated_modules(results) as package_name:
        animal_home_module = importlib.import_module(f'{package_name}.animal_home')
        AnimalHome = animal_home_module.AnimalHome

        dog_home = AnimalHome.model_validate({'pets': [{'bark': True}]})

        cat_module = importlib.import_module(f'{package_name}.cat')
        dog_module = importlib.import_module(f'{package_name}.dog')
        Cat = cat_module.Cat
        Dog = dog_module.Dog

        assert cat_module is not animal_home_module
        assert dog_module is not animal_home_module
        assert getattr(animal_home_module, 'Cat') is Cat
        assert getattr(animal_home_module, 'Dog') is Dog
        assert isinstance(dog_home, AnimalHome)
        assert isinstance(dog_home.pets[0], Dog)
        assert dog_home.pets[0].bark is True

        cat_home = AnimalHome.model_validate({'pets': [{'meow': True}]})
        assert isinstance(cat_home, AnimalHome)
        assert isinstance(cat_home.pets[0], Cat)
        assert cat_home.pets[0].meow is True
