from django.urls import path
app_name = 'useraccount'
from . import views

urlpatterns = [
    path('edit_profile/', views.EditMyProfileView.as_view(), name='edit_profile'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('accounts/login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('password_reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('notification/', views.NotificationView.as_view(), name='notification'),

    # Тикеты
    path('tickets/', views.TicketsView.as_view(), name='tickets'),
    path('tickets/create/', views.TicketCreateView.as_view(), name='ticket_create'),
    path('tickets/delete/', views.TicketDeleteView.as_view(), name='ticket_delete'),
    path('tickets/<uuid:ticket_id>/add_comment/', views.TicketCommentCreateView.as_view(), name='add_comment'),
    path('tickets/<slug:pk>/', views.TicketMessageView.as_view(), name='ticket_message'),
    # Вылпаты
    path('withdraw/', views.WithdrawPage.as_view(), name='withdraw'),
    path('withdraw/create/', views.WithdrawCreateView.as_view(), name='withdraw_create'),
    # Карта
    path('card/create/', views.CardsCreateView.as_view(), name='cards_create'),
    path('card/update/<int:pk>/', views.CardsUpdateView.as_view(), name='cards_update'),

]