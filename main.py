import os
from logging.config import dictConfig

from flask import Flask, url_for
try:
    from flask_restplus import Api
except ImportError:
    import werkzeug
    werkzeug.cached_property = werkzeug.utils.cached_property
    from flask_restplus import Api 

def create_app():

    dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
    })

    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.urandom(32)
    
    from views import main_views
    app.register_blueprint(main_views.bp)
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='127.0.0.1', debug=True)


