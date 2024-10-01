from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.urls import reverse


class User(AbstractUser):
    email = models.EmailField(unique=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    is_premium = models.BooleanField(default=False)
    premium_expiry = models.DateTimeField(null=True, blank=True)

    def update_premium_status(self):
        if self.premium_expiry and timezone.now() > self.premium_expiry:
            self.is_premium = False
            self.premium_expiry = None
            self.save()

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"


class Otp(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    expiry_time = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expiry_time

    def __str__(self):
        return f"{self.email} - {self.otp}"

    class Meta:
        verbose_name = "Otp"
        verbose_name_plural = "Otps"

class Community(models.Model):
    email = models.EmailField(unique=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
    
class Feedback(models.Model):
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message
    
class StartupIdea(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    idea = models.TextField()
    analysis = models.TextField()
    scores = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_public = models.BooleanField(default=False)
    upvotes = models.ManyToManyField(User, related_name='upvoted_ideas', blank=True)
    summary = models.CharField(max_length=255, null=True, blank=True)

    def upvote_count(self):
        return self.upvotes.count()

    def __str__(self):
        return f"{self.user.email}'s idea: {self.idea[:50]}..."

    class Meta:
        verbose_name = "Startup Idea"
        verbose_name_plural = "Startup Ideas"

class Comment(models.Model):
    startup_idea = models.ForeignKey(StartupIdea, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')

    def __str__(self):
        return f"Comment by {self.user.email} on {self.startup_idea}"

    class Meta:
        verbose_name = "Comment"
        verbose_name_plural = "Comments"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    content = models.TextField()
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True, related_name='notification')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.user.email}: {self.content[:50]}..."

    def get_absolute_url(self):
        return reverse('chat:public_idea_detail', kwargs={'idea_id': self.comment.startup_idea.id}) + f'#comment-{self.comment.id}'



class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    payment_id = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=20)
    order_id = models.CharField(max_length=100)
    signature = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.payment_id}"
    

class Transaction(models.Model):
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='transaction')
    order_id = models.CharField(max_length=100, unique=True)
    signature = models.CharField(max_length=200)
    status = models.CharField(max_length=20, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.payment.user.email} - {self.order_id}"
    

class StartupPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='startup_plans')
    startup_idea = models.CharField(max_length=255)
    description = models.TextField()
    personal_goals = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s plan: {self.startup_idea}"

class Module(models.Model):
    startup_plan = models.ForeignKey(StartupPlan, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    order = models.IntegerField()
    description = models.CharField(max_length=2005)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.startup_plan.startup_idea} - Module: {self.title}"

class Task(models.Model):
    module = models.ForeignKey(Module, related_name='tasks', on_delete=models.CASCADE)
    description = models.TextField()
    order = models.IntegerField()
    is_completed = models.BooleanField(default=False)

class Todo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    description = models.TextField()
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
