from django.urls import path
from cards import views

urlpatterns = [
    path('manage-cards/', views.manage_cards, name="manage_cards"),
    path('report-cards/', views.report_cards, name="report_cards"),
    path('export/cards/csv/', views.export_cards_csv, name='export_cards_csv'),
    path('add-card-manual/', views.add_card_manual, name='add_card_manual'),
    path('card/update/<uuid:uid>/', views.update_card, name='update_card'),
    path('pending_cards/', views.pending_cards, name="pending_cards"),
    path('cards/approve_reject/<uuid:uid>/', views.approve_reject_cards, name='approve_reject_cards'),
    path('export_card/<str:model_name>/<str:city>/', views.export_card_and_city_excel, name='export_card_and_city_excel'),
    path('unpaid-cards/', views.unpaid_cards, name="unpaid_cards"),
    path('paid-cards/', views.paid_cards, name="paid_cards"),
    path('report-paid-cards/', views.report_paid_cards, name="report_paid_cards"),
    path('card/update_unpaid/<uuid:uid>/', views.update_unpaid_card, name='update_unpaid_card'),
    path('cards/update-field/<uuid:uid>/', views.update_card_field, name='update_card_field'),
    path('cancelled-cards/', views.cancelled_cards, name="cancelled_cards"),
    path('card/cancel/<uuid:uid>/', views.cancel_card, name='cancel_card'),
    path('card/activate/<uuid:uid>/', views.activate_card, name='activate_card'),
    path('holded-cards/', views.holded_cards, name="holded_cards"),
    path('card/hold/<uuid:uid>/', views.hold_card, name='hold_card'),
    path('card/unhold/<uuid:uid>/', views.unhold_card, name='unhold_card'),
]