from flask import Blueprint, request, session, redirect, url_for, render_template, flash, jsonify, Response
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect, CSRFError
from wtforms import FloatField, IntegerField, SubmitField, StringField, FieldList, FormField
from wtforms.validators import DataRequired, NumberRange, ValidationError, Optional, Length
from flask_login import current_user, login_required
from flask_jwt_extended import jwt_required, get_jwt_identity, jwt_optional
from flask_cors import cross_origin
import utils
from utils import logger
from datetime import datetime
from bson import ObjectId
from translations import trans
from models import log_tool_usage, create_budget
import uuid
import bleach
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from io import BytesIO
from helpers.branding_helpers import draw_ficore_pdf_header

# Web Blueprint for existing HTML routes
budget_bp = Blueprint(
    'budget',
    __name__,
    template_folder='templates/',
    url_prefix='/budget'
)

# API Blueprint for JSON endpoints
api_budget_bp = Blueprint(
    'api_budget',
    __name__,
    url_prefix='/api/budget'
)

# CSRF exemption for API routes
csrf = CSRFProtect()

def clean_currency(value):
    """Transform input into a float, using improved validation from utils."""
    try:
        return utils.clean_currency(value)
    except Exception:
        return 0.0

def strip_commas(value):
    """Filter to remove commas and return a float."""
    return clean_currency(value)

def format_currency(value):
    """Format a numeric value with comma separation, no currency symbol."""
    try:
        numeric_value = float(value)
        formatted = f"{numeric_value:,.2f}"
        return formatted
    except (ValueError, TypeError):
        return "0.00"

def deduct_ficore_credits(db, user_id, amount, action, budget_id=None):
    """
    Deduct Ficore Credits from user balance with enhanced error logging and transaction handling.
    """
    session_id = session.get('sid', 'unknown')
    try:
        if not user_id or amount <= 0:
            logger.error(f"Invalid params for credit deduction: user_id={user_id}, amount={amount}, action={action}",
                         extra={'session_id': session_id, 'user_id': user_id})
            return False

        user = db.users.find_one({'_id': user_id})
        if not user:
            logger.error(f"User {user_id} not found for credit deduction, action: {action}",
                         extra={'session_id': session_id, 'user_id': user_id})
            return False

        current_balance = float(user.get('ficore_credit_balance', 0))
        if current_balance < amount:
            logger.warning(f"Insufficient credits for user {user_id}: required {amount}, available {current_balance}, action: {action}",
                           extra={'session_id': session_id, 'user_id': user_id})
            return False

        with db.client.start_session() as mongo_session:
            with mongo_session.start_transaction():
                result = db.users.update_one(
                    {'_id': user_id},
                    {'$inc': {'ficore_credit_balance': -amount}},
                    session=mongo_session
                )
                if result.modified_count == 0:
                    logger.error(f"Failed to deduct {amount} credits for user {user_id}, action: {action}",
                                 extra={'session_id': session_id, 'user_id': user_id})
                    db.ficore_credit_transactions.insert_one({
                        '_id': ObjectId(),
                        'user_id': user_id,
                        'action': action,
                        'amount': float(-amount),
                        'budget_id': str(budget_id) if budget_id else None,
                        'timestamp': datetime.utcnow(),
                        'session_id': session_id,
                        'status': 'failed'
                    }, session=mongo_session)
                    raise ValueError("No documents modified")

                db.ficore_credit_transactions.insert_one({
                    '_id': ObjectId(),
                    'user_id': user_id,
                    'action': action,
                    'amount': float(-amount),
                    'budget_id': str(budget_id) if budget_id else None,
                    'timestamp': datetime.utcnow(),
                    'session_id': session_id,
                    'status': 'completed'
                }, session=mongo_session)

                db.audit_logs.insert_one({
                    'admin_id': 'system',
                    'action': f'deduct_ficore_credits_{action}',
                    'details': {
                        'user_id': user_id,
                        'amount': amount,
                        'budget_id': str(budget_id) if budget_id else None,
                        'previous_balance': current_balance,
                        'new_balance': current_balance - amount
                    },
                    'timestamp': datetime.utcnow()
                }, session=mongo_session)

                mongo_session.commit_transaction()

        logger.info(f"Deducted {amount} credits for {action} by user {user_id}. New balance: {current_balance - amount}",
                    extra={'session_id': session_id, 'user_id': user_id})
        return True

    except Exception as e:
        logger.error(f"Error deducting {amount} credits for {action} by user {user_id}: {str(e)}",
                     exc_info=True, extra={'session_id': session_id, 'user_id': user_id})
        return False

class CustomCategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=50)])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0, max=10000000000)])

class BudgetForm(FlaskForm):
    income = FloatField('Monthly Income', validators=[DataRequired(), NumberRange(min=0, max=10000000000)])
    housing = FloatField('Housing/Rent', validators=[DataRequired(), NumberRange(min=0, max=10000000000)])
    food = FloatField('Food', validators=[DataRequired(), NumberRange(min=0, max=10000000000)])
    transport = FloatField('Transport', validators=[DataRequired(), NumberRange(min=0, max=10000000000)])
    dependents = IntegerField('Dependents Support', validators=[DataRequired(), NumberRange(min=0, max=100)])
    miscellaneous = FloatField('Miscellaneous', validators=[DataRequired(), NumberRange(min=0, max=10000000000)])
    others = FloatField('Others', validators=[DataRequired(), NumberRange(min=0, max=10000000000)])
    savings_goal = FloatField('Savings Goal', validators=[DataRequired(), NumberRange(min=0, max=10000000000)])
    custom_categories = FieldList(FormField(CustomCategoryForm), min_entries=0, max_entries=20)
    submit = SubmitField('Calculate Budget')

# Web Routes (retained for HTML compatibility)
@budget_bp.route('/index', methods=['GET'])
@login_required
def index():
    data = {
        'title': trans('budget_title'),
        'subtitle': trans('budget_subtitle'),
        'create_description': trans('budget_create_description'),
        'dashboard_description': trans('budget_dashboard_description'),
        'manage_description': trans('budget_manage_description'),
        'tips': [
            trans('budget_tip_track_expenses'),
            trans('budget_tip_ajo_savings'),
            trans('budget_tip_data_subscriptions'),
            trans('budget_tip_plan_dependents')
        ]
    }
    return render_template('budget/index.html', **data)

@budget_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    form = BudgetForm()
    user_id = current_user.id
    db = utils.get_mongo_db()

    if request.method == 'POST' and form.validate_on_submit():
        budget_data = {
            'user_id': str(user_id),
            'income': form.income.data,
            'fixed_expenses': form.housing.data + form.food.data + form.transport.data,
            'variable_expenses': form.miscellaneous.data + form.others.data,
            'savings_goal': form.savings_goal.data,
            'dependents': form.dependents.data,
            'housing': form.housing.data,
            'food': form.food.data,
            'transport': form.transport.data,
            'miscellaneous': form.miscellaneous.data,
            'others': form.others.data,
            'custom_categories': [{'name': bleach.clean(cat.name.data), 'amount': cat.amount.data} for cat in form.custom_categories],
            'created_at': datetime.utcnow(),
            'session_id': session.get('sid')
        }
        budget_data['surplus_deficit'] = budget_data['income'] - budget_data['fixed_expenses'] - budget_data['variable_expenses'] - budget_data['savings_goal']

        budget_id = create_budget(db, budget_data)
        deduct_ficore_credits(db, user_id, 1, 'create_budget', budget_id)
        log_tool_usage('budget', db, user_id, session.get('sid'), 'create_budget')
        db.audit_logs.insert_one({
            'user_id': user_id,
            'action': 'create_budget',
            'details': {'budget_id': str(budget_id), 'email': current_user.email},
            'timestamp': datetime.utcnow()
        })
        flash(trans('budget_created_success'), 'success')
        return redirect(url_for('budget.dashboard'))

    data = {
        'form': form,
        'tips': [trans('budget_tip_track_expenses'), trans('budget_tip_ajo_savings'), trans('budget_tip_data_subscriptions'), trans('budget_tip_plan_dependents')],
        'activities': utils.get_recent_activities(user_id, db=db, limit=5)
    }
    return render_template('budget/new.html', **data)

