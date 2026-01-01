"""Main Flask application."""
import os
import sys

# Ensure repo root is in Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, jsonify, request
from whitenoise import WhiteNoise
from app.config import Config
from app.routes.health import health_bp
from app.routes.api import api_bp


def create_app():
    """Create and configure the Flask application."""
    static_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')

    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
        static_folder=static_folder
    )

    app.config.from_object(Config)

    # Ensure upload folder exists
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(api_bp)

    # Main page route
    @app.route('/')
    def index():
        return render_template('index.html')

    # Admin panel route
    @app.route('/admin')
    def admin():
        return render_template('admin.html')

    # Global error handlers for API routes to ensure JSON responses
    @app.errorhandler(500)
    def internal_error(error):
        if request.path.startswith('/api/'):
            app.logger.error(f"Internal server error: {str(error)}")
            return jsonify({'error': 'Internal server error. Please try again.'}), 500
        return render_template('error.html', error=error), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        if request.path.startswith('/api/'):
            app.logger.error(f"Unhandled exception: {str(error)}")
            return jsonify({'error': f'Server error: {str(error)}'}), 500
        raise error

    return app


# For gunicorn
app = create_app()

# Wrap with WhiteNoise for serving static files in production
app.wsgi_app = WhiteNoise(app.wsgi_app, root=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'), prefix='static/')

if __name__ == '__main__':
    # For local development only - production uses gunicorn
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
