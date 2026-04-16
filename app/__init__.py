"""Application factory."""

from flask import Flask, render_template, redirect, url_for
from flask_login import login_required, current_user
from config import Config


def create_app(config_class=Config):
    app = Flask(__name__,
                template_folder='templates',
                static_folder='../static')
    app.config.from_object(config_class)

    # Initialize extensions
    from app.extensions import db, migrate, login_manager, csrf
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # User loader for Flask-Login
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp)

    from app.hr import bp as hr_bp
    app.register_blueprint(hr_bp)

    from app.pm import bp as pm_bp
    app.register_blueprint(pm_bp)

    from app.finance import bp as finance_bp
    app.register_blueprint(finance_bp)

    from app.employee import bp as employee_bp
    app.register_blueprint(employee_bp)

    # ── Force password change enforcement ─────────────────────────────────
    @app.before_request
    def check_password_change():
        """Redirect users who must change their password."""
        from flask import request as req
        from flask_login import current_user as cu
        if cu.is_authenticated and cu.must_change_password:
            allowed = {'auth.change_password', 'auth.logout', 'static'}
            if req.endpoint and req.endpoint not in allowed:
                return redirect(url_for('auth.change_password'))

    # ── Root routes ──────────────────────────────────────────────────────
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('main_dashboard'))
        return redirect(url_for('auth.login'))

    @app.route('/dashboard')
    @login_required
    def main_dashboard():
        """Show module cards based on user permissions."""
        from app.models import Module
        if current_user.is_admin:
            modules = Module.query.order_by(Module.name).all()
        else:
            modules = current_user.modules
        return render_template('dashboard.html', modules=modules)

    # ── Error handlers ───────────────────────────────────────────────────
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500

    # ── Context processors ───────────────────────────────────────────────
    @app.context_processor
    def inject_modules():
        """Make user's permitted modules available in all templates."""
        if current_user.is_authenticated:
            from app.models import Module
            if current_user.is_admin:
                user_modules = Module.query.order_by(Module.name).all()
            else:
                user_modules = current_user.modules
            return dict(user_modules=user_modules)
        return dict(user_modules=[])

    return app