@budget_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    user_id = current_user.id
    db = utils.get_mongo_db()

    budgets = utils.get_budgets(user_id, limit=20)
    latest_budget = budgets[0] if budgets else None
    categories = []
    insights = []

    if latest_budget:
        total_expenses = latest_budget.get('fixed_expenses', 0) + latest_budget.get('variable_expenses', 0)
        categories = [
            {'label': trans('budget_housing_rent'), 'value': latest_budget.get('housing', 0), 'color': '#FF6384'},
            {'label': trans('budget_food'), 'value': latest_budget.get('food', 0), 'color': '#36A2EB'},
            {'label': trans('budget_transport'), 'value': latest_budget.get('transport', 0), 'color': '#FFCE56'},
            {'label': trans('budget_miscellaneous'), 'value': latest_budget.get('miscellaneous', 0), 'color': '#4BC0C0'},
            {'label': trans('budget_others'), 'value': latest_budget.get('others', 0), 'color': '#9966FF'}
        ] + [{'label': cat['name'], 'value': cat['amount'], 'color': '#FF9F40'} for cat in latest_budget.get('custom_categories', [])]

        surplus_deficit = latest_budget.get('surplus_deficit', 0)
        if surplus_deficit > 0:
            insights.append(trans('budget_insight_surplus'))
        elif surplus_deficit < 0:
            insights.append(trans('budget_insight_deficit'))

        db.audit_logs.insert_one({
            'user_id': user_id,
            'action': 'view_budget_dashboard',
            'details': {'latest_budget_id': str(latest_budget['_id'])},
            'timestamp': datetime.utcnow()
        })

    data = {
        'latest_budget': latest_budget,
        'budgets': budgets,
        'categories': categories,
        'insights': insights,
        'tips': [trans('budget_tip_track_expenses'), trans('budget_tip_ajo_savings'), trans('budget_tip_data_subscriptions'), trans('budget_tip_plan_dependents')]
    }
    return render_template('budget/dashboard.html', **data)

@budget_bp.route('/manage', methods=['GET'])
@login_required
def manage():
    user_id = current_user.id
    db = utils.get_mongo_db()

    budgets = utils.get_budgets(user_id, limit=20)
    formatted_budgets = {}
    for idx, budget in enumerate(budgets, 1):
        budget['surplus_deficit_formatted'] = format_currency(budget.get('surplus_deficit', 0))
        formatted_budgets[str(budget['_id'])] = budget

    db.audit_logs.insert_one({
        'user_id': user_id,
        'action': 'view_budget_manage',
        'details': {'budget_count': len(budgets)},
        'timestamp': datetime.utcnow()
    })

    return render_template('budget/manage.html', budgets=formatted_budgets)

@budget_bp.route('/delete_budget', methods=['POST'])
@login_required
def delete_budget():
    user_id = current_user.id
    db = utils.get_mongo_db()
    budget_id = request.form.get('budget_id')

    if not ObjectId.is_valid(budget_id):
        flash(trans('budget_invalid_id'), 'danger')
        return redirect(url_for('budget.manage'))

    budget = db.budgets.find_one({'_id': ObjectId(budget_id), 'user_id': str(user_id)})
    if not budget:
        flash(trans('budget_not_found'), 'danger')
        return redirect(url_for('budget.manage'))

    with db.client.start_session() as mongo_session:
        with mongo_session.start_transaction():
            result = db.budgets.delete_one({'_id': ObjectId(budget_id)}, session=mongo_session)
            if result.deleted_count > 0:
                deduct_ficore_credits(db, user_id, 1, 'delete_budget', budget_id)
                db.audit_logs.insert_one({
                    'user_id': user_id,
                    'action': 'delete_budget',
                    'details': {'budget_id': budget_id},
                    'timestamp': datetime.utcnow()
                })
                utils.cache.delete_memoized(utils.get_budgets)
                log_tool_usage('budget', db, user_id, session.get('sid'), 'delete_budget')
                flash(trans('budget_deleted'), 'success')
                mongo_session.commit_transaction()

    return redirect(url_for('budget.manage'))

