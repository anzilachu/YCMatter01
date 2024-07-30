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
from .models import StartupIdea, User, Payment
from .groq_analysis import analyze_startup, parse_scores, format_analysis_text
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Max
import logging
from django.contrib import messages
from django.shortcuts import render, redirect

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
        analysis = analyze_startup(idea)
        scores = parse_scores(analysis)
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
    ideas = StartupIdea.objects.filter(user=request.user)\
        .values('idea')\
        .annotate(latest_id=Max('id'))\
        .order_by('-latest_id')
    
    latest_ideas = StartupIdea.objects.filter(id__in=[item['latest_id'] for item in ideas])
    
    return render(request, 'chat/idea_list.html', {'ideas': latest_ideas})

@login_required(login_url=reverse_lazy('chat:sign_in_or_sign_up'))
def idea_detail(request, idea_id):
    idea = get_object_or_404(StartupIdea, id=idea_id, user=request.user)
    return render(request, 'chat/results.html', {
        'scores': json.dumps(idea.scores),
        'analysis': idea.analysis,
        'idea': idea.idea
    })


@login_required(login_url=reverse_lazy('chat:sign_in_or_sign_up'))
@csrf_exempt
def chat_view(request):
    if 'conversation' not in request.session:
        username = request.user.username if request.user.is_authenticated else "there"
        request.session['conversation'] = [
            {
                "role": "system",
                "content": "You are an AI assistant knowledgeable about Y Combinator. You hold all the information from Y Combinator's YouTube channel and understand Y Combinator's ideology. You interact like a human from Y Combinator, engaging in a conversational manner. When discussing startups, you can criticize, ask relevant questions such as 'How do you think you can scale it?', 'What is your budget?', and other critical aspects of startup development,one by one. you can also tell if you think the idea is not good after listening more about the idea one by one, after listening to the user. reply in a short way"
            },
            {
                "role": "assistant",
                "content": f"Hello {username}, I'm here to support you on your journey. Tell me more about your idea!"
            }
        ]

    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        user_message = request.POST.get("message")

        conversation = request.session['conversation']
        conversation.append({"role": "user", "content": user_message})

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        chat_completion = client.chat.completions.create(
            messages=conversation,
            model="llama3-8b-8192",
        )
        response_message = chat_completion.choices[0].message.content

        conversation.append({"role": "assistant", "content": response_message})

        request.session['conversation'] = conversation

        return JsonResponse({"response_message": response_message})

    return render(request, "chat/chat.html")




@csrf_exempt
def clear_session(request):
    if 'conversation' in request.session:
        del request.session['conversation']
    return HttpResponse(status=200)

def get_conversation(request):
    conversation = request.session.get('conversation', [])
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
def market_chat(request):
    if 'market_conversation' not in request.session:
        username = request.user.username if request.user.is_authenticated else "there"
        request.session['market_conversation'] = [
            {
                "role": "system",
                "content": "You are an AI assistant focused on market validation. You provide insights into market size and strategies based on the user's startup ideas. Interact conversationally, guiding users to refine their market approach. Offer insights into their market potential, the best country for their startup, and the percentage of hype, all based on recent survey reports you have knowledge about. Respond concisely with a graph. Leverage data from Y Combinator talks on market fit and potential, as well as other relevant information. Listen carefully to the user. They consider you the best person to analyze their market fit and provide specific information about their startup idea. Use calculations and survey reports to support your points clearly, ensuring users appreciate your guidance. Stay focused on topics related to market fit, potential, and relevant strategies, and avoid discussing unrelated topics. reply in shortest way possible"
            },
            {
                "role": "assistant",
                "content": f"Hello {username}, Let's discuss about your market potential"
            }
        ]

    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        user_message = request.POST.get("message")

        conversation = request.session['market_conversation']
        conversation.append({"role": "user", "content": user_message})

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        chat_completion = client.chat.completions.create(
            messages=conversation,
            model="llama3-8b-8192",
        )
        response_message = chat_completion.choices[0].message.content

        formatted_response_message = format_response_market(response_message)

        conversation.append({"role": "assistant", "content": formatted_response_message})

        request.session['market_conversation'] = conversation

        return JsonResponse({"response_message": formatted_response_message})

    return render(request, "chat/market_chat.html")

