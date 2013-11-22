#!/usr/bin/env python

import re
from inspect import getdoc
from urlparse import urlparse


def parse_doc(lines):
    """Create a data structure from a Sphinx-style docstring"""
    doc = {}
    for line in lines:
        m = re.match(r'^(:\w+) ([^:]*)(?:: ?)?(.*)$', line)
        if m is None:
            continue
        key, name, value = m.groups()
        if key not in doc:
            doc[key] = []
        doc[key].append({
            'name': name,
            'value': value
        })
    return doc


def parameterize(path):
    """Parmeterize path using Swagger-style for parameters.
    For example the Flask route /api/v1/users/<int:user_id> is translated to
    /api/v1/users/{user_id}
    """
    def fparam(p):
        if p.startswith('<') and p.endswith('>'):
            _, _, parameter = p.strip('<>').rpartition(':')
            return '{%s}' % (parameter,)
        return p
    return '/'.join(map(fparam, path.split('/')))


def lremove(s, prefix):
    """Remove prefix from string s"""
    return s[len(prefix):] if s.startswith(prefix) else s


class APIEndpoint(object):

    def __init__(self, app, rule, prefix):
        self.app = app
        self.rule = rule
        # Keep leading / for endpoint paths
        if prefix.endswith('/'):
            prefix = prefix[:-1]
        self.path = parameterize(lremove(str(rule), prefix))

    def _filter_methods(self, methods=('GET', 'POST', 'PUT', 'DELETE')):
        """Filter methods to generate endpoints for"""
        return self.rule.methods.intersection(methods)

    def _make_parameters(self, lines):
        """Make parameters from :param lines"""
        doc = parse_doc(lines)

        def _get_value(key, name, default=None):
            for p in doc.get(key, []):
                if p.get('name') == name:
                    return p.get('value', default)
            return default

        def make_parameter(param_type, name, value):
            required = (param['name'] for param in doc.get(':required', []))
            return {
                'paramType': _get_value(':paramtype', name, param_type),
                'name': name,
                'description': value,
                'dataType': _get_value(':type', name, 'string'),
                'defaultValue': _get_value(':default', name, ''),
                'required': param_type == 'path' or name in required
            }

        parameters = []

        for query in doc.get(':param', []):
            name = query.get('name')
            param_type = 'path' if name in self.rule.arguments else 'query'
            parameters.append(make_parameter(param_type, name,
                                             query.get('value', '')))
        return parameters

    def _make_status_codes(self, lines):
        """Make status code from :statuscode lines"""
        doc = parse_doc(lines)
        status_codes = []
        for status_code in doc.get(':statuscode', []):
            status_codes.append({
                'code': status_code.get('name'),
                'message': status_code.get('value', '')
            })
        return status_codes

    def _make_summary(self, lines):
        """Make summary from lines that are not directives"""
        return '\n'.join((line for line in lines
                         if not line.startswith(':'))).strip()

    def _make_notes(self, lines):
        notes = (param['name'] or param['value']
                 for param in parse_doc(lines).get(':notes', []))
        return ' '.join(notes)

    def _make_operation(self, method):
        """Make operation based on the given method"""
        view_function = self.app.view_functions.get(self.rule.endpoint)

        operation = {
            'method': method,
            'nickname': self.rule.endpoint,
            'parameters': [],
            'summary': '',
            'responseMessages': []
        }

        lines = [line for line in (getdoc(view_function) or '').splitlines()]
        operation['summary'] = self._make_summary(lines)
        notes = self._make_notes(lines)
        if len(notes) > 0:
            operation['notes'] = notes
        operation['parameters'] = self._make_parameters(lines)
        operation['responseMessages'] = self._make_status_codes(lines)
        return operation

    def make_operations(self):
        return [self._make_operation(m) for m in self._filter_methods()]


class APIBuilder(object):

    def __init__(self, app, prefix):
        self.app = app
        self.prefix = prefix

    def _find_endpoints(self):
        """Find and create API endpoints for routes that match prefix"""
        return [APIEndpoint(self.app, rule, self.prefix)
                for rule in self.app.url_map.iter_rules()
                if str(rule).startswith(self.prefix)]

    def make_apis(self, description=None):
        """Make all APIs"""
        return [dict(path=endpoint.path, description=description,
                operations=endpoint.make_operations())
                for endpoint in self._find_endpoints()]


def make_resources(app, base_path, resource_path=None, description=None,
                   api_version='1', swagger_version='1.2'):
    """Make Swagger resources from app, using base_path as the base path for
    the API. The parameter resource_path is used to filter which routes to
    generate resources for. If resource_path is not set, the path portion of
    base_path is used.
    """
    resource_path = resource_path or urlparse(base_path).path
    builder = APIBuilder(app, resource_path)
    return {
        'apiVersion': api_version,
        'swaggerVersion': swagger_version,
        'basePath': base_path,
        'resourcePath': resource_path,
        'apis': builder.make_apis(description)
    }