@budget_bp.route('/export_pdf/<export_type>', defaults={'budget_id': None}, methods=['GET'])
@budget_bp.route('/export_pdf/<export_type>/<budget_id>', methods=['GET'])
@login_required
def export_pdf(export_type, budget_id=None):
    user_id = current_user.id
    db = utils.get_mongo_db()
    credit_cost = 1 if export_type == 'single' else 2

    if export_type not in ['single', 'history']:
        flash(trans('budget_invalid_export_type'), 'danger')
        return redirect(url_for('budget.manage'))

    is_single_budget = export_type == 'single'
    if is_single_budget and not budget_id:
        flash(trans('budget_id_required'), 'danger')
        return redirect(url_for('budget.manage'))

    budgets = utils.get_budgets(user_id, limit=20 if is_single_budget else 100)
    budget = next((b for b in budgets if str(b['_id']) == budget_id), None) if is_single_budget else None

    if is_single_budget and not budget:
        flash(trans('budget_not_found'), 'danger')
        return redirect(url_for('budget.manage'))

    db.audit_logs.insert_one({
        'user_id': user_id,
        'action': f'export_budget_pdf_{export_type}',
        'details': {'budget_id': budget_id if is_single_budget else None},
        'timestamp': datetime.utcnow()
    })

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    draw_ficore_pdf_header(p, current_user, y_start=height - 50)
    y = height - 100

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, f"{'Budget Details' if is_single_budget else 'Budget History'} Export")
    y -= 30

    p.setFont("Helvetica", 10)
    if is_single_budget:
        p.drawString(50, y, f"Budget ID: {budget_id}")
        p.drawString(50, y - 15, f"Created: {utils.format_date(budget.get('created_at'))}")
        p.drawString(50, y - 30, f"Income: {format_currency(budget.get('income', 0))}")
        p.drawString(50, y - 45, f"Fixed Expenses: {format_currency(budget.get('fixed_expenses', 0))}")
        p.drawString(50, y - 60, f"Variable Expenses: {format_currency(budget.get('variable_expenses', 0))}")
        p.drawString(50, y - 75, f"Savings Goal: {format_currency(budget.get('savings_goal', 0))}")
        p.drawString(50, y - 90, f"Surplus/Deficit: {format_currency(budget.get('surplus_deficit', 0))}")
        p.drawString(50, y - 105, f"Dependents: {budget.get('dependents', 0)}")
        y -= 125

        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, y, "Expense Categories")
        y -= 15
        p.setFont("Helvetica", 9)
        p.drawString(50, y, f"Housing: {format_currency(budget.get('housing', 0))}")
        p.drawString(50, y - 15, f"Food: {format_currency(budget.get('food', 0))}")
        p.drawString(50, y - 30, f"Transport: {format_currency(budget.get('transport', 0))}")
        p.drawString(50, y - 45, f"Miscellaneous: {format_currency(budget.get('miscellaneous', 0))}")
        p.drawString(50, y - 60, f"Others: {format_currency(budget.get('others', 0))}")
        y -= 75

        if budget.get('custom_categories', []):
            p.setFont("Helvetica-Bold", 10)
            p.drawString(50, y, "Custom Categories")
            y -= 15
            p.setFont("Helvetica", 9)
            for cat in budget.get('custom_categories', []):
                if y < 50:
                    p.showPage()
                    draw_ficore_pdf_header(p, current_user, y_start=height - 50)
                    y = height - 50
                    p.setFont("Helvetica", 9)
                p.drawString(50, y, f"{cat['name']}: {format_currency(cat['amount'])}")
                y -= 15
    else:
        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, y, "Date")
        p.drawString(150, y, "Income")
        p.drawString(220, y, "Fixed Exp.")
        p.drawString(290, y, "Variable Exp.")
        p.drawString(370, y, "Savings Goal")
        p.drawString(450, y, "Surplus/Deficit")
        y -= 20

        p.setFont("Helvetica", 9)
        for budget in budgets:
            if y < 50:
                p.showPage()
                draw_ficore_pdf_header(p, current_user, y_start=height - 50)
                y = height - 120
                p.setFont("Helvetica-Bold", 10)
                p.drawString(50, y, "Date")
                p.drawString(150, y, "Income")
                p.drawString(220, y, "Fixed Exp.")
                p.drawString(290, y, "Variable Exp.")
                p.drawString(370, y, "Savings Goal")
                p.drawString(450, y, "Surplus/Deficit")
                y -= 20
                p.setFont("Helvetica", 9)

            p.drawString(50, y, utils.format_date(budget.get('created_at')))
            p.drawString(150, y, format_currency(budget.get('income', 0)))
            p.drawString(220, y, format_currency(budget.get('fixed_expenses', 0)))
            p.drawString(290, y, format_currency(budget.get('variable_expenses', 0)))
            p.drawString(370, y, format_currency(budget.get('savings_goal', 0)))
            p.drawString(450, y, format_currency(budget.get('surplus_deficit', 0)))
            y -= 15

    p.save()
    buffer.seek(0)

    if not utils.is_admin() and not deduct_ficore_credits(db, user_id, credit_cost, f'export_budget_pdf_{export_type}', budget_id if is_single_budget else None):
        flash(trans('budget_credit_deduction_failed'), 'danger')
        return redirect(url_for('budget.manage'))

    filename = f"budget_{export_type}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

