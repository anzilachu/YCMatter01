import os
from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
from groq import Groq
from django.views.decorators.csrf import csrf_exempt
from django.core.signing import Signer, BadSignature
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from .forms import SignUpForm, OTPVerificationForm, SignInForm
from .models import Otp, User
import datetime
from django.core.mail import send_mail
from django.utils import timezone
from django.shortcuts import render, HttpResponse, redirect
from django.core.mail import send_mail
from django.contrib import messages
from django.conf import settings
import random
import string
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from dotenv import load_dotenv
from .models import StartupIdea, User, Payment,Transaction
from .groq_analysis import analyze_startup, parse_scores, format_analysis_text
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Max
import logging
from django.contrib import messages
from django.shortcuts import render, redirect
import re

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.http import JsonResponse
from .models import StartupIdea, Comment, Notification

logger = logging.getLogger(__name__)

signer = Signer()

load_dotenv()

import json

def home(request):
    return render(request, "chat/home.html")

@login_required(login_url=reverse_lazy('chat:sign_in_or_sign_up'))
def analyze_idea(request):
    if request.method == 'POST':
        idea = request.POST.get('idea')
        analysis = ""
        scores = {}
        attempts = 0
        
        # Retry mechanism
        while attempts < 3:  # Limit the number of attempts to avoid infinite loops
            analysis = analyze_startup(idea)
            scores = parse_scores(analysis)
            
            if scores:  # Check if scores were successfully parsed
                break  # Exit the loop if scores are found
            
            attempts += 1  # Increment the attempt counter

        formatted_analysis = format_analysis_text(analysis)
        
        # Save the idea and analysis to the database
        startup_idea = StartupIdea.objects.create(
            user=request.user,
            idea=idea,
            analysis=formatted_analysis,
            scores=scores
        )
        
        return redirect('chat:idea_detail', idea_id=startup_idea.id)
    
    return render(request, 'chat/home.html')


@login_required(login_url=reverse_lazy('chat:sign_in_or_sign_up'))
def analysis_results(request):
    scores = request.session.get('scores', {})
    analysis = request.session.get('analysis', '')
    return render(request, 'chat/results.html', {
        'scores': json.dumps(scores),
        'analysis': analysis
    })


@login_required(login_url=reverse_lazy('chat:sign_in_or_sign_up'))
def idea_list(request):
    user_ideas = StartupIdea.objects.filter(user=request.user).order_by('-id')
    public_ideas = StartupIdea.objects.filter(is_public=True).exclude(user=request.user).order_by('-id')
    return render(request, 'chat/idea_list.html', {'user_ideas': user_ideas, 'public_ideas': public_ideas})


@login_required(login_url=reverse_lazy('chat:sign_in_or_sign_up'))
def make_idea_public(request, idea_id):
    idea = get_object_or_404(StartupIdea, id=idea_id, user=request.user)
    idea.is_public = True
    idea.save()
    return JsonResponse({'status': 'success'})

from django.http import Http404

@login_required(login_url=reverse_lazy('chat:sign_in_or_sign_up'))
def public_idea_detail(request, idea_id):
    idea = get_object_or_404(StartupIdea, id=idea_id)
    
    if idea.is_public or idea.user == request.user:
        comments = idea.comments.all().order_by('-created_at')
        return render(request, 'chat/public_idea_detail.html', {
            'idea': idea,
            'comments': comments,
            'scores': json.dumps(idea.scores),
            'analysis': idea.analysis,
        })
    else:
        return redirect('chat:idea_list')

@login_required(login_url=reverse_lazy('chat:sign_in_or_sign_up'))
def add_comment(request, idea_id):
    if request.method == 'POST':
        idea = get_object_or_404(StartupIdea, id=idea_id, is_public=True)
        content = request.POST.get('content')
        comment = Comment.objects.create(startup_idea=idea, user=request.user, content=content)

        if idea.user != request.user:
            Notification.objects.create(
                user=idea.user,
                content=f"{request.user.username} commented on your idea: {content[:50]}...",
                comment=comment
            )

        return JsonResponse({'status': 'success', 'comment_id': comment.id})
    return JsonResponse({'status': 'error'}, status=400)


