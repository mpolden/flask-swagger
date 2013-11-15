flask-swagger
=============
A Flask extension for auto-generating
[Swagger](https://developers.helloreverb.com/swagger/) resource listings
and API declarations using inspection and docstrings.

Basic example
-------------
```python
from flask import Flask, jsonify
import flask.ext.swagger as swagger
app = Flask(__name__)


@app.route('/api/users/<int:user_id>')
def users():
    """
    Retrieve a user by ID

    :param user_id: User ID
    :type user_id: long
    :required user_id

    :statuscode 200: User in JSON format
    :statuscode 404: No user found
    """

    # XXX: Implementation


@app.route('/docs')
def api_docs():
    resources = swagger.make_resources(app, 'http://localhost:5000/api')
    return jsonify(resources)


if __name__ == "__main__":
    app.run()
```

Notes
-----
Does not support the entire Swagger specification yet. There is currently no
support for models.