# API Routes for Mobile (JSON-only)
@api_budget_bp.route('/index', methods=['GET'])
@cross_origin(origins=['http://localhost:8100', 'https://ficoreafrica.com'])
@jwt_optional
def api_index():
    user_id = get_jwt_identity() or (current_user.id if current_user.is_authenticated else None)
    data = {
        'title': trans('budget_title'),
        'subtitle': trans('budget_subtitle'),
        'create_description': trans('budget_create_description'),
        'dashboard_description': trans('budget_dashboard_description'),
        'manage_description': trans('budget_manage_description'),
        'tips': [
            trans('budget_tip_track_expenses'),
            trans('budget_tip_ajo_savings'),
            trans('budget_tip_data_subscriptions'),
            trans('budget_tip_plan_dependents')
        ]
    }
    return jsonify(data), 200

@api_budget_bp.route('/new', methods=['POST'])
@cross_origin(origins=['http://localhost:8100', 'https://ficoreafrica.com'])
@csrf.exempt
@jwt_required()
def api_new():
    user_id = get_jwt_identity()
    db = utils.get_mongo_db()
    form = BudgetForm(data=request.json)

    if form.validate():
        budget_data = {
            'user_id': str(user_id),
            'income': form.income.data,
            'fixed_expenses': form.housing.data + form.food.data + form.transport.data,
            'variable_expenses': form.miscellaneous.data + form.others.data,
            'savings_goal': form.savings_goal.data,
            'dependents': form.dependents.data,
            'housing': form.housing.data,
            'food': form.food.data,
            'transport': form.transport.data,
            'miscellaneous': form.miscellaneous.data,
            'others': form.others.data,
            'custom_categories': [{'name': bleach.clean(cat.name.data), 'amount': cat.amount.data} for cat in form.custom_categories],
            'created_at': datetime.utcnow(),
            'session_id': session.get('sid')
        }
        budget_data['surplus_deficit'] = budget_data['income'] - budget_data['fixed_expenses'] - budget_data['variable_expenses'] - budget_data['savings_goal']

        budget_id = create_budget(db, budget_data)
        deduct_ficore_credits(db, user_id, 1, 'create_budget', budget_id)
        log_tool_usage('budget', db, user_id, session.get('sid'), 'create_budget')
        db.audit_logs.insert_one({
            'user_id': user_id,
            'action': 'create_budget',
            'details': {'budget_id': str(budget_id), 'email': db.users.find_one({'_id': user_id})['email']},
            'timestamp': datetime.utcnow()
        })
        return jsonify({'success': True, 'budget_id': str(budget_id), 'message': trans('budget_created_success')}), 201

    return jsonify({'success': False, 'errors': form.errors}), 400