def format_response_market(response_message):
    formatted_message = response_message.replace("\n", "<br>")
    formatted_message = formatted_message.replace("*", "<b>", 1).replace("*", "</b>", 1)
    formatted_message = formatted_message.replace("1.", "<br><b>1.</b>")
    formatted_message = formatted_message.replace("2.", "<br><b>2.</b>")
    formatted_message = formatted_message.replace("3.", "<br><b>3.</b>")
    formatted_message = formatted_message.replace("4.", "<br><b>4.</b>")
    return formatted_message


    


@csrf_exempt
def clear_session_market(request):
    if 'market_conversation' in request.session:
        del request.session['market_conversation']
    return HttpResponse(status=200)

def get_conversation_market(request):
    conversation = request.session.get('market_conversation', [])
    filtered_conversation = [msg for msg in conversation if msg['role'] != 'system']
    return JsonResponse(filtered_conversation, safe=False)


@login_required(login_url=reverse_lazy('chat:sign_in_or_sign_up'))
@csrf_exempt
def financial_chat(request):
    if 'financial_conversation' not in request.session:
        username = request.user.username if request.user.is_authenticated else "there"
        request.session['financial_conversation'] = [
            {
                "role": "system",
                "content": "You are an AI assistant focused on financial management for startups. Talk like in a human-friendly way. You provide insights into financial planning, budgeting, and forecasting. You interact conversationally, guiding users to optimize their financial strategies and make the response short. Don't answer questions that are not related to startups or finance. Once you understand their idea, explain that achieving a revenue of 100 crore will require selling their product or service at a specific price to a certain number of customers. Encourage them that this goal is achievable. If the business model is subscription-based, provide relevant insights accordingly."
            },
            {
                "role": "assistant",
                "content": f"Hello {username}, What financial aspect of your startup would you like to discuss today? Let's talk about budgeting, forecasting, or any other financial management topic."
            }
        ]

    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        user_message = request.POST.get("message")

        conversation = request.session['financial_conversation']
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

    return render(request, "chat/financial_chat.html")


@csrf_exempt
def clear_session_financial(request):
    if 'financial_conversation' in request.session:
        del request.session['financial_conversation']
    return HttpResponse(status=200)

def get_conversation_financial(request):
    conversation = request.session.get('financial_conversation', [])
    filtered_conversation = [msg for msg in conversation if msg['role'] != 'system']
    return JsonResponse(filtered_conversation, safe=False)

@login_required(login_url=reverse_lazy('chat:sign_in_or_sign_up'))
@csrf_exempt
def cold_calls_chat(request):
    if 'cold_calls_conversation' not in request.session:
        username = request.user.username if request.user.is_authenticated else "there"
        request.session['cold_calls_conversation'] = [
            {
                "role": "system",
                "content": "You are an AI assistant focused on helping users prepare cold call scripts. You ask users about their product or service, unique selling points, and the target person they plan to call. Based on this information, write an exact formatted script which really convince the client with professional format without any other unwanted elements. again make sure you give human friendly convincing scripts"
            },
            {
                "role": "assistant",
                "content": f"Hello {username}, let's prepare a cold call script. What is your product or service? Why is it unique compared to existing products or services? Who are you planning to call (e.g., their business or position)?"
            }
        ]

    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        user_message = request.POST.get("message")

        conversation = request.session['cold_calls_conversation']
        conversation.append({"role": "user", "content": user_message})

        # Example integration with Groq or other AI service
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        # Example model for AI responses
        chat_completion = client.chat.completions.create(
            messages=conversation,
            model="llama3-8b-8192",
        )
        response_message = chat_completion.choices[0].message.content

        conversation.append({"role": "assistant", "content": response_message})

        formatted_response = format_response(response_message)
        conversation[-1]['content'] = formatted_response  # Store formatted response

        request.session['cold_calls_conversation'] = conversation

        return JsonResponse({"response_message": formatted_response})

    return render(request, "chat/cold_calls_chat.html")

