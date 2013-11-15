#!/usr/bin/env python

import unittest
from inspect import getdoc

from flask import Flask

from flask_swagger import (APIBuilder, APIEndpoint, lremove, make_resources,
                           parameterize, parse_doc)


class SwaggerGenTestCase(unittest.TestCase):

    def setUp(self):
        def spam():
            """
            Retrieve an user

            :notes Implementation notes
            :notes More implementation notes
            :param user_id: User ID
            :param username: Lookup by username
            :type user_id: int
            :type username: string
            :required user_id
            :statuscode 200: Successful response
            :statuscode 404: No such user
            """
        self.doc = getdoc(spam).splitlines()

    def test_parse_doc(self):
        self.assertEqual({}, parse_doc([]))
        self.assertEqual({}, parse_doc(['spam', 'eggs']))
        self.assertEqual({':param': [{'name': 'ham',
                                      'value': 'eggs and spam'}]},
                         parse_doc([':param ham: eggs and spam']))
        self.assertEqual({':param': ['ham']},
                         parse_doc([':param ham:']))

        parameters = parse_doc(self.doc)
        self.assertEqual([{'name': 'user_id', 'value': 'User ID'},
                          {'name': 'username', 'value': 'Lookup by username'}],
                         parameters[':param'])
        self.assertEqual(['user_id'], parameters[':required'])
        self.assertEqual([{'name': '200', 'value': 'Successful response'},
                          {'name': '404', 'value': 'No such user'}],
                         parameters[':statuscode'])
        self.assertEqual(['Implementation notes', 'More implementation notes'],
                         parameters[':notes'])

    def test_parameterize(self):
        self.assertEqual('/api/users', parameterize('/api/users'))
        self.assertEqual('/api/users/{user_id}',
                         parameterize('/api/users/<user_id>'))
        self.assertEqual('/api/users/{user_id}',
                         parameterize('/api/users/<int:user_id>'))

    def test_lremove(self):
        self.assertEqual('/api/v1/users', lremove('/api/v1/users', ''))
        self.assertEqual('/users/api/v1', lremove('/api/v1/users/api/v1',
                                                  '/api/v1'))
        self.assertEqual('/users', lremove('/api/v1/users', '/api/v1'))


class APIEndpointTestCase(unittest.TestCase):

    def setUp(self):
        doc = """
        Retrieve an user

        :param user_id: User ID
        :param username: Lookup by username
        :type user_id: int
        :type username: string
        :required user_id
        :statuscode 200: Successful response
        :statuscode 404: No such user
        """
        self.doc = [l.strip() for l in doc.splitlines() if len(l.strip()) > 0]
        self.endpoint = APIEndpoint(None, None, '/api/users/<int:user_id>')

    def test_make_status_codes(self):
        self.assertEqual([], self.endpoint._make_status_codes([]))
        self.assertEqual([], self.endpoint._make_status_codes(['foo', 'bar']))
        self.assertEqual([{'code': '200', 'message': 'Successful response'},
                          {'code': '404', 'message': 'No such user'}],
                         self.endpoint._make_status_codes(self.doc))

    def test_make_summary(self):
        self.assertEqual('Retrieve an user',
                         self.endpoint._make_summary(self.doc))


class APIBuilderTestCase(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        self.app = Flask(__name__)

        @self.app.route('/api/users/<int:user_id>')
        def users():
            """
            Retrieve a user

            :param user_id: User ID
            :type user_id: long
            :required user_id

            :param include_roles: True to include roles in result
            :type include_roles: boolean
            :default include_roles: false

            :statuscode 200: User in JSON format
            :statuscode 400: Bad request
            """

        @self.app.route('/api/users/<int:user_id>/avatar', methods=['POST'])
        def avatar():
            """
            Upload a user avatar

            :param user_id: User ID
            :type user_id: long
            :required user_id

            :param image: Avatar image
            :type image: file
            :paramtype image: body
            :required image
            """
        self.builder = APIBuilder(self.app, '/api')

    def test_find_endpoints(self):
        endpoints = self.builder._find_endpoints()
        self.assertEqual(2, len(endpoints))
        self.assertEqual(self.app, endpoints[0].app)
        self.assertEqual('/users/{user_id}/avatar', endpoints[0].path)
        self.assertEqual('/users/{user_id}', endpoints[1].path)

    def test_make_apis_images(self):
        expected = {'operations': [{'responseMessages': [
            {'message': 'User in JSON format', 'code': '200'},
            {'message': 'Bad request', 'code': '400'}],
            'nickname': 'users', 'method': 'GET', 'parameters': [
                {'name': 'user_id', 'dataType': 'long', 'paramType': 'path',
                 'required': True, 'defaultValue': '',
                 'description': 'User ID'},
                {'name': 'include_roles', 'dataType': 'boolean',
                 'paramType': 'query', 'required': False,
                 'defaultValue': 'false',
                 'description': 'True to include roles in result'}],
            'summary': 'Retrieve a user'}],
            'path': '/users/{user_id}', 'description': None}
        self.assertEqual(expected, self.builder.make_apis()[1])

    def test_make_apis_groups(self):
        expected = {'operations': [
            {'responseMessages': [],
             'nickname': 'avatar', 'method': 'POST',
             'parameters': [
                 {'name': 'user_id', 'dataType': 'long',
                  'paramType': 'path', 'required': True, 'defaultValue': '',
                  'description': 'User ID'},
                 {'name': 'image',
                  'dataType': 'file', 'paramType': 'body', 'required': True,
                  'defaultValue': '', 'description': 'Avatar image'}],
             'summary': 'Upload a user avatar'}],
            'path': '/users/{user_id}/avatar', 'description': None}
        self.assertEqual(expected, self.builder.make_apis()[0])


class SwaggerGenIntegrationTestCase(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        self.app = Flask(__name__)

        @self.app.route('/api/users/search')
        def users_search():
            """
            Search for users

            :param name: Name to search for

            :param include_roles: True to include roles in result
            :type include_roles: boolean
            :default include_roles: false

            :param page: Page number
            :type page: integer
            :default page: 1

            :param page_size: Page size
            :type page_size: integer
            :default pagesize: 25

            :statuscode 200: Users in JSON format
            :statuscode 400: Bad request
            """

    def test_make_resources(self):
        expected = {'basePath': 'http://foo.bar/api', 'apis': [{'operations': [
            {'summary': 'Search for users', 'nickname': 'users_search',
             'method': 'GET', 'parameters': [
                 {'name': 'name', 'dataType': 'string', 'paramType': 'query',
                  'required': False, 'defaultValue': '',
                  'description': 'Name to search for'},
                 {'name': 'include_roles', 'dataType': 'boolean',
                  'paramType': 'query', 'required': False,
                  'defaultValue': 'false',
                  'description': 'True to include roles in result'},
                 {'name': 'page', 'dataType': 'integer', 'paramType': 'query',
                  'required': False, 'defaultValue': '1',
                  'description': 'Page number'},
                 {'name': 'page_size', 'dataType': 'integer',
                  'paramType': 'query', 'required': False, 'defaultValue': '',
                  'description': 'Page size'}],
             'responseMessages': [
                 {'message': 'Users in JSON format', 'code': '200'},
                 {'message': 'Bad request', 'code': '400'}]
             }], 'path': '/users/search',
            'description': None}],
            'resourcePath': '/api/',
            'swaggerVersion': '1.2', 'apiVersion': '1'}
        actual = make_resources(self.app, 'http://foo.bar/api')
        self.assertEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()