@api_budget_bp.route('/dashboard', methods=['GET'])
@cross_origin(origins=['http://localhost:8100', 'https://ficoreafrica.com'])
@jwt_required()
def api_dashboard():
    user_id = get_jwt_identity()
    db = utils.get_mongo_db()
    page = max(1, int(request.args.get('page', 1)))
    limit = max(1, min(50, int(request.args.get('limit', 10))))

    budgets = utils.get_budgets(user_id, page=page, limit=limit)
    total_budgets = db.budgets.count_documents({'user_id': str(user_id)})
    latest_budget = budgets[0] if budgets else None
    categories = []
    insights = []

    if latest_budget:
        total_expenses = latest_budget.get('fixed_expenses', 0) + latest_budget.get('variable_expenses', 0)
        categories = [
            {'label': trans('budget_housing_rent'), 'value': latest_budget.get('housing', 0), 'color': '#FF6384'},
            {'label': trans('budget_food'), 'value': latest_budget.get('food', 0), 'color': '#36A2EB'},
            {'label': trans('budget_transport'), 'value': latest_budget.get('transport', 0), 'color': '#FFCE56'},
            {'label': trans('budget_miscellaneous'), 'value': latest_budget.get('miscellaneous', 0), 'color': '#4BC0C0'},
            {'label': trans('budget_others'), 'value': latest_budget.get('others', 0), 'color': '#9966FF'}
        ] + [{'label': bleach.clean(cat['name']), 'value': cat['amount'], 'color': '#FF9F40'} for cat in latest_budget.get('custom_categories', [])]

        surplus_deficit = latest_budget.get('surplus_deficit', 0)
        if surplus_deficit > 0:
            insights.append(trans('budget_insight_surplus'))
        elif surplus_deficit < 0:
            insights.append(trans('budget_insight_deficit'))

        db.audit_logs.insert_one({
            'user_id': user_id,
            'action': 'view_budget_dashboard',
            'details': {'latest_budget_id': str(latest_budget['_id'])},
            'timestamp': datetime.utcnow()
        })

    data = {
        'latest_budget': latest_budget,
        'budgets': budgets,
        'categories': categories,
        'insights': insights,
        'tips': [trans('budget_tip_track_expenses'), trans('budget_tip_ajo_savings'), trans('budget_tip_data_subscriptions'), trans('budget_tip_plan_dependents')],
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total_budgets,
            'pages': (total_budgets + limit - 1) // limit
        }
    }
    return jsonify(data), 200

