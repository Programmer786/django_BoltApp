from django.urls import path

from authentication import views

urlpatterns = [
    path('login/', views.login_page, name="login"),
    path('register-user/', views.register_page, name="register"),
    path('activate/<email_token>/', views.activate_email, name="activate_email"),
    path('logout/', views.logout_page, name="logout_page"),
    path('users-profile/<user_id>', views.users_profile, name="users_profile"),
    path('update-profile/', views.update_profile, name='update_profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('disable/', views.disable_role_user, name='disable_role_user'),
    path('enable/', views.enable_role_user, name='enable_role_user'),

    path('update-profile-image/', views.update_profile_image, name='update_profile_image'),
    path('manage-accounts/', views.manage_accounts, name="manage_accounts"),
    path('add-account/', views.add_account, name="add_account"),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('users/<int:user_id>/change-password/', views.admin_change_password, name='admin_change_password'),
    path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:user_id>/verify-email/', views.verify_user_email, name='verify_user_email'),
    path('logs-activity/', views.logs_activity, name="logs_activity"),
    path('manage-notes/', views.manage_notes, name="manage_notes"),
    path('add-note/', views.add_note, name="add_note"),
    path('notes/<int:note_id>/update/', views.update_note, name="update_note"),
    path('notes/<int:note_id>/delete/', views.delete_note, name="delete_note"),
]
