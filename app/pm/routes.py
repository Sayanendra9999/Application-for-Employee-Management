"""PM routes — projects, tasks, milestones, members, notifications, REST APIs."""

from datetime import date
from flask import render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import current_user
from app.pm import bp
from app.decorators import module_required
from app.extensions import db
from app.models import (Project, ProjectMember, Task, Milestone,
                        Notification, User, AuditLog, Module)
from app.pm.forms import ProjectForm, TaskForm, MilestoneForm


def _get_user_projects(user):
    """Return projects visible to the user based on role hierarchy."""
    if user.is_admin:
        return Project.query.order_by(Project.created_at.desc()).all()
    # Projects assigned to this user as PM
    pm_projects = Project.query.filter_by(assigned_pm=user.id).all()
    if pm_projects:
        return pm_projects
    # Projects where user is a member
    member_project_ids = db.session.query(ProjectMember.project_id).filter_by(user_id=user.id).subquery()
    return Project.query.filter(Project.id.in_(member_project_ids)).order_by(Project.created_at.desc()).all()


def _is_pm_or_admin(user, project):
    """Check if user is the assigned PM or an admin."""
    return user.is_admin or project.assigned_pm == user.id


def _can_view_project(user, project):
    """Check if user can view this project."""
    if user.is_admin or project.assigned_pm == user.id:
        return True
    return ProjectMember.query.filter_by(project_id=project.id, user_id=user.id).first() is not None


# ---------------------------------------------------------------------------
# Helper: create notification
# ---------------------------------------------------------------------------
def notify(user_id, title, message, category='info', link=''):
    """Create a notification for a user."""
    n = Notification(user_id=user_id, title=title, message=message,
                     category=category, link=link)
    db.session.add(n)


def log_audit(user_id, action, entity_type, entity_id=None, details=''):
    """Write an audit log entry."""
    log = AuditLog(
        user_id=user_id, action=action, entity_type=entity_type,
        entity_id=entity_id, details=details,
        ip_address=request.remote_addr or ''
    )
    db.session.add(log)


# ===========================================================================
# DASHBOARD
# ===========================================================================
@bp.route('/')
@module_required('pm')
def dashboard():
    visible_projects = _get_user_projects(current_user)
    visible_ids = [p.id for p in visible_projects]

    total_projects = len(visible_projects)
    active_projects = sum(1 for p in visible_projects if p.status == 'In Progress')
    completed_projects = sum(1 for p in visible_projects if p.status == 'Completed')
    on_hold_projects = sum(1 for p in visible_projects if p.status == 'On Hold')

    task_q = Task.query.filter(Task.project_id.in_(visible_ids)) if visible_ids else Task.query.filter(False)
    total_tasks = task_q.count()
    pending_tasks = task_q.filter(Task.status == 'Pending').count()
    tasks_done = task_q.filter(Task.status == 'Done').count()
    tasks_in_progress = task_q.filter(Task.status == 'In Progress').count()
    overdue_tasks = task_q.filter(Task.due_date < db.func.current_date(), Task.status != 'Done').count()

    ms_q = Milestone.query.filter(Milestone.project_id.in_(visible_ids)) if visible_ids else Milestone.query.filter(False)
    total_milestones = ms_q.count()
    completed_milestones = ms_q.filter(Milestone.status == 'Completed').count()

    recent_projects = visible_projects[:5]

    # Determine user's PM role context
    is_project_manager = any(p.assigned_pm == current_user.id for p in visible_projects)
    is_team_member = not current_user.is_admin and not is_project_manager

    # Unread notifications for current user
    unread_notifications = Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).order_by(Notification.created_at.desc()).limit(10).all()

    return render_template('pm/dashboard.html',
                           total_projects=total_projects,
                           active_projects=active_projects,
                           completed_projects=completed_projects,
                           on_hold_projects=on_hold_projects,
                           total_tasks=total_tasks,
                           pending_tasks=pending_tasks,
                           tasks_done=tasks_done,
                           tasks_in_progress=tasks_in_progress,
                           overdue_tasks=overdue_tasks,
                           total_milestones=total_milestones,
                           completed_milestones=completed_milestones,
                           recent_projects=recent_projects,
                           unread_notifications=unread_notifications,
                           is_project_manager=is_project_manager,
                           is_team_member=is_team_member)


# ===========================================================================
# NOTIFICATIONS
# ===========================================================================
@bp.route('/notifications')
@module_required('pm')
def notifications():
    all_notifs = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc()).limit(50).all()
    return render_template('pm/notifications.html', notifications=all_notifs)


@bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
@module_required('pm')
def mark_notification_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id != current_user.id:
        abort(403)
    notif.is_read = True
    db.session.commit()
    if notif.link:
        return redirect(notif.link)
    return redirect(url_for('pm.notifications'))


@bp.route('/notifications/mark-all-read', methods=['POST'])
@module_required('pm')
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False)\
        .update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('pm.notifications'))


# ===========================================================================
# PROJECTS — CRUD
# ===========================================================================
@bp.route('/projects')
@module_required('pm')
def projects():
    status_filter = request.args.get('status', '')
    visible = _get_user_projects(current_user)
    if status_filter:
        visible = [p for p in visible if p.status == status_filter]
    can_create = current_user.is_admin
    return render_template('pm/projects.html', projects=visible,
                           current_status=status_filter,
                           can_create=can_create)


@bp.route('/projects/add', methods=['GET', 'POST'])
@module_required('pm')
def add_project():
    if not current_user.is_admin:
        flash('Only Admin can create projects.', 'danger')
        return redirect(url_for('pm.projects'))
    form = ProjectForm()
    # Populate PM dropdown with users who have pm module access
    pm_module = Module.query.filter_by(slug='pm').first()
    pm_users = pm_module.users.all() if pm_module else []
    form.assigned_pm.choices = [(0, '-- Select PM --')] + [
        (u.id, u.full_name) for u in pm_users if not u.is_admin
    ]
    if form.validate_on_submit():
        existing = Project.query.filter(
            db.func.lower(Project.name) == form.name.data.strip().lower()
        ).first()
        if existing:
            flash(f'Project "{form.name.data}" already exists.', 'danger')
            return render_template('pm/project_form.html', form=form, title='New Project')

        assigned = form.assigned_pm.data if form.assigned_pm.data != 0 else None
        project = Project(
            name=form.name.data.strip(),
            description=form.description.data or '',
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            deadline=form.deadline.data,
            estimated_hours=form.estimated_hours.data or 0.0,
            status=form.status.data,
            assigned_pm=assigned,
            created_by=current_user.id
        )
        db.session.add(project)
        db.session.flush()  # ensure project.id is available
        log_audit(current_user.id, 'CREATE', 'Project', project.id,
                  f'Created project "{project.name}"')
        # Notify assigned PM
        if assigned:
            notify(assigned, 'Project Assigned',
                   f'You have been assigned as Project Manager for "{project.name}".',
                   category='info',
                   link=url_for('pm.project_detail', project_id=project.id))
        db.session.commit()
        flash(f'Project "{project.name}" created.', 'success')
        return redirect(url_for('pm.project_detail', project_id=project.id))
    return render_template('pm/project_form.html', form=form, title='New Project')


@bp.route('/projects/<int:project_id>')
@module_required('pm')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    if not _can_view_project(current_user, project):
        abort(403)
    members = ProjectMember.query.filter_by(project_id=project.id).all()
    tasks = Task.query.filter_by(project_id=project.id).order_by(Task.created_at.desc()).all()
    milestones = Milestone.query.filter_by(project_id=project.id)\
        .order_by(Milestone.deadline.asc().nullslast()).all()
    # For add-member dropdown: show all active users (PM/admin will use this)
    all_users = User.query.filter_by(is_active_user=True).order_by(User.full_name).all()
    progress = project.progress
    can_manage = _is_pm_or_admin(current_user, project)

    return render_template('pm/project_detail.html', project=project,
                           members=members, tasks=tasks, milestones=milestones,
                           all_users=all_users, progress=progress,
                           can_manage=can_manage)


@bp.route('/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@module_required('pm')
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not _is_pm_or_admin(current_user, project):
        abort(403)
    form = ProjectForm(obj=project)
    # Populate PM dropdown
    pm_module = Module.query.filter_by(slug='pm').first()
    pm_users = pm_module.users.all() if pm_module else []
    form.assigned_pm.choices = [(0, '-- Select PM --')] + [
        (u.id, u.full_name) for u in pm_users if not u.is_admin
    ]
    if request.method == 'GET':
        form.assigned_pm.data = project.assigned_pm or 0
    if form.validate_on_submit():
        # Duplicate check (exclude self)
        existing = Project.query.filter(
            db.func.lower(Project.name) == form.name.data.strip().lower(),
            Project.id != project.id
        ).first()
        if existing:
            flash(f'Project "{form.name.data}" already exists.', 'danger')
            return render_template('pm/project_form.html', form=form,
                                   title='Edit Project', project=project)

        old_status = project.status
        project.name = form.name.data.strip()
        project.description = form.description.data or ''
        project.start_date = form.start_date.data
        project.end_date = form.end_date.data
        project.deadline = form.deadline.data
        project.estimated_hours = form.estimated_hours.data or 0.0
        project.status = form.status.data
        if current_user.is_admin:
            project.assigned_pm = form.assigned_pm.data if form.assigned_pm.data != 0 else None

        log_audit(current_user.id, 'UPDATE', 'Project', project.id,
                  f'Updated project "{project.name}"')

        # Notify if project is delayed
        if project.is_delayed and old_status != project.status:
            notify(project.created_by,
                   'Project Delayed',
                   f'Project "{project.name}" is past its deadline.',
                   category='warning',
                   link=url_for('pm.project_detail', project_id=project.id))

        db.session.commit()
        flash(f'Project "{project.name}" updated.', 'success')
        return redirect(url_for('pm.project_detail', project_id=project.id))
    return render_template('pm/project_form.html', form=form,
                           title='Edit Project', project=project)


@bp.route('/projects/<int:project_id>/delete', methods=['POST'])
@module_required('pm')
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not current_user.is_admin:
        abort(403)
    project_name = project.name
    log_audit(current_user.id, 'DELETE', 'Project', project.id,
              f'Deleted project "{project_name}"')
    db.session.delete(project)
    db.session.commit()
    flash(f'Project "{project_name}" deleted.', 'info')
    return redirect(url_for('pm.projects'))


# ===========================================================================
# TEAM / MEMBERS
# ===========================================================================
@bp.route('/projects/<int:project_id>/add-member', methods=['POST'])
@module_required('pm')
def add_member(project_id):
    project = Project.query.get_or_404(project_id)
    if not _is_pm_or_admin(current_user, project):
        flash('Only the assigned PM or Admin can manage team members.', 'danger')
        return redirect(url_for('pm.project_detail', project_id=project.id))
    user_id = request.form.get('user_id', type=int)
    role = request.form.get('role', 'Developer')
    if user_id:
        existing = ProjectMember.query.filter_by(
            project_id=project.id, user_id=user_id
        ).first()
        if existing:
            flash('User is already a member of this project.', 'warning')
        else:
            member = ProjectMember(project_id=project.id,
                                   user_id=user_id, role=role)
            db.session.add(member)
            # Notify the added user
            user = User.query.get(user_id)
            notify(user_id,
                   'Added to Project',
                   f'You have been added to project "{project.name}" as {role}.',
                   category='info',
                   link=url_for('pm.project_detail', project_id=project.id))
            log_audit(current_user.id, 'CREATE', 'ProjectMember', None,
                      f'Added {user.full_name} to project "{project.name}" as {role}')
            db.session.commit()
            flash(f'{user.full_name} added as {role}.', 'success')
    return redirect(url_for('pm.project_detail', project_id=project.id))


@bp.route('/projects/<int:project_id>/remove-member/<int:member_id>', methods=['POST'])
@module_required('pm')
def remove_member(project_id, member_id):
    member = ProjectMember.query.get_or_404(member_id)
    project = Project.query.get_or_404(project_id)
    if not _is_pm_or_admin(current_user, project):
        flash('Only the assigned PM or Admin can manage team members.', 'danger')
        return redirect(url_for('pm.project_detail', project_id=project_id))
    user_name = member.user.full_name
    notify(member.user_id,
           'Removed from Project',
           f'You have been removed from project "{member.project.name}".',
           category='warning')
    log_audit(current_user.id, 'DELETE', 'ProjectMember', member_id,
              f'Removed {user_name} from project')
    db.session.delete(member)
    db.session.commit()
    flash(f'{user_name} removed.', 'info')
    return redirect(url_for('pm.project_detail', project_id=project_id))


# ===========================================================================
# TASKS — CRUD
# ===========================================================================
@bp.route('/projects/<int:project_id>/tasks/add', methods=['GET', 'POST'])
@module_required('pm')
def add_task(project_id):
    project = Project.query.get_or_404(project_id)
    if not _is_pm_or_admin(current_user, project):
        abort(403)
    form = TaskForm()
    # Only show project members in the assignment dropdown
    members = ProjectMember.query.filter_by(project_id=project.id).all()
    member_users = [User.query.get(m.user_id) for m in members]
    # Also include the assigned PM
    if project.pm_owner and project.pm_owner not in member_users:
        member_users.insert(0, project.pm_owner)
    form.assigned_to.choices = [(0, '-- Unassigned --')] + \
        [(u.id, u.full_name) for u in member_users if u]

    if form.validate_on_submit():
        assigned = form.assigned_to.data if form.assigned_to.data != 0 else None
        task = Task(
            project_id=project.id,
            title=form.title.data,
            description=form.description.data or '',
            assigned_to=assigned,
            priority=form.priority.data,
            status=form.status.data,
            estimated_hours=form.estimated_hours.data or 0.0,
            due_date=form.due_date.data
        )
        db.session.add(task)

        # Notify assigned employee
        if assigned:
            user = User.query.get(assigned)
            notify(assigned,
                   'Task Assigned',
                   f'You have been assigned task "{task.title}" in project "{project.name}".',
                   category='info',
                   link=url_for('pm.project_detail', project_id=project.id))

        log_audit(current_user.id, 'CREATE', 'Task', None,
                  f'Created task "{task.title}" in project "{project.name}"')
        project.check_and_update_status()
        db.session.commit()
        flash(f'Task "{task.title}" created.', 'success')
        return redirect(url_for('pm.project_detail', project_id=project.id))
    return render_template('pm/task_form.html', form=form, project=project,
                           title='New Task')


@bp.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@module_required('pm')
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    project = task.project
    if not _is_pm_or_admin(current_user, project):
        abort(403)
    form = TaskForm(obj=task)
    # Only show project members in the assignment dropdown
    members = ProjectMember.query.filter_by(project_id=project.id).all()
    member_users = [User.query.get(m.user_id) for m in members]
    if project.pm_owner and project.pm_owner not in member_users:
        member_users.insert(0, project.pm_owner)
    form.assigned_to.choices = [(0, '-- Unassigned --')] + \
        [(u.id, u.full_name) for u in member_users if u]

    if form.validate_on_submit():
        old_status = task.status
        old_assigned = task.assigned_to
        new_assigned = form.assigned_to.data if form.assigned_to.data != 0 else None

        task.title = form.title.data
        task.description = form.description.data or ''
        task.assigned_to = new_assigned
        task.priority = form.priority.data
        task.status = form.status.data
        task.estimated_hours = form.estimated_hours.data or 0.0
        task.due_date = form.due_date.data

        # Notify: task reassigned to new person
        if new_assigned and new_assigned != old_assigned:
            notify(new_assigned,
                   'Task Assigned',
                   f'You have been assigned task "{task.title}" in project "{task.project.name}".',
                   category='info',
                   link=url_for('pm.project_detail', project_id=task.project_id))

        # Notify: task status updated → tell assigned employee
        if old_status != task.status and task.assigned_to:
            notify(task.assigned_to,
                   'Task Updated',
                   f'Task "{task.title}" status changed to {task.status}.',
                   category='info',
                   link=url_for('pm.project_detail', project_id=task.project_id))

        # Notify PM when task is completed
        if task.status == 'Done' and old_status != 'Done':
            project = task.project
            notify(project.created_by,
                   'Task Completed',
                   f'Task "{task.title}" in project "{project.name}" has been marked as Done.',
                   category='success',
                   link=url_for('pm.project_detail', project_id=project.id))

            # Check if project is delayed after update
            if project.is_delayed:
                notify(project.created_by,
                       'Project Delayed',
                       f'Project "{project.name}" is past its deadline.',
                       category='warning',
                       link=url_for('pm.project_detail', project_id=project.id))

        log_audit(current_user.id, 'UPDATE', 'Task', task.id,
                  f'Updated task "{task.title}"')
        task.project.check_and_update_status()
        db.session.commit()
        flash(f'Task "{task.title}" updated.', 'success')
        return redirect(url_for('pm.project_detail', project_id=task.project_id))
    return render_template('pm/task_form.html', form=form, project=task.project,
                           title='Edit Task', task=task)


@bp.route('/tasks/<int:task_id>/delete', methods=['POST'])
@module_required('pm')
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    project_id = task.project_id
    log_audit(current_user.id, 'DELETE', 'Task', task_id,
              f'Deleted task "{task.title}"')
    db.session.delete(task)
    db.session.commit()
    
    project = Project.query.get(project_id)
    if project:
        project.check_and_update_status()
        db.session.commit()
        
    flash('Task deleted.', 'info')
    return redirect(url_for('pm.project_detail', project_id=project_id))


@bp.route('/tasks/<int:task_id>/log-hours', methods=['POST'])
@module_required('pm')
def log_task_hours(task_id):
    task = Task.query.get_or_404(task_id)
    if task.assigned_to != current_user.id:
        abort(403)
        
    actual_hours = request.form.get('actual_hours', type=float)
    if actual_hours is not None and actual_hours >= 0:
        task.actual_hours = actual_hours
        
        # Optionally mark as Done if user checks the box
        if request.form.get('mark_done') == 'on':
            old_status = task.status
            task.status = 'Done'
            
            if old_status != 'Done':
                project = task.project
                notify(project.created_by,
                       'Task Completed',
                       f'Task "{task.title}" in project "{project.name}" has been marked as Done.',
                       category='success',
                       link=url_for('pm.project_detail', project_id=project.id))
        
        task.project.check_and_update_status()
        db.session.commit()
        flash(f'Logged {actual_hours} hours for "{task.title}".', 'success')
    else:
        flash('Invalid hours value.', 'danger')
        
    return redirect(url_for('pm.project_detail', project_id=task.project_id))


# ===========================================================================
# MILESTONES — CRUD
# ===========================================================================
@bp.route('/projects/<int:project_id>/milestones/add', methods=['GET', 'POST'])
@module_required('pm')
def add_milestone(project_id):
    project = Project.query.get_or_404(project_id)
    form = MilestoneForm()
    if form.validate_on_submit():
        # Duplicate title check within project
        existing = Milestone.query.filter_by(
            project_id=project.id, title=form.title.data.strip()
        ).first()
        if existing:
            flash(f'Milestone "{form.title.data}" already exists in this project.', 'danger')
            return render_template('pm/milestone_form.html', form=form,
                                   project=project, title='New Milestone')

        milestone = Milestone(
            project_id=project.id,
            title=form.title.data.strip(),
            description=form.description.data or '',
            deadline=form.deadline.data,
            status=form.status.data
        )
        db.session.add(milestone)
        log_audit(current_user.id, 'CREATE', 'Milestone', None,
                  f'Created milestone "{milestone.title}" in project "{project.name}"')
        db.session.commit()
        flash(f'Milestone "{milestone.title}" created.', 'success')
        return redirect(url_for('pm.project_detail', project_id=project.id))
    return render_template('pm/milestone_form.html', form=form,
                           project=project, title='New Milestone')


@bp.route('/milestones/<int:milestone_id>/edit', methods=['GET', 'POST'])
@module_required('pm')
def edit_milestone(milestone_id):
    milestone = Milestone.query.get_or_404(milestone_id)
    form = MilestoneForm(obj=milestone)
    if form.validate_on_submit():
        old_status = milestone.status
        milestone.title = form.title.data.strip()
        milestone.description = form.description.data or ''
        milestone.deadline = form.deadline.data
        milestone.status = form.status.data

        # Notify PM when milestone completed
        if milestone.status == 'Completed' and old_status != 'Completed':
            project = milestone.project
            notify(project.created_by,
                   'Milestone Completed',
                   f'Milestone "{milestone.title}" in project "{project.name}" is complete.',
                   category='success',
                   link=url_for('pm.project_detail', project_id=project.id))

        log_audit(current_user.id, 'UPDATE', 'Milestone', milestone.id,
                  f'Updated milestone "{milestone.title}"')
        db.session.commit()
        flash(f'Milestone "{milestone.title}" updated.', 'success')
        return redirect(url_for('pm.project_detail',
                                project_id=milestone.project_id))
    return render_template('pm/milestone_form.html', form=form,
                           project=milestone.project,
                           title='Edit Milestone', milestone=milestone)


@bp.route('/milestones/<int:milestone_id>/delete', methods=['POST'])
@module_required('pm')
def delete_milestone(milestone_id):
    milestone = Milestone.query.get_or_404(milestone_id)
    project_id = milestone.project_id
    log_audit(current_user.id, 'DELETE', 'Milestone', milestone_id,
              f'Deleted milestone "{milestone.title}"')
    db.session.delete(milestone)
    db.session.commit()
    flash('Milestone deleted.', 'info')
    return redirect(url_for('pm.project_detail', project_id=project_id))


# ===========================================================================
# REST API ENDPOINTS (JSON)
# ===========================================================================

# ---- Projects API ---------------------------------------------------------
@bp.route('/api/projects', methods=['GET'])
@module_required('pm')
def api_projects():
    """GET all projects with progress."""
    projects = Project.query.order_by(Project.created_at.desc()).all()
    data = []
    for p in projects:
        data.append({
            'id': p.id,
            'name': p.name,
            'status': p.status,
            'progress': p.progress,
            'start_date': p.start_date.isoformat() if p.start_date else None,
            'end_date': p.end_date.isoformat() if p.end_date else None,
            'deadline': p.deadline.isoformat() if p.deadline else None,
            'is_delayed': p.is_delayed,
            'members_count': p.members.count(),
            'tasks_count': p.tasks.count(),
            'milestones_count': p.milestones.count(),
            'created_by': p.creator.full_name,
            'created_at': p.created_at.isoformat()
        })
    return jsonify({'projects': data, 'total': len(data)})


@bp.route('/api/projects/<int:project_id>', methods=['GET'])
@module_required('pm')
def api_project_detail(project_id):
    """GET single project with full details."""
    p = Project.query.get_or_404(project_id)
    members = [{'id': m.id, 'user_id': m.user_id, 'name': m.user.full_name,
                'role': m.role} for m in p.members]
    tasks = [{'id': t.id, 'title': t.title, 'status': t.status,
              'priority': t.priority, 'due_date': t.due_date.isoformat() if t.due_date else None,
              'assigned_to': t.assignee.full_name if t.assignee else None}
             for t in p.tasks]
    milestones = [{'id': ms.id, 'title': ms.title, 'status': ms.status,
                   'deadline': ms.deadline.isoformat() if ms.deadline else None,
                   'is_overdue': ms.is_overdue}
                  for ms in p.milestones]
    return jsonify({
        'id': p.id, 'name': p.name, 'description': p.description,
        'status': p.status, 'progress': p.progress,
        'start_date': p.start_date.isoformat() if p.start_date else None,
        'end_date': p.end_date.isoformat() if p.end_date else None,
        'deadline': p.deadline.isoformat() if p.deadline else None,
        'is_delayed': p.is_delayed,
        'created_by': p.creator.full_name,
        'members': members, 'tasks': tasks, 'milestones': milestones
    })


# ---- Tasks API -----------------------------------------------------------
@bp.route('/api/projects/<int:project_id>/tasks', methods=['GET'])
@module_required('pm')
def api_project_tasks(project_id):
    """GET all tasks for a project."""
    project = Project.query.get_or_404(project_id)
    tasks = Task.query.filter_by(project_id=project_id)\
        .order_by(Task.created_at.desc()).all()
    data = [{'id': t.id, 'title': t.title, 'description': t.description,
             'status': t.status, 'priority': t.priority,
             'assigned_to': t.assignee.full_name if t.assignee else None,
             'due_date': t.due_date.isoformat() if t.due_date else None,
             'created_at': t.created_at.isoformat()}
            for t in tasks]
    return jsonify({'project': project.name, 'tasks': data, 'total': len(data)})


# ---- Milestones API ------------------------------------------------------
@bp.route('/api/projects/<int:project_id>/milestones', methods=['GET'])
@module_required('pm')
def api_project_milestones(project_id):
    """GET all milestones for a project."""
    project = Project.query.get_or_404(project_id)
    milestones = Milestone.query.filter_by(project_id=project_id)\
        .order_by(Milestone.deadline.asc().nullslast()).all()
    data = [{'id': ms.id, 'title': ms.title, 'description': ms.description,
             'status': ms.status,
             'deadline': ms.deadline.isoformat() if ms.deadline else None,
             'is_overdue': ms.is_overdue,
             'created_at': ms.created_at.isoformat()}
            for ms in milestones]
    return jsonify({'project': project.name, 'milestones': data, 'total': len(data)})


# ---- Team API ------------------------------------------------------------
@bp.route('/api/projects/<int:project_id>/members', methods=['GET'])
@module_required('pm')
def api_project_members(project_id):
    """GET all members of a project."""
    project = Project.query.get_or_404(project_id)
    members = ProjectMember.query.filter_by(project_id=project_id).all()
    data = [{'id': m.id, 'user_id': m.user_id, 'name': m.user.full_name,
             'role': m.role, 'joined_at': m.joined_at.isoformat() if m.joined_at else None}
            for m in members]
    return jsonify({'project': project.name, 'members': data, 'total': len(data)})


# ---- Notifications API ---------------------------------------------------
@bp.route('/api/notifications', methods=['GET'])
@module_required('pm')
def api_notifications():
    """GET notifications for current user."""
    notifs = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc()).limit(20).all()
    data = [{'id': n.id, 'title': n.title, 'message': n.message,
             'category': n.category, 'is_read': n.is_read,
             'link': n.link, 'created_at': n.created_at.isoformat()}
            for n in notifs]
    unread_count = Notification.query.filter_by(
        user_id=current_user.id, is_read=False).count()
    return jsonify({'notifications': data, 'unread_count': unread_count})