@api_budget_bp.route('/manage', methods=['GET'])
@cross_origin(origins=['http://localhost:8100', 'https://ficoreafrica.com'])
@jwt_required()
def api_manage():
    user_id = get_jwt_identity()
    db = utils.get_mongo_db()
    page = max(1, int(request.args.get('page', 1)))
    limit = max(1, min(50, int(request.args.get('limit', 10))))

    budgets = utils.get_budgets(user_id, page=page, limit=limit)
    total_budgets = db.budgets.count_documents({'user_id': str(user_id)})
    formatted_budgets = {}
    for idx, budget in enumerate(budgets, 1):
        budget['surplus_deficit_formatted'] = format_currency(budget.get('surplus_deficit', 0))
        budget['custom_categories'] = [{'name': bleach.clean(cat['name']), 'amount': cat['amount']} for cat in budget.get('custom_categories', [])]
        formatted_budgets[str(budget['_id'])] = budget

    db.audit_logs.insert_one({
        'user_id': user_id,
        'action': 'view_budget_manage',
        'details': {'budget_count': len(budgets)},
        'timestamp': datetime.utcnow()
    })

    data = {
        'budgets': formatted_budgets,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total_budgets,
            'pages': (total_budgets + limit - 1) // limit
        }
    }
    return jsonify(data), 200

@api_budget_bp.route('/delete', methods=['POST'])
@cross_origin(origins=['http://localhost:8100', 'https://ficoreafrica.com'])
@csrf.exempt
@jwt_required()
def api_delete():
    user_id = get_jwt_identity()
    db = utils.get_mongo_db()
    data = request.get_json()
    budget_id = data.get('budget_id')

    if not ObjectId.is_valid(budget_id):
        return jsonify({'success': False, 'error': trans('budget_invalid_id')}), 400

    budget = db.budgets.find_one({'_id': ObjectId(budget_id), 'user_id': str(user_id)})
    if not budget:
        return jsonify({'success': False, 'error': trans('budget_not_found')}), 404

    with db.client.start_session() as mongo_session:
        with mongo_session.start_transaction():
            result = db.budgets.delete_one({'_id': ObjectId(budget_id)}, session=mongo_session)
            if result.deleted_count > 0:
                deduct_ficore_credits(db, user_id, 1, 'delete_budget', budget_id)
                db.audit_logs.insert_one({
                    'user_id': user_id,
                    'action': 'delete_budget',
                    'details': {'budget_id': budget_id},
                    'timestamp': datetime.utcnow()
                })
                utils.cache.delete_memoized(utils.get_budgets)
                log_tool_usage('budget', db, user_id, session.get('sid'), 'delete_budget')
                mongo_session.commit_transaction()
                return jsonify({'success': True, 'message': trans('budget_deleted')}), 200

    return jsonify({'success': False, 'error': trans('budget_delete_failed')}), 500