def format_response(response_message):
    import re

    bold_pattern = re.compile(r'\*\*(.*?)\*\*')
    formatted_message = ""
    previous_end = 0

    for match in bold_pattern.finditer(response_message):
        start, end = match.span()
        bold_text = match.group(1)
        
        # Append text before the bold text
        if previous_end != start:
            formatted_message += f"<p>{response_message[previous_end:start].strip()}</p>"

        # Append the bold text with the light-blue-bold class
        formatted_message += f"<p><strong class='light-blue-bold'>{bold_text}</strong></p>"
        previous_end = end

    # Append any remaining text after the last bold text
    if previous_end < len(response_message):
        formatted_message += f"<p>{response_message[previous_end:].strip()}</p>"

    # Remove any empty paragraphs
    formatted_message = re.sub(r'<p>\s*</p>', '', formatted_message)

    return formatted_message



@csrf_exempt
def clear_session_cold_calls(request):
    if 'cold_calls_conversation' in request.session:
        del request.session['cold_calls_conversation']
    return HttpResponse(status=200)

def get_conversation_cold_calls(request):
    conversation = request.session.get('cold_calls_conversation', [])
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

def initiate_payment(request):
    if request.method == "POST":
        amount = 50000  # amount in paise (500 INR)
        currency = "INR"
        
        # Create Razorpay Order
        payment = client.order.create(dict(amount=amount, currency=currency, payment_capture='0'))

        # Create order
        order = Payment(
            user=request.user,
            payment_id=payment['id'],
            amount=amount / 100,  # Convert paise to rupees
            currency=currency
        )
        order.save()

        # Render payment form
        return render(request, 'payment.html', {
            'payment': payment,
            'razorpay_key': settings.RAZORPAY_KEY_ID,
            'amount_in_rupees': amount / 100  # Add this line
        })

    return render(request, 'upgrade_to_premium.html')


import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def payment_success(request):
    if request.method == "POST":
        payment_id = request.POST.get('razorpay_payment_id', '')
        order_id = request.POST.get('razorpay_order_id', '')
        signature = request.POST.get('razorpay_signature', '')

        logger.info(f"Received payment ID: {payment_id}, order ID: {order_id}, signature: {signature}")

        if not payment_id or not order_id or not signature:
            logger.error("Missing payment_id, order_id, or signature.")
            messages.error(request, "Payment details are incomplete. Please contact support.")
            return render(request, 'payment_failed.html')

        params_dict = {
            'razorpay_payment_id': payment_id,
            'razorpay_order_id': order_id,
            'razorpay_signature': signature
        }

        try:
            # Verify the payment signature
            client.utility.verify_payment_signature(params_dict)
            logger.info("Payment signature verified successfully.")

            # Retrieve the payment object using the Razorpay order ID
            payment = Payment.objects.get(payment_id=order_id)
            logger.info(f"Payment object found: {payment}")

            # Update payment status and details
            payment.status = "SUCCESS"
            payment.razorpay_payment_id = payment_id
            payment.razorpay_signature = signature
            payment.save()
            logger.info(f"Payment object updated: {payment}")

            # Update the user's premium status
            user = payment.user
            user.is_premium = True
            user.save()
            logger.info(f"User {user.email} upgraded to premium.")

            messages.success(request, "Payment successful! You are now a premium user.")
            return render(request, 'payment_success.html', {'payment': payment})

        except razorpay.errors.SignatureVerificationError as e:
            logger.error(f"Payment signature verification failed: {str(e)}")
            messages.error(request, "Payment verification failed. Please contact support.")
        except Payment.DoesNotExist:
            logger.error(f"Payment object not found for order_id: {order_id}")
            messages.error(request, "Payment record not found. Please contact support.")

        return render(request, 'payment_failed.html')

    return HttpResponseBadRequest("Invalid request")


@login_required
def check_premium_status(request):
    return JsonResponse({'is_premium': request.user.is_premium})