@login_required(login_url=reverse_lazy('chat:sign_in_or_sign_up'))
def toggle_idea_visibility(request, idea_id):
    idea = get_object_or_404(StartupIdea, id=idea_id, user=request.user)
    idea.is_public = not idea.is_public
    idea.save()
    return JsonResponse({'status': 'success', 'is_public': idea.is_public})


@login_required(login_url=reverse_lazy('chat:sign_in_or_sign_up'))
def notifications(request):
    user_notifications = request.user.notifications.order_by('-created_at')
    unread_count = user_notifications.filter(is_read=False).count()
    
    # Mark all notifications as read when the user views them
    user_notifications.update(is_read=True)
    
    return render(request, 'chat/notifications.html', {
        'notifications': user_notifications,
        'unread_count': unread_count,
    })

def get_unread_notifications_count(request):
    if request.user.is_authenticated:
        return request.user.notifications.filter(is_read=False).count()
    return 0

@login_required
def get_notification_count(request):
    unread_count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({'count': unread_count})


@login_required(login_url=reverse_lazy('chat:sign_in_or_sign_up'))
def idea_detail(request, idea_id):
    idea = get_object_or_404(StartupIdea, id=idea_id, user=request.user)
    return render(request, 'chat/results.html', {
        'scores': json.dumps(idea.scores),
        'analysis': idea.analysis,
        'idea': idea  # Pass the entire idea object
    })

from django.core.paginator import Paginator
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required(login_url=reverse_lazy('chat:sign_in_or_sign_up'))
def public_idea_list(request):
    # Determine the filter based on user input, default to 'recent'
    filter_by = request.GET.get('filter', 'recent')

    # Filter ideas based on selection
    if filter_by == 'upvoted':
        public_ideas = StartupIdea.objects.filter(is_public=True).exclude(user=request.user).order_by('-upvotes', '-created_at')
    else:
        public_ideas = StartupIdea.objects.filter(is_public=True).exclude(user=request.user).order_by('-created_at')

    # Pagination: 9 ideas per page
    paginator = Paginator(public_ideas, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'chat/public_idea_list.html', {
        'page_obj': page_obj,
        'filter_by': filter_by
    })
from django.http import HttpResponseRedirect

def update_idea(request, idea_id):
    if request.method == 'POST':
        idea = get_object_or_404(StartupIdea, id=idea_id)
        idea.idea = request.POST.get('idea')
        idea.summary = request.POST.get('description')
        idea.save()
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import StartupIdea

@login_required(login_url=reverse_lazy('chat:sign_in_or_sign_up'))
def upvote_idea(request, idea_id):
    idea = get_object_or_404(StartupIdea, id=idea_id, is_public=True)
    user = request.user

    if user not in idea.upvotes.all():
        idea.upvotes.add(user)
        if idea.user != user:
            Notification.objects.create(
                user=idea.user,
                content=f"{user.username} upvoted your idea: '{idea.idea[:50]}...'"
            )
        return JsonResponse({'status': 'success', 'upvotes': idea.upvote_count()})
    else:
        idea.upvotes.remove(user)
        return JsonResponse({'status': 'success', 'upvotes': idea.upvote_count()})

import logging

logger = logging.getLogger(__name__)

@login_required(login_url=reverse_lazy('chat:sign_in_or_sign_up'))
@csrf_exempt
def chat_view(request, idea_id):
    idea = get_object_or_404(StartupIdea, id=idea_id, user=request.user)
    
    conversation_key = f'conversation_{idea_id}'
    
    if conversation_key not in request.session:
        username = request.user.username if request.user.is_authenticated else "there"
        
        system_message = {
            "role": "system",
            "content": f"You are an AI who have all the publically available data of y combinator youtube videos and real founder's experience based on that give insights, ask question to brainstorm the '{idea.idea}', the reply should really short, like a friendly chat, sometime you should say something funny to keep the coonversation active"
        }
        
        # Generate an initial question based on the idea
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        initial_prompt = f"""
                    Regarding the startup idea '{idea.idea}':

                    1. First, ask the user if they've only just thought of this idea or if they've studied it before.

                    2. If they've studied it:
                    Generate a thoughtful, specific, and concise question that:
                    - Shows understanding of the concept
                    - Encourages deeper thinking about an important aspect of the startup
                    - Is engaging and brief

                    3. If they haven't studied it:
                    Act as a friendly conversation partner. Ask basic, exploratory questions to help the user develop their idea further, as if two friends were casually discussing a startup concept.

                    Provide only the question or conversation starter, without any additional details.
                    """
        
        initial_completion = client.chat.completions.create(
            messages=[
                system_message,
                {"role": "user", "content": initial_prompt}
            ],
            model="llama3-8b-8192",
        )
        initial_question = initial_completion.choices[0].message.content
        
        request.session[conversation_key] = [
            system_message,
            {
                "role": "assistant",
                "content": f"Hello {username}! {initial_question}"
            }
        ]

    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        user_message = request.POST.get("message")
        logger.info(f"Received message: {user_message}")

        conversation = request.session.get(conversation_key, [])
        conversation.append({"role": "user", "content": user_message})

        try:
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            chat_completion = client.chat.completions.create(
                messages=conversation,
                model="llama3-8b-8192",
            )
            response_message = chat_completion.choices[0].message.content
            logger.info(f"AI response: {response_message}")

            conversation.append({"role": "assistant", "content": response_message})
            request.session[conversation_key] = conversation

            return JsonResponse({"response_message": response_message})
        except Exception as e:
            logger.error(f"Error in AI processing: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    return render(request, "chat/chat.html", {'idea': idea})

@csrf_exempt
def clear_session(request, idea_id):
    conversation_key = f'conversation_{idea_id}'
    if conversation_key in request.session:
        del request.session[conversation_key]
    return HttpResponse(status=200)

def get_conversation(request, idea_id):
    conversation_key = f'conversation_{idea_id}'
    conversation = request.session.get(conversation_key, [])
    filtered_conversation = [msg for msg in conversation if msg['role'] != 'system']
    return JsonResponse(filtered_conversation, safe=False)

def start_pitch(request):
    return render(request, "Pitch.html")



@login_required(login_url=reverse_lazy('chat:sign_in_or_sign_up'))
@csrf_exempt
def interview_view(request):
    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        username = request.user.username if request.user.is_authenticated else "there"
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        
        # Check if it's a custom pitch
        if request.headers.get('Content-Type') == 'application/json':
            data = json.loads(request.body)
            investor_name = data.get('investorName', 'an investor')
            industry_focus = data.get('industryFocus', '')
            investment_stage = data.get('investmentStage', '')
            
            system_message = (
                f"Your name is YCMatter AI and you are {investor_name}, an investor "
                f"{'focusing on ' + industry_focus if industry_focus else ''} "
                f"{'interested in ' + investment_stage + ' investments' if investment_stage else ''}. "
                f"You are talking to {username}, who wants to pitch their startup. "
                "Ask follow-up questions like an interview which is only 10 minutes long. "
                "After listening to the user and asking follow-up questions, "
                "provide honest thoughts about the startup. You can also be critical if necessary."
            )
            
            request.session['conversation_context'] = [{"role": "system", "content": system_message}]
            return JsonResponse({"message": "Custom pitch context set"})
        
        # Rest of your existing code for handling regular messages
        user_message = request.POST.get("message")
        context = request.session.get('conversation_context', [])

        if not context:
            context.append({"role": "system", "content": f"Your name is  YCMatter AI and you are a investor, you are talking to {username}, who want to pitch his startup, you ask follow up questions like an interview which is only 10 minutes, and after listening to the user after follow up questions you should tell really honest thoughts about the startup, you can also be mean"})

        context.append({"role": "user", "content": user_message})
        
        try:
            chat_completion = client.chat.completions.create(
                messages=context,
                model="llama3-8b-8192",
            )
            response_message = chat_completion.choices[0].message.content
            context.append({"role": "assistant", "content": response_message})
            request.session['conversation_context'] = context
            
            return JsonResponse({"response_message": response_message})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        
    
    return render(request, "chat/interview_chat.html", {'is_premium': request.user.is_premium})



@login_required(login_url=reverse_lazy('chat:sign_in_or_sign_up'))
@csrf_exempt
def clear_interview_context_view(request):
    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            if 'conversation_context' in request.session:
                del request.session['conversation_context'] 
            return JsonResponse({"message": "Conversation context cleared successfully"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request"}, status=400)


def contact(request):
    return render(request,'contact.html')

@method_decorator(csrf_exempt, name='dispatch')
class ContactFormView(View):
    def post(self, request):
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        
        if not name or not email or not message:
            return JsonResponse({'success': False, 'message': 'All fields are required.'})

        subject = f'Contact Form Submission from {name}'
        body = f'Name: {name}\nEmail: {email}\n\nMessage:\n{message}'
        try:
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [settings.DEFAULT_FROM_EMAIL])
            return JsonResponse({'success': True, 'message': 'Your message has been sent successfully!'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

def about(request):
    return render(request,'about.html')

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(email, otp):
    subject = 'Your OTP Code'
    message = f'Your OTP code is {otp}. It is valid for 1 minute.'
    email_from = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    send_mail(subject, message, email_from, recipient_list)

@csrf_exempt
def sign_in_or_sign_up(request):
    if request.method == 'POST':
        if 'sign-in' in request.POST:
            email = request.POST.get('email')
            user = User.objects.filter(email=email).first()
            if user:
                otp = generate_otp()
                expiry_time = timezone.now() + datetime.timedelta(minutes=10)
                Otp.objects.update_or_create(email=email, defaults={'otp': otp, 'expiry_time': expiry_time})
                send_otp_email(email, otp)
                signed_email = signer.sign(email)
                return redirect('chat:verify_otp', signed_email=signed_email)
            else:
                messages.error(request, 'Email not found. Please sign up.')

        elif 'sign-up' in request.POST:
            username = request.POST.get('username')
            email = request.POST.get('email')
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already registered. Please sign in.')
            else:
                otp = generate_otp()
                expiry_time = timezone.now() + datetime.timedelta(minutes=10)
                Otp.objects.update_or_create(email=email, defaults={'otp': otp, 'expiry_time': expiry_time})
                send_otp_email(email, otp)
                messages.success(request, 'OTP sent to your email. Please verify to complete registration.')
                signed_email = signer.sign(email)
                signed_username = signer.sign(username)
                return redirect('chat:verify_otp_signup', signed_email=signed_email, signed_username=signed_username)

    return render(request, 'login.html')


def verify_otp(request, signed_email):
    try:
        email = signer.unsign(signed_email)
    except BadSignature:
        messages.error(request, 'Invalid or tampered data.')
        return render(request, 'verify_otp.html')

    if request.method == 'POST':
        otp = request.POST.get('otp')
        otp_record = Otp.objects.filter(email=email).first()
        if otp_record and otp_record.otp == otp and not otp_record.is_expired():
            Otp.objects.filter(email=email).delete()
            user = User.objects.get(email=email)
            login(request, user)
            return redirect('chat:home')
        else:
            messages.error(request, 'Invalid or expired OTP.')

    return render(request, 'verify_otp.html', {'email': email})



def verify_otp_signup(request, signed_email, signed_username):
    try:
        email = signer.unsign(signed_email)
        username = signer.unsign(signed_username)
    except BadSignature:
        messages.error(request, 'Invalid or tampered data.')
        return render(request, 'verify_otp.html')

    if request.method == 'POST':
        otp = request.POST.get('otp')
        otp_record = Otp.objects.filter(email=email).first()
        if otp_record and otp_record.otp == otp and not otp_record.is_expired():
            user = User.objects.create_user(username=username, email=email, password=None)
            Otp.objects.filter(email=email).delete()
            login(request, user)
            messages.success(request, 'OTP verified and registration successful. You are now logged in.')
            return redirect('chat:home')
        else:
            messages.error(request, 'Invalid or expired OTP.')

    return render(request, 'verify_otp.html', {'email': email})

def logout_view(request):
    logout(request)
    return redirect('chat:home')


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from .models import Community

@method_decorator(csrf_exempt, name='dispatch')
class JoinCommunityView(View):
    def post(self, request):
        email = request.POST.get('email')
        if not email:
            return JsonResponse({'success': False, 'message': 'Email is required.'})

        if Community.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message': 'Email is already in the community.'})

        community_member = Community(email=email)
        community_member.save()
        return JsonResponse({'success': True, 'message': 'Successfully joined the community.'})
    

def chatcategory(request):
    return render(request,'chat/chat_category.html')


@login_required(login_url=reverse_lazy('chat:sign_in_or_sign_up'))
@csrf_exempt
def market_chat(request, idea_id):
    idea = get_object_or_404(StartupIdea, id=idea_id, user=request.user)
    
    conversation_key = f'market_conversation_{idea_id}'
    
    if conversation_key not in request.session:
        username = request.user.username if request.user.is_authenticated else "there"
        request.session[conversation_key] = [
            {
                "role": "system",
                "content": "You are an AI assistant focused on helping users make their startup ideas succeed in the market, act like a real friend who gonna make his friends idea to win the market at all cost. Provide detailed strategies, planning advice, and insights to ensure the idea can win in the market. Offer actionable recommendations on market potential, optimal strategies, and best practices . Use data from recent surveys, Y Combinator talks, and other relevant sources to support your guidance. Respond concisely and clearly, focusing on how to make the startup idea successful. Avoid unrelated topics and ensure your responses are actionable and motivating. keep the response really short like a real conversation"
            },
            {
                "role": "assistant",
                "content": f"Hello {username}, let's explore how to make your idea, {idea.idea}, a market winner. I'll provide strategies, planning tips, and insights to help you succeed."
            }
        ]


    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        user_message = request.POST.get("message")

        conversation = request.session[conversation_key]
        conversation.append({"role": "user", "content": user_message})

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        chat_completion = client.chat.completions.create(
            messages=conversation,
            model="llama3-8b-8192",
        )
        response_message = chat_completion.choices[0].message.content

        formatted_response_message = format_response_market(response_message)

        conversation.append({"role": "assistant", "content": formatted_response_message})

        request.session[conversation_key] = conversation

        return JsonResponse({"response_message": formatted_response_message})

    return render(request, "chat/market_chat.html", {'idea': idea})

def format_response_market(response_message):
    # Replace newlines with <br> tags
    formatted_message = response_message.replace("\n", "<br>")
    
    # Bold text between asterisks
    formatted_message = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', formatted_message)
    formatted_message = re.sub(r'\*(.*?)\*', r'<b>\1</b>', formatted_message)
    
    # Format numbered points
    for i in range(1, 5):
        formatted_message = formatted_message.replace(f"{i}.", f"<br><b>{i}.</b>")
    
    return formatted_message


@csrf_exempt
def clear_session_market(request, idea_id):
    conversation_key = f'market_conversation_{idea_id}'
    if conversation_key in request.session:
        del request.session[conversation_key]
    return HttpResponse(status=200)

def get_conversation_market(request, idea_id):
    conversation_key = f'market_conversation_{idea_id}'
    conversation = request.session.get(conversation_key, [])
    filtered_conversation = [msg for msg in conversation if msg['role'] != 'system']
    return JsonResponse(filtered_conversation, safe=False)


@login_required(login_url=reverse_lazy('chat:sign_in_or_sign_up'))
@csrf_exempt
def financial_chat(request, idea_id):
    idea = get_object_or_404(StartupIdea, id=idea_id, user=request.user)
    
    conversation_key = f'financial_conversation_{idea_id}'
    
    if conversation_key not in request.session:
        username = request.user.username if request.user.is_authenticated else "there"
        request.session[conversation_key] = [
            {
                "role": "system",
                "content": "You are an AI assistant specialized in profit planning for startups. Speak in a friendly, conversational manner. Your goal is to help users maximize their profits through effective planning and strategies. Offer insights into pricing, cost management, and revenue optimization. Keep responses short and focused. After understanding their idea, explain how reach a specific revenue goal involves setting the right price and reaching the right number of customers. Encourage them by showing that this goal is within reach. For subscription models, provide tailored advice on subscription pricing and scaling. keep responses short, dont give all information at once"
            },
            {
                "role": "assistant",
                "content": f"Hey {username}, ready to dive into profit planning for {idea.idea}? Let’s chat about pricing strategies, cost management, and how to hit that profit goal. I’m here to help you make your startup a success!"
            }
        ]


    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        user_message = request.POST.get("message")

        conversation = request.session[conversation_key]
        conversation.append({"role": "user", "content": user_message})

        # Example integration with Groq or other AI service
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        # Example model for AI responses
        chat_completion = client.chat.completions.create(
            messages=conversation,
            model="llama3-8b-8192",
        )
        response_message = chat_completion.choices[0].message.content

        # Formatting the response
        response_message = response_message.replace('\n', '<br>').replace('*', '<b>').replace('*', '</b>')

        conversation.append({"role": "assistant", "content": response_message})

        request.session['financial_conversation'] = conversation

        return JsonResponse({"response_message": response_message})

    return render(request, "chat/financial_chat.html",{'idea': idea})


@csrf_exempt
def clear_session_financial(request, idea_id):
    conversation_key = f'financial_conversation_{idea_id}'
    if conversation_key in request.session:
        del request.session[conversation_key]
    return HttpResponse(status=200)

def get_conversation_financial(request,idea_id):
    conversation_key = f'financial_conversation_{idea_id}'
    conversation = request.session.get(conversation_key, [])
    filtered_conversation = [msg for msg in conversation if msg['role'] != 'system']
    return JsonResponse(filtered_conversation, safe=False)

@login_required(login_url=reverse_lazy('chat:sign_in_or_sign_up'))
@csrf_exempt
def cold_calls_chat(request, idea_id):
    idea = get_object_or_404(StartupIdea, id=idea_id, user=request.user)
    
    conversation_key = f'cold_calls_conversation_{idea_id}'
    
    if conversation_key not in request.session:
        username = request.user.username if request.user.is_authenticated else "there"
        request.session[conversation_key] = [
            {
                "role": "system",
                "content": "You are an AI assistant dedicated to helping users outshine their competitors. Talk in a friendly, encouraging manner. Ask about the user's product or service, the unique innovations they offer, and you identify thier potential competitors and what they are lacking. Based on this information, provide a brief, actionable plan highlighting how to leverage these innovations to surpass competitors. Keep the response focused and motivating, emphasizing practical steps to gain a competitive edge."
            },
            {
                "role": "assistant",
                "content": f"Hey {username}, let’s crush the competition with {idea.idea}! What makes your product or service stand out? What are your competitors missing that you can offer? Let’s use these insights to create a winning strategy!"
            }
        ]


    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        user_message = request.POST.get("message")

        conversation = request.session[conversation_key]
        conversation.append({"role": "user", "content": user_message})

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        chat_completion = client.chat.completions.create(
            messages=conversation,
            model="llama3-8b-8192",
        )
        response_message = chat_completion.choices[0].message.content

        formatted_response_message = format_response(response_message)

        conversation.append({"role": "assistant", "content": formatted_response_message})

        request.session[conversation_key] = conversation

        return JsonResponse({"response_message": formatted_response_message})

    return render(request, "chat/cold_calls_chat.html", {'idea': idea})


def format_response(response_message):

    # Replace newlines with <br> tags
    formatted_message = response_message.replace("\n", "<br>")
    
    # Bold text between asterisks
    formatted_message = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', formatted_message)
    formatted_message = re.sub(r'\*(.*?)\*', r'<b>\1</b>', formatted_message)
    
    # Format numbered points
    for i in range(1, 5):
        formatted_message = formatted_message.replace(f"{i}.", f"<br><b>{i}.</b>")
    
    return formatted_message




@csrf_exempt
def clear_session_cold_calls(request, idea_id):
    conversation_key = f'cold_calls_conversation_{idea_id}'
    if conversation_key in request.session:
        del request.session[conversation_key]
    return HttpResponse(status=200)

def get_conversation_cold_calls(request, idea_id):
    conversation_key = f'cold_calls_conversation_{idea_id}'
    conversation = request.session.get(conversation_key, [])
    filtered_conversation = [msg for msg in conversation if msg['role'] != 'system']
    return JsonResponse(filtered_conversation, safe=False)


from .models import Feedback
from .forms import FeedbackForm

def submit_feedback(request):
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'message': 'Feedback submitted successfully!'})
        else:
            return JsonResponse({'errors': form.errors}, status=400)
    return JsonResponse({'message': 'Invalid request method'}, status=405)


import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@login_required
def initiate_payment(request):
    if request.method == "POST":
        amount = int(request.POST.get('amount', 33500))  # Default to 500 INR in paise
        currency = request.POST.get('currency', 'INR')

        try:
            razorpay_order = client.order.create(dict(amount=amount, currency=currency, payment_capture='0'))

            payment = Payment.objects.create(
                user=request.user,
                payment_id=razorpay_order['id'],
                amount=amount / 100, 
                currency=currency,
                status="INITIATED"
            )

            transaction = Transaction.objects.create(
                payment=payment,
                order_id=razorpay_order['id'],
                status='PENDING'
            )

            logger.info(f"Payment initiated for user {request.user.email}: {payment.payment_id}")

            return JsonResponse({
                'order_id': razorpay_order['id'],
                'amount': amount,
                'currency': currency,
                'razorpay_key': settings.RAZORPAY_KEY_ID
            })

        except Exception as e:
            logger.error(f"Error initiating payment: {str(e)}")
            return JsonResponse({'error': "Unable to initiate payment. Please try again later."}, status=400)

    return render(request, 'upgrade_to_premium.html')




@csrf_exempt
def payment_success(request):
    if request.method == "POST":
        payment_id = request.POST.get('razorpay_payment_id', '')
        order_id = request.POST.get('razorpay_order_id', '')
        signature = request.POST.get('razorpay_signature', '')

        logger.info(f"Received payment callback: payment_id={payment_id}, order_id={order_id}")

        if not all([payment_id, order_id, signature]):
            logger.error("Missing payment details in callback")
            messages.error(request, "Payment details are incomplete. Please contact support.")
            return render(request, 'payment_failed.html')

        try:
            params_dict = {
                'razorpay_payment_id': payment_id,
                'razorpay_order_id': order_id,
                'razorpay_signature': signature
            }
            client.utility.verify_payment_signature(params_dict)

            transaction = Transaction.objects.select_related('payment__user').get(order_id=order_id)
            payment = transaction.payment
            user = payment.user

            payment.status = "SUCCESS"
            payment.razorpay_payment_id = payment_id
            payment.save()

            transaction.status = "SUCCESS"
            transaction.signature = signature
            transaction.save()


            user.is_premium = True
            user.premium_expiry = timezone.now() + datetime.timedelta(days=30)
            user.save()

            logger.info(f"Payment successful for user {user.email}: {payment.payment_id}. Premium until {user.premium_expiry}")
            messages.success(request, f"Payment successful! You are now a premium user until {user.premium_expiry.strftime('%Y-%m-%d')}.")
            return render(request, 'payment_success.html', {'payment': payment})

        except razorpay.errors.SignatureVerificationError as e:
            logger.error(f"Payment signature verification failed: {str(e)}")
            messages.error(request, "Payment verification failed. Please contact support.")
        except Transaction.DoesNotExist:
            logger.error(f"Transaction not found for order_id: {order_id}")
            messages.error(request, "Payment record not found. Please contact support.")
        except Exception as e:
            logger.error(f"Unexpected error in payment_success: {str(e)}")
            messages.error(request, "An unexpected error occurred. Please contact support.")

        return render(request, 'payment_failed.html')

    return HttpResponseBadRequest("Invalid request")


@login_required
def check_premium_status(request):
    return JsonResponse({'is_premium': request.user.is_premium})