@api_budget_bp.route('/export_pdf/<export_type>', defaults={'budget_id': None}, methods=['GET'])
@api_budget_bp.route('/export_pdf/<export_type>/<budget_id>', methods=['GET'])
@cross_origin(origins=['http://localhost:8100', 'https://ficoreafrica.com'])
@jwt_required()
def api_export_pdf(export_type, budget_id=None):
    user_id = get_jwt_identity()
    db = utils.get_mongo_db()
    credit_cost = 1 if export_type == 'single' else 2

    if export_type not in ['single', 'history']:
        return jsonify({'error': trans('budget_invalid_export_type')}), 400

    is_single_budget = export_type == 'single'
    if is_single_budget and not budget_id:
        return jsonify({'error': trans('budget_id_required')}), 400

    budgets = utils.get_budgets(user_id, limit=20 if is_single_budget else 100)
    budget = next((b for b in budgets if str(b['_id']) == budget_id), None) if is_single_budget else None

    if is_single_budget and not budget:
        return jsonify({'error': trans('budget_not_found')}), 404

    db.audit_logs.insert_one({
        'user_id': user_id,
        'action': f'export_budget_pdf_{export_type}',
        'details': {'budget_id': budget_id if is_single_budget else None},
        'timestamp': datetime.utcnow()
    })

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    draw_ficore_pdf_header(p, db.users.find_one({'_id': user_id}), y_start=height - 50)
    y = height - 100

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, f"{'Budget Details' if is_single_budget else 'Budget History'} Export")
    y -= 30

    p.setFont("Helvetica", 10)
    if is_single_budget:
        p.drawString(50, y, f"Budget ID: {budget_id}")
        p.drawString(50, y - 15, f"Created: {utils.format_date(budget.get('created_at'))}")
        p.drawString(50, y - 30, f"Income: {format_currency(budget.get('income', 0))}")
        p.drawString(50, y - 45, f"Fixed Expenses: {format_currency(budget.get('fixed_expenses', 0))}")
        p.drawString(50, y - 60, f"Variable Expenses: {format_currency(budget.get('variable_expenses', 0))}")
        p.drawString(50, y - 75, f"Savings Goal: {format_currency(budget.get('savings_goal', 0))}")
        p.drawString(50, y - 90, f"Surplus/Deficit: {format_currency(budget.get('surplus_deficit', 0))}")
        p.drawString(50, y - 105, f"Dependents: {budget.get('dependents', 0)}")
        y -= 125

        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, y, "Expense Categories")
        y -= 15
        p.setFont("Helvetica", 9)
        p.drawString(50, y, f"Housing: {format_currency(budget.get('housing', 0))}")
        p.drawString(50, y - 15, f"Food: {format_currency(budget.get('food', 0))}")
        p.drawString(50, y - 30, f"Transport: {format_currency(budget.get('transport', 0))}")
        p.drawString(50, y - 45, f"Miscellaneous: {format_currency(budget.get('miscellaneous', 0))}")
        p.drawString(50, y - 60, f"Others: {format_currency(budget.get('others', 0))}")
        y -= 75

        if budget.get('custom_categories', []):
            p.setFont("Helvetica-Bold", 10)
            p.drawString(50, y, "Custom Categories")
            y -= 15
            p.setFont("Helvetica", 9)
            for cat in budget.get('custom_categories', []):
                if y < 50:
                    p.showPage()
                    draw_ficore_pdf_header(p, db.users.find_one({'_id': user_id}), y_start=height - 50)
                    y = height - 50
                    p.setFont("Helvetica", 9)
                p.drawString(50, y, f"{bleach.clean(cat['name'])}: {format_currency(cat['amount'])}")
                y -= 15
    else:
        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, y, "Date")
        p.drawString(150, y, "Income")
        p.drawString(220, y, "Fixed Exp.")
        p.drawString(290, y, "Variable Exp.")
        p.drawString(370, y, "Savings Goal")
        p.drawString(450, y, "Surplus/Deficit")
        y -= 20

        p.setFont("Helvetica", 9)
        for budget in budgets:
            if y < 50:
                p.showPage()
                draw_ficore_pdf_header(p, db.users.find_one({'_id': user_id}), y_start=height - 50)
                y = height - 120
                p.setFont("Helvetica-Bold", 10)
                p.drawString(50, y, "Date")
                p.drawString(150, y, "Income")
                p.drawString(220, y, "Fixed Exp.")
                p.drawString(290, y, "Variable Exp.")
                p.drawString(370, y, "Savings Goal")
                p.drawString(450, y, "Surplus/Deficit")
                y -= 20
                p.setFont("Helvetica", 9)

            p.drawString(50, y, utils.format_date(budget.get('created_at')))
            p.drawString(150, y, format_currency(budget.get('income', 0)))
            p.drawString(220, y, format_currency(budget.get('fixed_expenses', 0)))
            p.drawString(290, y, format_currency(budget.get('variable_expenses', 0)))
            p.drawString(370, y, format_currency(budget.get('savings_goal', 0)))
            p.drawString(450, y, format_currency(budget.get('surplus_deficit', 0)))
            y -= 15

    p.save()
    buffer.seek(0)

    if not utils.is_admin() and not deduct_ficore_credits(db, user_id, credit_cost, f'export_budget_pdf_{export_type}', budget_id if is_single_budget else None):
        return jsonify({'error': trans('budget_credit_deduction_failed')}), 402

    filename = f"budget_{export_type}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )