from django.urls import path
from .views import *

app_name = 'chat'

urlpatterns = [
    path('', home, name='home'),

    path('analyze/',analyze_idea, name='analyze_idea'),
    path('results/',analysis_results, name='analysis_results'),

    path('ideas/', idea_list, name='idea_list'),
    path('ideas/<int:idea_id>/', idea_detail, name='idea_detail'),
    path('public-ideas/<int:idea_id>/', public_idea_detail, name='public_idea_detail'),
    path('ideas/<int:idea_id>/make-public/', make_idea_public, name='make_idea_public'),
    path('ideas/<int:idea_id>/comment/', add_comment, name='add_comment'),
    path('notifications/', notifications, name='notifications'),
    path('update_idea/<int:idea_id>/', update_idea, name='update_idea'),

    path('get-notification-count/', get_notification_count, name='get_notification_count'),


    path('public-ideas/', public_idea_list, name='public_idea_list'),

    path('upvote/<int:idea_id>/',upvote_idea, name='upvote_idea'),


    path('toggle_idea_visibility/<int:idea_id>/',toggle_idea_visibility, name='toggle_idea_visibility'),
    

    path('pitch/',start_pitch,name='start_pitch'),

    path('idea/<int:idea_id>/chat/', chat_view, name='chat_view'),
    path('idea/<int:idea_id>/clear_session/', clear_session, name='clear_session'),
    path('idea/<int:idea_id>/get_conversation/', get_conversation, name='get_conversation'),

    path('idea/<int:idea_id>/market_chat/', market_chat, name='market_chat'),
    path('idea/<int:idea_id>/clear_session_market/', clear_session_market, name='clear_session_market'),
    path('idea/<int:idea_id>/get_conversation_market/', get_conversation_market, name='get_conversation_market'),

    path('idea/<int:idea_id>/financial_chat/', financial_chat, name='financial_chat'),
    path('idea/<int:idea_id>/clear_session_financial/', clear_session_financial, name='clear_session_financial'),
    path('idea/<int:idea_id>/get_conversation_financial/', get_conversation_financial, name='get_conversation_financial'),

    path('idea/<int:idea_id>/cold_calls_chat/', cold_calls_chat, name='cold_calls_chat'),
    path('idea/<int:idea_id>/clear_session_cold_calls/', clear_session_cold_calls, name='clear_session_cold_calls'),
    path('idea/<int:idea_id>/get_conversation_cold_calls/', get_conversation_cold_calls, name='get_conversation_cold_calls'),
    path('upvote/<int:idea_id>/', upvote_idea, name='upvote_idea'),

    path('submit_feedback/',submit_feedback, name='submit_feedback'),
    

    path('interview/', interview_view, name='interview_view'),
    path('clear-interview-context/', clear_interview_context_view, name='clear_interview_context'),


    path('about/', about, name='about'),
    
    path('contact/', contact, name='contact'),
    path('contact-form/', ContactFormView.as_view(), name='contact_form'),
    

    path('login/', sign_in_or_sign_up, name='sign_in_or_sign_up'),
    path('verify-otp/<str:signed_email>/',verify_otp, name='verify_otp'),
    path('verify-otp-signup/<str:signed_email>/<str:signed_username>/',verify_otp_signup, name='verify_otp_signup'),
    path('logout/', logout_view, name='logout'),

    path('join-community/', JoinCommunityView.as_view(), name='join_community'),

    path('upgrade/', initiate_payment, name='initiate_payment'),
    path('payment/success/', payment_success, name='payment_success'),

    path('check-premium-status/',check_premium_status, name='check_premium_status'),
    

]
